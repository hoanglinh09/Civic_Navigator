from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket

from ..prompts import HIGHLIGHT_TOOL_SYSTEM_PROMPT
from ...services.vision import call_vision_json


@dataclass
class HighlightResult:
    success: bool
    label: Optional[str] = None
    reason: Optional[str] = None  # element_not_found | low_confidence | error


async def highlight_tool(intent_vi: str, screenshot_b64: str, websocket: WebSocket) -> HighlightResult:
    prompt = (
        f"{HIGHLIGHT_TOOL_SYSTEM_PROMPT}\n\n"
        f"Tìm phần tử phù hợp với yêu cầu: \"{intent_vi}\"\n\n"
        "Return JSON only:\n"
        "{\n"
        "  \"found\": true/false,\n"
        "  \"element_description\": \"...\",\n"
        "  \"css_selector\": \"...\" hoặc null,\n"
        "  \"bbox\": {\"x\": 0, \"y\": 0, \"width\": 0, \"height\": 0},\n"
        "  \"label_vi\": \"...\",\n"
        "  \"confidence\": \"high\"|\"medium\"|\"low\"\n"
        "}"
    )
    try:
        result = await call_vision_json(screenshot_b64, prompt)
    except Exception:  # noqa: BLE001
        return HighlightResult(success=False, reason="error")

    found = bool(result.get("found"))
    confidence = (result.get("confidence") or "low").lower()
    if not found:
        return HighlightResult(success=False, reason="element_not_found")
    if confidence == "low":
        return HighlightResult(success=False, reason="low_confidence")

    label = (result.get("label_vi") or "Nhấn vào đây").strip()[:40]
    selector = result.get("css_selector")
    bbox = result.get("bbox")
    await websocket.send_json({"type": "inject_overlay", "selector": selector, "bbox": bbox, "label": label})
    return HighlightResult(success=True, label=label)
