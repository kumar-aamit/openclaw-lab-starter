import csv
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

INPUT_TYPES = ("text", "textarea", "select", "number", "toggle", "file")
LAYOUTS = ("review",)
PLANNED_LAYOUTS = ("workspace", "assistant")
OUTPUTS = ("json",)
PLANNED_OUTPUTS = ("stream", "chat")
BLOCK_KINDS = ("text", "score", "table", "checklist")
MODELS = ("fast", "smart")
STATUS_KINDS = ("airgap", "stored", "runs", "last", "model", "knowledge")
NAME = re.compile(r"^[a-z][a-z0-9_]*$")
SCREEN_KEYS = {"title", "description", "layout", "model", "reasoning", "inputs",
               "knowledge", "output", "answer", "examples", "status"}
INPUT_KEYS = {"name", "type", "label", "optional", "placeholder", "accept", "options", "default"}


class ScreenError(Exception):
    pass


@dataclass(frozen=True)
class InputSpec:
    name: str
    type: str
    label: str
    optional: bool = False
    placeholder: str = ""
    accept: str = ""
    choices: tuple[str, ...] = ()
    default: str = ""


@dataclass(frozen=True)
class AnswerBlock:
    kind: str
    key: str
    title: str
    columns: tuple[str, ...] = ()
    higher: str = ""  # score only: "worse" or "better" colors the value red, amber or green


@dataclass(frozen=True)
class StatusChip:
    kind: str
    label: str = ""


@dataclass(frozen=True)
class Example:
    label: str
    inputs: dict
    mock: dict | None = None


@dataclass(frozen=True)
class ScreenSpec:
    name: str
    title: str
    description: str
    layout: str
    model: str
    reasoning: bool
    inputs: tuple[InputSpec, ...]
    knowledge: Path | None
    output: str
    answer: tuple[AnswerBlock, ...]
    examples: tuple[Example, ...]
    prompt_path: Path
    status: tuple[StatusChip, ...] | None = None  # None: the platform's default set


def _choices(app_dir: Path, options, where: str) -> tuple[str, ...]:
    if isinstance(options, list):
        return tuple(str(o) for o in options)
    if isinstance(options, str) and options.endswith(".csv"):
        path = (app_dir / options).resolve()
        if not path.is_file() or app_dir.resolve() not in path.parents:
            raise ScreenError(f"{where}.options: app/{options} is missing; add the CSV file or list the options")
        with path.open(newline="", encoding="utf-8") as f:
            return tuple(row[0] for i, row in enumerate(csv.reader(f)) if i > 0 and row)
    raise ScreenError(f"{where}.options must be a list or a CSV file in data/, like data/assets.csv")


def _input(app_dir: Path, raw, where: str) -> InputSpec:
    if not isinstance(raw, dict):
        raise ScreenError(f"{where} must be a mapping like {{name: alert, type: textarea}}")
    for key in raw:
        if key not in INPUT_KEYS:
            raise ScreenError(f'{where}: unknown field "{key}"; use one of {", ".join(sorted(INPUT_KEYS))}')
    name = str(raw.get("name", ""))
    if not NAME.match(name):
        raise ScreenError(f'{where}.name "{name}" is not valid; use lowercase letters, digits and _, like alert')
    kind = str(raw.get("type", ""))
    if kind not in INPUT_TYPES:
        raise ScreenError(f'{where}.type "{kind}" is not valid; use one of {", ".join(INPUT_TYPES)}')
    choices = _choices(app_dir, raw.get("options"), where) if kind == "select" else ()
    if kind == "select" and not choices:
        raise ScreenError(f"{where}.options is empty; a select needs at least one option")
    return InputSpec(
        name=name, type=kind,
        label=str(raw.get("label") or name.replace("_", " ").capitalize()),
        optional=bool(raw.get("optional", False)),
        placeholder=str(raw.get("placeholder", "")),
        accept=str(raw.get("accept", ".txt,.log,.csv,.pdf" if kind == "file" else "")),
        choices=choices,
        default=str(raw.get("default", "")),
    )


