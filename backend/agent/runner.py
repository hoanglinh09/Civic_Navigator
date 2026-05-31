from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import WebSocket

from .default_plan import default_passport_renewal_plan
from .memory import ConversationMemory, build_memory_context
from .prompts import CONVERSATION_SYSTEM_PROMPT, PLAN_BUILDER_SYSTEM_PROMPT
from .state import AgentState, ProcedureStep
from .tools.highlight_tool import highlight_tool
from .tools.screenshot_tool import screenshot_tool
from .tools.search_tool import search_tool
from ..services.openrouter import OpenRouterError, extract_message_content, stream_text, chat_completion


def _system_message(state: AgentState) -> dict:
    return {"role": "system", "content": CONVERSATION_SYSTEM_PROMPT.format(memory_context=state["memory_context"]) }


def _safe_json_loads(text: str) -> Any:
    t = text.strip()
    if t.startswith("```"):
        t = t.removeprefix("```json").removeprefix("```").strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    # Try to locate first { ... } block.
    if not t.startswith("{"):
        start = t.find("{")
        end = t.rfind("}")
        if start != -1 and end != -1 and end > start:
            t = t[start : end + 1]
    return json.loads(t)


async def _emit_text(websocket: WebSocket, text: str) -> None:
    # Cheap tokenization to preserve a streaming-like UX in fallback paths.
    for part in text.split(" "):
        await websocket.send_json({"type": "agent_token", "token": part + " "})
        await asyncio.sleep(0.01)
    await websocket.send_json({"type": "agent_message_end"})


async def _emit_status(websocket: WebSocket, text: str) -> None:
    await websocket.send_json({"type": "system_status", "text": text})


async def build_plan_via_llm(search_text: str, user_intent: str) -> list[ProcedureStep]:
    messages = [
        {"role": "system", "content": PLAN_BUILDER_SYSTEM_PROMPT},
        {"role": "user", "content": f"TUTORIAL TEXT:\n{search_text}\n\nUSER INTENT:\n{user_intent}"},
    ]
    resp = await chat_completion(messages, stream=False, max_tokens=2000, temperature=0.2)
    content = extract_message_content(resp)
    data = _safe_json_loads(content)
    steps = []
    for i, raw in enumerate(data):
        raw.setdefault("step_number", i + 1)
        raw.setdefault("total_steps", len(data))
        raw.setdefault("completed", False)
        steps.append(raw)
    return steps


async def conversation_turn(state: AgentState) -> dict:
    msgs = [_system_message(state)] + state["conversation_history"]
    try:
        resp = await chat_completion(msgs, stream=False, max_tokens=800, temperature=0.2)
        content = extract_message_content(resp)
        return _safe_json_loads(content)
    except OpenRouterError:
        # Offline fallback intent router.
        last_user = ""
        for m in reversed(state["conversation_history"]):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        t = last_user.lower()
        if not state.get("procedure_steps"):
            return {
                "intent": "start_procedure",
                "reply_vi": "Mình sẽ hướng dẫn bạn làm thủ tục ‘Gia hạn hộ chiếu’ trên dichvucong.gov.vn. Mình sẽ đi từng bước và bạn là người thao tác nhé.",
                "needs_screenshot": False,
                "needs_highlight": False,
                "highlight_intent_vi": None,
                "advance_step": False,
            }
        if "xong" in t or "đã" in t or "ok" in t:
            return {
                "intent": "verify_and_advance",
                "reply_vi": None,
                "needs_screenshot": False,
                "needs_highlight": False,
                "highlight_intent_vi": None,
                "advance_step": True,
            }
        return {
            "intent": "execute_step",
            "reply_vi": None,
            "needs_screenshot": True,
            "needs_highlight": True,
            "highlight_intent_vi": "Làm nổi bật nút tiếp theo / nộp hồ sơ",
            "advance_step": False,
        }


