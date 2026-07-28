"""GO OIL DMS — Notification Engine.

Design:
  - Provider-agnostic dispatch bus with pluggable channels.
  - In-app is always live (persisted to `notifications` collection).
  - Email / WhatsApp / SMS channels are scaffolded (no external send yet) — they log the payload
    and return a delivery ticket. Real providers (SendGrid, Twilio, WhatsApp Business API) can
    be dropped in without changing call sites.
  - Preferences per user stored in `notification_preferences`.
  - Every notification carries `channel`, `severity`, `entity`, `actor`, `payload`, so the UI
    can group / filter / deep-link into the record.

Endpoints (prefix /api/notifications):
  GET  /                        list for current user (paginated)
  GET  /unread-count            { unread: int }
  POST /mark-read/{id}
  POST /mark-all-read
  DELETE /{id}
  GET  /preferences             per-user preference map
  PUT  /preferences             update preferences
  POST /send                    admin-only test send
  POST /trigger/{event}         admin-only manual event trigger (for QA)
"""
from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel

logger = logging.getLogger("gooil.dms.notifications")

DEFAULT_CHANNELS = ["in_app", "email", "whatsapp", "sms"]
DEFAULT_SEVERITIES = ["info", "success", "warning", "critical"]

# Default preference: in-app always on; other channels off until user opts in.
DEFAULT_PREFERENCES = {
    "in_app": True,
    "email": True,   # scaffolded (no send)
    "whatsapp": False,
    "sms": False,
    "digest": "off",  # off | daily | weekly
    "muted_categories": [],
}

# ---------- Channel adapters (scaffolds) ----------


