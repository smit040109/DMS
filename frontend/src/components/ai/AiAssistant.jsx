import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sparkles, Send, Bot, Loader2, RotateCcw, AlertCircle, ChevronRight, Download, FileSpreadsheet } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiErrorDetail } from "@/lib/api";

/**
 * AI Business Copilot — talks to /api/ai/copilot/*.
 * Backwards-compat: falls back to /api/ai/ask if copilot endpoint is unreachable.
 */

const FALLBACK_SUGGESTIONS = [
  "Which SKUs are at risk of stock-out this week?",
  "Summarize collections performance for the last 30 days",
  "Which distributors have the highest overdue receivables?",
  "Recommend actions to improve fill rate in the South-West region",
];

const SESSION_KEY = "go_oil_ai_session_id";

function newSessionId() {
  return `sess-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function AiAssistant({ open, onOpenChange }) {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]); // [{role, text, sources?, intent?, model?}]
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState({ ready: null }); // null=unknown, true/false
  const [statusMsg, setStatusMsg] = useState("");
  const [suggestions, setSuggestions] = useState(FALLBACK_SUGGESTIONS);
  const [sessionId, setSessionId] = useState(() => {
    return typeof window !== "undefined"
      ? (window.sessionStorage.getItem(SESSION_KEY) || newSessionId())
      : newSessionId();
  });

  const persistSession = useCallback((sid) => {
    setSessionId(sid);
    try { window.sessionStorage.setItem(SESSION_KEY, sid); } catch (e) { /* ignore */ }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const { data } = await api.get("/ai/copilot/status");
      setStatus({ ready: !!data.ready });
      setStatusMsg(data.message || "");
    } catch (e) {
      // status endpoint missing → probably offline or old build
      setStatus({ ready: false });
      setStatusMsg("AI Copilot is offline. Contact administrator.");
    }
  }, []);

  const loadSuggestions = useCallback(async () => {
    try {
      const { data } = await api.get("/ai/copilot/suggestions");
      if (data?.data?.length) setSuggestions(data.data);
    } catch (e) { /* keep fallback */ }
  }, []);

  useEffect(() => {
    if (open) {
      loadStatus();
      loadSuggestions();
    }
  }, [open, loadStatus, loadSuggestions]);

  const reset = () => {
    setMessages([]);
    persistSession(newSessionId());
  };

  const [exporting, setExporting] = useState(null); // `${idx}:${fmt}` while downloading

  const exportReport = async (idx, text, fmt) => {
    setExporting(`${idx}:${fmt}`);
    try {
      const { data } = await api.post(
        "/ai/copilot/export",
        { format: fmt, title: "GO OIL DMS — AI Report", content: text },
        { responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "excel" ? "ai_report.xlsx" : "ai_report.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`${fmt === "excel" ? "Excel" : "PDF"} downloaded`);
    } catch (e) {
      toast.error("Download failed. Please try again.");
    } finally {
      setExporting(null);
    }
  };

  const send = async (text) => {
    const msg = (text ?? prompt).trim();
    if (!msg) return;
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setPrompt("");
    setLoading(true);
    try {
      const { data } = await api.post("/ai/copilot/ask", {
        question: msg,
        session_id: sessionId,
      });
      if (data.session_id) persistSession(data.session_id);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: data.answer || "…",
          sources: data.sources || [],
          intent: data.intent,
          model: data.model,
        },
      ]);
    } catch (e) {
      const detail = formatApiErrorDetail(e.response?.data?.detail) || e.message;
      const is503 = e.response?.status === 503;
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: is503
            ? `AI Copilot is not ready:\n\n${detail}\n\nOnce your Emergent Universal Key is configured, this assistant will come online without any code changes.`
            : `Sorry, I couldn't process that. Error: ${detail}`,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const notReadyBanner = useMemo(() => {
    if (status.ready === false && statusMsg) {
      return (
        <div className="mx-6 mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900" data-testid="ai-not-ready">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold">AI Copilot offline</div>
            <div className="mt-0.5">{statusMsg}</div>
          </div>
        </div>
      );
    }
    return null;
  }, [status.ready, statusMsg]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg bg-white border-l border-[#E5E7EB] p-0 flex flex-col" data-testid="ai-copilot-sheet">
        <SheetHeader className="px-6 py-5 border-b border-[#E5E7EB]">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gold/15 flex items-center justify-center">
              <Sparkles size={18} className="text-gold-dark" />
            </div>
            <div className="flex-1">
              <SheetTitle className="font-display font-bold text-ink flex items-center gap-2">
                Business Copilot
                {status.ready === true && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                    Live
                  </span>
                )}
                {status.ready === false && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">
                    Offline
                  </span>
                )}
              </SheetTitle>
              <SheetDescription className="text-xs">Executive-grade answers on sales, finance, inventory, returns.</SheetDescription>
            </div>
            <button
              onClick={reset}
              className="text-xs text-ink-muted hover:text-ink flex items-center gap-1 px-2 py-1 rounded hover:bg-canvas"
              data-testid="ai-reset"
            >
              <RotateCcw size={12} /> New chat
            </button>
          </div>
        </SheetHeader>

        {notReadyBanner}

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
          {messages.length === 0 && (
            <div>
              <div className="text-sm text-ink-muted mb-3">Try one of these:</div>
              <div className="grid grid-cols-1 gap-2">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => send(s)}
                    disabled={loading}
                    className="text-left text-sm rounded-lg border border-[#E5E7EB] p-3 hover:bg-canvas transition flex items-center justify-between group disabled:opacity-50"
                    data-testid={`ai-suggestion-${i}`}
                  >
                    <span>{s}</span>
                    <ChevronRight size={14} className="text-ink-muted opacity-0 group-hover:opacity-100 transition" />
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
              <div className={`max-w-[80%] flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
                <div
                  className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-ink text-white"
                      : m.error
                        ? "bg-amber-50 border border-amber-200 text-ink whitespace-pre-wrap"
                        : "bg-canvas border border-[#E5E7EB] text-ink whitespace-pre-wrap"
                  }`}
                >
                  {m.text}
                </div>
                {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                  <div className="mt-1.5 text-[10px] text-ink-muted space-y-0.5">
                    <div className="font-semibold uppercase tracking-wider">Sources</div>
                    {m.sources.map((s, si) => (
                      <div key={si} className="flex items-center gap-1">
                        <span className="opacity-70">·</span>
                        <span className="font-mono">{s.endpoint}</span>
                      </div>
                    ))}
                  </div>
                )}
                {m.role === "assistant" && m.model && (
                  <div className="mt-1 text-[10px] text-ink-muted">
                    Model: {m.model}{m.intent ? ` · Intent: ${m.intent}` : ""}
                  </div>
                )}
                {m.role === "assistant" && !m.error && m.text && m.text.length > 20 && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <button
                      onClick={() => exportReport(i, m.text, "pdf")}
                      disabled={exporting === `${i}:pdf`}
                      className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border border-[#E5E7EB] text-ink-muted hover:bg-canvas hover:text-ink disabled:opacity-50"
                      data-testid={`ai-export-pdf-${i}`}
                    >
                      {exporting === `${i}:pdf` ? <Loader2 size={11} className="animate-spin" /> : <Download size={11} />} PDF
                    </button>
                    <button
                      onClick={() => exportReport(i, m.text, "excel")}
                      disabled={exporting === `${i}:excel`}
                      className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-md border border-[#E5E7EB] text-ink-muted hover:bg-canvas hover:text-ink disabled:opacity-50"
                      data-testid={`ai-export-excel-${i}`}
                    >
                      {exporting === `${i}:excel` ? <Loader2 size={11} className="animate-spin" /> : <FileSpreadsheet size={11} />} Excel
                    </button>
                  </div>
                )}
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
              placeholder="Ask about sales, finance, inventory, returns…"
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
