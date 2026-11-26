"""Load an app folder and run one screen: inputs → hooks → knowledge → prompt → model → answer."""
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import httpx
import jinja2

from .appspec import AppSpec, load_app_spec
from .blocks import answer_problems, json_schema, placeholder_answer
from .config import Settings
from .hookrunner import Ctx, HookError, load_hooks, run_prepare
from .knowledge import KnowledgeIndex, Passage
from .llm import ModelError, complete_json
from .screens import ScreenSpec, load_screen


class RunError(Exception):
    pass


@dataclass
class Runtime:
    settings: Settings
    spec: AppSpec
    screens: dict[str, ScreenSpec]
    indexes: dict[str, KnowledgeIndex]
    hooks: ModuleType | None
    prompts: jinja2.Environment


@dataclass
class RunResult:
    answer: dict
    sources: list[Passage]
    prompt: str
    tier: str
    model_name: str
    model_ms: int | None
    total_ms: int
    mocked: bool


def load_runtime(settings: Settings) -> Runtime:
    """Raises AppSpecError, ScreenError or HookError with a message naming the file and the fix."""
    app_dir = Path(settings.app_dir)
    spec = load_app_spec(app_dir)
    screens = {name: load_screen(app_dir, name) for name in spec.screens}
    indexes = {name: KnowledgeIndex.build(s.knowledge) for name, s in screens.items()}
    prompts = jinja2.Environment(
        loader=jinja2.FileSystemLoader(app_dir / "prompts"),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    return Runtime(settings, spec, screens, indexes, load_hooks(app_dir), prompts)


def _example_inputs(rt: Runtime, screen: ScreenSpec, example: int | None) -> dict[str, str]:
    if example is None:
        return {}
    if not 0 <= example < len(screen.examples):
        raise RunError(f"screen {screen.name} has no example {example}")
    values = dict(screen.examples[example].inputs)
    root = Path(rt.settings.app_dir).resolve()
    for spec in screen.inputs:
        if spec.type == "file" and values.get(spec.name):
            path = (root / values[spec.name]).resolve()
            if root not in path.parents or not path.is_file():
                raise RunError(f"example file app/{values[spec.name]} is missing")
            values[spec.name] = path.read_text(encoding="utf-8", errors="replace")
    return values


def _prompt_vars(screen: ScreenSpec, values: dict[str, str]) -> dict:
    out = {}
    for spec in screen.inputs:
        value = values.get(spec.name, "")
        if spec.type == "toggle":
            out[spec.name] = str(value).lower() in ("1", "true", "on", "yes")
        else:
            out[spec.name] = str(value)
    return out


def _render(rt: Runtime, screen: ScreenSpec, variables: dict) -> str:
    try:
        return rt.prompts.get_template(f"{screen.name}.md").render(**variables)
    except jinja2.UndefinedError as exc:
        names = ", ".join(sorted(variables))
        raise RunError(f"app/prompts/{screen.name}.md: {exc.message}; use one of {names}") from None
    except jinja2.TemplateError as exc:
        raise RunError(f"app/prompts/{screen.name}.md line {getattr(exc, 'lineno', '?')}: {exc}") from None


def _sources_block(sources: list[Passage]) -> str:
    lines = ["", "", "Source passages. When a step comes from one, set its source to the [n] label."]
    for i, p in enumerate(sources, 1):
        title = f"{p.source} — {p.heading}" if p.heading else p.source
        lines.append(f"[{i}] {title}\n{p.text}")
    return "\n".join(lines)


async def run_screen(rt: Runtime, screen: ScreenSpec, inputs: dict[str, str], example: int | None,
                     client: httpx.AsyncClient) -> RunResult:
    start = time.perf_counter()
    values = _example_inputs(rt, screen, example)
    values.update({k: v for k, v in inputs.items() if v not in (None, "")})
    for spec in screen.inputs:
        if not spec.optional and spec.type != "toggle" and not str(values.get(spec.name, "")).strip():
            raise RunError(f"{spec.label} is required")

    variables = _prompt_vars(screen, values)
    ctx = Ctx(app_dir=Path(rt.settings.app_dir), inputs=dict(variables), screen=screen.name,
              site=rt.spec.site or rt.settings.site_name)
    try:
        extra = run_prepare(rt.hooks, ctx)
    except HookError as exc:
        raise RunError(str(exc)) from None
    clash = set(extra) & set(variables)
    if clash:
        raise RunError(f"app/hooks.py: prepare(ctx) returned {', '.join(sorted(clash))}, which is already an input name")
    variables.update(extra)

    query = " ".join(str(v)[:1000] for v in variables.values() if isinstance(v, str))
    sources = rt.indexes[screen.name].search(query, k=4) if screen.knowledge else []
    variables.update(site=ctx.site, app_name=rt.spec.name)
    prompt = _render(rt, screen, variables) + (_sources_block(sources) if sources else "")

    endpoint = rt.settings.smart if screen.model == "smart" else rt.settings.fast
    if rt.settings.mock:
        mock = screen.examples[example].mock if example is not None else None
        answer, model_ms = (mock or placeholder_answer(screen.answer)), None
    else:
        system = (f"You are {rt.spec.name}, an assistant running on-site at {ctx.site}. "
                  "Reply with one JSON object that matches the schema. Be short and specific.")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        try:
            answer, model_ms = await complete_json(
                client, endpoint, rt.settings.api_key, messages, json_schema(screen.answer),
                reasoning=screen.reasoning, tier=screen.model)
        except ModelError as exc:
            raise RunError(str(exc)) from None

    problems = answer_problems(screen.answer, answer)
    if problems:
        raise RunError("the answer did not fit the screen: " + "; ".join(problems))
    return RunResult(
        answer=answer, sources=sources, prompt=prompt, tier=screen.model,
        model_name=endpoint.model, model_ms=model_ms,
        total_ms=round((time.perf_counter() - start) * 1000), mocked=rt.settings.mock,
    )
