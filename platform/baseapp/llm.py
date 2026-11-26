"""OpenAI-compatible chat completions over httpx. No SDK."""
import json
import re
import time

import httpx

from .config import ModelEndpoint

FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)
THINK = re.compile(r"<think>.*?</think>\s*", re.S)


class ModelError(Exception):
    pass


def _tokens(body: dict, content: str) -> int:
    """Tokens the call used, from usage; estimated at 4 characters a token if the server sends none."""
    usage = body.get("usage") if isinstance(body, dict) else None
    if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
        return usage["total_tokens"]
    return max(1, len(content) // 4)


async def _post(client: httpx.AsyncClient, endpoint: ModelEndpoint, api_key: str | None, payload: dict,
                tier: str, timeout: float) -> tuple[str, int, int]:
    if not endpoint.configured:
        raise ModelError(f"the {tier} model is not configured; set LLM_{tier.upper()}_URL and LLM_{tier.upper()}_MODEL")
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
        body = response.json()
        content = body["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise ModelError(f"the {tier} model sent a reply in an unexpected shape") from None
    return THINK.sub("", content).strip(), ms, _tokens(body, content)


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
) -> tuple[dict, int, int]:
    """One structured answer: (the parsed JSON, model ms, tokens used)."""
    payload = {
        "model": endpoint.model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
    }
    if not reasoning:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    content, ms, tokens = await _post(client, endpoint, api_key, payload, tier, timeout)
    fenced = FENCE.match(content)
    if fenced:
        content = fenced.group(1)
    try:
        return json.loads(content), ms, tokens
    except ValueError:
        raise ModelError(f"the {tier} model did not return JSON: {content[:120]!r}") from None


async def complete_text(
    client: httpx.AsyncClient,
    endpoint: ModelEndpoint,
    api_key: str | None,
    messages: list[dict],
    *,
    tier: str,
    max_tokens: int = 256,
    timeout: float = 60.0,
) -> tuple[str, int, int]:
    """A short plain-text answer, used by the status page: (text, model ms, tokens used)."""
    payload = {
        "model": endpoint.model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    return await _post(client, endpoint, api_key, payload, tier, timeout)
