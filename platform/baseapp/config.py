import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


JSON_MODES = ("schema", "object", "prompt")


@dataclass(frozen=True)
class ModelEndpoint:
    """json_mode is how answers are asked for: schema (response_format json_schema), object
    (json_object, with the schema in the prompt) or prompt (no response_format, schema in the prompt)."""

    url: str
    model: str
    precision: str = ""
    json_mode: str = "schema"

    def __post_init__(self):
        object.__setattr__(self, "url", self.url.strip().rstrip("/"))
        object.__setattr__(self, "model", self.model.strip())
        object.__setattr__(self, "precision", self.precision.strip())
        mode = self.json_mode.strip().lower()
        object.__setattr__(self, "json_mode", mode if mode in JSON_MODES else "schema")

    @property
    def configured(self) -> bool:
        return bool(self.url and self.model)

    @property
    def short_name(self) -> str:
        return self.model.rsplit("/", 1)[-1] if self.model else "not configured"


def app_version(env: Mapping[str, str]) -> str:
    """APP_VERSION if set, else the build number OpenShift puts in OPENSHIFT_BUILD_NAME (user-7-4 → 4)."""
    if env.get("APP_VERSION", "").strip():
        return env["APP_VERSION"].strip()
    match = re.search(r"-(\d+)$", env.get("OPENSHIFT_BUILD_NAME", "").strip())
    return match.group(1) if match else "dev"


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
    version: str = "dev"

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        return cls(
            app_dir=Path(env.get("APP_DIR") or "/opt/app-root/app"),
            port=int(env.get("APP_PORT") or 8742),
            commit=env.get("APP_COMMIT") or "dev",
            site_name=env.get("SITE_NAME") or "dCloud lab",
            mock=env.get("LLM_MOCK", "0").strip() == "1",
            api_key=env.get("LLM_API_KEY", "").strip() or None,
            fast=ModelEndpoint(env.get("LLM_FAST_URL", ""), env.get("LLM_FAST_MODEL", ""),
                               env.get("LLM_FAST_PRECISION", "FP8"), env.get("LLM_FAST_JSON", "schema")),
            smart=ModelEndpoint(env.get("LLM_SMART_URL", ""), env.get("LLM_SMART_MODEL", ""),
                                env.get("LLM_SMART_PRECISION", "NVFP4"), env.get("LLM_SMART_JSON", "schema")),
            lab_user=env.get("LAB_USER", "").strip(),
            version=app_version(env),
        )