class ChannelResult(dict):
    """Delivery ticket returned by every channel."""

    def __init__(self, channel: str, ok: bool, provider: str = "scaffold",
                 message_id: str | None = None, error: str | None = None):
        super().__init__(
            channel=channel,
            ok=ok,
            provider=provider,
            message_id=message_id,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class InAppChannel:
    name = "in_app"

    def __init__(self, db):
        self.db = db

    async def send(self, notif: dict) -> ChannelResult:
        # Already persisted by NotificationBus.dispatch — this is a no-op ack.
        return ChannelResult("in_app", ok=True, provider="db", message_id=notif["id"])


class EmailChannel:
    """Scaffold — plug in SendGrid/SMTP later.

    Configure via env: EMAIL_PROVIDER=sendgrid|smtp, SENDGRID_API_KEY / SMTP_URL, EMAIL_FROM.
    While unconfigured, we log the payload so QA can verify triggers.
    """
    name = "email"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def send(self, notif: dict) -> ChannelResult:
        provider = self.config.get("provider", "unconfigured")
        if provider == "unconfigured":
            logger.info(f"[notif/email SCAFFOLD] to={notif.get('recipient_email')} subj={notif.get('title')}")
            return ChannelResult("email", ok=True, provider="scaffold",
                                 message_id=f"stub-{uuid.uuid4().hex[:8]}")
        # Real provider integration would go here.
        return ChannelResult("email", ok=True, provider=provider)


class WhatsAppChannel:
    name = "whatsapp"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def send(self, notif: dict) -> ChannelResult:
        provider = self.config.get("provider", "unconfigured")
        if provider == "unconfigured":
            logger.info(f"[notif/whatsapp SCAFFOLD] to={notif.get('recipient_phone')} body={notif.get('body')[:100] if notif.get('body') else ''}")
            return ChannelResult("whatsapp", ok=True, provider="scaffold",
                                 message_id=f"stub-{uuid.uuid4().hex[:8]}")
        return ChannelResult("whatsapp", ok=True, provider=provider)


class SMSChannel:
    name = "sms"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def send(self, notif: dict) -> ChannelResult:
        provider = self.config.get("provider", "unconfigured")
        if provider == "unconfigured":
            logger.info(f"[notif/sms SCAFFOLD] to={notif.get('recipient_phone')} body={notif.get('body')[:70] if notif.get('body') else ''}")
            return ChannelResult("sms", ok=True, provider="scaffold",
                                 message_id=f"stub-{uuid.uuid4().hex[:8]}")
        return ChannelResult("sms", ok=True, provider=provider)


# ---------- Bus ----------


class NotificationBus:
    def __init__(self, db):
        self.db = db
        self.channels = {
            "in_app": InAppChannel(db),
            "email": EmailChannel(),
            "whatsapp": WhatsAppChannel(),
            "sms": SMSChannel(),
        }

    async def _get_preferences(self, user_id: str) -> dict:
        p = await self.db.notification_preferences.find_one({"user_id": user_id}, {"_id": 0})
        if not p:
            return {"user_id": user_id, **DEFAULT_PREFERENCES}
        merged = {**DEFAULT_PREFERENCES, **p}
        return merged

    async def _persist(self, notif: dict) -> None:
        await self.db.notifications.insert_one(dict(notif))

    async def dispatch(
        self,
        *,
        recipient_id: str,
        title: str,
        body: str,
        category: str = "general",
        severity: str = "info",
        entity_type: str | None = None,
        entity_id: str | None = None,
        actor_id: str | None = None,
        payload: dict | None = None,
        channels: list[str] | None = None,
        recipient_email: str | None = None,
        recipient_phone: str | None = None,
    ) -> dict:
        """Dispatch a notification. Returns the persisted in-app record + delivery tickets."""
        prefs = await self._get_preferences(recipient_id)
        if category in (prefs.get("muted_categories") or []):
            return {"skipped": "muted", "category": category}
        channels_to_try = channels or [c for c in DEFAULT_CHANNELS if prefs.get(c, False)]
        # in_app always mandatory
        if "in_app" not in channels_to_try:
            channels_to_try = ["in_app"] + channels_to_try

        notif = {
            "id": f"notif-{uuid.uuid4().hex[:12]}",
            "recipient_id": recipient_id,
            "recipient_email": recipient_email,
            "recipient_phone": recipient_phone,
            "title": title,
            "body": body,
            "category": category,
            "severity": severity if severity in DEFAULT_SEVERITIES else "info",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_id": actor_id,
            "payload": payload or {},
            "read": False,
            "delivery": {},
            "channels": channels_to_try,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._persist(notif)
        for ch in channels_to_try:
            adapter = self.channels.get(ch)
            if not adapter:
                continue
            try:
                result = await adapter.send(notif)
                notif["delivery"][ch] = dict(result)
            except Exception as e:
                notif["delivery"][ch] = {"ok": False, "error": str(e)}
                logger.exception(f"channel {ch} failed for notif {notif['id']}")
        # persist delivery ticket
        await self.db.notifications.update_one(
            {"id": notif["id"]}, {"$set": {"delivery": notif["delivery"]}},
        )
        return notif


# ---------- Router ----------


class PrefsUpdate(BaseModel):
    in_app: Optional[bool] = None
    email: Optional[bool] = None
    whatsapp: Optional[bool] = None
    sms: Optional[bool] = None
    digest: Optional[str] = None
    muted_categories: Optional[List[str]] = None


class ManualSend(BaseModel):
    recipient_id: str
    title: str
    body: str
    category: str = "general"
    severity: str = "info"
    channels: Optional[List[str]] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None


def build_notifications_router(db, get_current_user, require_admin_dep=None):
    bus = NotificationBus(db)
    router = APIRouter(prefix="/notifications", tags=["notifications"])

    @router.get("/")
    async def list_my_notifications(
        limit: int = Query(50, ge=1, le=200),
        unread_only: bool = Query(False),
        category: Optional[str] = Query(None),
        user: dict = Depends(get_current_user),
    ):
        q: Dict[str, Any] = {"recipient_id": user["id"]}
        if unread_only:
            q["read"] = False
        if category:
            q["category"] = category
        rows = await db.notifications.find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"data": rows, "count": len(rows)}

    @router.get("/unread-count")
    async def unread_count(user: dict = Depends(get_current_user)):
        n = await db.notifications.count_documents({"recipient_id": user["id"], "read": False})
        return {"unread": n}

    @router.post("/mark-read/{notif_id}")
    async def mark_read(notif_id: str, user: dict = Depends(get_current_user)):
        r = await db.notifications.update_one(
            {"id": notif_id, "recipient_id": user["id"]},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
        )
        if r.matched_count == 0:
            raise HTTPException(404, "Notification not found")
        return {"ok": True}

    @router.post("/mark-all-read")
    async def mark_all_read(user: dict = Depends(get_current_user)):
        r = await db.notifications.update_many(
            {"recipient_id": user["id"], "read": False},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "updated": r.modified_count}

    @router.delete("/{notif_id}")
    async def delete_notif(notif_id: str, user: dict = Depends(get_current_user)):
        r = await db.notifications.delete_one({"id": notif_id, "recipient_id": user["id"]})
        if r.deleted_count == 0:
            raise HTTPException(404, "Notification not found")
        return {"ok": True}

    @router.get("/preferences")
    async def get_prefs(user: dict = Depends(get_current_user)):
        return await bus._get_preferences(user["id"])

    @router.put("/preferences")
    async def set_prefs(body: PrefsUpdate, user: dict = Depends(get_current_user)):
        upd = {k: v for k, v in body.dict().items() if v is not None}
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Build $setOnInsert with defaults that aren't being updated
        insert_doc = {"user_id": user["id"], "created_at": upd["updated_at"]}
        for k, v in DEFAULT_PREFERENCES.items():
            if k not in upd:
                insert_doc[k] = v
        await db.notification_preferences.update_one(
            {"user_id": user["id"]},
            {"$set": upd, "$setOnInsert": insert_doc},
            upsert=True,
        )
        return await bus._get_preferences(user["id"])

    @router.post("/send")
    async def manual_send(body: ManualSend, user: dict = Depends(get_current_user)):
        # allow anyone to send to self; only admin roles can send to others.
        if body.recipient_id != user["id"] and user.get("role") not in ("super_admin", "company_admin"):
            raise HTTPException(403, "Cannot send to another user")
        return await bus.dispatch(
            recipient_id=body.recipient_id,
            title=body.title,
            body=body.body,
            category=body.category,
            severity=body.severity,
            channels=body.channels,
            actor_id=user["id"],
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )

    @router.post("/trigger/{event}")
    async def trigger_demo(event: str, user: dict = Depends(get_current_user)):
        """QA convenience endpoint — fires a canned notification of the given event kind."""
        if user.get("role") not in ("super_admin", "company_admin"):
            raise HTTPException(403, "Admin only")
        specs = {
            "approval_pending": ("Approval waiting", "You have an approval request awaiting review.", "warning", "approvals"),
            "low_stock": ("Low stock alert", "SKU stock is below reorder point at your branch.", "warning", "inventory"),
            "expiry_warning": ("Expiry warning", "A batch will expire in 15 days.", "warning", "expiry"),
            "payment_received": ("Payment received", "A payment has been credited.", "success", "finance"),
            "invoice_created": ("New invoice", "A new invoice has been issued.", "info", "billing"),
            "claim_settled": ("Claim settled", "Your claim has been approved and settled.", "success", "claims"),
        }
        spec = specs.get(event)
        if not spec:
            raise HTTPException(404, f"Unknown event '{event}'")
        title, body, sev, cat = spec
        return await bus.dispatch(
            recipient_id=user["id"], title=title, body=body,
            severity=sev, category=cat, actor_id=user["id"],
        )

    router._bus = bus  # expose for import elsewhere if needed
    return router


# expose a factory that other modules can import to publish events without router coupling
def get_bus(db) -> NotificationBus:
    return NotificationBus(db)
