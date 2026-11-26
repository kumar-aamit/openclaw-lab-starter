"""OpenAI-compatible chat completions over httpx. No SDK."""
import json
import re
import time

import httpx

from .config import ModelEndpoint

FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)


class ModelError(Exception):
    pass


async def complete_json(
    client: httpx.AsyncClient,
    endpoint: ModelEndpoint,
    api_key: str | None,
    messages: list[dict],
    schema: dict,
    *,
    reasoning: bool,
    tier: str,
    timeout: float = 120.0,
) -> tuple[dict, int]:
    if not endpoint.configured:
        raise ModelError(f"the {tier} model is not configured; set LLM_{tier.upper()}_URL and LLM_{tier.upper()}_MODEL")
    payload = {
        "model": endpoint.model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
    }
    if not reasoning:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    start = time.perf_counter()
    try:
        response = await client.post(f"{endpoint.url}/chat/completions", json=payload, headers=headers, timeout=timeout)
    except httpx.TimeoutException:
        raise ModelError(f"the {tier} model did not answer within {timeout:g} s") from None
    except httpx.HTTPError as exc:
        raise ModelError(f"the {tier} model is unreachable ({type(exc).__name__})") from None
    ms = round((time.perf_counter() - start) * 1000)
    if response.status_code != 200:
        raise ModelError(f"the {tier} model returned HTTP {response.status_code}: {response.text[:200]}")
    try:
        content = response.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise ModelError(f"the {tier} model sent a reply in an unexpected shape") from None
    content = content.strip()
    fenced = FENCE.match(content)
    if fenced:
        content = fenced.group(1)
    try:
        return json.loads(content), ms
    except ValueError:
        raise ModelError(f"the {tier} model did not return JSON: {content[:120]!r}") from None
