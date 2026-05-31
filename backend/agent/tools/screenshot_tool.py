from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket


@dataclass
class ScreenshotPayload:
    b64: str
    width: int
    height: int
    url: str


async def request_screenshot(websocket: WebSocket) -> None:
    await websocket.send_json({"type": "request_screenshot"})


async def screenshot_tool(websocket: WebSocket, wait_for_screenshot) -> Optional[ScreenshotPayload]:
    """Ask panel to capture a screenshot and await payload via provided waiter."""
    await request_screenshot(websocket)
    msg = await wait_for_screenshot(timeout_s=25)
    if msg is None:
        return None
    return ScreenshotPayload(b64=msg.data, width=msg.width, height=msg.height, url=msg.url)
