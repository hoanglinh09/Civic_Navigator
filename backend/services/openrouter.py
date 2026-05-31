from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx

from .. import config


class OpenRouterError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    if not config.OPENROUTER_API_KEY:
        return {}
    return {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": config.SERVER_REFERER,
        "X-Title": config.SERVER_TITLE,
        "Content-Type": "application/json",
    }


async def chat_completion(messages: list[dict], *, model: Optional[str] = None, stream: bool = False, max_tokens: int = 1200, temperature: float = 0.2) -> Any:
    if not config.OPENROUTER_API_KEY:
        raise OpenRouterError("OPENROUTER_API_KEY not set")

    payload = {
        "model": model or config.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }

    url = f"{config.OPENROUTER_BASE_URL}/chat/completions"
    async with httpx.AsyncClient(timeout=60.0) as client:
        if not stream:
            r = await client.post(url, headers=_headers(), json=payload)
            r.raise_for_status()
            return r.json()

        r = await client.post(url, headers=_headers(), json=payload)
        r.raise_for_status()
        return r


async def stream_text(messages: list[dict], *, model: Optional[str] = None, max_tokens: int = 1200, temperature: float = 0.2) -> AsyncIterator[str]:
    """Yields delta content tokens from OpenRouter SSE stream."""

    r = await chat_completion(messages, model=model, stream=True, max_tokens=max_tokens, temperature=temperature)
    assert isinstance(r, httpx.Response)

    async for line in r.aiter_lines():
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            break
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            continue
        delta = (((obj.get("choices") or [{}])[0]).get("delta") or {}).get("content")
        if delta:
            yield delta


def extract_message_content(resp_json: dict) -> str:
    try:
        return resp_json["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        raise OpenRouterError(f"Unexpected OpenRouter response: {e}")
