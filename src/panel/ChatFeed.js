import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef } from "react";
export function ChatFeed({ messages }) {
    const bottomRef = useRef(null);
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages.length]);
    return (_jsxs("div", { className: "flex-1 overflow-auto p-4 space-y-4 bg-white", children: [messages.length === 0 && (_jsxs("div", { className: "flex flex-col items-center justify-center h-full text-center space-y-3", children: [_jsx("div", { className: "w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center", children: _jsx("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "none", stroke: "#10b981", strokeWidth: "1.5", strokeLinecap: "round", strokeLinejoin: "round", children: _jsx("path", { d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" }) }) }), _jsx("p", { className: "text-sm text-slate-500 max-w-[200px]", children: "Xin ch\u00E0o! B\u1EA1n c\u1EA7n h\u1ED7 tr\u1EE3 th\u1EE7 t\u1EE5c h\u00E0nh ch\u00EDnh g\u00EC h\u00F4m nay?" })] })), messages.map((m) => (_jsx("div", { className: m.role === "user" ? "flex justify-end" : "flex justify-start", children: _jsx("div", { className: "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed " +
                        (m.role === "user"
                            ? "bg-emerald-500 text-white shadow-sm"
                            : m.role === "system"
                                ? "bg-slate-100 text-slate-500 italic"
                                : "bg-slate-100 text-slate-800 shadow-sm"), children: m.text }) }, m.id))), _jsx("div", { ref: bottomRef })] }));
}
