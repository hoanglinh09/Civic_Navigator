import { jsxs as _jsxs, jsx as _jsx } from "react/jsx-runtime";
export function ProgressBar({ current, total, label, tier, }) {
    const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
    const color = tier === "handoff"
        ? "bg-red-500"
        : tier === "confirm"
            ? "bg-amber-400"
            : "bg-emerald-500";
    const tierLabel = tier === "handoff"
        ? "Dữ liệu cá nhân"
        : tier === "confirm"
            ? "Xác nhận"
            : "Hướng dẫn";
    const tierColor = tier === "handoff"
        ? "bg-red-50 text-red-600"
        : tier === "confirm"
            ? "bg-amber-50 text-amber-600"
            : "bg-emerald-50 text-emerald-600";
    return (_jsxs("div", { className: "px-4 py-3 bg-white border-b border-slate-200 shadow-sm", children: [_jsxs("div", { className: "flex items-center justify-between mb-1", children: [total > 0 ? (_jsxs("span", { className: "text-xs font-medium text-slate-500", children: ["B\u01B0\u1EDBc ", current, " / ", total] })) : (_jsx("span", { className: "text-xs text-slate-400", children: "Ch\u01B0a b\u1EAFt \u0111\u1EA7u" })), tier !== "inform" && (_jsx("span", { className: `text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${tierColor}`, children: tierLabel }))] }), _jsx("div", { className: "text-sm font-semibold text-slate-800 truncate mb-2", children: label || "Đang chờ..." }), total > 0 && (_jsx("div", { className: "h-1.5 rounded-full bg-slate-100 overflow-hidden", children: _jsx("div", { className: `h-1.5 ${color} rounded-full transition-all duration-500`, style: { width: `${pct}%` } }) }))] }));
}
