import { useEffect, useRef, useState } from "react";
function uuidv4() {
    return crypto.randomUUID();
}
export function useWebSocket(backendWsUrl) {
    const [status, setStatus] = useState("Đang kết nối...");
    const [connected, setConnected] = useState(false);
    const wsRef = useRef(null);
    const sessionIdRef = useRef(uuidv4());
    useEffect(() => {
        const ws = new WebSocket(`${backendWsUrl}/ws/${sessionIdRef.current}`);
        wsRef.current = ws;
        ws.onopen = async () => {
            setConnected(true);
            const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
            const currentUrl = tab?.url ?? "";
            const init = { type: "session_init", session_id: sessionIdRef.current, current_url: currentUrl };
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
    function send(msg) {
        const ws = wsRef.current;
        if (!ws || ws.readyState !== WebSocket.OPEN)
            return;
        ws.send(JSON.stringify(msg));
    }
    function setOnMessage(handler) {
        const ws = wsRef.current;
        if (!ws)
            return;
        ws.onmessage = (ev) => {
            try {
                const m = JSON.parse(ev.data);
                handler(m);
            }
            catch {
                // ignore
            }
        };
    }
    return { send, setOnMessage, status, connected, sessionId: sessionIdRef.current };
}
