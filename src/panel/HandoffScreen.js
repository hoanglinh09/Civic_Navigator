import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function HandoffScreen({ variant }) {
    const title = variant === "login" ? "Đăng nhập" : "Nhập dữ liệu cá nhân";
    const iconPath = variant === "login"
        ? "M12 15v2m-6 4h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2zm10-10V7a4 4 0 0 0-8 0v4h8z"
        : "M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2z";
    const desc = variant === "login"
        ? "Bạn hãy tự đăng nhập. Trợ lý sẽ tạm dừng để đảm bảo riêng tư."
        : "Bạn hãy tự điền thông tin cá nhân. Trợ lý sẽ không chụp màn hình trong bước này.";
    return (_jsx("div", { className: "absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center p-6", children: _jsxs("div", { className: "w-full max-w-xs rounded-2xl bg-white border border-slate-200 shadow-lg p-5 text-center", children: [_jsx("div", { className: "w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3", children: _jsx("svg", { width: "22", height: "22", viewBox: "0 0 24 24", fill: "none", stroke: "#6b7280", strokeWidth: "1.75", strokeLinecap: "round", strokeLinejoin: "round", children: _jsx("path", { d: iconPath }) }) }), _jsx("div", { className: "text-sm font-semibold text-slate-800", children: title }), _jsx("div", { className: "text-xs text-slate-500 mt-1.5 leading-relaxed", children: desc })] }) }));
}
