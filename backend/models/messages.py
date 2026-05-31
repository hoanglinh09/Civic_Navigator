from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class BaseWSMessage(BaseModel):
    type: str


class SessionInitMessage(BaseWSMessage):
    type: Literal["session_init"]
    session_id: str
    current_url: str


class UserMessage(BaseWSMessage):
    type: Literal["user_message"]
    text: str


class UserDoneMessage(BaseWSMessage):
    type: Literal["user_done"]


class ScreenshotMessage(BaseWSMessage):
    type: Literal["screenshot"]
    data: str  # base64 PNG, no data: prefix
    width: int
    height: int
    url: str


class UISyncResponseMessage(BaseWSMessage):
    type: Literal["ui_sync_response"]
    visible_step_label: Optional[str] = None
    overlay_label: Optional[str] = None


ClientToServerMessage = SessionInitMessage | UserMessage | UserDoneMessage | ScreenshotMessage | UISyncResponseMessage


def parse_client_message(data: Any) -> ClientToServerMessage:
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError("Invalid WS message")
    t = data.get("type")
    if t == "session_init":
        return SessionInitMessage.model_validate(data)
    if t == "user_message":
        return UserMessage.model_validate(data)
    if t == "user_done":
        return UserDoneMessage.model_validate(data)
    if t == "screenshot":
        return ScreenshotMessage.model_validate(data)
    if t == "ui_sync_response":
        return UISyncResponseMessage.model_validate(data)
    raise ValueError(f"Unknown WS message type: {t}")


class StepUpdate(BaseModel):
    type: Literal["step_update"] = "step_update"
    current_step: int
    total_steps: int
    step_label: str
    action_tier: Literal["inform", "confirm", "handoff"]


class SystemStatus(BaseModel):
    type: Literal["system_status"] = "system_status"
    text: str


class AgentToken(BaseModel):
    type: Literal["agent_token"] = "agent_token"
    token: str


class AgentMessageEnd(BaseModel):
    type: Literal["agent_message_end"] = "agent_message_end"


class RequestScreenshot(BaseModel):
    type: Literal["request_screenshot"] = "request_screenshot"


class InjectOverlay(BaseModel):
    type: Literal["inject_overlay"] = "inject_overlay"
    selector: Optional[str] = None
    bbox: Optional[dict] = None
    label: str


class ClearOverlay(BaseModel):
    type: Literal["clear_overlay"] = "clear_overlay"


class HandoffStart(BaseModel):
    type: Literal["handoff_start"] = "handoff_start"


class HandoffEnd(BaseModel):
    type: Literal["handoff_end"] = "handoff_end"


class LoginHandoffStart(BaseModel):
    type: Literal["login_handoff_start"] = "login_handoff_start"


class LoginHandoffEnd(BaseModel):
    type: Literal["login_handoff_end"] = "login_handoff_end"


class ProcedureComplete(BaseModel):
    type: Literal["procedure_complete"] = "procedure_complete"


class UISyncCheck(BaseModel):
    type: Literal["ui_sync_check"] = "ui_sync_check"
