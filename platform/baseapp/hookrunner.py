"""Load the app's optional hooks.py and run prepare(ctx) before each answer."""
import csv
import importlib.util
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType


class HookError(Exception):
    pass


@dataclass
class Ctx:
    """What hooks.py sees: the screen's inputs plus read-only helpers for app/data/."""

    app_dir: Path
    inputs: dict
    screen: str = ""
    site: str = ""
    extra: dict = field(default_factory=dict)

    def _data_path(self, name: str) -> Path:
        root = (Path(self.app_dir) / "data").resolve()
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file():
            raise HookError(f'ctx.data("{name}"): no such file in app/data/')
        return path

    def data(self, name: str) -> list[dict]:
        with self._data_path(name).open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def text(self, name: str) -> str:
        return self._data_path(name).read_text(encoding="utf-8", errors="replace")


def load_hooks(app_dir: Path) -> ModuleType | None:
    path = Path(app_dir) / "hooks.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("app_hooks", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise HookError(_describe(exc, "importing app/hooks.py")) from None
    return module


def _describe(exc: Exception, doing: str) -> str:
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename.endswith("hooks.py")]
    where = f"app/hooks.py line {frames[-1].lineno}" if frames else "app/hooks.py"
    return f"{where}: {type(exc).__name__}: {exc} (while {doing})"


def run_prepare(hooks: ModuleType | None, ctx: Ctx) -> dict:
    if hooks is None or not hasattr(hooks, "prepare"):
        return {}
    try:
        result = hooks.prepare(ctx)
    except HookError:
        raise
    except Exception as exc:
        raise HookError(_describe(exc, "running prepare(ctx)")) from None
    if not isinstance(result, dict):
        raise HookError(f"app/hooks.py: prepare(ctx) must return a dict, got {type(result).__name__}")
    return result
