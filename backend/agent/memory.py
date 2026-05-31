from __future__ import annotations

import json
from dataclasses import dataclass

from .state import AgentState


def build_memory_context(state: AgentState) -> str:
    lines: list[str] = []
    if state.get("procedure_name"):
        lines.append(f"Đang hỗ trợ thủ tục: {state['procedure_name']}")
    steps = state.get("procedure_steps") or []
    if steps:
        total = len(steps)
        idx = state.get("current_step_index", 0)
        step = steps[idx] if 0 <= idx < total else None
        label = f" — {step['label_vi']}" if step else ""
        lines.append(f"Bước hiện tại: {idx + 1}/{total}{label}")
    if state.get("current_url"):
        lines.append(f"URL hiện tại: {state['current_url']}")
    if state.get("last_instruction_emitted"):
        txt = state["last_instruction_emitted"] or ""
        lines.append(f"Hướng dẫn vừa phát: {txt[:120]}...")
    return "\n".join(lines)


@dataclass
class ConversationMemory:
    history: list[dict]

    def append_user(self, text: str) -> None:
        self.history.append({"role": "user", "content": text})

    def append_assistant(self, text: str) -> None:
        self.history.append({"role": "assistant", "content": text})

    def append_tool_result(self, tool: str, content: str) -> None:
        # OpenRouter supports "tool" role inconsistently across models.
        # We keep it as an assistant note so the conversation LLM stays aware.
        self.history.append({"role": "assistant", "content": f"[tool_result:{tool}] {content}"})

    def maybe_summarize(self) -> None:
        # Minimal safe implementation: keep last 40 messages.
        # This is a placeholder for the v1.1.0 summarization requirement.
        if len(self.history) <= 40:
            return
        older = self.history[:-40]
        summary = {
            "role": "assistant",
            "content": "[Tóm tắt ngắn] " + json.dumps(older, ensure_ascii=True)[:1500],
        }
        self.history = [summary] + self.history[-40:]
