export function ProgressBar({
  current,
  total,
  label,
  tier,
}: {
  current: number;
  total: number;
  label: string;
  tier: "inform" | "confirm" | "handoff";
}) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  const color =
    tier === "handoff"
      ? "bg-red-500"
      : tier === "confirm"
        ? "bg-amber-400"
        : "bg-emerald-500";
  const tierLabel =
    tier === "handoff"
      ? "Dữ liệu cá nhân"
      : tier === "confirm"
        ? "Xác nhận"
        : "Hướng dẫn";
  const tierColor =
    tier === "handoff"
      ? "bg-red-50 text-red-600"
      : tier === "confirm"
        ? "bg-amber-50 text-amber-600"
        : "bg-emerald-50 text-emerald-600";

  return (
    <div className="px-4 py-3 bg-white border-b border-slate-200 shadow-sm">
      <div className="flex items-center justify-between mb-1">
        {total > 0 ? (
          <span className="text-xs font-medium text-slate-500">
            Bước {current} / {total}
          </span>
        ) : (
          <span className="text-xs text-slate-400">Chưa bắt đầu</span>
        )}
        {tier !== "inform" && (
          <span
            className={`text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${tierColor}`}
          >
            {tierLabel}
          </span>
        )}
      </div>
      <div className="text-sm font-semibold text-slate-800 truncate mb-2">
        {label || "Đang chờ..."}
      </div>
      {total > 0 && (
        <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-1.5 ${color} rounded-full transition-all duration-500`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}