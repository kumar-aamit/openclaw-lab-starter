"""`make check`: everything an app must pass before it is pushed."""
import ast
import logging
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
from fastapi.testclient import TestClient  # noqa: E402

from .appspec import AppSpecError
from .config import Settings
from .hookrunner import HookError
from .pin import tree_hash
from .runner import load_runtime
from .screens import ScreenError

URL = re.compile(r"https?://[^\s\"'<>)\]]+")
WHITE_TEXT_MIN = 4.5


def luminance(hex_color: str) -> float:
    rgb = [int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_with_white(hex_color: str) -> float:
    return 1.05 / (luminance(hex_color) + 0.05)


def authored_files(app_dir: Path) -> list[Path]:
    files = [app_dir / "app.yaml", app_dir / "hooks.py"]
    files += sorted((app_dir / "screens").glob("*.yaml")) + sorted((app_dir / "prompts").glob("*.md"))
    return [f for f in files if f.is_file()]


def external_urls(app_dir: Path) -> list[str]:
    problems = []
    for f in authored_files(app_dir):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for url in URL.findall(line):
                problems.append(f"app/{f.relative_to(app_dir).as_posix()} line {n}: {url} is an outside "
                                f"address; the app must work with no internet, so remove it")
    return problems


def hook_imports(app_dir: Path) -> list[str]:
    path = app_dir / "hooks.py"
    if not path.is_file():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"app/hooks.py line {exc.lineno}: {exc.msg}"]
    problems = []
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            top = name.split(".")[0]
            if top not in sys.stdlib_module_names:
                problems.append(f"app/hooks.py line {node.lineno}: {top} is not in the Python standard library; "
                                f"hooks.py can only use the standard library")
    return problems


def bad_citations(screen, result: dict) -> list[str]:
    found = len(result["sources"])
    bad = []
    for block in screen.answer:
        if block.kind != "checklist":
            continue
        for item in result["answer"].get(block.key) or []:
            ref = str(item.get("source") or "")
            match = re.fullmatch(r"\[(\d+)\]", ref.strip())
            if ref.strip() and (not match or not 1 <= int(match.group(1)) <= found):
                bad.append(ref)
    return bad


def default_platform_dir() -> Path | None:
    if os.environ.get("PLATFORM_DIR"):
        return Path(os.environ["PLATFORM_DIR"])
    candidate = Path(__file__).resolve().parent.parent
    return candidate if (candidate / "PIN").is_file() else None


def main(app_dir: Path | None = None, platform_dir: Path | None = None) -> int:
    logging.getLogger("baseapp").disabled = True
    from .main import create_app

    app_dir = Path(app_dir or os.environ.get("APP_DIR", "app"))
    platform_dir = platform_dir or default_platform_dir()
    failures = 0

    def ok(what):
        print(f"ok    {what}")

    def fail(what):
        nonlocal failures
        failures += 1
        print(f"FAIL  {what}")

    if platform_dir is not None and not (platform_dir / "PIN").is_file():
        print("skip  platform/PIN not found, so platform/ is not compared; lab users' repos get one when seeded")
    elif platform_dir is not None:
        pin = (platform_dir / "PIN").read_text().strip()
        if tree_hash(platform_dir / "baseapp") == pin:
            ok("platform/ is unchanged")
        else:
            fail("platform/ was changed; only edit app/. Restore it with: git checkout -- platform/")

    for problem in external_urls(app_dir):
        fail(problem)
    import_problems = hook_imports(app_dir)
    for problem in import_problems:
        fail(problem)
    if import_problems:
        return finish(failures)

    settings = Settings.from_env({**os.environ, "APP_DIR": str(app_dir), "LLM_MOCK": "1"})
    try:
        rt = load_runtime(settings)
    except (AppSpecError, ScreenError, HookError) as exc:
        fail(str(exc))
        return finish(failures)
    ok(f"app.yaml and {len(rt.screens)} screen file(s) load")

    ratio = contrast_with_white(rt.spec.brand)
    if ratio >= WHITE_TEXT_MIN:
        ok(f"brand {rt.spec.brand} is readable under white text ({ratio:.1f}:1)")
    else:
        fail(f"app/app.yaml: brand {rt.spec.brand} is too light for white text ({ratio:.1f}:1, needs "
             f"{WHITE_TEXT_MIN}:1); pick a darker color")

    client = TestClient(create_app(settings))
    for name, screen in rt.screens.items():
        page = client.get(f"/s/{name}")
        if page.status_code != 200:
            fail(f"{name}: the screen page answered HTTP {page.status_code}")
        if not screen.examples:
            fail(f"{name}: add at least one example to app/screens/{name}.yaml so the screen can be tried")
        for i, ex in enumerate(screen.examples):
            r = client.post(f"/api/screens/{name}/run", json={"example": i})
            html = client.post(f"/s/{name}/run", data={"example": str(i)})
            if r.status_code != 200:
                fail(f'{name}: example "{ex.label}": {r.json().get("error", r.text)}')
            elif html.status_code != 200 or "notice-fail" in html.text:
                fail(f'{name}: example "{ex.label}" did not render; HTTP {html.status_code}')
            elif bad := bad_citations(screen, r.json()):
                fail(f'{name}: example "{ex.label}": mock cites {", ".join(bad)} but the knowledge search '
                     f'found {len(r.json()["sources"])} passage(s); cite one of those or leave source empty')
            else:
                ok(f'{name}: example "{ex.label}" runs and renders')
    return finish(failures)


def finish(failures: int) -> int:
    if failures:
        print(f"\n{failures} problem(s). Fix them and run make check again.")
        return 1
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
