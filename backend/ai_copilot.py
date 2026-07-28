"""GO OIL DMS — AI Business Copilot.

A business analyst assistant that answers analytical questions by:
  1. Detecting the user's intent (executive / sales / finance / inventory / party / general).
  2. Fetching the appropriate structured context from analytics endpoints (already computed in Phase 4).
  3. Passing the context + question to the LLM (Emergent Universal Key by default).
  4. Returning: {answer, sources: [{endpoint, key_numbers}], model, tokens, session_id}.

Sessions:
  - Multi-turn conversation history stored in `ai_copilot_sessions` keyed by session_id.
  - Frontend controls session_id lifetime (new session per page, or per user).

Providers:
  - Default provider/model: openai / gpt-5.4 (per verified playbook).
  - Selectable via env vars AI_PROVIDER + AI_MODEL, or per-request 'model' param.
  - Requires EMERGENT_LLM_KEY in env. If missing, returns 503 with a helpful message.

Endpoints (prefix /api/ai/copilot):
  POST /ask               synchronous ask (non-streaming) → recommended for MVP
  GET  /suggestions       list of pre-canned executive questions
  GET  /sessions/{id}     fetch history
  DELETE /sessions/{id}   reset session
"""
from __future__ import annotations
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel

logger = logging.getLogger("gooil.dms.ai_copilot")

# Emergent SDK (optional at import — degrade if missing)
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    _EI_OK = True
except Exception as e:
    _EI_OK = False
    _EI_IMPORT_ERROR = str(e)


DEFAULT_PROVIDER = os.environ.get("AI_PROVIDER", "openai")
DEFAULT_MODEL = os.environ.get("AI_MODEL", "gpt-5.4")

SYSTEM_PROMPT = """You are the GO OIL DMS Business Analyst Copilot.

Your role: an executive-grade business analyst for a Distribution Management System covering
oil & lubricant sales across branches, distributors, retailers and end customers.

RULES:
1. Speak like a seasoned CFO / COO — direct, quantified, concise. No pleasantries or filler.
2. Every material claim MUST cite a number from the CONTEXT block below.
3. Never invent numbers. If the context doesn't contain what's needed, say so and suggest which report to run.
4. Round money to Naira (₦) with commas. Round percentages to one decimal.
5. Use bullet lists for scans. Use paragraphs for narrative diagnoses.
6. When asked "why" questions, list top-3 root causes ordered by impact, each with the supporting metric.
7. When asked "which" questions, return a ranked list of at most 5 items with the deciding metric.
8. Close every answer with a one-line "Next Best Action" prescription.

You are speaking to: {user_role} ({user_name}).
Current date: {today}.
"""

# Canned executive suggestions the frontend can display.
SUGGESTIONS = [
    "Why are sales decreasing this month?",
    "Which distributor has the highest outstanding?",
    "Which products are near expiry in the next 30 days?",
    "Which branch has the lowest inventory turnover?",
    "Which retailer has the most returns?",
    "How many approvals are pending and who is blocked?",
    "Give me a daily executive summary.",
    "What's our biggest cash risk this week?",
    "Which SKUs generated the highest gross margin last month?",
    "Which distributor is under-performing and why?",
]

# Intent → analytics-context to fetch.
INTENT_MATRIX = {
    "sales":     ["sales", "executive"],
    "finance":   ["finance", "executive"],
    "inventory": ["inventory", "executive"],
    "expiry":    ["inventory"],
    "returns":   ["executive"],
    "approvals": ["executive"],
    "executive": ["executive"],
    "general":   ["executive"],
}

_INTENT_KEYWORDS = {
    "sales":     ["sales", "revenue", "top skus", "best selling", "primary order", "secondary order", "growth"],
    "finance":   ["outstanding", "receivable", "aging", "collection", "cash", "wallet", "coupon", "cashback", "ledger", "reconcile"],
    "inventory": ["stock", "inventory", "reorder", "batch", "warehouse"],
    "expiry":    ["expiry", "expiring", "near expiry", "shelf life"],
    "returns":   ["return", "damage", "claim", "replacement", "credit note"],
    "approvals": ["approval", "pending", "waiting", "escalation"],
}


def _detect_intent(q: str) -> str:
    ql = q.lower()
    scores = {intent: sum(1 for kw in kws if kw in ql) for intent, kws in _INTENT_KEYWORDS.items()}
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else "executive"


