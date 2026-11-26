import re
from dataclasses import dataclass, fields
from pathlib import Path

import yaml

ICON_DIR = Path(__file__).parent / "static" / "vendor" / "icons"
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
FILE_LABEL = "app/app.yaml"


class AppSpecError(Exception):
    pass


def available_icons() -> set[str]:
    return {p.stem for p in ICON_DIR.glob("*.svg")}


@dataclass(frozen=True)
class AppSpec:
    name: str = "Mock App"
    mark: str = ""
    brand: str = "#17202B"
    site: str | None = None
    screens: tuple[str, ...] = ()

    @property
    def mark_icon(self) -> str | None:
        return self.mark if self.mark in available_icons() else None

    @property
    def mark_letter(self) -> str:
        if len(self.mark) == 1 and self.mark.isalpha():
            return self.mark.upper()
        return (self.name[:1] or "A").upper()


def _error(where: str, problem: str) -> AppSpecError:
    return AppSpecError(f"{FILE_LABEL}: {where}: {problem}")


def load_app_spec(app_dir: Path) -> AppSpec:
    path = Path(app_dir) / "app.yaml"
    if not path.is_file():
        return AppSpec()
    text = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.MarkedYAMLError as exc:
        last_line = max((i + 1 for i, s in enumerate(text.splitlines()) if s.strip()), default=1)
        line = min(exc.problem_mark.line + 1, last_line) if exc.problem_mark else "?"
        raise _error(f"line {line}", f"{exc.problem or 'invalid YAML'}; check the indentation and brackets") from None
    except yaml.YAMLError as exc:
        raise _error("file", f"invalid YAML ({exc}); check the indentation and brackets") from None
    if data is None:
        return AppSpec()
    if not isinstance(data, dict):
        raise _error("file", "expected fields like name: and brand:; write one field per line")

    known = {f.name for f in fields(AppSpec)}
    for key in data:
        if key not in known:
            raise _error(str(key), f'unknown field "{key}"; use one of {", ".join(sorted(known))}')

    values = {}
    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
            raise _error("name", "name must be text of 1 to 40 characters; shorten it")
        values["name"] = name.strip()
    if "brand" in data:
        if data["brand"] is None:
            raise _error("brand", 'brand is empty; put the color in quotes, like brand: "#1D4ED8", '
                                  "because # without quotes starts a comment")
        brand = str(data["brand"])
        if not HEX_COLOR.match(brand):
            raise _error("brand", f'brand "{brand}" is not valid; use a hex color like "#1D4ED8"')
        values["brand"] = brand.upper()
    if "mark" in data:
        mark = str(data["mark"]).strip()
        is_letter = len(mark) == 1 and mark.isalpha()
        if not is_letter and mark not in available_icons():
            raise _error("mark", f'mark "{mark}" is not valid; use one letter or one of {", ".join(sorted(available_icons()))}')
        values["mark"] = mark
    if "site" in data:
        if not isinstance(data["site"], str) or not data["site"].strip():
            raise _error("site", 'site must be text, like "HQ data center"')
        values["site"] = data["site"].strip()
    if "screens" in data:
        screens = data["screens"] or []
        if not isinstance(screens, list) or not all(isinstance(s, str) for s in screens):
            raise _error("screens", "screens must be a list of names, like [triage]")
        values["screens"] = tuple(screens)
    return AppSpec(**values)
