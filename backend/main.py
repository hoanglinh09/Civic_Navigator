from __future__ import annotations

import asyncio
import time
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import contextlib

from . import config
from .models.messages import parse_client_message
from .session import AgentSession, new_state
from .agent.memory import ConversationMemory


app = FastAPI(title="Civic Navigator Backend")

# Cấu hình CORS để đảm bảo Extension kết nối mượt mà không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: Dict[str, AgentSession] = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _session_gc_loop() -> None:
    while True:
        await asyncio.sleep(30)
        now = time.time()
        to_delete = []
        for sid, sess in list(_sessions.items()):
            if now - sess.last_seen_ts > config.SESSION_TTL_SECONDS:
                to_delete.append(sid)
        for sid in to_delete:
            _sessions.pop(sid, None)


@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_session_gc_loop())


@app.websocket("/ws/{session_id}")
async def ws(session_id: str, websocket: WebSocket):
    await websocket.accept()
    print(f"[WS] Kết nối mới được thiết lập. Session ID: {session_id}")

    # Cơ chế Reconnect: Giữ lại trạng thái session cũ nếu F5 trang để tránh mất trí nhớ
    if session_id in _sessions:
        sess = _sessions[session_id]
        sess.websocket = websocket
        sess.last_seen_ts = time.time()
        print(f"[WS] Tái sử dụng session cũ thành công cho ID: {session_id}")
    else:
        state = new_state(session_id)
        memory = ConversationMemory([])
        sess = AgentSession(session_id=session_id, websocket=websocket, state=state, memory=memory)
        _sessions[session_id] = sess
        print(f"[WS] Đã khởi tạo session mới hoàn toàn cho ID: {session_id}")

    await websocket.send_json({"type": "connected", "session_id": session_id})

    agent_task = asyncio.create_task(sess.agent_loop())
    try:
        while True:
            # Nhận dữ liệu JSON trực tiếp từ Extension gửi lên
            data = await websocket.receive_json()
            sess.last_seen_ts = time.time()
            
            print(f"[WS RECEIVE] Dữ liệu thô từ Extension: {data}")
            
            # Khôi phục luồng parse gói tin nguyên bản của bạn
            try:
                msg = parse_client_message(data)
                print(f"[WS PARSE] Parse gói tin thành công sang Object: {type(msg).__name__}")
                await sess.put_incoming(msg)
            except Exception as pe:
                print(f"[WS PARSE ERROR] Lỗi parse hệ thống cũ ({str(pe)}). Đẩy thẳng data thô để chữa cháy.")
                await sess.put_incoming(data)
                
    except WebSocketDisconnect:
        print(f"[WS DISCONNECT] Khách hàng ngắt kết nối WebSocket. Session ID: {session_id}")
    finally:
        agent_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await agent_task