def _block(raw, where: str) -> AnswerBlock:
    if isinstance(raw, str):
        kind, opts = raw, {}
    elif isinstance(raw, dict) and len(raw) == 1:
        kind, opts = next(iter(raw.items()))
        opts = opts or {}
    else:
        raise ScreenError(f"{where} must be a block name like score, or score: {{title: Severity}}")
    if kind not in BLOCK_KINDS:
        raise ScreenError(f'{where}: block "{kind}" is not valid; use one of {", ".join(BLOCK_KINDS)}')
    if not isinstance(opts, dict):
        raise ScreenError(f"{where}.{kind} must be a mapping like {{title: Severity}}")
    columns = tuple(str(c) for c in opts.get("columns", ()))
    if kind == "table" and not columns:
        raise ScreenError(f"{where}.table needs columns, like columns: [Technique, Evidence]")
    higher = str(opts.get("higher", ""))
    if higher and (kind != "score" or higher not in ("worse", "better")):
        raise ScreenError(f"{where}.higher: use higher: worse or higher: better, and only on a score")
    key = str(opts.get("key", kind))
    if not NAME.match(key):
        raise ScreenError(f'{where}.key "{key}" is not valid; use lowercase letters, digits and _')
    return AnswerBlock(kind=kind, key=key, title=str(opts.get("title", kind.capitalize())), columns=columns,
                       higher=higher)


def _status(raw, where: str = "status") -> tuple[StatusChip, ...]:
    kinds = ", ".join(STATUS_KINDS)
    if raw in (False, "off"):
        return ()
    if not isinstance(raw, list):
        raise ScreenError(f"{where} must be a list like [airgap, stored, runs: Reviews], or off")
    chips = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            kind, label = item, ""
        elif isinstance(item, dict) and len(item) == 1:
            kind, label = next(iter(item.items()))
            label = "" if label is None else str(label)
        else:
            raise ScreenError(f"{where}[{i}] must be a chip name like runs, or runs: Reviews to rename it")
        if kind not in STATUS_KINDS:
            raise ScreenError(f'{where}[{i}]: chip "{kind}" is not valid; use one of {kinds}')
        if len(label) > 24:
            raise ScreenError(f'{where}[{i}]: label "{label}" is longer than 24 characters; shorten it')
        chips.append(StatusChip(kind=str(kind), label=label))
    if len({c.kind for c in chips}) != len(chips):
        raise ScreenError(f"{where} lists a chip twice; list each chip once")
    return tuple(chips)


def _knowledge(app_dir: Path, value: str) -> Path:
    fix = "use a folder inside app/, like knowledge/"
    if Path(value).is_absolute():
        raise ScreenError(f'knowledge: "{value}" is an absolute path; {fix}')
    if ".." in Path(value).parts:
        raise ScreenError(f'knowledge: "{value}" uses .. to leave app/; {fix}')
    root = app_dir.resolve()
    folder = (app_dir / value).resolve()
    if folder == root:
        raise ScreenError(f'knowledge: "{value}" is app/ itself; {fix}')
    if root not in folder.parents:
        raise ScreenError(f"knowledge: app/{value} is a symlink to {folder}, outside app/; "
                          f"copy the documents into a folder inside app/ instead")
    if not folder.is_dir():
        raise ScreenError(f"knowledge: app/{value} is missing; create the folder or remove knowledge:")
    for path in sorted(folder.rglob("*")):
        if root not in path.resolve().parents:
            rel = Path(value, path.relative_to(folder)).as_posix()
            raise ScreenError(f"knowledge: app/{rel} is a symlink to {path.resolve()}, outside app/; "
                              f"copy the file into app/{Path(value).as_posix()}/ instead")
    return folder


