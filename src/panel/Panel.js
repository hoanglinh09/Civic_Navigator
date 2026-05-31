import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChatFeed } from "./ChatFeed";
import { ProgressBar } from "./ProgressBar";
import { HandoffScreen } from "./HandoffScreen";
import { useWebSocket } from "./useWebSocket";
const BACKEND_WS_URL = "ws://localhost:8000";
function id() {
    return crypto.randomUUID();
}
export function Panel() {
    const { send, setOnMessage, status } = useWebSocket(BACKEND_WS_URL);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [step, setStep] = useState({ current: 0, total: 0, label: "", tier: "inform" });
    const [overlayLabel, setOverlayLabel] = useState(null);
    const [handoff, setHandoff] = useState(null);
    const composingAssistantId = useRef(null);
    const visibleStepLabel = useMemo(() => (step.label ? step.label : null), [step.label]);
    useEffect(() => {
        setOnMessage(async (m) => {
            if (m.type === "system_status") {
                setMessages((prev) => [...prev, { id: id(), role: "system", text: m.text }]);
                return;
            }
            if (m.type === "step_update") {
                setStep({ current: m.current_step, total: m.total_steps, label: m.step_label, tier: m.action_tier });
                return;
            }
            if (m.type === "agent_token") {
                setMessages((prev) => {
                    const mid = composingAssistantId.current ?? id();
                    composingAssistantId.current = mid;
                    const existingIndex = prev.findIndex((x) => x.id === mid);
                    if (existingIndex === -1) {
                        return [...prev, { id: mid, role: "assistant", text: m.token }];
                    }
                    const next = prev.slice();
                    next[existingIndex] = { ...next[existingIndex], text: next[existingIndex].text + m.token };
                    return next;
                });
                return;
            }
            if (m.type === "agent_message_end") {
                composingAssistantId.current = null;
                return;
            }
            if (m.type === "request_screenshot") {
                const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
                if (!tab?.id)
                    return;
                chrome.runtime.sendMessage({ type: "capture_screenshot", tabId: tab.id }, (resp) => {
                    if (!resp?.ok)
                        return;
                    send({ type: "screenshot", data: resp.data, width: resp.width, height: resp.height, url: tab.url ?? "" });
                });
                return;
            }
            if (m.type === "inject_overlay") {
                setOverlayLabel(m.label);
                const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
                if (!tab?.id)
                    return;
                chrome.tabs.sendMessage(tab.id, { type: "inject_overlay", selector: m.selector, bbox: m.bbox, label: m.label });
                return;
            }
            if (m.type === "clear_overlay") {
                setOverlayLabel(null);
                const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
                if (!tab?.id)
                    return;
                chrome.tabs.sendMessage(tab.id, { type: "clear_overlay" });
                return;
            }
            if (m.type === "handoff_start") {
                setHandoff("data");
                return;
            }
            if (m.type === "handoff_end") {
                setHandoff(null);
                return;
            }
            if (m.type === "login_handoff_start") {
                setHandoff("login");
                return;
            }
            if (m.type === "login_handoff_end") {
                setHandoff(null);
                return;
            }
            if (m.type === "procedure_complete") {
                setMessages((prev) => [...prev, { id: id(), role: "system", text: "Hoàn tất phiên hướng dẫn." }]);
                return;
            }
            if (m.type === "ui_sync_check") {
                send({ type: "ui_sync_response", visible_step_label: visibleStepLabel, overlay_label: overlayLabel });
                return;
            }
        });
    }, [send, setOnMessage, overlayLabel, visibleStepLabel]);
    const showDone = step.tier === "confirm" || step.tier === "handoff";
    return (_jsxs("div", { className: "h-screen flex flex-col relative bg-white", children: [_jsx(ProgressBar, { current: step.current, total: step.total, label: step.label, tier: step.tier }), _jsxs("div", { className: "px-4 py-1.5 text-xs bg-emerald-50 text-emerald-600 border-b border-emerald-100 font-medium flex items-center gap-1.5", children: [_jsx("span", { className: "inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" }), status] }), _jsx(ChatFeed, { messages: messages }), _jsxs("div", { className: "p-4 bg-white border-t border-slate-200 shadow-[0_-1px_4px_rgba(0,0,0,0.04)]", children: [_jsxs("form", { className: "flex gap-2 items-end", onSubmit: (e) => {
                            e.preventDefault();
                            const txt = input.trim();
                            if (!txt)
                                return;
                            setMessages((prev) => [...prev, { id: id(), role: "user", text: txt }]);
                            send({ type: "user_message", text: txt });
                            setInput("");
                        }, children: [_jsx("input", { className: "flex-1 rounded-xl bg-slate-50 border border-slate-200 px-4 py-2.5 text-sm text-slate-800 placeholder-slate-400 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 transition-all", value: input, onChange: (e) => setInput(e.target.value), placeholder: "Nh\u1EADp y\u00EAu c\u1EA7u c\u1EE7a b\u1EA1n..." }), showDone ? (_jsx("button", { type: "button", className: "rounded-xl bg-emerald-500 hover:bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors whitespace-nowrap", onClick: () => {
                                    setMessages((prev) => [...prev, { id: id(), role: "user", text: "Xong rồi" }]);
                                    send({ type: "user_done" });
                                }, children: "Xong r\u1ED3i" })) : null, _jsx("button", { type: "submit", className: "rounded-xl bg-slate-100 hover:bg-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors", children: _jsxs("svg", { width: "16", height: "16", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", children: [_jsx("line", { x1: "22", y1: "2", x2: "11", y2: "13" }), _jsx("polygon", { points: "22 2 15 22 11 13 2 9 22 2" })] }) })] }), _jsx("div", { className: "text-[11px] text-slate-400 mt-2 leading-relaxed", children: "B\u1EA1n lu\u00F4n c\u00F3 th\u1EC3 g\u00F5 c\u00E2u h\u1ECFi ho\u1EB7c \u0111i\u1EC1u ch\u1EC9nh, k\u1EC3 c\u1EA3 khi \u0111ang ch\u1EDD tr\u1EA3 l\u1EDDi." })] }), handoff ? _jsx(HandoffScreen, { variant: handoff }) : null] }));
}