async def sync_ui(websocket: WebSocket, state: AgentState, wait_for_ui_sync_response) -> bool:
    # Gate: must verify panel agrees on current step/overlay labels.
    step = state["procedure_steps"][state["current_step_index"]]
    for _ in range(3):
        await websocket.send_json({"type": "ui_sync_check"})
        resp = await wait_for_ui_sync_response(timeout_s=3)
        if resp is None:
            continue
        visible_ok = (resp.visible_step_label or "") == step["label_vi"]
        overlay_expected = state.get("last_overlay_label_requested")
        overlay_ok = True
        if overlay_expected:
            overlay_ok = (resp.overlay_label or "") == overlay_expected
        if visible_ok and overlay_ok:
            state["ui_synced"] = True
            return True

        # Re-emit step and overlay so the panel can resync.
        await websocket.send_json(
            {
                "type": "step_update",
                "current_step": step["step_number"],
                "total_steps": step["total_steps"],
                "step_label": step["label_vi"],
                "action_tier": step["action_tier"],
            }
        )
        await asyncio.sleep(0.2)
    state["ui_synced"] = False
    return False


async def execute_current_step(
    websocket: WebSocket,
    state: AgentState,
    turn_decision: dict,
    wait_for_screenshot,
    wait_for_ui_sync_response,
) -> None:
    step = state["procedure_steps"][state["current_step_index"]]
    state["session_status"] = "executing"
    state["ui_synced"] = False
    await websocket.send_json(
        {
            "type": "step_update",
            "current_step": step["step_number"],
            "total_steps": step["total_steps"],
            "step_label": step["label_vi"],
            "action_tier": step["action_tier"],
        }
    )

    if step["action_tier"] == "handoff":
        # Privacy: do not request screenshots; show handoff UI.
        if state.get("login_required") and not state.get("login_completed"):
            await websocket.send_json({"type": "login_handoff_start"})
        else:
            await websocket.send_json({"type": "handoff_start"})
        await _emit_text(websocket, step["instruction_vi"])
        state["last_instruction_emitted"] = step["instruction_vi"]
        state["memory_context"] = build_memory_context(state)
        await sync_ui(websocket, state, wait_for_ui_sync_response)
        state["session_status"] = "awaiting_user"
        return

    # Non-handoff steps: optionally look at the screen and highlight.
    screenshot = None
    if bool(turn_decision.get("needs_screenshot")):
        screenshot = await screenshot_tool(websocket, wait_for_screenshot)
        if screenshot:
            state["last_screenshot_b64"] = screenshot.b64
            state["current_url"] = screenshot.url

    if screenshot and bool(turn_decision.get("needs_highlight")) and turn_decision.get("highlight_intent_vi"):
        hr = await highlight_tool(str(turn_decision.get("highlight_intent_vi")), screenshot.b64, websocket)
        if hr.success:
            state["last_overlay_label_requested"] = hr.label
        else:
            state["last_overlay_label_requested"] = None
            await websocket.send_json({"type": "clear_overlay"})
    else:
        state["last_overlay_label_requested"] = None
        await websocket.send_json({"type": "clear_overlay"})

    # Instruction preference: turn_decision.reply_vi if provided, else step instruction.
    instruction = turn_decision.get("reply_vi") or step["instruction_vi"]
    await _emit_text(websocket, instruction)
    state["last_instruction_emitted"] = instruction
    state["memory_context"] = build_memory_context(state)

    await sync_ui(websocket, state, wait_for_ui_sync_response)
    state["session_status"] = "awaiting_user" if step["action_tier"] == "confirm" else "executing"
    if step["action_tier"] == "inform":
        # Auto-advance after a short pause; user can interrupt by sending a message.
        await asyncio.sleep(1.5)


def _maybe_mark_login_complete(state: AgentState) -> None:
    step = state["procedure_steps"][state["current_step_index"]]
    if step["label_vi"].lower().startswith("đăng nhập"):
        state["login_completed"] = True
        state["login_required"] = True


