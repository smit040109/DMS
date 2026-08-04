"""
GO OIL — Enterprise Coupon & Reward Engine
==========================================

Domain-Driven design for coupon lifecycle management with:
 * Two independent coupon systems: CASH (₹) and REWARD (points)
 * Immutable wallet-transaction ledger — balance is DERIVED, never stored
 * Immutable audit log for every state transition
 * Secure QR payload (code + secret token + HMAC signature)
 * Sales-Officer-only scan flow (retailer -> distributor auto)
 * Owner/Accountant driven redemption workflow producing Credit Notes
   (cash) or Dispatch Advices (points)

Collections (all prefixed dms_v2_ to isolate from legacy coupons):
  dms_v2_coupon_batches
  dms_v2_coupons
  dms_v2_retailer_wallets            (identity rows only)
  dms_v2_wallet_transactions         (immutable)
  dms_v2_redemption_requests
  dms_v2_credit_notes
  dms_v2_dispatch_advices
  dms_v2_coupon_audit_log            (immutable)
  dms_v2_coupon_fraud_attempts

Mounted at:  /api/dms/coupons/*
"""
from __future__ import annotations

import hmac
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import Response


# ═════════════════════════ helpers ══════════════════════════════════════════
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _clean(d: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


def _round(v: Any, n: int = 2) -> float:
    try:
        return round(float(v), n)
    except Exception:
        return 0.0


# ── crypto helpers ─────────────────────────────────────────────────────────
_APP_SECRET = os.environ.get("COUPON_MASTER_SECRET") or os.environ.get("JWT_SECRET") or "gooil-master-secret"


def _random_group(n: int = 4) -> str:
    """4-char base32-like group using an unambiguous alphabet."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # skip 0/O/1/I
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _gen_coupon_code(prefix: str = "GO") -> str:
    """
    Generates a non-sequential, secure coupon code like  QSRD-9X7K-LA82-MPQ4.
    Prefix is optional and only used inside PDF header for human readability.
    """
    return "-".join(_random_group(4) for _ in range(4))


def _gen_secret_token() -> str:
    return secrets.token_hex(16)  # 32-char hex


def _sign(batch_secret: str, coupon_code: str, secret_token: str) -> str:
    """HMAC-SHA256 signature — batch_secret keeps signatures batch-scoped."""
    msg = f"{coupon_code}|{secret_token}".encode()
    key = (batch_secret + "|" + _APP_SECRET).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def _qr_payload(coupon_code: str, secret_token: str, signature: str) -> str:
    """JSON-ish compact payload embedded in QR."""
    return f"GOOIL:{coupon_code}:{secret_token}:{signature}"


def _qr_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


def _parse_qr(payload: str) -> Optional[Tuple[str, str, str]]:
    """Returns (code, token, signature) or None if malformed."""
    if not payload:
        return None
    p = payload.strip()
    if p.startswith("GOOIL:"):
        parts = p[len("GOOIL:"):].split(":")
        if len(parts) == 3:
            return parts[0].upper().strip(), parts[1].strip(), parts[2].strip()
    return None


# ═════════════════════════ router builder ══════════════════════════════════
def build_coupons_router(db, get_current_user, notify=None):
    """
    Args:
        db: motor asyncio db
        get_current_user: FastAPI dependency returning user dict
        notify: optional async notify(user_id, kind, title, body, url) callable
    """
    router = APIRouter(prefix="/dms/coupons", tags=["dms-coupons"])

    # ── role guards ─────────────────────────────────────────────────────────
    def _guard(*allowed):
        async def _dep(user: dict = Depends(get_current_user)) -> dict:
            role = user.get("role")
            if role in allowed or role == "super_admin":
                return user
            raise HTTPException(status_code=403, detail=f"Requires role in {allowed}")
        return _dep

    owner_only = _guard("owner")
    owner_or_accountant = _guard("owner", "owner_accountant")
    salesperson_only = _guard("salesperson")

    # ── audit helper ────────────────────────────────────────────────────────
    async def _audit(user: dict, event: str, entity_type: str, entity_id: str,
                     details: Optional[Dict[str, Any]] = None) -> None:
        await db.dms_v2_coupon_audit_log.insert_one({
            "id": _nid("aud"),
            "event": event,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_id": user.get("id"),
            "actor_name": user.get("name") or user.get("email"),
            "actor_role": user.get("role"),
            "details": details or {},
            "at": _now(),
        })

    # ── fraud logging ───────────────────────────────────────────────────────
    async def _log_fraud(reason: str, coupon_code: str, user: dict,
                         retailer_id: Optional[str] = None,
                         distributor_id: Optional[str] = None,
                         extra: Optional[Dict[str, Any]] = None):
        await db.dms_v2_coupon_fraud_attempts.insert_one({
            "id": _nid("fra"),
            "reason": reason,
            "coupon_code": coupon_code,
            "actor_id": user.get("id"),
            "actor_name": user.get("name"),
            "actor_role": user.get("role"),
            "retailer_id": retailer_id,
            "distributor_id": distributor_id,
            "extra": extra or {},
            "at": _now(),
        })

    # ── wallet balance derivation (never stored) ────────────────────────────
    async def _wallet_balance(retailer_id: str, wallet_type: str) -> float:
        """Balance = SUM(signed amount) across all wallet transactions."""
        cursor = db.dms_v2_wallet_transactions.aggregate([
            {"$match": {"retailer_id": retailer_id, "wallet_type": wallet_type}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ])
        async for row in cursor:
            return _round(row.get("total", 0))
        return 0.0

    async def _ensure_wallet(retailer_id: str, wallet_type: str) -> None:
        await db.dms_v2_retailer_wallets.update_one(
            {"retailer_id": retailer_id, "wallet_type": wallet_type},
            {"$setOnInsert": {
                "id": _nid("wal"),
                "retailer_id": retailer_id,
                "wallet_type": wallet_type,
                "created_at": _now(),
            }},
            upsert=True,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # BATCH MANAGEMENT (Owner)
    # ─────────────────────────────────────────────────────────────────────────
    @router.post("/batches")
    async def create_batch(body: Dict[str, Any] = Body(...), user: dict = Depends(owner_only)):
        """Generate a new coupon batch. Coupons are CREATED in status='generated'
        (NOT yet usable) — Owner must Activate the batch before use."""
        title = (body.get("title") or "").strip()
        coupon_type = (body.get("coupon_type") or "").strip().lower()
        coupon_value = _round(body.get("coupon_value", 0))
        count = int(body.get("count") or 0)
        notes = (body.get("notes") or "").strip()
        expires_at = body.get("expires_at")  # optional ISO date

        if coupon_type not in ("cash", "reward"):
            raise HTTPException(400, "coupon_type must be 'cash' or 'reward'")
        if coupon_value <= 0:
            raise HTTPException(400, "coupon_value must be > 0")
        if count <= 0 or count > 100_000:
            raise HTTPException(400, "count must be between 1 and 100,000")
        if not title:
            title = f"{coupon_type.upper()} ₹{coupon_value:g} × {count}"

        # allocate batch_no
        counter = await db.dms_v2_meta.find_one_and_update(
            {"key": "batch_counter"}, {"$inc": {"value": 1}},
            upsert=True, return_document=True,
        )
        batch_no = int((counter or {}).get("value", 1))

        batch_id = _nid("cbt")
        batch_secret = secrets.token_hex(24)
        batch_doc = {
            "id": batch_id,
            "batch_no": batch_no,
            "batch_label": f"GO-{coupon_type.upper()[:1]}-{batch_no:05d}",
            "title": title,
            "coupon_type": coupon_type,
            "coupon_value": coupon_value,
            "count": count,
            "notes": notes,
            "expires_at": expires_at,
            "status": "generated",           # generated → activated → printed → issued
            "active": False,                  # becomes True on activate
            "hmac_secret": batch_secret,
            "created_by": user["id"],
            "created_by_name": user.get("name"),
            "created_at": _now(),
            "activated_at": None,
            "activated_by": None,
            "printed_at": None,
            "printed_by": None,
            "issued_at": None,
            "issued_by": None,
            "closed_at": None,
        }
        await db.dms_v2_coupon_batches.insert_one(batch_doc)

        # bulk create coupons (chunked)
        CHUNK = 2000
        codes_seen: set[str] = set()
        created = 0
        while created < count:
            n_this = min(CHUNK, count - created)
            docs: List[Dict[str, Any]] = []
            for _ in range(n_this):
                # ensure uniqueness inside the batch (16^16 collision practically 0)
                while True:
                    code = _gen_coupon_code()
                    if code not in codes_seen:
                        codes_seen.add(code)
                        break
                token = _gen_secret_token()
                sig = _sign(batch_secret, code, token)
                qr = _qr_payload(code, token, sig)
                docs.append({
                    "id": _nid("cpn"),
                    "coupon_code": code,
                    "batch_id": batch_id,
                    "batch_no": batch_no,
                    "batch_label": batch_doc["batch_label"],
                    "coupon_type": coupon_type,
                    "coupon_value": coupon_value,
                    "secret_token": token,
                    "signature": sig,
                    "qr_hash": _qr_hash(qr),
                    "status": "generated",   # generated → activated → printed → issued_to_production → unused → claimed → redemption_pending → redeemed
                    "active": False,
                    "claimed_by_user_id": None,
                    "claimed_by_user_name": None,
                    "claim_timestamp": None,
                    "retailer_id": None,
                    "retailer_name": None,
                    "distributor_id": None,
                    "distributor_name": None,
                    "wallet_transaction_id": None,
                    "redemption_request_id": None,
                    "expires_at": expires_at,
                    "created_at": _now(),
                    "updated_at": _now(),
                })
            await db.dms_v2_coupons.insert_many(docs)
            created += n_this

        await _audit(user, "batch.generated", "batch", batch_id, {
            "count": count, "coupon_type": coupon_type,
            "coupon_value": coupon_value, "batch_label": batch_doc["batch_label"],
        })

        return {
            "ok": True, "batch": _clean(batch_doc),
            "message": f"Generated {count} coupons in batch {batch_doc['batch_label']}. "
                       f"Activate the batch to make them usable.",
        }

    @router.post("/batches/{bid}/activate")
    async def activate_batch(bid: str, user: dict = Depends(owner_only)):
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        if b["status"] not in ("generated",):
            raise HTTPException(400, f"Batch is already {b['status']}; only 'generated' batches can be activated")
        await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
            "status": "activated", "active": True,
            "activated_at": _now(), "activated_by": user["id"],
        }})
        # activate all coupons in batch — move status to 'unused' (usable),
        # printed/issued flags are optional operational tags handled below.
        await db.dms_v2_coupons.update_many(
            {"batch_id": bid, "status": "generated"},
            {"$set": {"status": "unused", "active": True, "updated_at": _now()}},
        )
        await _audit(user, "batch.activated", "batch", bid, {"batch_label": b["batch_label"]})
        return {"ok": True, "message": f"Batch {b['batch_label']} activated"}

    @router.post("/batches/{bid}/mark-printed")
    async def mark_printed(bid: str, user: dict = Depends(owner_only)):
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        if not b.get("active"):
            raise HTTPException(400, "Activate the batch before marking as printed")
        await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
            "status": "printed" if b["status"] in ("activated", "printed") else b["status"],
            "printed_at": _now(), "printed_by": user["id"],
        }})
        await _audit(user, "batch.printed", "batch", bid, {"batch_label": b["batch_label"]})
        return {"ok": True}

    @router.post("/batches/{bid}/issue-to-production")
    async def issue_to_production(bid: str, user: dict = Depends(owner_only)):
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        if not b.get("active"):
            raise HTTPException(400, "Activate the batch before issuing to production")
        await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
            "status": "issued_to_production",
            "issued_at": _now(), "issued_by": user["id"],
        }})
        await _audit(user, "batch.issued_to_production", "batch", bid, {"batch_label": b["batch_label"]})
        return {"ok": True}

    @router.post("/batches/{bid}/deactivate")
    async def deactivate_batch(bid: str, user: dict = Depends(owner_only)):
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
            "active": False, "closed_at": _now(),
        }})
        # cancel remaining unused coupons
        await db.dms_v2_coupons.update_many(
            {"batch_id": bid, "status": "unused"},
            {"$set": {"status": "cancelled", "active": False, "updated_at": _now()}},
        )
        await _audit(user, "batch.deactivated", "batch", bid, {"batch_label": b["batch_label"]})
        return {"ok": True}

    @router.get("/batches")
    async def list_batches(
        status: Optional[str] = Query(None),
        coupon_type: Optional[str] = Query(None),
        user: dict = Depends(get_current_user),
    ):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if coupon_type: q["coupon_type"] = coupon_type
        docs = await db.dms_v2_coupon_batches.find(q, {"_id": 0, "hmac_secret": 0})\
            .sort("batch_no", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/batches/{bid}")
    async def get_batch(bid: str, user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        b.pop("hmac_secret", None)
        # counts by status
        pipeline = [
            {"$match": {"batch_id": bid}},
            {"$group": {"_id": "$status", "n": {"$sum": 1}}},
        ]
        by_status: Dict[str, int] = {}
        async for row in db.dms_v2_coupons.aggregate(pipeline):
            by_status[row["_id"]] = row["n"]
        b["counts_by_status"] = by_status
        b["total_value"] = _round(b["coupon_value"] * b["count"])
        return b

    # ─────────────────────────────────────────────────────────────────────────
    # PRINT / EXPORT (PDF grid + Excel manifest)
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/batches/{bid}/export-pdf")
    async def export_pdf(bid: str, user: dict = Depends(owner_only)):
        """
        Printable PDF grid — 3×4 = 12 coupons per A4 page.
        Each cell: QR + coupon code + type + value + batch label.
        """
        import qrcode
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.utils import ImageReader

        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        secret = b["hmac_secret"]
        coupons = await db.dms_v2_coupons.find({"batch_id": bid}, {"_id": 0}).to_list(200_000)
        if not coupons:
            raise HTTPException(400, "No coupons in batch")

        buf = BytesIO()
        c = pdfcanvas.Canvas(buf, pagesize=A4)
        page_w, page_h = A4
        margin = 12 * mm
        cols, rows = 3, 4
        cell_w = (page_w - 2 * margin) / cols
        cell_h = (page_h - 2 * margin) / rows

        for i, cp in enumerate(coupons):
            col = i % cols
            row = (i // cols) % rows
            new_page_needed = i > 0 and i % (cols * rows) == 0
            if new_page_needed:
                c.showPage()

            x0 = margin + col * cell_w
            y0 = page_h - margin - (row + 1) * cell_h

            # border
            c.setLineWidth(0.6)
            c.rect(x0 + 2, y0 + 2, cell_w - 4, cell_h - 4)

            # QR
            payload = _qr_payload(cp["coupon_code"], cp["secret_token"], cp["signature"])
            qr_img = qrcode.make(payload)
            qr_reader = ImageReader(qr_img.get_image() if hasattr(qr_img, "get_image") else qr_img)
            qr_size = min(cell_w, cell_h) * 0.55
            c.drawImage(qr_reader,
                        x0 + (cell_w - qr_size) / 2,
                        y0 + cell_h - qr_size - 8 * mm,
                        width=qr_size, height=qr_size,
                        preserveAspectRatio=True, mask="auto")

            # text block below QR
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(x0 + cell_w / 2, y0 + cell_h - qr_size - 12 * mm, "GO OIL")
            c.setFont("Helvetica", 7)
            type_label = "CASH ₹" if b["coupon_type"] == "cash" else "REWARD "
            unit = "" if b["coupon_type"] == "cash" else " pts"
            c.drawCentredString(x0 + cell_w / 2, y0 + cell_h - qr_size - 16 * mm,
                                f"{type_label}{b['coupon_value']:g}{unit}")
            c.setFont("Courier-Bold", 8)
            c.drawCentredString(x0 + cell_w / 2, y0 + cell_h - qr_size - 20 * mm,
                                cp["coupon_code"])
            c.setFont("Helvetica-Oblique", 6)
            c.drawCentredString(x0 + cell_w / 2, y0 + 6 * mm,
                                f"{b['batch_label']} • Do not photocopy")

        c.showPage()
        c.save()
        buf.seek(0)
        # mark printed (idempotent)
        if b["status"] in ("activated",):
            await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
                "status": "printed", "printed_at": _now(), "printed_by": user["id"],
            }})
            await _audit(user, "batch.printed", "batch", bid, {"batch_label": b["batch_label"]})

        return Response(
            content=buf.read(),
            media_type="application/pdf",
            headers={"Content-Disposition":
                     f'attachment; filename="{b["batch_label"]}_coupons.pdf"'},
        )

    @router.get("/batches/{bid}/export-xlsx")
    async def export_xlsx(bid: str, user: dict = Depends(owner_only)):
        from openpyxl import Workbook
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        coupons = await db.dms_v2_coupons.find({"batch_id": bid}, {"_id": 0})\
            .sort("coupon_code", 1).to_list(200_000)
        wb = Workbook()
        ws = wb.active
        ws.title = "Coupons"
        ws.append([
            "Coupon Code", "Type", "Value", "Status", "Batch",
            "Retailer", "Distributor", "Claimed On", "Claimed By", "QR Payload",
        ])
        for cp in coupons:
            payload = _qr_payload(cp["coupon_code"], cp["secret_token"], cp["signature"])
            ws.append([
                cp["coupon_code"], cp["coupon_type"], cp["coupon_value"],
                cp["status"], b["batch_label"],
                cp.get("retailer_name") or "",
                cp.get("distributor_name") or "",
                (cp.get("claim_timestamp") or "")[:19].replace("T", " "),
                cp.get("claimed_by_user_name") or "",
                payload,
            ])
        for col in "ABCDEFGHIJ":
            ws.column_dimensions[col].width = 22

        out = BytesIO()
        wb.save(out)
        out.seek(0)
        return Response(
            content=out.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition":
                     f'attachment; filename="{b["batch_label"]}_manifest.xlsx"'},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # COUPON LISTING (Owner)
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("")
    async def list_coupons(
        status: Optional[str] = Query(None),
        coupon_type: Optional[str] = Query(None),
        batch_id: Optional[str] = Query(None),
        retailer_id: Optional[str] = Query(None),
        distributor_id: Optional[str] = Query(None),
        code: Optional[str] = Query(None),
        limit: int = Query(200, ge=1, le=1000),
        user: dict = Depends(get_current_user),
    ):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if coupon_type: q["coupon_type"] = coupon_type
        if batch_id: q["batch_id"] = batch_id
        if retailer_id: q["retailer_id"] = retailer_id
        if distributor_id: q["distributor_id"] = distributor_id
        if code: q["coupon_code"] = code.strip().upper()
        docs = await db.dms_v2_coupons.find(q, {"_id": 0, "secret_token": 0, "signature": 0})\
            .sort("created_at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/detail/{cid}")
    async def get_coupon(cid: str, user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        # hide secrets
        cp.pop("secret_token", None)
        cp.pop("signature", None)
        return cp

    # ─────────────────────────────────────────────────────────────────────────
    # SALES OFFICER (salesperson) — SCAN FLOW
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/so/retailers")
    async def so_retailers(user: dict = Depends(salesperson_only)):
        """Retailers under distributors assigned to this Sales Officer.
        Distributor is auto-derived from the selected retailer (spec)."""
        sp_id = user["id"]
        dist_ids = await db.dms_sp_assignments.distinct("distributor_id", {"salesperson_id": sp_id})
        if not dist_ids:
            return {"data": [], "count": 0}
        retailers = await db.dms_retailers.find(
            {"distributor_id": {"$in": dist_ids}},
            {"_id": 0, "id": 1, "name": 1, "distributor_id": 1, "distributor_name": 1,
             "phone": 1, "address": 1, "city": 1, "shop_name": 1},
        ).sort("name", 1).to_list(2000)
        return {"data": retailers, "count": len(retailers)}

    @router.post("/scan")
    async def scan_coupon(body: Dict[str, Any] = Body(...),
                          user: dict = Depends(salesperson_only)):
        """
        Sales Officer scans a coupon on behalf of a retailer.
        Body: { qr_payload OR coupon_code (+ secret_token), retailer_id }

        Flow:
          1. Validate retailer + auto-fetch distributor
          2. Parse & validate QR (code, token, signature)
          3. Lookup coupon → must be status='unused', active=True
          4. Insert immutable wallet_transaction (credit)
          5. Update coupon → claimed (status='claimed')
          6. Audit log
        """
        retailer_id = (body.get("retailer_id") or "").strip()
        if not retailer_id:
            raise HTTPException(400, "retailer_id is required")

        # parse coupon input
        qr = body.get("qr_payload")
        code: Optional[str] = None
        token: Optional[str] = None
        sig: Optional[str] = None
        if qr:
            parsed = _parse_qr(qr)
            if not parsed:
                await _log_fraud("malformed_qr", (qr or "")[:32].upper(), user, retailer_id)
                raise HTTPException(400, "Malformed QR — not a valid GO OIL coupon")
            code, token, sig = parsed
        else:
            code = (body.get("coupon_code") or "").strip().upper()
            token = (body.get("secret_token") or "").strip()
            sig = (body.get("signature") or "").strip()
            if not code:
                raise HTTPException(400, "coupon_code or qr_payload required")

        # validate retailer + Sales Officer authorization
        retailer = _clean(await db.dms_retailers.find_one({"id": retailer_id}))
        if not retailer:
            raise HTTPException(404, "Retailer not found")
        distributor_id = retailer.get("distributor_id")
        if not distributor_id:
            raise HTTPException(400, "Retailer has no distributor assigned")

        # SO must be assigned to this distributor
        allowed = await db.dms_sp_assignments.find_one({
            "salesperson_id": user["id"], "distributor_id": distributor_id,
        })
        if not allowed:
            await _log_fraud("so_not_assigned_to_distributor", code, user,
                             retailer_id, distributor_id)
            raise HTTPException(403, "You are not assigned to this retailer's distributor")

        distributor = _clean(await db.dms_distributors.find_one({"id": distributor_id})) or {}

        # fetch coupon
        cp = _clean(await db.dms_v2_coupons.find_one({"coupon_code": code}))
        if not cp:
            await _log_fraud("invalid_code", code, user, retailer_id, distributor_id)
            raise HTTPException(400, "Invalid coupon code")

        # batch active check
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]}))
        if not batch or not batch.get("active"):
            await _log_fraud("batch_inactive", code, user, retailer_id, distributor_id)
            raise HTTPException(400, "Coupon batch is not active")

        # expiry
        if cp.get("expires_at") and cp["expires_at"] < _now():
            await db.dms_v2_coupons.update_one({"id": cp["id"]},
                                               {"$set": {"status": "expired", "updated_at": _now()}})
            await _log_fraud("expired", code, user, retailer_id, distributor_id)
            raise HTTPException(400, "Coupon has expired")

        # coupon status
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            await _log_fraud("already_claimed", code, user, retailer_id, distributor_id,
                             {"previous_status": cp["status"],
                              "previously_claimed_at": cp.get("claim_timestamp"),
                              "previously_claimed_by_retailer": cp.get("retailer_id")})
            raise HTTPException(400,
                                f"Coupon already claimed on "
                                f"{(cp.get('claim_timestamp') or '')[:10]} by another retailer")
        if cp["status"] in ("cancelled", "expired"):
            await _log_fraud(cp["status"], code, user, retailer_id, distributor_id)
            raise HTTPException(400, f"Coupon is {cp['status']}")
        if cp["status"] != "unused":
            await _log_fraud(f"bad_status_{cp['status']}", code, user, retailer_id, distributor_id)
            raise HTTPException(400, f"Coupon cannot be claimed (status={cp['status']})")
        if not cp.get("active"):
            await _log_fraud("coupon_inactive", code, user, retailer_id, distributor_id)
            raise HTTPException(400, "Coupon is inactive")

        # cryptographic checks — only if token/sig provided (QR path)
        expected_sig = _sign(batch["hmac_secret"], cp["coupon_code"], cp["secret_token"])
        if token:
            if token != cp["secret_token"]:
                await _log_fraud("invalid_token", code, user, retailer_id, distributor_id)
                raise HTTPException(400, "Invalid coupon token")
        if sig:
            if sig != expected_sig or sig != cp["signature"]:
                await _log_fraud("invalid_signature", code, user, retailer_id, distributor_id)
                raise HTTPException(400, "Invalid coupon signature")

        # ── ATOMIC-ISH CLAIM ────────────────────────────────────────────────
        # attempt to move status unused → claimed
        upd = await db.dms_v2_coupons.update_one(
            {"id": cp["id"], "status": "unused"},
            {"$set": {
                "status": "claimed",
                "claimed_by_user_id": user["id"],
                "claimed_by_user_name": user.get("name") or user.get("email"),
                "claim_timestamp": _now(),
                "retailer_id": retailer_id,
                "retailer_name": retailer.get("name"),
                "distributor_id": distributor_id,
                "distributor_name": distributor.get("name"),
                "updated_at": _now(),
            }},
        )
        if upd.modified_count != 1:
            # concurrent scan lost the race
            await _log_fraud("race_lost", code, user, retailer_id, distributor_id)
            raise HTTPException(400, "Coupon has just been claimed by another scan")

        # wallet transaction (immutable credit)
        wallet_type = "cash" if cp["coupon_type"] == "cash" else "reward"
        await _ensure_wallet(retailer_id, wallet_type)
        tx_id = _nid("wtx")
        await db.dms_v2_wallet_transactions.insert_one({
            "id": tx_id,
            "retailer_id": retailer_id,
            "distributor_id": distributor_id,
            "wallet_type": wallet_type,
            "kind": "credit_coupon",
            "amount": _round(cp["coupon_value"]),   # positive = credit
            "coupon_id": cp["id"],
            "coupon_code": cp["coupon_code"],
            "batch_id": cp["batch_id"],
            "created_by": user["id"],
            "created_by_name": user.get("name"),
            "created_by_role": user.get("role"),
            "at": _now(),
        })

        # link tx back to coupon
        await db.dms_v2_coupons.update_one(
            {"id": cp["id"]}, {"$set": {"wallet_transaction_id": tx_id, "updated_at": _now()}}
        )

        # audit
        await _audit(user, "coupon.claimed", "coupon", cp["id"], {
            "coupon_code": cp["coupon_code"], "coupon_type": cp["coupon_type"],
            "coupon_value": cp["coupon_value"], "retailer_id": retailer_id,
            "retailer_name": retailer.get("name"),
            "distributor_id": distributor_id,
            "distributor_name": distributor.get("name"),
            "wallet_transaction_id": tx_id,
        })

        # optional retailer notification
        if notify:
            user_of_ret = await db.users.find_one({"retailer_id": retailer_id, "role": "retailer"},
                                                  {"_id": 0, "id": 1})
            if user_of_ret:
                unit = "₹" if wallet_type == "cash" else ""
                suffix = "" if wallet_type == "cash" else " points"
                try:
                    await notify(user_of_ret["id"], "coupon_scanned",
                                 f"Coupon credited to your {wallet_type} wallet",
                                 f"{unit}{cp['coupon_value']:g}{suffix} added by {user.get('name')}",
                                 "/dms/retailer/wallet")
                except Exception:
                    pass

        new_bal = await _wallet_balance(retailer_id, wallet_type)
        return {
            "ok": True,
            "coupon_code": cp["coupon_code"],
            "coupon_type": cp["coupon_type"],
            "coupon_value": cp["coupon_value"],
            "wallet_type": wallet_type,
            "new_balance": new_bal,
            "retailer_name": retailer.get("name"),
            "distributor_name": distributor.get("name"),
            "message": (f"₹{cp['coupon_value']:g} credited to {retailer.get('name')}'s Cash Wallet"
                        if wallet_type == "cash"
                        else f"{cp['coupon_value']:g} points credited to {retailer.get('name')}'s Reward Wallet"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # RETAILER — WALLET & HISTORY (read-only)
    # ─────────────────────────────────────────────────────────────────────────
    async def _my_retailer(user: dict) -> Dict[str, Any]:
        if user.get("role") != "retailer":
            raise HTTPException(403, "Retailer only")
        rid = user.get("retailer_id")
        ret = None
        if rid:
            ret = _clean(await db.dms_retailers.find_one({"id": rid}))
        if not ret:
            ret = _clean(await db.dms_retailers.find_one({"user_id": user["id"]}))
        if not ret:
            raise HTTPException(400, "Retailer profile not linked to your user")
        return ret

    @router.get("/retailer/wallet")
    async def retailer_wallet(user: dict = Depends(get_current_user)):
        ret = await _my_retailer(user)
        cash = await _wallet_balance(ret["id"], "cash")
        pts = await _wallet_balance(ret["id"], "reward")
        # pending redemptions (subtract virtually from displayed balance? spec says
        # balance = SUM(transactions). Debit tx is created only on approval, so raw
        # balance is correct. We surface pending separately.)
        pend_cash = await db.dms_v2_redemption_requests.count_documents({
            "retailer_id": ret["id"], "wallet_type": "cash", "status": "pending",
        })
        pend_pts = await db.dms_v2_redemption_requests.count_documents({
            "retailer_id": ret["id"], "wallet_type": "reward", "status": "pending",
        })
        return {
            "retailer_id": ret["id"], "retailer_name": ret["name"],
            "distributor_id": ret.get("distributor_id"),
            "cash_wallet": {"balance": cash, "pending_redemptions": pend_cash},
            "reward_wallet": {"balance": pts, "pending_redemptions": pend_pts},
        }

    @router.get("/retailer/transactions")
    async def retailer_transactions(wallet_type: Optional[str] = Query(None),
                                    limit: int = Query(200, ge=1, le=1000),
                                    user: dict = Depends(get_current_user)):
        ret = await _my_retailer(user)
        q: Dict[str, Any] = {"retailer_id": ret["id"]}
        if wallet_type: q["wallet_type"] = wallet_type
        docs = await db.dms_v2_wallet_transactions.find(q, {"_id": 0})\
            .sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/retailer/coupons")
    async def retailer_coupons(user: dict = Depends(get_current_user)):
        ret = await _my_retailer(user)
        docs = await db.dms_v2_coupons.find(
            {"retailer_id": ret["id"]},
            {"_id": 0, "secret_token": 0, "signature": 0},
        ).sort("claim_timestamp", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/retailer/redemptions")
    async def retailer_redemptions(user: dict = Depends(get_current_user)):
        ret = await _my_retailer(user)
        docs = await db.dms_v2_redemption_requests.find({"retailer_id": ret["id"]}, {"_id": 0})\
            .sort("created_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    # ─────────────────────────────────────────────────────────────────────────
    # REDEMPTIONS — Cash & Reward
    # ─────────────────────────────────────────────────────────────────────────
    @router.post("/redemptions")
    async def create_redemption(body: Dict[str, Any] = Body(...),
                                user: dict = Depends(get_current_user)):
        """
        Anyone with knowledge of a retailer can raise a redemption request.
        In practice: Owner/Accountant creates it during month-end; Distributor
        may initiate on behalf of retailer.
        Body: { retailer_id, wallet_type, amount, notes }
        """
        role = user.get("role")
        if role not in ("owner", "owner_accountant", "distributor",
                        "distributor_accountant", "team_leader", "salesperson", "super_admin"):
            raise HTTPException(403, "Not allowed")

        retailer_id = (body.get("retailer_id") or "").strip()
        wallet_type = (body.get("wallet_type") or "").strip().lower()
        amount = _round(body.get("amount", 0))
        notes = (body.get("notes") or "").strip()

        if wallet_type not in ("cash", "reward"):
            raise HTTPException(400, "wallet_type must be cash or reward")
        if amount <= 0:
            raise HTTPException(400, "amount must be > 0")

        ret = _clean(await db.dms_retailers.find_one({"id": retailer_id}))
        if not ret:
            raise HTTPException(404, "Retailer not found")
        did = ret.get("distributor_id")

        bal = await _wallet_balance(retailer_id, wallet_type)
        # exclude amounts locked in already-pending requests
        pending_sum = 0.0
        async for r in db.dms_v2_redemption_requests.find(
            {"retailer_id": retailer_id, "wallet_type": wallet_type, "status": "pending"},
            {"_id": 0, "amount": 1},
        ):
            pending_sum += _round(r.get("amount", 0))
        available = _round(bal - pending_sum)
        if amount > available + 0.001:
            raise HTTPException(400,
                                f"Insufficient wallet balance. Available: {available}, requested: {amount}")

        # allocate redemption number
        counter = await db.dms_v2_meta.find_one_and_update(
            {"key": f"redemption_counter_{wallet_type}"},
            {"$inc": {"value": 1}}, upsert=True, return_document=True,
        )
        rn = int((counter or {}).get("value", 1))
        prefix = "CR" if wallet_type == "cash" else "PR"
        yy = datetime.utcnow().strftime("%y")
        redemption_no = f"{prefix}-{yy}-{rn:05d}"

        rid = _nid("red")
        doc = {
            "id": rid,
            "redemption_no": redemption_no,
            "retailer_id": retailer_id,
            "retailer_name": ret.get("name"),
            "distributor_id": did,
            "distributor_name": ret.get("distributor_name"),
            "wallet_type": wallet_type,
            "amount": amount,
            "status": "pending",          # pending → approved → completed  (or rejected)
            "notes": notes,
            "created_by": user["id"],
            "created_by_name": user.get("name"),
            "created_by_role": role,
            "created_at": _now(),
            "approved_by": None,
            "approved_at": None,
            "rejected_reason": None,
            "credit_note_id": None,
            "credit_note_no": None,
            "dispatch_advice_id": None,
            "dispatch_advice_no": None,
        }
        await db.dms_v2_redemption_requests.insert_one(doc)
        await _audit(user, "redemption.requested", "redemption", rid, {
            "wallet_type": wallet_type, "amount": amount,
            "retailer_id": retailer_id, "distributor_id": did,
            "redemption_no": redemption_no,
        })
        return {"ok": True, "redemption": _clean(doc)}

    @router.get("/redemptions")
    async def list_redemptions(
        status: Optional[str] = Query(None),
        wallet_type: Optional[str] = Query(None),
        retailer_id: Optional[str] = Query(None),
        distributor_id: Optional[str] = Query(None),
        user: dict = Depends(get_current_user),
    ):
        q: Dict[str, Any] = {}
        role = user.get("role")
        if role == "distributor":
            q["distributor_id"] = user.get("distributor_id")
        elif role == "distributor_accountant":
            q["distributor_id"] = user.get("distributor_id")
        elif role == "retailer":
            ret = await _my_retailer(user)
            q["retailer_id"] = ret["id"]
        elif role in ("owner", "owner_accountant", "team_leader", "super_admin"):
            if distributor_id: q["distributor_id"] = distributor_id
            if retailer_id: q["retailer_id"] = retailer_id
        else:
            raise HTTPException(403, "Access denied")
        if status: q["status"] = status
        if wallet_type: q["wallet_type"] = wallet_type
        docs = await db.dms_v2_redemption_requests.find(q, {"_id": 0})\
            .sort("created_at", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.post("/redemptions/{rid}/approve")
    async def approve_redemption(rid: str, body: Dict[str, Any] = Body(default_factory=dict),
                                 user: dict = Depends(owner_or_accountant)):
        """
        Approves a pending redemption:
          * CASH   → generates Credit Note → reduces distributor primary ledger outstanding
                      (creates a dms_primary_ledger entry kind='coupon_credit')
          * REWARD → generates Dispatch Advice → stock will be sent
        In both cases: an immutable wallet DEBIT transaction is created (retailer wallet).
        """
        r = _clean(await db.dms_v2_redemption_requests.find_one({"id": rid}))
        if not r:
            raise HTTPException(404, "Redemption request not found")
        if r["status"] != "pending":
            raise HTTPException(400, f"Redemption is already {r['status']}")

        # safety recheck balance
        bal = await _wallet_balance(r["retailer_id"], r["wallet_type"])
        if r["amount"] > bal + 0.001:
            raise HTTPException(400, f"Wallet balance ({bal}) insufficient for {r['amount']}")

        # mark all coupons feeding this amount as redemption_pending → redeemed
        # We attribute redemption to the earliest claimed coupons up to amount.
        remaining = _round(r["amount"])
        to_close_ids: List[str] = []
        async for cp in db.dms_v2_coupons.find(
            {"retailer_id": r["retailer_id"], "coupon_type": r["wallet_type"],
             "status": "claimed"},
            {"_id": 0, "id": 1, "coupon_value": 1},
        ).sort("claim_timestamp", 1):
            if remaining <= 0.001:
                break
            v = _round(cp.get("coupon_value", 0))
            if v <= 0:
                continue
            to_close_ids.append(cp["id"])
            remaining -= v
        # note: perfect coin-change is not required — we mark whole coupons; any
        # over/short flowing forward is tolerated because the wallet ledger stays
        # the source of truth. We only tag coupons as "redeemed" for reporting.
        if to_close_ids:
            await db.dms_v2_coupons.update_many(
                {"id": {"$in": to_close_ids}},
                {"$set": {"status": "redeemed", "redemption_request_id": rid,
                          "updated_at": _now()}},
            )

        now = _now()
        cn_id = None; cn_no = None
        da_id = None; da_no = None

        if r["wallet_type"] == "cash":
            # Credit Note
            counter = await db.dms_v2_meta.find_one_and_update(
                {"key": "credit_note_counter"}, {"$inc": {"value": 1}},
                upsert=True, return_document=True,
            )
            n = int((counter or {}).get("value", 1))
            cn_no = f"CN-{datetime.utcnow().strftime('%y')}-{n:05d}"
            cn_id = _nid("cn")
            await db.dms_v2_credit_notes.insert_one({
                "id": cn_id, "cn_no": cn_no,
                "redemption_id": rid, "redemption_no": r["redemption_no"],
                "retailer_id": r["retailer_id"], "retailer_name": r["retailer_name"],
                "distributor_id": r["distributor_id"], "distributor_name": r["distributor_name"],
                "amount": r["amount"],
                "reason": "Cash coupon redemption",
                "notes": body.get("notes") or r.get("notes") or "",
                "issued_by": user["id"], "issued_by_name": user.get("name"),
                "issued_at": now,
                "status": "issued",
            })

            # Push into existing primary ledger (spec: distributor outstanding reduces)
            if r["distributor_id"]:
                await db.dms_primary_ledger.insert_one({
                    "id": _nid("le"),
                    "distributor_id": r["distributor_id"],
                    "kind": "coupon_credit",
                    "reference_id": cn_id,
                    "reference_no": cn_no,
                    "amount": r["amount"],
                    "method": "credit_note",
                    "description": f"Credit Note {cn_no} — cash coupon redemption for retailer {r['retailer_name']}",
                    "at": now,
                    "recorded_by": user["id"],
                })
        else:
            # Dispatch Advice
            counter = await db.dms_v2_meta.find_one_and_update(
                {"key": "dispatch_advice_counter"}, {"$inc": {"value": 1}},
                upsert=True, return_document=True,
            )
            n = int((counter or {}).get("value", 1))
            da_no = f"DA-{datetime.utcnow().strftime('%y')}-{n:05d}"
            da_id = _nid("da")
            await db.dms_v2_dispatch_advices.insert_one({
                "id": da_id, "da_no": da_no,
                "redemption_id": rid, "redemption_no": r["redemption_no"],
                "retailer_id": r["retailer_id"], "retailer_name": r["retailer_name"],
                "distributor_id": r["distributor_id"], "distributor_name": r["distributor_name"],
                "points": r["amount"],
                "items": body.get("items") or [],   # e.g. [{product_id, qty}]
                "notes": body.get("notes") or r.get("notes") or "",
                "status": "issued",                 # issued → dispatched
                "issued_by": user["id"], "issued_by_name": user.get("name"),
                "issued_at": now,
            })

        # DEBIT wallet transaction (immutable)
        await db.dms_v2_wallet_transactions.insert_one({
            "id": _nid("wtx"),
            "retailer_id": r["retailer_id"],
            "distributor_id": r["distributor_id"],
            "wallet_type": r["wallet_type"],
            "kind": "debit_redemption",
            "amount": -_round(r["amount"]),           # negative = debit
            "redemption_id": rid,
            "credit_note_id": cn_id, "credit_note_no": cn_no,
            "dispatch_advice_id": da_id, "dispatch_advice_no": da_no,
            "created_by": user["id"], "created_by_name": user.get("name"),
            "created_by_role": user.get("role"),
            "at": now,
        })

        # mark request approved
        upd = {"status": "approved", "approved_by": user["id"], "approved_at": now}
        if cn_id: upd.update({"credit_note_id": cn_id, "credit_note_no": cn_no})
        if da_id: upd.update({"dispatch_advice_id": da_id, "dispatch_advice_no": da_no})
        await db.dms_v2_redemption_requests.update_one({"id": rid}, {"$set": upd})

        await _audit(user, "redemption.approved", "redemption", rid, {
            "wallet_type": r["wallet_type"], "amount": r["amount"],
            "credit_note_no": cn_no, "dispatch_advice_no": da_no,
        })

        if notify:
            user_of_ret = await db.users.find_one({"retailer_id": r["retailer_id"], "role": "retailer"},
                                                  {"_id": 0, "id": 1})
            if user_of_ret:
                try:
                    await notify(
                        user_of_ret["id"], "redemption_approved",
                        f"Redemption approved — {r['redemption_no']}",
                        (f"Credit Note {cn_no} issued for ₹{r['amount']:g}"
                         if cn_no else
                         f"Dispatch Advice {da_no} issued for {r['amount']:g} points"),
                        "/dms/retailer/redemptions",
                    )
                except Exception:
                    pass

        return {"ok": True,
                "credit_note_no": cn_no, "dispatch_advice_no": da_no,
                "message": "Redemption approved"}

    @router.post("/redemptions/{rid}/reject")
    async def reject_redemption(rid: str, body: Dict[str, Any] = Body(default_factory=dict),
                                user: dict = Depends(owner_or_accountant)):
        r = _clean(await db.dms_v2_redemption_requests.find_one({"id": rid}))
        if not r:
            raise HTTPException(404, "Not found")
        if r["status"] != "pending":
            raise HTTPException(400, f"Redemption already {r['status']}")
        reason = (body.get("reason") or "").strip() or "Not specified"
        await db.dms_v2_redemption_requests.update_one({"id": rid}, {"$set": {
            "status": "rejected", "rejected_reason": reason,
            "approved_by": user["id"], "approved_at": _now(),
        }})
        await _audit(user, "redemption.rejected", "redemption", rid, {"reason": reason})
        return {"ok": True}

    # ─────────────────────────────────────────────────────────────────────────
    # DISTRIBUTOR views
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/dist/summary")
    async def dist_summary(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("distributor", "distributor_accountant"):
            raise HTTPException(403, "Distributor only")
        did = user.get("distributor_id")
        if not did:
            raise HTTPException(400, "Distributor profile not linked")

        retailers = await db.dms_retailers.find({"distributor_id": did}, {"_id": 0}).to_list(1000)
        rows: List[Dict[str, Any]] = []
        for r in retailers:
            cash_bal = await _wallet_balance(r["id"], "cash")
            pts_bal = await _wallet_balance(r["id"], "reward")
            rows.append({
                "retailer_id": r["id"], "retailer_name": r.get("name"),
                "cash_balance": cash_bal, "reward_balance": pts_bal,
            })
        cn = await db.dms_v2_credit_notes.count_documents({"distributor_id": did})
        red_pending = await db.dms_v2_redemption_requests.count_documents(
            {"distributor_id": did, "status": "pending"})
        red_approved = await db.dms_v2_redemption_requests.count_documents(
            {"distributor_id": did, "status": "approved"})
        return {"retailers": rows,
                "credit_notes_count": cn,
                "pending_redemptions": red_pending,
                "approved_redemptions": red_approved}

    @router.get("/dist/credit-notes")
    async def dist_credit_notes(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("distributor", "distributor_accountant"):
            raise HTTPException(403, "Distributor only")
        did = user.get("distributor_id")
        docs = await db.dms_v2_credit_notes.find({"distributor_id": did}, {"_id": 0})\
            .sort("issued_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/dist/dispatch-advices")
    async def dist_dispatch_advices(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("distributor", "distributor_accountant"):
            raise HTTPException(403, "Distributor only")
        did = user.get("distributor_id")
        docs = await db.dms_v2_dispatch_advices.find({"distributor_id": did}, {"_id": 0})\
            .sort("issued_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    # ─────────────────────────────────────────────────────────────────────────
    # OWNER — Credit Notes & Dispatch Advices lists
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/credit-notes")
    async def list_credit_notes(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        docs = await db.dms_v2_credit_notes.find({}, {"_id": 0}).sort("issued_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/dispatch-advices")
    async def list_dispatch_advices(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        docs = await db.dms_v2_dispatch_advices.find({}, {"_id": 0}).sort("issued_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.post("/dispatch-advices/{da_id}/mark-dispatched")
    async def mark_dispatched(da_id: str, user: dict = Depends(owner_or_accountant)):
        d = _clean(await db.dms_v2_dispatch_advices.find_one({"id": da_id}))
        if not d:
            raise HTTPException(404, "Not found")
        if d["status"] == "dispatched":
            return {"ok": True, "message": "Already dispatched"}
        await db.dms_v2_dispatch_advices.update_one({"id": da_id}, {"$set": {
            "status": "dispatched", "dispatched_at": _now(), "dispatched_by": user["id"],
        }})
        await _audit(user, "dispatch_advice.dispatched", "dispatch_advice", da_id,
                     {"da_no": d.get("da_no")})
        return {"ok": True}

    # ─────────────────────────────────────────────────────────────────────────
    # REPORTS
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/reports/summary")
    async def reports_summary(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")

        pipeline_status = [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]
        by_status: Dict[str, int] = {"generated": 0, "unused": 0, "claimed": 0,
                                     "redemption_pending": 0, "redeemed": 0,
                                     "expired": 0, "cancelled": 0}
        async for r in db.dms_v2_coupons.aggregate(pipeline_status):
            by_status[r["_id"]] = r["n"]

        # by type
        by_type: Dict[str, Dict[str, Any]] = {"cash": {}, "reward": {}}
        pipeline_type = [
            {"$group": {"_id": {"t": "$coupon_type", "s": "$status"},
                        "n": {"$sum": 1},
                        "v": {"$sum": "$coupon_value"}}}]
        async for r in db.dms_v2_coupons.aggregate(pipeline_type):
            t = r["_id"]["t"]; s = r["_id"]["s"]
            by_type.setdefault(t, {}).setdefault(s, {"count": 0, "value": 0.0})
            by_type[t][s]["count"] = r["n"]
            by_type[t][s]["value"] = _round(r["v"])

        total_batches = await db.dms_v2_coupon_batches.count_documents({})
        active_batches = await db.dms_v2_coupon_batches.count_documents({"active": True})
        fraud = await db.dms_v2_coupon_fraud_attempts.count_documents({})
        pending_red = await db.dms_v2_redemption_requests.count_documents({"status": "pending"})

        # wallet totals
        wallet_totals: Dict[str, float] = {"cash": 0.0, "reward": 0.0}
        async for r in db.dms_v2_wallet_transactions.aggregate([
            {"$group": {"_id": "$wallet_type", "t": {"$sum": "$amount"}}},
        ]):
            wallet_totals[r["_id"]] = _round(r["t"])

        return {
            "totals": by_status,
            "by_type": by_type,
            "batches": {"total": total_batches, "active": active_batches},
            "fraud_attempts": fraud,
            "pending_redemptions": pending_red,
            "wallet_totals": wallet_totals,
        }

    @router.get("/reports/salesperson")
    async def reports_salesperson(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        pipeline = [
            {"$match": {"status": {"$in": ["claimed", "redemption_pending", "redeemed"]}}},
            {"$group": {"_id": "$claimed_by_user_id",
                        "name": {"$first": "$claimed_by_user_name"},
                        "scans": {"$sum": 1},
                        "cash_value": {"$sum": {"$cond": [
                            {"$eq": ["$coupon_type", "cash"]}, "$coupon_value", 0]}},
                        "reward_value": {"$sum": {"$cond": [
                            {"$eq": ["$coupon_type", "reward"]}, "$coupon_value", 0]}}}},
            {"$sort": {"scans": -1}},
        ]
        rows: List[Dict[str, Any]] = []
        async for r in db.dms_v2_coupons.aggregate(pipeline):
            rows.append({
                "salesperson_id": r["_id"], "salesperson_name": r.get("name"),
                "scans": r["scans"],
                "cash_value": _round(r.get("cash_value", 0)),
                "reward_points": _round(r.get("reward_value", 0)),
            })
        return {"data": rows, "count": len(rows)}

    @router.get("/reports/duplicate-scans")
    async def reports_duplicate(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        docs = await db.dms_v2_coupon_fraud_attempts.find(
            {"reason": {"$in": ["already_claimed", "race_lost"]}}, {"_id": 0},
        ).sort("at", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/reports/fraud")
    async def reports_fraud(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        docs = await db.dms_v2_coupon_fraud_attempts.find({}, {"_id": 0})\
            .sort("at", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/audit-log")
    async def audit_log(entity_id: Optional[str] = Query(None),
                        limit: int = Query(200, ge=1, le=1000),
                        user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {}
        if entity_id: q["entity_id"] = entity_id
        docs = await db.dms_v2_coupon_audit_log.find(q, {"_id": 0})\
            .sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/reports/wallet-summary")
    async def wallet_summary(user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        # per-retailer wallet balances
        rows: List[Dict[str, Any]] = []
        async for w in db.dms_v2_retailer_wallets.find({}, {"_id": 0}):
            bal = await _wallet_balance(w["retailer_id"], w["wallet_type"])
            ret = await db.dms_retailers.find_one({"id": w["retailer_id"]},
                                                   {"_id": 0, "name": 1, "distributor_name": 1, "distributor_id": 1})
            rows.append({
                "retailer_id": w["retailer_id"],
                "retailer_name": (ret or {}).get("name"),
                "distributor_id": (ret or {}).get("distributor_id"),
                "distributor_name": (ret or {}).get("distributor_name"),
                "wallet_type": w["wallet_type"], "balance": bal,
            })
        return {"data": rows, "count": len(rows)}

    return router


__all__ = ["build_coupons_router"]
