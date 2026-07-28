import React, { useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Send, Bot, Loader2 } from "lucide-react";
import api, { formatApiErrorDetail } from "@/lib/api";

const SUGGESTIONS = [
  "Which SKUs are at risk of stock-out this week?",
  "Summarize collections performance for the last 30 days",
  "Which distributors have the highest overdue receivables?",
  "Recommend actions to improve fill rate in the South-West region",
];

export default function AiAssistant({ open, onOpenChange }) {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]); // [{role, text}]
  const [loading, setLoading] = useState(false);

  const send = async (text) => {
    const msg = (text ?? prompt).trim();
    if (!msg) return;
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setPrompt("");
    setLoading(true);
    try {
      const { data } = await api.post("/ai/ask", { prompt: msg });
      setMessages((m) => [...m, { role: "assistant", text: data.reply || "…" }]);
    } catch (e) {
      const err = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      setMessages((m) => [...m, { role: "assistant", text: `⚠️ ${err}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg bg-white border-l border-[#E5E7EB] p-0 flex flex-col">
        <SheetHeader className="px-6 py-5 border-b border-[#E5E7EB]">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gold/15 flex items-center justify-center">
              <Sparkles size={18} className="text-gold-dark" />
            </div>
            <div>
              <SheetTitle className="font-display font-bold text-ink">GO OIL AI Copilot</SheetTitle>
              <SheetDescription className="text-xs">Ask about orders, inventory, ledger, KPIs.</SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {messages.length === 0 && (
            <div>
              <div className="text-sm text-ink-muted mb-3">Try one of these:</div>
              <div className="grid grid-cols-1 gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-left text-sm rounded-lg border border-[#E5E7EB] p-3 hover:bg-canvas transition"
                    data-testid={`ai-suggestion-${s.slice(0, 12)}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "assistant" && (
                <div className="h-8 w-8 shrink-0 rounded-lg bg-gold/15 flex items-center justify-center">
                  <Bot size={16} className="text-gold-dark" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "bg-ink text-white"
                    : "bg-canvas border border-[#E5E7EB] text-ink whitespace-pre-wrap"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-sm text-ink-muted">
              <Loader2 size={14} className="animate-spin" /> Thinking…
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-[#E5E7EB] bg-canvas">
          <div className="flex items-end gap-2">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="Ask the AI copilot..."
              className="min-h-[46px] max-h-32 bg-white border-[#E5E7EB] resize-none"
              data-testid="ai-prompt"
            />
            <Button
              onClick={() => send()}
              disabled={loading || !prompt.trim()}
              className="bg-gold hover:bg-gold-dark text-white h-11 px-4"
              data-testid="ai-send"
            >
              <Send size={15} />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