async def run_agent_turn(
    websocket: WebSocket,
    state: AgentState,
    memory: ConversationMemory,
    wait_for_screenshot,
    wait_for_ui_sync_response,
) -> None:
    state["memory_context"] = build_memory_context(state)
    memory.maybe_summarize()

    decision = await conversation_turn(state)
    intent = decision.get("intent")
    reply_vi = decision.get("reply_vi")
    if reply_vi:
        # Optional assistant message not tied to a step.
        await _emit_text(websocket, str(reply_vi))
        state["last_instruction_emitted"] = str(reply_vi)
        state["memory_context"] = build_memory_context(state)

    if intent == "start_procedure":
        state["session_status"] = "searching"
        await _emit_status(websocket, "Đang tìm hiểu quy trình...")
        procedure_name = state.get("user_intent") or "Gia hạn hộ chiếu"
        search_text = await search_tool(procedure_name)
        state["search_results_raw"] = search_text
        memory.append_tool_result("search", f"len={len(search_text)}")

        state["session_status"] = "planning"
        try:
            steps = await build_plan_via_llm(search_text, state.get("user_intent") or procedure_name)
        except Exception:  # noqa: BLE001
            steps = default_passport_renewal_plan()
        state["procedure_name"] = procedure_name
        state["procedure_steps"] = steps
        state["current_step_index"] = 0
        memory.append_assistant(f"[Kế hoạch đã lập: {len(steps)} bước cho '{procedure_name}'. Bước 1: {steps[0]['label_vi']}]" )
        state["memory_context"] = build_memory_context(state)
        intent = "execute_step"

    if intent in ("execute_step", "user_correction", "user_question", "user_done", "verify_and_advance"):
        if not state.get("procedure_steps"):
            # No plan yet: force start.
            state["user_intent"] = state.get("user_intent") or "Gia hạn hộ chiếu"
            state["conversation_history"].append({"role": "assistant", "content": "[Chưa có kế hoạch, bắt đầu lập kế hoạch...]"})
            await run_agent_turn(websocket, state, memory, wait_for_screenshot, wait_for_ui_sync_response)
            return

        if intent in ("verify_and_advance", "user_done") or bool(decision.get("advance_step")):
            # Minimal verification: trust user; optionally check URL pattern when we have it.
            step = state["procedure_steps"][state["current_step_index"]]
            expected = step.get("expected_url_pattern") or ""
            if expected and state.get("current_url") and expected not in (state["current_url"] or "") and state["recovery_attempts"] < 2:
                state["recovery_attempts"] += 1
                await _emit_text(websocket, "Mình chưa chắc bạn đang ở đúng trang cho bước này. Bạn có thể bấm chụp lại màn hình hoặc mô tả bạn đang thấy gì không?")
                state["session_status"] = "awaiting_user"
                return

            step["completed"] = True
            _maybe_mark_login_complete(state)
            if step["action_tier"] == "handoff":
                if state.get("login_required") and not state.get("login_completed"):
                    await websocket.send_json({"type": "login_handoff_end"})
                else:
                    await websocket.send_json({"type": "handoff_end"})

            state["current_step_index"] += 1
            state["recovery_attempts"] = 0
            if state["current_step_index"] >= len(state["procedure_steps"]):
                state["session_status"] = "complete"
                await _emit_text(websocket, f"✓ Hoàn thành! Bạn đã hoàn tất {state.get('procedure_name') or 'thủ tục'}.")
                await websocket.send_json({"type": "procedure_complete"})
                return
            await execute_current_step(websocket, state, decision, wait_for_screenshot, wait_for_ui_sync_response)
            return

        # Regular execute (no advance)
        await execute_current_step(websocket, state, decision, wait_for_screenshot, wait_for_ui_sync_response)
        return

    if intent == "procedure_complete":
        state["session_status"] = "complete"
        await _emit_text(websocket, f"✓ Hoàn thành! Bạn đã hoàn tất {state.get('procedure_name') or 'thủ tục'}.")
        await websocket.send_json({"type": "procedure_complete"})
        return

    # general_reply
    if not reply_vi:
        await _emit_text(websocket, "Bạn có thể nói bạn đang muốn làm thủ tục gì trên dichvucong.gov.vn không?")
