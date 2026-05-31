import { useEffect, useRef, useState } from "react";

export type ServerMessage =
  | { type: "connected"; session_id: string }
  | { type: "system_status"; text: string }
  | { type: "agent_token"; token: string }
  | { type: "agent_message_end" }
  | {
      type: "step_update";
      current_step: number;
      total_steps: number;
      step_label: string;
      action_tier: "inform" | "confirm" | "handoff";
    }
  | { type: "request_screenshot" }
  | {
      type: "inject_overlay";
      selector?: string | null;
      bbox?: { x: number; y: number; width: number; height: number } | null;
      label: string;
    }
  | { type: "clear_overlay" }
  | { type: "handoff_start" }
  | { type: "handoff_end" }
  | { type: "login_handoff_start" }
  | { type: "login_handoff_end" }
  | { type: "procedure_complete" }
  | { type: "ui_sync_check" };

export type ClientMessage =
  | { type: "session_init"; session_id: string; current_url: string }
  | { type: "user_message"; text: string }
  | { type: "user_done" }
  | {
      type: "screenshot";
      data: string;
      width: number;
      height: number;
      url: string;
    }
  | {
      type: "ui_sync_response";
      visible_step_label: string | null;
      overlay_label: string | null;
    };

function uuidv4(): string {
  return crypto.randomUUID();
}

export function useWebSocket(backendWsUrl: string) {
  const [status, setStatus] = useState<string>("Đang kết nối...");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionIdRef = useRef<string>(uuidv4());

  useEffect(() => {
    const ws = new WebSocket(`${backendWsUrl}/ws/${sessionIdRef.current}`);
    wsRef.current = ws;
    ws.onopen = async () => {
      setConnected(true);
      const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
      const currentUrl = tab?.url ?? "";
      const init: ClientMessage = { type: "session_init", session_id: sessionIdRef.current, current_url: currentUrl };
      ws.send(JSON.stringify(init));
      setStatus("Đã kết nối");
    };
    ws.onclose = () => {
      setConnected(false);
      setStatus("Mất kết nối");
    };
    ws.onerror = () => {
      setConnected(false);
      setStatus("Lỗi kết nối");
    };
    return () => {
      ws.close();
    };
  }, [backendWsUrl]);

  function send(msg: ClientMessage) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(msg));
  }

  function setOnMessage(handler: (m: ServerMessage) => void) {
    const ws = wsRef.current;
    if (!ws) return;
    ws.onmessage = (ev) => {
      try {
        const m = JSON.parse(ev.data) as ServerMessage;
        handler(m);
      } catch {
        // ignore
      }
    };
  }

  return { send, setOnMessage, status, connected, sessionId: sessionIdRef.current };
}