def _summarise_context(ctx: dict) -> dict:
    """Extract the top 12 numbers from a context blob so the LLM sees only what matters."""
    summary: dict = {}
    if not isinstance(ctx, dict):
        return {"note": "empty"}
    scope = ctx.get("scope")
    if scope == "executive":
        summary["kpis"] = ctx.get("summary", {})
        summary["alerts_by_severity"] = ctx.get("alerts_summary", {})
        summary["top_alerts"] = ctx.get("recent_alerts", [])[:5]
    elif scope == "sales":
        summary["totals"] = ctx.get("totals") or ctx.get("summary") or {}
        summary["top_skus"] = (ctx.get("top_skus") or ctx.get("top") or [])[:5]
        summary["top_distributors"] = (ctx.get("top_distributors") or [])[:5]
        summary["timeseries_tail"] = (ctx.get("timeseries") or ctx.get("series") or [])[-7:]
    elif scope == "finance":
        summary["ar_aging"] = ctx.get("ar_aging") or ctx.get("aging") or {}
        summary["totals"] = ctx.get("totals") or ctx.get("summary") or {}
        summary["top_outstanding"] = (ctx.get("top_outstanding") or [])[:5]
    elif scope == "inventory":
        summary["buckets"] = ctx.get("buckets") or ctx.get("totals") or {}
        summary["expiring"] = (ctx.get("expiring") or ctx.get("near_expiry") or [])[:8]
        summary["low_stock"] = (ctx.get("low_stock") or [])[:8]
    else:
        summary = ctx
    return summary


class AskIn(BaseModel):
    question: str
    session_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