def load_screen(app_dir: Path, name: str) -> ScreenSpec:
    app_dir = Path(app_dir)
    label = f"app/screens/{name}.yaml"
    path = app_dir / "screens" / f"{name}.yaml"
    if not path.is_file():
        raise ScreenError(f"{label} is missing; app.yaml lists screen {name}, so add that file")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ScreenError(f"{label}: invalid YAML ({exc}); check the indentation and brackets") from None
    if not isinstance(raw, dict):
        raise ScreenError(f"{label}: expected fields like title: and layout:")

    def fail(msg: str):
        raise ScreenError(f"{label}: {msg}")

    for key in raw:
        if key not in SCREEN_KEYS:
            fail(f'unknown field "{key}"; use one of {", ".join(sorted(SCREEN_KEYS))}')

    layout = str(raw.get("layout", "review"))
    if layout in PLANNED_LAYOUTS:
        fail(f'layout "{layout}" is not available in this platform version; use review')
    if layout not in LAYOUTS:
        fail(f'layout "{layout}" is not valid; use review')
    model = str(raw.get("model", "fast"))
    if model not in MODELS:
        fail(f'model "{model}" is not valid; use fast or smart')
    output = str(raw.get("output", "json"))
    if output in PLANNED_OUTPUTS:
        fail(f'output "{output}" is not available in this platform version; use json')
    if output not in OUTPUTS:
        fail(f'output "{output}" is not valid; use json')
    reasoning = raw.get("reasoning", True)
    if reasoning not in (True, False, "on", "off"):
        fail('reasoning must be on or off')

    raw_inputs = raw.get("inputs") or []
    if not isinstance(raw_inputs, list) or not raw_inputs:
        fail("inputs must list at least one input, like - {name: alert, type: textarea}")
    try:
        inputs = tuple(_input(app_dir, r, f"inputs[{i}]") for i, r in enumerate(raw_inputs))
        raw_answer = raw.get("answer") or []
        if not isinstance(raw_answer, list) or not raw_answer:
            raise ScreenError("answer must list at least one block, like [text]")
        blocks = []
        for i, r in enumerate(raw_answer):
            b = _block(r, f"answer[{i}]")
            if b.key in {x.key for x in blocks}:
                raise ScreenError(f'answer[{i}]: key "{b.key}" is used twice; add key: to one of them')
            blocks.append(b)
    except ScreenError as exc:
        fail(str(exc))

    if len({i.name for i in inputs}) != len(inputs):
        fail("two inputs share a name; give each input its own name")

    knowledge = None
    if raw.get("knowledge"):
        try:
            knowledge = _knowledge(app_dir, str(raw["knowledge"]))
        except ScreenError as exc:
            fail(str(exc))

    names = {i.name for i in inputs}
    examples = []
    for i, ex in enumerate(raw.get("examples") or []):
        if not isinstance(ex, dict) or not isinstance(ex.get("inputs"), dict):
            fail(f"examples[{i}] needs label: and inputs:")
        for key in ex["inputs"]:
            if key not in names:
                fail(f'examples[{i}].inputs: unknown input "{key}"; use one of {", ".join(sorted(names))}')
        if ex.get("mock") is not None and not isinstance(ex["mock"], dict):
            fail(f"examples[{i}].mock must be the JSON answer the mock model returns")
        examples.append(Example(label=str(ex.get("label") or f"Example {i + 1}"),
                                inputs={k: str(v) for k, v in ex["inputs"].items()},
                                mock=ex.get("mock")))

    status = None
    if "status" in raw:
        try:
            status = _status(raw["status"])
        except ScreenError as exc:
            fail(str(exc))
        if knowledge is None and any(c.kind == "knowledge" for c in status):
            fail("status lists knowledge but the screen has no knowledge: folder; add one or drop the chip")

    prompt_path = app_dir / "prompts" / f"{name}.md"
    if not prompt_path.is_file():
        raise ScreenError(f"app/prompts/{name}.md is missing; every screen needs a prompt file")

    return ScreenSpec(
        name=name,
        title=str(raw.get("title") or name.replace("_", " ").capitalize()),
        description=str(raw.get("description", "")),
        layout=layout, model=model, reasoning=reasoning in (True, "on"),
        inputs=inputs, knowledge=knowledge, output=output, answer=tuple(blocks),
        examples=tuple(examples), prompt_path=prompt_path, status=status,
    )
