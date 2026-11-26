import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelEndpoint:
    url: str
    model: str

    def __post_init__(self):
        object.__setattr__(self, "url", self.url.strip().rstrip("/"))
        object.__setattr__(self, "model", self.model.strip())

    @property
    def configured(self) -> bool:
        return bool(self.url and self.model)


@dataclass(frozen=True)
class Settings:
    app_dir: Path
    port: int
    commit: str
    site_name: str
    mock: bool
    api_key: str | None
    fast: ModelEndpoint
    smart: ModelEndpoint
    lab_user: str = ""

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        return cls(
            app_dir=Path(env.get("APP_DIR") or "/opt/app-root/app"),
            port=int(env.get("APP_PORT") or 8742),
            commit=env.get("APP_COMMIT") or "dev",
            site_name=env.get("SITE_NAME") or "dCloud lab",
            mock=env.get("LLM_MOCK", "0").strip() == "1",
            api_key=env.get("LLM_API_KEY", "").strip() or None,
            fast=ModelEndpoint(env.get("LLM_FAST_URL", ""), env.get("LLM_FAST_MODEL", "")),
            smart=ModelEndpoint(env.get("LLM_SMART_URL", ""), env.get("LLM_SMART_MODEL", "")),
            lab_user=env.get("LAB_USER", "").strip(),
        )
