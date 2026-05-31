from __future__ import annotations

import json
from typing import Any

from .openrouter import extract_message_content, chat_completion


def _clean_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.removeprefix("```json").removeprefix("```").strip()
        if t.endswith("```"):
            t = t[: -3].strip()
    return t


async def call_vision_json(screenshot_b64: str, prompt: str, *, model: str | None = None) -> Any:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    resp = await chat_completion(messages, model=model, stream=False, max_tokens=1200, temperature=0.2)
    content = extract_message_content(resp)
    clean = _clean_json(content)
    return json.loads(clean)