def build_ai_copilot_router(db, get_current_user, analytics_router):
    router = APIRouter(prefix="/ai/copilot", tags=["ai-copilot"])

    # Locate the ai-context callable on the analytics router — cheaper than HTTP loopback.
    _ai_context_endpoint = None
    for r in analytics_router.routes:
        if getattr(r, "path", "").endswith("/ai-context/{scope}"):
            _ai_context_endpoint = r.endpoint
            break

    async def _gather_context(intents: List[str], user: dict) -> List[dict]:
        collected: List[dict] = []
        for intent in intents:
            scope = intent if intent in ("executive", "sales", "finance", "inventory") else "executive"
            try:
                if _ai_context_endpoint:
                    ctx = await _ai_context_endpoint(scope=scope, user=user)
                    collected.append({
                        "scope": scope,
                        "endpoint": f"/api/analytics/ai-context/{scope}",
                        "context": ctx,
                    })
            except Exception as e:
                logger.warning(f"ai-context/{scope} failed: {e}")
        return collected

    def _extract_sources(gathered: List[dict]) -> List[dict]:
        out = []
        for g in gathered:
            summ = _summarise_context(g.get("context") or {})
            key_numbers = {}
            # try to pull 3-5 headline numbers
            if "kpis" in summ and isinstance(summ["kpis"], dict):
                for k, v in list(summ["kpis"].items())[:5]:
                    if isinstance(v, (int, float, str)):
                        key_numbers[k] = v
            elif "totals" in summ and isinstance(summ["totals"], dict):
                for k, v in list(summ["totals"].items())[:5]:
                    if isinstance(v, (int, float, str)):
                        key_numbers[k] = v
            out.append({
                "endpoint": g["endpoint"],
                "scope": g["scope"],
                "key_numbers": key_numbers,
            })
        return out

    async def _load_history(session_id: str) -> List[dict]:
        s = await db.ai_copilot_sessions.find_one({"id": session_id}, {"_id": 0})
        return (s or {}).get("history", [])

    async def _save_history(session_id: str, user_id: str, history: List[dict]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await db.ai_copilot_sessions.update_one(
            {"id": session_id},
            {"$set": {"history": history, "user_id": user_id, "updated_at": now},
             "$setOnInsert": {"id": session_id, "created_at": now}},
            upsert=True,
        )

    @router.get("/suggestions")
    async def suggestions(user: dict = Depends(get_current_user)):
        return {"data": SUGGESTIONS}

    @router.get("/status")
    async def status(user: dict = Depends(get_current_user)):
        key_set = bool(os.environ.get("EMERGENT_LLM_KEY"))
        return {
            "sdk_available": _EI_OK,
            "key_configured": key_set,
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
            "ready": _EI_OK and key_set,
            "message": (
                "Ready" if _EI_OK and key_set
                else "AI Copilot requires EMERGENT_LLM_KEY in backend/.env "
                     "(get one from Emergent → Profile → Universal Key)."
            ),
        }

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str, user: dict = Depends(get_current_user)):
        s = await db.ai_copilot_sessions.find_one({"id": session_id, "user_id": user["id"]}, {"_id": 0})
        if not s:
            return {"id": session_id, "history": []}
        return s

    @router.delete("/sessions/{session_id}")
    async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
        r = await db.ai_copilot_sessions.delete_one({"id": session_id, "user_id": user["id"]})
        return {"ok": True, "deleted": r.deleted_count}

    @router.post("/ask")
    async def ask(body: AskIn, user: dict = Depends(get_current_user)):
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not _EI_OK:
            raise HTTPException(
                503,
                f"emergentintegrations SDK unavailable: {globals().get('_EI_IMPORT_ERROR', 'unknown')}",
            )
        if not api_key:
            raise HTTPException(
                503,
                "EMERGENT_LLM_KEY not configured. Please add it to backend/.env "
                "and restart. Get your key from Emergent → Profile → Universal Key.",
            )

        question = (body.question or "").strip()
        if not question:
            raise HTTPException(400, "Question is required")

        session_id = body.session_id or f"sess-{uuid.uuid4().hex[:12]}"
        provider = (body.provider or DEFAULT_PROVIDER).lower()
        model = body.model or DEFAULT_MODEL

        # 1. Gather structured context from our analytics layer
        intent = _detect_intent(question)
        scopes = INTENT_MATRIX.get(intent, INTENT_MATRIX["executive"])
        gathered = await _gather_context(scopes, user)
        context_bundle = {
            "user": {"name": user.get("name"), "role": user.get("role"),
                        "email": user.get("email")},
            "date": datetime.now(timezone.utc).isoformat(),
            "detected_intent": intent,
            "contexts": [{"scope": g["scope"], "data": _summarise_context(g["context"])}
                          for g in gathered],
        }

        # 2. Build the LLM chat
        system_message = SYSTEM_PROMPT.format(
            user_role=user.get("role", "executive"),
            user_name=user.get("name", "there"),
            today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        try:
            chat = LlmChat(
                api_key=api_key,
                session_id=session_id,
                system_message=system_message,
            ).with_model(provider, model)
        except Exception as e:
            raise HTTPException(500, f"Failed to initialise LlmChat ({provider}/{model}): {e}")

        # 3. Load prior history and replay (LlmChat is stateless across calls)
        history = await _load_history(session_id)
        # LlmChat replay is done implicitly through session id in some SDKs;
        # to be safe we prepend prior turns to the current user message.

        prior_transcript = ""
        for turn in history[-6:]:  # last 3 exchanges
            role = turn.get("role", "user")
            prior_transcript += f"\n[{role.upper()}]: {turn.get('content','')}\n"

        composed = (
            f"{prior_transcript}\n"
            f"CONTEXT (structured business snapshot for your reference):\n"
            f"{json.dumps(context_bundle, default=str)[:8000]}\n\n"
            f"USER QUESTION: {question}"
        )

        # 4. Non-streaming call (per user pref "lean & real")
        try:
            resp = await chat.send_message(UserMessage(text=composed))
        except AttributeError:
            # Some SDK versions expose only stream_message — fall back to collecting text.
            try:
                from emergentintegrations.llm.chat import TextDelta, StreamDone
                chunks: List[str] = []
                async for ev in chat.stream_message(UserMessage(text=composed)):
                    if isinstance(ev, TextDelta):
                        chunks.append(ev.content)
                    elif isinstance(ev, StreamDone):
                        break
                resp = "".join(chunks)
            except Exception as e:
                raise HTTPException(500, f"LLM call failed: {e}")
        except Exception as e:
            raise HTTPException(500, f"LLM call failed: {e}")

        # LlmChat.send_message returns either a string, or a response object with .content.
        if isinstance(resp, str):
            answer_text = resp
            usage = None
        else:
            answer_text = getattr(resp, "content", None) or getattr(resp, "text", None) or str(resp)
            usage = getattr(resp, "usage", None)

        # 5. Persist history
        history = history + [
            {"role": "user", "content": question,
             "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": answer_text,
             "timestamp": datetime.now(timezone.utc).isoformat(),
             "model": f"{provider}/{model}"},
        ]
        await _save_history(session_id, user["id"], history[-40:])  # cap history

        return {
            "session_id": session_id,
            "answer": answer_text,
            "sources": _extract_sources(gathered),
            "intent": intent,
            "model": f"{provider}/{model}",
            "usage": usage,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    return router
