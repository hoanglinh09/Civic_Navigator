from __future__ import annotations

from typing import List, Literal, Optional, TypedDict


class ProcedureStep(TypedDict):
    step_number: int
    total_steps: int
    label_vi: str
    expected_url_pattern: str
    action_tier: Literal["inform", "confirm", "handoff"]
    instruction_vi: str
    field_name: Optional[str]
    is_personal_data: bool
    completed: bool


class ToolCallRecord(TypedDict):
    tool: str  # "search" | "screenshot" | "highlight" | "llm"
    turn: int
    result_summary: str


class AgentState(TypedDict):
    session_id: str

    # Memory
    conversation_history: List[dict]
    memory_context: str
    tool_call_history: List[ToolCallRecord]
    turn_index: int

    # Procedure
    user_intent: Optional[str]
    procedure_name: Optional[str]
    procedure_steps: List[ProcedureStep]
    current_step_index: int
    search_results_raw: Optional[str]

    # Screen
    last_screenshot_b64: Optional[str]
    last_page_analysis: Optional[dict]
    current_url: Optional[str]

    # Login
    login_required: bool
    login_completed: bool

    # Flow control
    session_status: Literal[
        "idle",
        "parsing_intent",
        "searching",
        "planning",
        "awaiting_login",
        "executing",
        "awaiting_user",
        "verifying",
        "recovering",
        "complete",
        "error",
    ]
    error_message: Optional[str]
    recovery_attempts: int

    # UI consistency
    ui_synced: bool
    last_instruction_emitted: Optional[str]
    last_overlay_label_requested: Optional[str]
