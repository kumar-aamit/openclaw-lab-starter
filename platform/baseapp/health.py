import asyncio
import time
from dataclasses import dataclass

import httpx

from .config import ModelEndpoint, Settings


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool | None  # None = skipped, not tested
    detail: str
    ms: int | None


async def check_model(
    name: str,
    endpoint: ModelEndpoint,
    api_key: str | None,
    client: httpx.AsyncClient,
    timeout: float = 3.0,
) -> CheckResult:
    if not endpoint.configured:
        return CheckResult(name, False, "not configured", None)
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    start = time.perf_counter()
    try:
        response = await client.get(f"{endpoint.url}/models", headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        return CheckResult(name, False, f"timeout after {timeout:g} s", None)
    except httpx.HTTPError as exc:
        return CheckResult(name, False, f"unreachable: {type(exc).__name__}", None)
    ms = round((time.perf_counter() - start) * 1000)
    if response.status_code != 200:
        return CheckResult(name, False, f"HTTP {response.status_code}", ms)
    try:
        served = {m.get("id") for m in response.json().get("data", [])}
    except (ValueError, AttributeError):
        return CheckResult(name, False, "unexpected reply from /models", ms)
    if endpoint.model not in served:
        return CheckResult(name, False, f"model {endpoint.model} not served", ms)
    return CheckResult(name, True, f"{endpoint.model} answered", ms)


async def run_checks(settings: Settings, client: httpx.AsyncClient) -> list[CheckResult]:
    if settings.mock:
        return [CheckResult(n, None, "skipped: mock mode", None) for n in ("Fast model", "Smart model")]
    return list(await asyncio.gather(
        check_model("Fast model", settings.fast, settings.api_key, client),
        check_model("Smart model", settings.smart, settings.api_key, client),
    ))
