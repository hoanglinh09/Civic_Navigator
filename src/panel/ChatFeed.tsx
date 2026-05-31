import { useEffect, useRef } from "react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
};

export function ChatFeed({ messages }: { messages: ChatMessage[] }) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4 bg-white">
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <p className="text-sm text-slate-500 max-w-[200px]">
            Xin chào! Bạn cần hỗ trợ thủ tục hành chính gì hôm nay?
          </p>
        </div>
      )}
      {messages.map((m) => (
        <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
          <div
            className={
              "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed " +
              (m.role === "user"
                ? "bg-emerald-500 text-white shadow-sm"
                : m.role === "system"
                  ? "bg-slate-100 text-slate-500 italic"
                  : "bg-slate-100 text-slate-800 shadow-sm")
            }
          >
            {m.text}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}