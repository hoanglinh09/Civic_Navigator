from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List

from fastapi import WebSocket
from openai import AsyncOpenAI

from . import config
from .agent.memory import ConversationMemory


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Bạn là AI agent hỗ trợ người dùng thao tác trên Cổng Dịch vụ công Quốc gia Việt Nam.

MỤC TIÊU:
- Đồng hành với người dùng theo thời gian thực
- Hướng dẫn thao tác từng bước
- Giữ hội thoại tự nhiên và liền mạch
- Chủ động hỗ trợ như trợ lý thật

NGUYÊN TẮC:
- Nếu chưa có dữ liệu UI cụ thể, vẫn hướng dẫn theo quy trình phổ biến chung
- Không được bịa chi tiết giao diện cụ thể như:
  + màu sắc
  + icon
  + vị trí
  + tên button chưa được cung cấp
- Không tự nói rằng mình "không đủ dữ liệu" cho các yêu cầu phổ biến
- Không onboarding lại từ đầu
- Không reset workflow
- Không yêu cầu gửi ảnh chụp màn hình
- Nếu có search_results thì phải dựa vào đó để phân tích dịch vụ phù hợp
- Nếu có nhiều kết quả, hãy giúp người dùng chọn bằng tên dịch vụ thật
- Không tự tưởng tượng giao diện

PHONG CÁCH:
- Tự nhiên
- Gần gũi
- Chủ động
- Ngắn gọn
- Giống trợ lý thật
- Không markdown
QUAN TRỌNG:
- Mỗi lần chỉ hướng dẫn MỘT hành động tiếp theo
- Không mô tả toàn bộ quy trình một lúc
- Không viết kiểu bài hướng dẫn
- Hãy phản hồi như trợ lý đang theo sát người dùng realtime
"""


class AgentSession:

    def __init__(
        self,
        session_id: str,
        websocket: WebSocket,
        state: dict,
        memory: ConversationMemory
    ):

        self.session_id = session_id
        self.websocket = websocket
        self.state = state
        self.memory = memory

        self.ai_client = AsyncOpenAI(
            api_key=config.OPENROUTER_API_KEY,
            base_url=config.OPENROUTER_BASE_URL
        )

        self.incoming_queue = asyncio.Queue()

        self.last_seen_ts = time.time()

        self.is_processing = False
        self.cancel_requested = False

        # =====================================================
        # CONTEXT MEMORY
        # =====================================================

        self.goal: str = ""

        self.ui_state: Dict[str, Any] = {}

        self.execution_history: List[dict] = []

        self.last_ai_response: str = ""

        self.last_observer_ts = 0

        print(f"[AGENT READY] {session_id}")

    # =========================================================
    # SEND WS
    # =========================================================

    async def send_json(self, data: dict):

        try:
            await self.websocket.send_json(data)

        except Exception as e:
            print(f"[WS ERROR] {e}")

    # =========================================================
    # QUEUE
    # =========================================================

    async def put_incoming(self, msg: Any):

        self.last_seen_ts = time.time()

        await self.incoming_queue.put(msg)

    # =========================================================
    # STREAM AI
    # =========================================================

    async def stream_ai_response(
        self,
        messages: List[dict]
    ) -> str:

        full_text = ""

        try:

            stream = await self.ai_client.chat.completions.create(
                model=config.OPENROUTER_MODEL,
                messages=messages,
                temperature=0.2,
                stream=True
            )

            await self.send_json({
                "type": "agent_message_start"
            })

            async for chunk in stream:

                if self.cancel_requested:
                    break

                try:

                    delta = chunk.choices[0].delta.content

                    if not delta:
                        continue

                    full_text += delta

                    await self.send_json({
                        "type": "agent_token",
                        "token": delta
                    })

                except Exception:
                    continue

            await self.send_json({
                "type": "agent_message_end"
            })

        except Exception as e:

            print(f"[STREAM ERROR] {e}")

            await self.send_json({
                "type": "agent_message_start"
            })

            await self.send_json({
                "type": "agent_token",
                "token": "Xin lỗi, hệ thống đang gặp sự cố xử lý."
            })

            await self.send_json({
                "type": "agent_message_end"
            })

        return full_text

    # =========================================================
    # MAIN LOOP
    # =========================================================

    async def agent_loop(self):

        try:

            while True:

                incoming = await self.incoming_queue.get()

                self.last_seen_ts = time.time()

                # =================================================
                # PARSE PAYLOAD
                # =================================================

                if isinstance(incoming, dict):

                    msg_type = incoming.get("type", "")
                    payload = incoming

                else:

                    msg_type = getattr(incoming, "type", "")
                    payload = incoming.__dict__

                # =================================================
                # SESSION INIT
                # =================================================

                if msg_type == "session_init":

                    self.incoming_queue.task_done()
                    continue

                # =================================================
                # USER MESSAGE
                # =================================================

                if msg_type == "user_message":

                    if self.is_processing:

                        self.cancel_requested = True
                        await asyncio.sleep(0.1)

                    self.cancel_requested = False
                    self.is_processing = True

                    await self.handle_user_message(payload)

                    self.is_processing = False

                    self.incoming_queue.task_done()
                    continue

                # =================================================
                # UI STATE SYNC
                # =================================================

                if msg_type == "ui_state_sync":

                    ui_state = payload.get("ui_state", {})

                    self.ui_state.update(ui_state)

                    await self.react_to_ui_state()

                    self.incoming_queue.task_done()
                    continue

                self.incoming_queue.task_done()

        except asyncio.CancelledError:
            pass

    # =========================================================
    # HANDLE USER MESSAGE
    # =========================================================

    async def handle_user_message(self, payload: dict):

        user_text = payload.get("text", "").strip()

        if user_text:

            self.goal = user_text

        # =====================================================
        # UI STATE UPDATE
        # =====================================================

        current_url = payload.get(
            "current_url",
            "https://dichvucong.gov.vn"
        )

        self.ui_state["current_url"] = current_url

        optional_fields = [
            "page_title",
            "buttons",
            "forms",
            "visible_text",
            "search_results",
            "errors",
            "breadcrumbs",
            "current_service"
        ]

        for field in optional_fields:

            if field in payload:

                self.ui_state[field] = payload[field]

        # =====================================================
        # HISTORY
        # =====================================================

        self.execution_history.append({
            "type": "user_message",
            "content": user_text,
            "time": time.time()
        })

        # =====================================================
        # AGENT STATE
        # =====================================================

        await self.send_json({
            "type": "agent_state",
            "state": "thinking"
        })

        await self.send_json({
            "type": "step_update",
            "current_step": 0,
            "total_steps": 0,
            "step_label": "Đang phân tích trạng thái hiện tại...",
            "action_tier": "inform"
        })

        # =====================================================
        # UI CONTEXT
        # =====================================================

        ui_context = {
            "current_url": self.ui_state.get("current_url"),
            "page_title": self.ui_state.get("page_title"),
            "visible_text": self.ui_state.get("visible_text"),
            "buttons": self.ui_state.get("buttons", []),
            "forms": self.ui_state.get("forms", []),
            "search_results": self.ui_state.get("search_results", []),
            "errors": self.ui_state.get("errors", []),
            "breadcrumbs": self.ui_state.get("breadcrumbs", []),
            "current_service": self.ui_state.get("current_service")
        }

        # =====================================================
        # PROMPT
        # =====================================================

        prompt = f"""
