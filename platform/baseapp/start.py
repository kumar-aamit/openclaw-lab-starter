"""The start page: use cases to copy a prompt from, and which steps of a brief the app already has."""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from markupsafe import Markup, escape

from .screens import ScreenSpec

USECASES = Path(__file__).parent / "usecases.yaml"
BLOCK_ORDER = ("score", "text", "table", "checklist")
BLOCK_NAMES = {"score": "Score", "text": "Text", "table": "Table", "checklist": "Checklist"}


@dataclass(frozen=True)
class Step:
    name: str
    prompt: str
    adds: tuple[str, ...]
    done_when: tuple[str, ...] = ()
    see: str = ""


@dataclass(frozen=True)
class UseCase:
    id: str
    name: str
    screen: str
    inputs: tuple[str, ...]
    steps: tuple[Step, ...]
    industry: str = ""
    own: bool = False
    sample: dict = field(default_factory=dict)

    @property
    def guided(self) -> bool:
        return len(self.steps) > 1


def _step(raw: dict) -> Step:
    return Step(name=raw["name"], prompt=raw["prompt"].strip(), adds=tuple(raw["adds"]),
                done_when=tuple(raw.get("done_when", ())), see=raw.get("see", ""))


@lru_cache(maxsize=1)
def use_cases() -> tuple[UseCase, ...]:
    cases = []
    for raw in yaml.safe_load(USECASES.read_text(encoding="utf-8")):
        steps = [_step(s) for s in raw["steps"]] if "steps" in raw else \
            [Step(name="Build", prompt=raw["prompt"].strip(), adds=tuple(raw["blocks"]))]
        cases.append(UseCase(id=raw["id"], name=raw["name"], screen=raw["screen"], inputs=tuple(raw["inputs"]),
                             steps=tuple(steps), industry=raw.get("industry", ""), own=raw.get("own", False),
                             sample=raw.get("sample", {})))
    return tuple(cases)


def _has(screens: list[ScreenSpec], need: str) -> bool:
    if need == "screen":
        return bool(screens)
    if need == "knowledge":
        return any(s.knowledge for s in screens)
    return any(b.kind == need for s in screens for b in s.answer)


def steps_done(case: UseCase, screens: list[ScreenSpec]) -> int:
    if not case.guided:
        return 0
    done = 0
    for step in case.steps:
        if not all(_has(screens, need) for need in step.done_when):
            break
        done += 1
    return done


def preview(case: UseCase, view: int) -> list[dict]:
    """The answer blocks the preview draws for the step in view: shown, and new in that step."""
    if case.guided:
        shown = {b for s in case.steps[:view + 1] for b in s.adds}
        fresh = set(case.steps[view].adds)
    else:
        shown, fresh = set(case.steps[0].adds), set()
    kinds = BLOCK_ORDER if case.own else [k for k in BLOCK_ORDER if k in shown]
    return [{"kind": k, "name": BLOCK_NAMES[k], "shown": k in shown, "fresh": k in fresh} for k in kinds]


def bold(text: str) -> Markup:
    return Markup(re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(escape(text))))