MỤC TIÊU NGƯỜI DÙNG:
{self.goal}

TRẠNG THÁI GIAO DIỆN:
{json.dumps(ui_context, ensure_ascii=False)}

LỊCH SỬ GẦN ĐÂY:
{json.dumps(self.execution_history[-6:], ensure_ascii=False)}

TIN NHẮN MỚI:
{user_text}

YÊU CẦU:
- Chỉ hướng dẫn đúng 1 bước tiếp theo gần nhất
- Không giải thích toàn bộ quy trình
- Không liệt kê nhiều bước cùng lúc
- Không gửi checklist dài
- Không gửi hướng dẫn từ đầu đến cuối
- Phản hồi giống trợ lý đang đồng hành realtime
- Sau mỗi bước, chờ người dùng thao tác tiếp
- Ưu tiên hội thoại ngắn
- Mỗi phản hồi tối đa 2-3 câu ngắn
- Nếu người dùng đã ở đúng bước thì chỉ hướng dẫn thao tác kế tiếp
- Không onboarding lại
- Không lặp lại thông tin cũ
- Không markdown
"""

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = await self.stream_ai_response(messages)

        self.last_ai_response = response

        self.execution_history.append({
            "type": "assistant_response",
            "content": response,
            "time": time.time()
        })

        await self.send_json({
            "type": "agent_state",
            "state": "waiting_user"
        })

    # =========================================================
    # UI OBSERVER
    # =========================================================

    async def react_to_ui_state(self):

        if not self.goal:
            return

        now = time.time()

        # =====================================================
        # ANTI SPAM
        # =====================================================

        if now - self.last_observer_ts < 4:
            return

        self.last_observer_ts = now

        current_url = self.ui_state.get("current_url", "")

        if not current_url:
            return

        page_title = self.ui_state.get("page_title", "")
        errors = self.ui_state.get("errors", [])
        search_results = self.ui_state.get("search_results", [])

        # =====================================================
        # ONLY IMPORTANT EVENTS
        # =====================================================

        if not errors and not page_title and not search_results:
            return

        await self.send_json({
            "type": "agent_state",
            "state": "observing"
        })

        # =====================================================
        # OBSERVER PROMPT
        # =====================================================

        prompt = f"""
Người dùng đang thao tác trên Cổng Dịch vụ công.

MỤC TIÊU:
{self.goal}

TRẠNG THÁI GIAO DIỆN:
{json.dumps(self.ui_state, ensure_ascii=False)}

YÊU CẦU:
- Nếu có lỗi thì hỗ trợ xử lý
- Nếu có search_results thì giúp phân tích kết quả
- Nếu người dùng đã sang bước mới thì hướng dẫn bước tiếp theo
- Không bịa giao diện
- Không tự đoán dữ liệu không tồn tại
- Ngắn gọn và tự nhiên
"""

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = await self.stream_ai_response(messages)

        self.execution_history.append({
            "type": "observer_response",
            "content": response,
            "time": time.time()
        })

        await self.send_json({
            "type": "agent_state",
            "state": "waiting_user"
        })


# =========================================================
# COMPATIBLE WITH OLD MAIN.PY
# =========================================================

def new_state(session_id: str):

    return {
        "session_id": session_id
    }