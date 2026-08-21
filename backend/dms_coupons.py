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

import base64
import hmac
import hashlib
import json
import os
import re
import secrets
import tempfile
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from fastapi.responses import Response

# AES-256-GCM for encrypted QR payload (v2)
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _AES_AVAILABLE = True
except Exception:  # pragma: no cover
    AESGCM = None  # type: ignore
    _AES_AVAILABLE = False


# ═════════════════════════ helpers ══════════════════════════════════════════
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _nid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _clean(d: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if d and "_id" in d:
        d.pop("_id", None)
    return d


# ── Background PDF-generation job registry ──────────────────────────────────
# Large coupon batches (e.g. 1400 coupons) take longer than the edge/ingress
# proxy timeout (~60s) to render synchronously, causing an empty/502 response.
# We therefore render in the background and let the client poll for completion,
# then download the finished PDF. Files are written to a temp dir keyed by job.
import asyncio  # noqa: E402
_PDF_JOB_DIR = os.path.join(tempfile.gettempdir(), "gooil_coupon_pdfs")
os.makedirs(_PDF_JOB_DIR, exist_ok=True)
_PDF_JOBS: Dict[str, Dict[str, Any]] = {}


def _prune_pdf_jobs(max_age_sec: int = 3600, max_keep: int = 50) -> None:
    """Drop old finished jobs + their temp files to bound disk/memory."""
    try:
        items = sorted(_PDF_JOBS.items(), key=lambda kv: kv[1].get("_ts", 0))
        # remove by count
        while len(items) > max_keep:
            jid, j = items.pop(0)
            _PDF_JOBS.pop(jid, None)
            p = j.get("path")
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass
    except Exception:
        pass


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
    """JSON-ish compact payload embedded in QR (v1 legacy format)."""
    return f"GOOIL:{coupon_code}:{secret_token}:{signature}"


def _qr_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()


# ── AES-256-GCM encrypted payload (v2) ─────────────────────────────────────
def _aes_master_key() -> bytes:
    """Derive a 32-byte AES-256 master key from env / master secret.
    Env COUPON_ENCRYPTION_KEY (base64 or hex, 32 bytes) takes precedence.
    Otherwise deterministically derived from COUPON_MASTER_SECRET.
    """
    raw = os.environ.get("COUPON_ENCRYPTION_KEY")
    if raw:
        try:
            k = base64.b64decode(raw)
            if len(k) == 32:
                return k
        except Exception:
            pass
        try:
            k = bytes.fromhex(raw)
            if len(k) == 32:
                return k
        except Exception:
            pass
    # Derive from master secret (stable across restarts)
    return hashlib.sha256(("AES-256|COUPON|" + _APP_SECRET).encode()).digest()


_AES_KEY = _aes_master_key()


def _aes_encrypt(plaintext: bytes, aad: bytes = b"gooil-coupon-v2") -> bytes:
    """AES-256-GCM encrypt. Returns nonce(12) || ciphertext || tag."""
    if not _AES_AVAILABLE:
        raise RuntimeError("cryptography package not available for AES-GCM")
    nonce = secrets.token_bytes(12)
    aead = AESGCM(_AES_KEY)
    ct = aead.encrypt(nonce, plaintext, aad)
    return nonce + ct


def _aes_decrypt(blob: bytes, aad: bytes = b"gooil-coupon-v2") -> bytes:
    if not _AES_AVAILABLE:
        raise RuntimeError("cryptography package not available for AES-GCM")
    if len(blob) < 13:
        raise ValueError("ciphertext too short")
    nonce, ct = blob[:12], blob[12:]
    aead = AESGCM(_AES_KEY)
    return aead.decrypt(nonce, ct, aad)


def _sign_v2(batch_secret: str, ciphertext_b64: str) -> str:
    """HMAC-SHA256 signature computed over the base64 ciphertext (v2)."""
    key = (batch_secret + "|" + _APP_SECRET + "|v2").encode()
    return hmac.new(key, ciphertext_b64.encode(), hashlib.sha256).hexdigest()


def _qr_payload_v2(visible_serial: str, hidden_secure_id: str, batch_id: str,
                   batch_secret: str, coupon_type: str, coupon_value: float) -> str:
    """
    Encrypted, signed QR payload — v2.
    Format: GOOIL2|{b64(nonce+ciphertext+tag)}|{signature_hex}
    The plaintext (JSON) contains: v, s, h, b, t, r, ts.
    NO plaintext of serial / hidden id / batch id is visible in the QR data.
    """
    inner = {
        "v": 2,
        "s": visible_serial,
        "h": hidden_secure_id,
        "b": batch_id,
        "t": coupon_type,
        "r": _round(coupon_value),
        "ts": int(datetime.now(timezone.utc).timestamp()),
    }
    plain = json.dumps(inner, separators=(",", ":"), sort_keys=True).encode()
    blob = _aes_encrypt(plain)
    ct_b64 = base64.urlsafe_b64encode(blob).decode().rstrip("=")
    sig = _sign_v2(batch_secret, ct_b64)
    return f"GOOIL2|{ct_b64}|{sig}"


def _b64_urlsafe_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class QrParseError(Exception):
    """Represents a QR parsing / decryption failure with a specific reason code."""

    def __init__(self, reason: str, message: str = ""):
        self.reason = reason  # one of the fraud reasons
        self.message = message or reason
        super().__init__(self.message)


def _parse_qr_v2_only(payload: str) -> Dict[str, Any]:
    """Parse a v2 QR payload. Returns the decrypted inner dict.
    Raises QrParseError with an actionable fraud reason on failure.
    """
    if not payload or not payload.strip().startswith("GOOIL2|"):
        raise QrParseError("wrong_version", "Not a v2 GO OIL QR")
    parts = payload.strip().split("|")
    if len(parts) != 3:
        raise QrParseError("modified_payload", "Malformed v2 payload")
    _, ct_b64, sig = parts
    if not ct_b64 or not sig or len(sig) != 64:
        raise QrParseError("modified_payload", "Malformed v2 payload fields")
    # Try decryption first (with AAD) — a QR from an online generator will fail here
    try:
        blob = _b64_urlsafe_decode(ct_b64)
    except Exception:
        raise QrParseError("modified_payload", "Payload not base64")
    try:
        plain = _aes_decrypt(blob)
    except Exception:
        # Wrong key, tampered ciphertext, or generated by another system
        raise QrParseError("invalid_encryption", "Payload could not be decrypted")
    try:
        inner = json.loads(plain.decode())
    except Exception:
        raise QrParseError("modified_payload", "Decrypted plaintext is not valid JSON")
    if not isinstance(inner, dict) or inner.get("v") != 2:
        raise QrParseError("wrong_version", "Unexpected payload version")
    inner["_ct_b64"] = ct_b64
    inner["_sig"] = sig
    return inner


def _parse_qr(payload: str) -> Optional[Tuple[str, str, str]]:
    """Legacy v1 parser — returns (code, token, signature) or None if malformed."""
    if not payload:
        return None
    p = payload.strip()
    if p.startswith("GOOIL:"):
        parts = p[len("GOOIL:"):].split(":")
        if len(parts) == 3:
            return parts[0].upper().strip(), parts[1].strip(), parts[2].strip()
    return None


def _detect_qr_version(payload: str) -> str:
    """Returns 'v2', 'v1', or 'unknown'."""
    if not payload:
        return "unknown"
    p = payload.strip()
    if p.startswith("GOOIL2|"):
        return "v2"
    if p.startswith("GOOIL:"):
        return "v1"
    return "unknown"


# ── serial number helpers ──────────────────────────────────────────────────
_PREFIX_RE = re.compile(r"^[A-Z0-9]{1,10}$")


def _validate_prefix(p: str) -> str:
    p = (p or "").strip().upper()
    if not p:
        raise HTTPException(400, "prefix is required for prefix_sequential mode")
    if not _PREFIX_RE.match(p):
        raise HTTPException(400, "prefix must be 1-10 chars, A-Z and 0-9 only (uppercase)")
    return p


def _fmt_serial(prefix: str, num: int, pad: int) -> str:
    return f"{prefix}{str(num).zfill(pad)}"


def _normalize_serial(user_input: str, batch: Dict[str, Any]) -> Optional[str]:
    """Smart serial normalizer.
    Given user input like 'ABC1' or 'abc001' or '1' and a batch with prefix=ABC,
    pad=3 → returns 'ABC001'.
    Returns None if input can't be interpreted.
    """
    if not user_input:
        return None
    s = str(user_input).strip().upper()
    prefix = (batch.get("prefix") or "").upper()
    pad = int(batch.get("serial_pad") or 3)
    if not prefix:
        # random_secure batch — accept exactly as typed
        return s
    if s.startswith(prefix):
        num_part = s[len(prefix):].lstrip("0") or "0"
        if not num_part.isdigit():
            return None
        return _fmt_serial(prefix, int(num_part), pad)
    if s.isdigit():
        return _fmt_serial(prefix, int(s), pad)
    return None


# ── request-context helpers (IP, GPS, device) ──────────────────────────────
def _client_ip(request: Optional[Request]) -> Optional[str]:
    if not request:
        return None
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    xr = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if xr:
        return xr.strip()
    return getattr(request.client, "host", None) if request.client else None


def _client_meta(request: Optional[Request], body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = body or {}
    return {
        "ip_address": _client_ip(request),
        "user_agent": (request.headers.get("user-agent") if request else None),
        "gps_lat": body.get("gps_lat"),
        "gps_lng": body.get("gps_lng"),
        "device_id": body.get("device_id") or (request.headers.get("x-device-id") if request else None),
    }


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
                         extra: Optional[Dict[str, Any]] = None,
                         request: Optional[Request] = None,
                         body: Optional[Dict[str, Any]] = None):
        meta = _client_meta(request, body)
        await db.dms_v2_coupon_fraud_attempts.insert_one({
            "id": _nid("fra"),
            "reason": reason,
            "coupon_code": coupon_code,
            "actor_id": user.get("id"),
            "actor_name": user.get("name"),
            "actor_role": user.get("role"),
            "retailer_id": retailer_id,
            "distributor_id": distributor_id,
            "ip_address": meta.get("ip_address"),
            "user_agent": meta.get("user_agent"),
            "gps_lat": meta.get("gps_lat"),
            "gps_lng": meta.get("gps_lng"),
            "device_id": meta.get("device_id"),
            "extra": extra or {},
            "at": _now(),
        })

        # ── Fraud Alert → instant owner notification (best-effort) ───────────
        # Written directly in the notification-bell schema (recipient_id +
        # created_at) so it shows up immediately in every owner's bell.
        try:
            gps_lat = meta.get("gps_lat")
            gps_lng = meta.get("gps_lng")
            if gps_lat is not None and gps_lng is not None:
                loc = f"GPS {gps_lat}, {gps_lng}"
            elif meta.get("ip_address"):
                loc = f"IP {meta.get('ip_address')}"
            else:
                loc = "location unknown"
            actor = user.get("name") or user.get("email") or (user.get("role") or "user")
            owners = await db.users.find({"role": "owner"}, {"_id": 0, "id": 1}).to_list(50)
            for o in owners:
                if not o.get("id"):
                    continue
                await db.dms_notifications.insert_one({
                    "id": _nid("ntf"),
                    "recipient_id": o["id"],
                    "kind": "coupon_fraud",
                    "title": f"Fraud alert: {reason.replace('_', ' ')}",
                    "body": f"Coupon {coupon_code or '—'} · by {actor} · {loc}",
                    "link": "/dms/owner/coupons/fraud",
                    "read": False,
                    "created_at": _now(),
                })
        except Exception:
            pass

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

    async def _retailer_ledger_balance(retailer_id: str) -> Dict[str, float]:
        """Retailer ↔ Distributor secondary-goods outstanding, derived from
        dms_retailer_ledger. Mirrors dms_router.secondary_ledger math:
          billed  = invoice + debit_note
          paid    = payment + coupon_credit + credit_note
          outstanding = billed - paid   (negative ⇒ credit balance)
        Returns {billed, paid, outstanding, credit}. `outstanding` is never
        negative for display; the surplus is exposed as `credit`."""
        billed = 0.0
        paid = 0.0
        async for e in db.dms_retailer_ledger.find(
            {"retailer_id": retailer_id}, {"_id": 0, "kind": 1, "amount": 1}
        ):
            k = e.get("kind")
            amt = _round(e.get("amount", 0))
            if k in ("invoice", "debit_note"):
                billed += amt
            elif k in ("payment", "coupon_credit", "credit_note"):
                paid += amt
        net = _round(billed - paid)
        return {
            "billed": _round(billed),
            "paid": _round(paid),
            "outstanding": _round(net if net > 0 else 0.0),
            "credit": _round(-net if net < 0 else 0.0),
        }

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
        (NOT yet usable) — Owner must Activate the batch (or activate coupons
        singly/by range) before use.

        Supports two serial modes:
          * prefix_sequential (default): visible_serial = PREFIX + zero-padded number
                                         (e.g. prefix=ABC start=1 pad=3 → ABC001…)
          * random_secure   : visible_serial = 16-char random (legacy)

        Every coupon gets an INDEPENDENT UUID v4 hidden_secure_id and its QR
        payload is AES-256-GCM encrypted + HMAC-SHA256 signed (v2 format).
        """
        title = (body.get("title") or "").strip()
        coupon_type = (body.get("coupon_type") or "").strip().lower()
        coupon_value = _round(body.get("coupon_value", 0))
        count = int(body.get("count") or 0)
        notes = (body.get("notes") or "").strip()
        expires_at = body.get("expires_at")  # optional ISO date

        # New serial-config knobs (all optional; defaults are prefix_sequential)
        serial_mode = (body.get("serial_mode") or "prefix_sequential").strip().lower()
        prefix = (body.get("prefix") or "").strip().upper()
        serial_start = int(body.get("serial_start") or 1)
        serial_pad = int(body.get("serial_pad") or 3)

        if coupon_type not in ("cash", "reward"):
            raise HTTPException(400, "coupon_type must be 'cash' or 'reward'")
        if coupon_value <= 0:
            raise HTTPException(400, "coupon_value must be > 0")
        if count <= 0 or count > 100_000:
            raise HTTPException(400, "count must be between 1 and 100,000")
        if serial_mode not in ("prefix_sequential", "random_secure"):
            raise HTTPException(400, "serial_mode must be prefix_sequential or random_secure")
        if serial_mode == "prefix_sequential":
            prefix = _validate_prefix(prefix)
            if serial_start < 0 or serial_start > 9_999_999:
                raise HTTPException(400, "serial_start must be between 0 and 9,999,999")
            if serial_pad < 1 or serial_pad > 10:
                raise HTTPException(400, "serial_pad must be between 1 and 10")
            # ensure padding is large enough for max serial
            max_serial = serial_start + count - 1
            if len(str(max_serial)) > serial_pad:
                raise HTTPException(400,
                    f"serial_pad ({serial_pad}) is too small for max serial {max_serial} — "
                    f"increase padding")
            # duplicate check inside a single batch is guaranteed by sequential nature;
            # cross-batch duplicates are ALLOWED (different batches may share prefix),
            # but each coupon's visible_serial IS unique across ALL batches:
            first = _fmt_serial(prefix, serial_start, serial_pad)
            last = _fmt_serial(prefix, max_serial, serial_pad)
            existing = await db.dms_v2_coupons.find_one(
                {"visible_serial": {"$in": [first, last]}}, {"_id": 0, "visible_serial": 1})
            if existing:
                raise HTTPException(400,
                    f"Serial range {first}..{last} overlaps with existing coupons — "
                    f"choose a different prefix or serial_start")

        if not title:
            if serial_mode == "prefix_sequential":
                title = f"{coupon_type.upper()} {prefix} × {count}"
            else:
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
            # new serial config (persisted for audit/print)
            "serial_mode": serial_mode,
            "prefix": prefix if serial_mode == "prefix_sequential" else None,
            "serial_start": serial_start if serial_mode == "prefix_sequential" else None,
            "serial_pad": serial_pad if serial_mode == "prefix_sequential" else None,
            "serial_end": (serial_start + count - 1) if serial_mode == "prefix_sequential" else None,
            "qr_version": "v2",
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
        seq = serial_start
        while created < count:
            n_this = min(CHUNK, count - created)
            docs: List[Dict[str, Any]] = []
            for _ in range(n_this):
                if serial_mode == "prefix_sequential":
                    visible = _fmt_serial(prefix, seq, serial_pad)
                    seq += 1
                else:
                    # ensure uniqueness inside the batch
                    while True:
                        visible = _gen_coupon_code()
                        if visible not in codes_seen:
                            codes_seen.add(visible)
                            break
                # INDEPENDENT UUID v4 (never derived from anything visible)
                hidden_id = str(uuid.uuid4())
                # legacy secret_token still generated (used by v1 signing path
                # for backward compatibility if someone ever manually crafts v1)
                token = _gen_secret_token()
                sig_v1 = _sign(batch_secret, visible, token)  # v1 signature (retained)
                qr_v2 = _qr_payload_v2(visible, hidden_id, batch_id,
                                       batch_secret, coupon_type, coupon_value)
                # extract the ciphertext + signature parts to store the canonical signature
                _, ct_b64, sig_v2 = qr_v2.split("|", 2)
                docs.append({
                    "id": _nid("cpn"),
                    # NEW (spec-compliant)
                    "visible_serial": visible,
                    "hidden_secure_id": hidden_id,
                    "qr_version": "v2",
                    "qr_ciphertext_b64": ct_b64,        # canonical stored ciphertext
                    "qr_signature_v2": sig_v2,          # canonical v2 HMAC signature
                    # LEGACY aliases (kept for backward compatibility)
                    "coupon_code": visible,             # alias — same as visible_serial
                    "secret_token": token,              # independent, kept for v1 compat
                    "signature": sig_v1,                # v1 HMAC signature (unused for v2 scans)
                    "qr_hash": _qr_hash(qr_v2),
                    # denormalised references
                    "batch_id": batch_id,
                    "batch_no": batch_no,
                    "batch_label": batch_doc["batch_label"],
                    "coupon_type": coupon_type,
                    "coupon_value": coupon_value,
                    "status": "generated",
                    "active": False,
                    "activated_at": None,
                    "activated_by": None,
                    "deactivated_at": None,
                    "deactivated_by": None,
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
            "serial_mode": serial_mode, "prefix": batch_doc.get("prefix"),
            "serial_start": batch_doc.get("serial_start"),
            "serial_end": batch_doc.get("serial_end"),
            "qr_version": "v2",
        })

        # strip secret from response
        resp_batch = {k: v for k, v in batch_doc.items() if k != "hmac_secret"}
        return {
            "ok": True, "batch": _clean(resp_batch),
            "message": f"Generated {count} coupons in batch {batch_doc['batch_label']}. "
                       f"Activate the batch (or individual coupons) to make them usable.",
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
        # cancel remaining unused coupons — protect claimed / redeemed rows
        res = await db.dms_v2_coupons.update_many(
            {"batch_id": bid, "status": "unused"},
            {"$set": {"status": "cancelled", "active": False,
                      "deactivated_at": _now(), "deactivated_by": user["id"],
                      "updated_at": _now()}},
        )
        await _audit(user, "batch.deactivated", "batch", bid, {
            "batch_label": b["batch_label"], "cancelled_unused": res.modified_count,
        })
        return {"ok": True, "cancelled_unused": res.modified_count}

    # ─────────────────────────────────────────────────────────────────────────
    # PER-COUPON ACTIVATION (Single + Range)
    # ─────────────────────────────────────────────────────────────────────────
    @router.post("/coupons/{cid}/activate")
    async def activate_single_coupon(cid: str, user: dict = Depends(owner_or_accountant)):
        """Activate ONE coupon. Rules:
        * Batch must NOT be closed (deactivate_batch sets closed_at).
        * Coupon must be in 'generated' state OR in 'unused' with active=False.
        * Cannot activate a coupon that has been claimed/redeemed/cancelled/expired.
        * Idempotent: if already active + unused → returns ok:true, changed:false.
        """
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]})) or {}
        if batch.get("closed_at"):
            raise HTTPException(400, "Batch is closed — cannot activate coupons")
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            raise HTTPException(400, f"Coupon already {cp['status']} — cannot activate")
        if cp["status"] in ("cancelled", "voided", "expired"):
            raise HTTPException(400, f"Coupon is {cp['status']} — cannot activate")
        if cp.get("active") and cp["status"] == "unused":
            return {"ok": True, "changed": False, "message": "Already active"}
        await db.dms_v2_coupons.update_one({"id": cid}, {"$set": {
            "status": "unused", "active": True,
            "activated_at": _now(), "activated_by": user["id"],
            "updated_at": _now(),
        }})
        # if batch was 'generated', keep the coarse batch status intact; if this is
        # the first activation of any coupon and batch was 'generated', flip batch
        # to 'activated' + active=True (spec: activating any coupon activates batch).
        if batch.get("status") == "generated":
            await db.dms_v2_coupon_batches.update_one({"id": batch["id"]}, {"$set": {
                "status": "activated", "active": True,
                "activated_at": _now(), "activated_by": user["id"],
            }})
        await _audit(user, "coupon.activated", "coupon", cid, {
            "visible_serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "batch_id": cp["batch_id"], "scope": "single",
        })
        return {"ok": True, "changed": True}

    @router.post("/coupons/{cid}/deactivate")
    async def deactivate_single_coupon(cid: str, user: dict = Depends(owner_only)):
        """Deactivate a single coupon (only if not claimed/redeemed)."""
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            raise HTTPException(400, f"Cannot deactivate a {cp['status']} coupon")
        await db.dms_v2_coupons.update_one({"id": cid}, {"$set": {
            "status": "cancelled", "active": False,
            "deactivated_at": _now(), "deactivated_by": user["id"],
            "updated_at": _now(),
        }})
        await _audit(user, "coupon.deactivated", "coupon", cid, {
            "visible_serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "batch_id": cp["batch_id"], "scope": "single",
        })
        return {"ok": True}

    # ─────────────────────────────────────────────────────────────────────────
    # VOID / CANCEL (Settings) — by SERIAL number or by BATCH.
    # Voided coupons keep a full audit record and CANNOT be re-activated or
    # encashed unless an owner explicitly runs the authorized recovery flow.
    # ─────────────────────────────────────────────────────────────────────────
    async def _find_coupon_by_serial(serial: str) -> Optional[Dict[str, Any]]:
        s = (serial or "").strip().upper()
        if not s:
            return None
        cp = await db.dms_v2_coupons.find_one({"visible_serial": s})
        if not cp:
            cp = await db.dms_v2_coupons.find_one({"coupon_code": s})
        return _clean(cp)

    @router.post("/coupons/void-by-serial/preview")
    async def void_by_serial_preview(body: Dict[str, Any] = Body(...),
                                     user: dict = Depends(owner_or_accountant)):
        """Preview a single-serial void (no state change) so the UI can confirm."""
        cp = await _find_coupon_by_serial(body.get("serial") or "")
        if not cp:
            raise HTTPException(404, "No coupon found for that serial number")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]})) or {}
        can_void = cp["status"] not in ("claimed", "redemption_pending", "redeemed")
        return {
            "serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "status": cp["status"],
            "coupon_type": cp.get("coupon_type"),
            "coupon_value": cp.get("coupon_value"),
            "batch_label": batch.get("batch_label"),
            "can_void": can_void,
            "already_voided": cp["status"] == "voided",
            "reason_blocked": None if can_void else f"Coupon is {cp['status']} — cannot void",
        }

    @router.post("/coupons/void-by-serial")
    async def void_by_serial(body: Dict[str, Any] = Body(...),
                             user: dict = Depends(owner_or_accountant)):
        """Void ONE coupon by its visible serial number. Requires a reason.
        Blocks coupons already claimed/redeemed (money already given)."""
        serial = (body.get("serial") or "").strip().upper()
        reason = (body.get("reason") or "").strip()
        if not serial:
            raise HTTPException(400, "serial is required")
        if not reason:
            raise HTTPException(400, "A reason is required to void a coupon")
        cp = await _find_coupon_by_serial(serial)
        if not cp:
            raise HTTPException(404, "No coupon found for that serial number")
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            raise HTTPException(400, f"Cannot void a {cp['status']} coupon (already encashed)")
        if cp["status"] == "voided":
            return {"ok": True, "changed": False, "message": "Already voided"}
        await db.dms_v2_coupons.update_one({"id": cp["id"]}, {"$set": {
            "status": "voided", "active": False,
            "voided_at": _now(), "voided_by": user["id"],
            "voided_by_name": user.get("name") or user.get("email"),
            "void_reason": reason, "void_scope": "serial",
            "prev_status_before_void": cp["status"],
            "deactivated_at": _now(), "deactivated_by": user["id"],
            "updated_at": _now(),
        }})
        await _audit(user, "coupon.voided", "coupon", cp["id"], {
            "visible_serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "batch_id": cp["batch_id"], "scope": "serial", "reason": reason,
            "prev_status": cp["status"],
        })
        return {"ok": True, "changed": True,
                "serial": cp.get("visible_serial") or cp.get("coupon_code")}

    @router.post("/coupons/void-batch/preview")
    async def void_batch_preview(body: Dict[str, Any] = Body(...),
                                 user: dict = Depends(owner_or_accountant)):
        """Preview a batch void: how many coupons will be voided vs skipped
        (claimed/redeemed coupons are protected and skipped)."""
        bid = (body.get("batch_id") or "").strip()
        label = (body.get("batch_label") or "").strip()
        batch = None
        if bid:
            batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        elif label:
            batch = _clean(await db.dms_v2_coupon_batches.find_one({"batch_label": label}))
        if not batch:
            raise HTTPException(404, "Batch not found")
        protected = ("claimed", "redemption_pending", "redeemed")
        total = await db.dms_v2_coupons.count_documents({"batch_id": batch["id"]})
        skip = await db.dms_v2_coupons.count_documents(
            {"batch_id": batch["id"], "status": {"$in": list(protected)}})
        already = await db.dms_v2_coupons.count_documents(
            {"batch_id": batch["id"], "status": "voided"})
        return {
            "batch_id": batch["id"], "batch_label": batch.get("batch_label"),
            "total": total, "will_void": max(0, total - skip - already),
            "skipped_encashed": skip, "already_voided": already,
        }

    @router.post("/coupons/void-batch")
    async def void_batch(body: Dict[str, Any] = Body(...),
                         user: dict = Depends(owner_or_accountant)):
        """Void ALL non-encashed coupons in a batch (by batch_id or batch_label).
        Protects claimed/redeemed coupons. Requires a reason. Closes the batch."""
        bid = (body.get("batch_id") or "").strip()
        label = (body.get("batch_label") or "").strip()
        reason = (body.get("reason") or "").strip()
        if not reason:
            raise HTTPException(400, "A reason is required to void a batch")
        batch = None
        if bid:
            batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        elif label:
            batch = _clean(await db.dms_v2_coupon_batches.find_one({"batch_label": label}))
        if not batch:
            raise HTTPException(404, "Batch not found")
        res = await db.dms_v2_coupons.update_many(
            {"batch_id": batch["id"],
             "status": {"$in": ["generated", "unused", "cancelled", "assigned"]}},
            {"$set": {"status": "voided", "active": False,
                      "voided_at": _now(), "voided_by": user["id"],
                      "voided_by_name": user.get("name") or user.get("email"),
                      "void_reason": reason, "void_scope": "batch",
                      "deactivated_at": _now(), "deactivated_by": user["id"],
                      "updated_at": _now()}},
        )
        await db.dms_v2_coupon_batches.update_one({"id": batch["id"]}, {"$set": {
            "active": False, "closed_at": _now(),
            "voided_at": _now(), "voided_by": user["id"], "void_reason": reason,
        }})
        await _audit(user, "batch.voided", "batch", batch["id"], {
            "batch_label": batch.get("batch_label"), "scope": "batch",
            "reason": reason, "voided_count": res.modified_count,
        })
        return {"ok": True, "voided_count": res.modified_count,
                "batch_label": batch.get("batch_label")}

    @router.post("/coupons/{cid}/recover")
    async def recover_voided_coupon(cid: str, body: Dict[str, Any] = Body(default={}),
                                    user: dict = Depends(owner_only)):
        """AUTHORIZED RECOVERY — restore a voided coupon back to usable (unused).
        Owner only. Requires a reason. Fully audited."""
        reason = (body.get("reason") or "").strip()
        if not reason:
            raise HTTPException(400, "A reason is required for recovery")
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        if cp["status"] != "voided":
            raise HTTPException(400, f"Only voided coupons can be recovered (this is {cp['status']})")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]})) or {}
        batch_note = None
        if not batch.get("active") or batch.get("closed_at"):
            batch_note = "Batch is inactive/closed — re-activate the batch for the coupon to be scannable."
        await db.dms_v2_coupons.update_one({"id": cid}, {"$set": {
            "status": "unused", "active": True,
            "recovered_at": _now(), "recovered_by": user["id"],
            "recovered_by_name": user.get("name") or user.get("email"),
            "recover_reason": reason, "updated_at": _now(),
        }, "$unset": {"voided_at": "", "voided_by": "", "void_reason": ""}})
        await _audit(user, "coupon.recovered", "coupon", cid, {
            "visible_serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "batch_id": cp["batch_id"], "reason": reason,
        })
        return {"ok": True, "batch_note": batch_note}


    @router.post("/activate-range/preview")
    async def activate_range_preview(body: Dict[str, Any] = Body(...),
                                     user: dict = Depends(owner_or_accountant)):
        """
        Live preview of an activation range — DOES NOT change any coupon state.
        Returns coupons_found / already_active / ready_to_activate / skipped
        so the UI can render confidence-boosting details before the actual activate.

        Body: { batch_id, from_serial, to_serial }
              OR { batch_id, from_number, to_number }
        """
        batch_id = (body.get("batch_id") or "").strip()
        if not batch_id:
            raise HTTPException(400, "batch_id is required")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": batch_id}))
        if not batch:
            raise HTTPException(404, "Batch not found")
        if batch.get("closed_at"):
            raise HTTPException(400, "Batch is closed")

        from_serial_in = (body.get("from_serial") or "").strip() or None
        to_serial_in = (body.get("to_serial") or "").strip() or None
        from_num = body.get("from_number")
        to_num = body.get("to_number")

        from_serial: Optional[str] = None
        to_serial: Optional[str] = None
        if from_serial_in and to_serial_in:
            from_serial = _normalize_serial(from_serial_in, batch)
            to_serial = _normalize_serial(to_serial_in, batch)
            if not from_serial or not to_serial:
                raise HTTPException(400,
                    f"Could not interpret serial range '{from_serial_in}' … '{to_serial_in}'")
        elif from_num is not None and to_num is not None:
            if not batch.get("prefix"):
                raise HTTPException(400, "Batch has no prefix; use from_serial/to_serial instead")
            pad = int(batch.get("serial_pad") or 3)
            prefix = batch["prefix"]
            from_serial = _fmt_serial(prefix, int(from_num), pad)
            to_serial = _fmt_serial(prefix, int(to_num), pad)
        else:
            raise HTTPException(400,
                "Provide either (from_serial,to_serial) or (from_number,to_number)")

        if from_serial > to_serial:
            from_serial, to_serial = to_serial, from_serial

        # Validate FROM / TO actually exist in the batch (spec requires it)
        first_exists = await db.dms_v2_coupons.find_one(
            {"batch_id": batch_id, "visible_serial": from_serial}, {"_id": 1})
        last_exists = await db.dms_v2_coupons.find_one(
            {"batch_id": batch_id, "visible_serial": to_serial}, {"_id": 1})
        if not first_exists:
            raise HTTPException(400,
                f"From Serial {from_serial} not found in batch {batch.get('batch_label')}")
        if not last_exists:
            raise HTTPException(400,
                f"To Serial {to_serial} not found in batch {batch.get('batch_label')}")

        base_q = {
            "batch_id": batch_id,
            "visible_serial": {"$gte": from_serial, "$lte": to_serial},
        }
        # coupons_found: total coupons in this range within the batch
        coupons_found = await db.dms_v2_coupons.count_documents(base_q)

        # already_active: currently active + unused (nothing to do)
        already_active = await db.dms_v2_coupons.count_documents({
            **base_q, "status": "unused", "active": True,
        })
        # ready_to_activate: eligible for activation now
        ready_q = {
            **base_q,
            "status": {"$in": ["generated", "unused"]},
            "$or": [{"active": {"$ne": True}}, {"status": "generated"}],
        }
        ready_to_activate = await db.dms_v2_coupons.count_documents(ready_q)

        # skipped: everything else (claimed / redeemed / cancelled / expired / etc.)
        skipped = coupons_found - already_active - ready_to_activate
        if skipped < 0:
            skipped = 0

        return {
            "ok": True,
            "batch_id": batch_id,
            "batch_label": batch.get("batch_label"),
            "coupon_type": batch.get("coupon_type"),
            "coupon_value": batch.get("coupon_value"),
            "from_serial": from_serial,
            "to_serial": to_serial,
            "coupons_found": coupons_found,
            "already_active": already_active,
            "ready_to_activate": ready_to_activate,
            "skipped": skipped,
        }

    @router.post("/activate-range")
    async def activate_range(body: Dict[str, Any] = Body(...),
                             user: dict = Depends(owner_or_accountant)):
        """
        Activate a range of coupons within a batch.
        Body: { batch_id, from_serial, to_serial }
              OR { batch_id, from_number, to_number }  (uses prefix from batch)
        Only coupons currently in a NOT-YET-CLAIMED state can be activated.
        """
        batch_id = (body.get("batch_id") or "").strip()
        if not batch_id:
            raise HTTPException(400, "batch_id is required")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": batch_id}))
        if not batch:
            raise HTTPException(404, "Batch not found")
        if batch.get("closed_at"):
            raise HTTPException(400, "Batch is closed")

        from_serial_in = (body.get("from_serial") or "").strip() or None
        to_serial_in = (body.get("to_serial") or "").strip() or None
        from_num = body.get("from_number")
        to_num = body.get("to_number")

        # resolve to canonical serials (smart normalization — 'ABC1' → 'ABC001')
        from_serial: Optional[str] = None
        to_serial: Optional[str] = None
        if from_serial_in and to_serial_in:
            from_serial = _normalize_serial(from_serial_in, batch)
            to_serial = _normalize_serial(to_serial_in, batch)
            if not from_serial or not to_serial:
                raise HTTPException(400,
                    f"Could not interpret serial range '{from_serial_in}' … '{to_serial_in}' — "
                    f"expected format like {batch.get('prefix','ABC')}"
                    f"{'0' * int(batch.get('serial_pad') or 3)}1")
        elif from_num is not None and to_num is not None:
            if not batch.get("prefix"):
                raise HTTPException(400, "Batch has no prefix; use from_serial/to_serial instead")
            pad = int(batch.get("serial_pad") or 3)
            prefix = batch["prefix"]
            from_serial = _fmt_serial(prefix, int(from_num), pad)
            to_serial = _fmt_serial(prefix, int(to_num), pad)
        else:
            raise HTTPException(400, "Provide either (from_serial,to_serial) or (from_number,to_number)")

        if from_serial > to_serial:
            from_serial, to_serial = to_serial, from_serial

        # Spec: validate FROM / TO actually exist in the batch
        first_exists = await db.dms_v2_coupons.find_one(
            {"batch_id": batch_id, "visible_serial": from_serial}, {"_id": 1})
        last_exists = await db.dms_v2_coupons.find_one(
            {"batch_id": batch_id, "visible_serial": to_serial}, {"_id": 1})
        if not first_exists:
            raise HTTPException(400,
                f"From Serial {from_serial} not found in batch {batch.get('batch_label')}")
        if not last_exists:
            raise HTTPException(400,
                f"To Serial {to_serial} not found in batch {batch.get('batch_label')}")

        # RANGE query — string comparison is safe because zero-padded numeric serials
        # sort correctly lexicographically within a batch.
        q = {
            "batch_id": batch_id,
            "visible_serial": {"$gte": from_serial, "$lte": to_serial},
            "status": {"$in": ["generated", "unused"]},
            # only activate coupons that are NOT already active+unused
            "$or": [{"active": {"$ne": True}}, {"status": "generated"}],
        }
        cnt = await db.dms_v2_coupons.count_documents(q)
        res = await db.dms_v2_coupons.update_many(q, {"$set": {
            "status": "unused", "active": True,
            "activated_at": _now(), "activated_by": user["id"],
            "updated_at": _now(),
        }})
        if batch.get("status") == "generated" and res.modified_count > 0:
            await db.dms_v2_coupon_batches.update_one({"id": batch_id}, {"$set": {
                "status": "activated", "active": True,
                "activated_at": _now(), "activated_by": user["id"],
            }})
        await _audit(user, "coupon.range_activated", "batch", batch_id, {
            "batch_label": batch.get("batch_label"),
            "from_serial": from_serial, "to_serial": to_serial,
            "matched": cnt, "activated": res.modified_count,
        })
        return {"ok": True, "matched": cnt, "activated": res.modified_count,
                "from_serial": from_serial, "to_serial": to_serial}

    @router.post("/deactivate-range")
    async def deactivate_range(body: Dict[str, Any] = Body(...),
                               user: dict = Depends(owner_only)):
        """Deactivate a range of coupons (cancel them). Claimed/redeemed rows are
        protected and skipped."""
        batch_id = (body.get("batch_id") or "").strip()
        if not batch_id:
            raise HTTPException(400, "batch_id is required")
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": batch_id}))
        if not batch:
            raise HTTPException(404, "Batch not found")
        from_serial_in = (body.get("from_serial") or "").strip()
        to_serial_in = (body.get("to_serial") or "").strip()
        if not from_serial_in or not to_serial_in:
            raise HTTPException(400, "from_serial and to_serial are required")
        from_serial = _normalize_serial(from_serial_in, batch)
        to_serial = _normalize_serial(to_serial_in, batch)
        if not from_serial or not to_serial:
            raise HTTPException(400, f"Could not interpret range '{from_serial_in}' … '{to_serial_in}'")
        if from_serial > to_serial:
            from_serial, to_serial = to_serial, from_serial
        q = {
            "batch_id": batch_id,
            "visible_serial": {"$gte": from_serial, "$lte": to_serial},
            "status": {"$in": ["generated", "unused"]},
        }
        res = await db.dms_v2_coupons.update_many(q, {"$set": {
            "status": "cancelled", "active": False,
            "deactivated_at": _now(), "deactivated_by": user["id"],
            "updated_at": _now(),
        }})
        await _audit(user, "coupon.range_deactivated", "batch", batch_id, {
            "batch_label": batch.get("batch_label"),
            "from_serial": from_serial, "to_serial": to_serial,
            "deactivated": res.modified_count,
        })
        return {"ok": True, "deactivated": res.modified_count,
                "from_serial": from_serial, "to_serial": to_serial}

    @router.post("/coupons/bulk-activate")
    async def bulk_activate_coupons(body: Dict[str, Any] = Body(...),
                                    user: dict = Depends(owner_or_accountant)):
        """Activate a hand-picked list of coupon IDs. Skips coupons that cannot
        be activated (already claimed / cancelled / expired) and returns per-coupon
        status."""
        coupon_ids: List[str] = list(body.get("coupon_ids") or [])
        if not coupon_ids:
            raise HTTPException(400, "coupon_ids is required")
        if len(coupon_ids) > 10_000:
            raise HTTPException(400, "Cannot activate more than 10,000 coupons in one call")
        # only touch coupons currently in a non-terminal state
        q = {"id": {"$in": coupon_ids},
             "status": {"$in": ["generated", "unused"]},
             "$or": [{"active": {"$ne": True}}, {"status": "generated"}]}
        matched = await db.dms_v2_coupons.count_documents(q)
        res = await db.dms_v2_coupons.update_many(q, {"$set": {
            "status": "unused", "active": True,
            "activated_at": _now(), "activated_by": user["id"],
            "updated_at": _now(),
        }})
        # Flip any generated batches touched by this activation to 'activated'
        touched_batches = await db.dms_v2_coupons.distinct("batch_id", {"id": {"$in": coupon_ids}})
        if touched_batches:
            await db.dms_v2_coupon_batches.update_many(
                {"id": {"$in": touched_batches}, "status": "generated"},
                {"$set": {"status": "activated", "active": True,
                          "activated_at": _now(), "activated_by": user["id"]}},
            )
        await _audit(user, "coupon.bulk_activated", "coupons", "", {
            "requested": len(coupon_ids),
            "matched_eligible": matched,
            "activated": res.modified_count,
            "batches": touched_batches,
        })
        return {"ok": True,
                "requested": len(coupon_ids),
                "matched_eligible": matched,
                "activated": res.modified_count,
                "skipped": len(coupon_ids) - res.modified_count}

    @router.post("/coupons/bulk-deactivate")
    async def bulk_deactivate_coupons(body: Dict[str, Any] = Body(...),
                                      user: dict = Depends(owner_only)):
        """Deactivate a hand-picked list of coupon IDs (claimed/redeemed rows skipped)."""
        coupon_ids: List[str] = list(body.get("coupon_ids") or [])
        if not coupon_ids:
            raise HTTPException(400, "coupon_ids is required")
        if len(coupon_ids) > 10_000:
            raise HTTPException(400, "Cannot deactivate more than 10,000 coupons in one call")
        q = {"id": {"$in": coupon_ids},
             "status": {"$in": ["generated", "unused"]}}
        res = await db.dms_v2_coupons.update_many(q, {"$set": {
            "status": "cancelled", "active": False,
            "deactivated_at": _now(), "deactivated_by": user["id"],
            "updated_at": _now(),
        }})
        await _audit(user, "coupon.bulk_deactivated", "coupons", "", {
            "requested": len(coupon_ids), "deactivated": res.modified_count,
        })
        return {"ok": True,
                "requested": len(coupon_ids),
                "deactivated": res.modified_count,
                "skipped": len(coupon_ids) - res.modified_count}

    # ─────────────────────────────────────────────────────────────────────────
    # QR IMAGE + PAYLOAD (owner / accountant only) — for showing QR & unique ID
    # on the Owner dashboard alongside the visible serial.
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/coupons/{cid}/qr-image")
    async def coupon_qr_image(cid: str, size: int = Query(6, ge=2, le=20),
                              user: dict = Depends(owner_or_accountant)):
        """Return the QR code as a PNG image for a single coupon.
        Available to Owner + Owner Accountant only.
        """
        import qrcode
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        # reconstruct the canonical v2 payload from stored ciphertext + sig,
        # or fall back to v1 legacy payload for pre-migration coupons.
        if cp.get("qr_version") == "v2" and cp.get("qr_ciphertext_b64") and cp.get("qr_signature_v2"):
            payload = f"GOOIL2|{cp['qr_ciphertext_b64']}|{cp['qr_signature_v2']}"
        else:
            payload = _qr_payload(cp.get("coupon_code") or cp.get("visible_serial"),
                                   cp.get("secret_token", ""), cp.get("signature", ""))
        qr = qrcode.QRCode(version=None, box_size=size, border=2,
                            error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png",
                        headers={"Cache-Control": "private, max-age=3600"})

    @router.get("/coupons/{cid}/qr-payload")
    async def coupon_qr_payload(cid: str, user: dict = Depends(owner_or_accountant)):
        """Return the raw QR payload string + all identifiers of a single coupon.
        Available to Owner + Owner Accountant only. Used by the UI to show
        Visible Serial, Hidden Unique ID (UUID v4), and the encrypted QR text.
        Signature/ciphertext are included since Owner+Accountant already have
        full access to the batch data on their dashboard.
        """
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        if cp.get("qr_version") == "v2" and cp.get("qr_ciphertext_b64") and cp.get("qr_signature_v2"):
            payload = f"GOOIL2|{cp['qr_ciphertext_b64']}|{cp['qr_signature_v2']}"
        else:
            payload = _qr_payload(cp.get("coupon_code") or cp.get("visible_serial"),
                                   cp.get("secret_token", ""), cp.get("signature", ""))
        return {
            "id": cp["id"],
            "visible_serial": cp.get("visible_serial") or cp.get("coupon_code"),
            "hidden_secure_id": cp.get("hidden_secure_id"),
            "qr_version": cp.get("qr_version") or "v1",
            "qr_payload": payload,
            "batch_id": cp.get("batch_id"),
            "batch_label": cp.get("batch_label"),
            "coupon_type": cp.get("coupon_type"),
            "coupon_value": cp.get("coupon_value"),
            "status": cp.get("status"),
            "active": bool(cp.get("active")),
        }

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
    async def export_pdf(bid: str,
                          diameter_mm: float = 35.0,
                          per_row: Optional[int] = None,
                          side: str = Query("both", pattern="^(front|back|both)$"),
                          user: dict = Depends(owner_only)):
        """
        Printable PDF for the printing press — matches the GOOIL CorelDraw
        circular coupon design (die-cut circular MECHANIC COUPON).

        Query params:
          diameter_mm  – die-cut coupon diameter in mm (default 34, matches CorelDraw)
          per_row      – override columns per row (auto-fit based on diameter by default)

        STRICTLY contains only:
          * QR image  (encrypted payload — v2)
          * Visible Serial
          * Coupon Type
          * Coupon Value

        No UUID, no secret token, no signature, no batch label, no batch secret,
        no internal IDs are ever printed. High-res QR (ERROR_CORRECT_H).
        """
        import qrcode
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import HexColor, white

        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        coupons = await db.dms_v2_coupons.find({"batch_id": bid}, {"_id": 0})\
            .sort("visible_serial", 1).to_list(200_000)
        if not coupons:
            raise HTTPException(400, "No coupons in batch")

        # ── Build the print-ready PDF from the OFFICIAL artwork template ──
        # 11x17in sheet, 35mm round die-cut, cutting-friendly grid, front + back,
        # mixed values supported. Only QR / Serial / Value are dynamic; the
        # approved GOOiL artwork is used verbatim (never redrawn).
        import coupon_template
        pdf_bytes = coupon_template.build_print_pdf(
            coupons, side=side, title=b.get("batch_label", "coupons"))
        buf = BytesIO(pdf_bytes)
        buf.seek(0)

        # mark printed (idempotent)
        if b["status"] in ("activated",):
            await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
                "status": "printed", "printed_at": _now(), "printed_by": user["id"],
            }})
            await _audit(user, "batch.printed", "batch", bid,
                         {"batch_label": b["batch_label"],
                          "diameter_mm": 35.0, "side": side,
                          "layout": "11x17in/35mm/cutting-friendly"})

        return Response(
            content=buf.read(),
            media_type="application/pdf",
            headers={"Content-Disposition":
                     f'attachment; filename="{b["batch_label"]}_coupons_35mm_{side}.pdf"'},
        )

    # ─── ASYNC batch PDF (background render + poll + download) ──────────────
    # For large batches the synchronous endpoint above can exceed the proxy
    # timeout. These endpoints render in the background so the HTTP request
    # returns immediately; the client polls status then downloads.
    @router.post("/batches/{bid}/export-pdf-async")
    async def export_pdf_async(bid: str,
                               side: str = Query("both", pattern="^(front|back|both)$"),
                               user: dict = Depends(owner_only)):
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        coupons = await db.dms_v2_coupons.find({"batch_id": bid}, {"_id": 0})\
            .sort("visible_serial", 1).to_list(200_000)
        if not coupons:
            raise HTTPException(400, "No coupons in batch")

        # mark printed (idempotent) — same behaviour as sync endpoint
        if b["status"] in ("activated",):
            await db.dms_v2_coupon_batches.update_one({"id": bid}, {"$set": {
                "status": "printed", "printed_at": _now(), "printed_by": user["id"],
            }})
            await _audit(user, "batch.printed", "batch", bid,
                         {"batch_label": b["batch_label"], "diameter_mm": 35.0,
                          "side": side, "layout": "11x17in/35mm/cutting-friendly"})

        job_id = _nid("pdfjob")
        filename = f'{b["batch_label"]}_coupons_35mm_{side}.pdf'
        _PDF_JOBS[job_id] = {
            "status": "pending", "path": None, "filename": filename,
            "error": None, "count": len(coupons), "_ts": datetime.now(timezone.utc).timestamp(),
        }
        _prune_pdf_jobs()

        async def _run():
            try:
                import coupon_template
                pdf_bytes = await asyncio.to_thread(
                    coupon_template.build_print_pdf, coupons, side=side,
                    title=b.get("batch_label", "coupons"))
                path = os.path.join(_PDF_JOB_DIR, job_id + ".pdf")
                with open(path, "wb") as fh:
                    fh.write(pdf_bytes)
                _PDF_JOBS[job_id].update(status="done", path=path)
            except Exception as e:  # pragma: no cover
                _PDF_JOBS[job_id].update(status="error", error=str(e))

        asyncio.create_task(_run())
        return {"job_id": job_id, "status": "pending", "count": len(coupons), "filename": filename}

    @router.get("/pdf-jobs/{job_id}")
    async def pdf_job_status(job_id: str, user: dict = Depends(owner_only)):
        j = _PDF_JOBS.get(job_id)
        if not j:
            raise HTTPException(404, "Job not found or expired")
        return {"status": j["status"], "ready": j["status"] == "done",
                "error": j.get("error"), "filename": j.get("filename"),
                "count": j.get("count")}

    @router.get("/pdf-jobs/{job_id}/download")
    async def pdf_job_download(job_id: str, user: dict = Depends(owner_only)):
        j = _PDF_JOBS.get(job_id)
        if not j:
            raise HTTPException(404, "Job not found or expired")
        if j["status"] == "error":
            raise HTTPException(500, j.get("error") or "PDF generation failed")
        if j["status"] != "done" or not j.get("path") or not os.path.exists(j["path"]):
            raise HTTPException(409, "PDF not ready yet")
        with open(j["path"], "rb") as fh:
            data = fh.read()
        return Response(
            content=data, media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{j["filename"]}"'},
        )

    # ─── MIXED PRINTING — many batches / selected coupons on shared sheets ──
    import coupon_template as _ct
    COUPONS_PER_SHEET = _ct.PER_SHEET  # 11x17in / 35mm cutting-friendly grid (77)

    async def _resolve_mixed_coupons(body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve a mixed-print selection body into a de-duplicated, sorted
        list of coupon docs. Supports coupon_ids / batch_ids / items(range)."""
        coupons: List[Dict[str, Any]] = []
        seen: set[str] = set()

        def _add(cursor_docs):
            for cp in cursor_docs:
                if cp["id"] not in seen:
                    seen.add(cp["id"])
                    coupons.append(cp)

        if body.get("coupon_ids"):
            docs = await db.dms_v2_coupons.find(
                {"id": {"$in": list(body["coupon_ids"])}}, {"_id": 0}
            ).sort("visible_serial", 1).to_list(200_000)
            _add(docs)
        if body.get("batch_ids"):
            docs = await db.dms_v2_coupons.find(
                {"batch_id": {"$in": list(body["batch_ids"])}}, {"_id": 0}
            ).sort("visible_serial", 1).to_list(200_000)
            _add(docs)
        for item in (body.get("items") or []):
            q: Dict[str, Any] = {"batch_id": item.get("batch_id")}
            fs, ts = item.get("from_serial"), item.get("to_serial")
            if fs and ts:
                q["visible_serial"] = {"$gte": str(fs), "$lte": str(ts)}
            docs = await db.dms_v2_coupons.find(q, {"_id": 0})\
                .sort("visible_serial", 1).to_list(200_000)
            _add(docs)
        return coupons

    async def _label_for_selection(body: Dict[str, Any]) -> str:
        """Human-readable description of a print selection for the history log."""
        parts: List[str] = []
        b_ids = list(body.get("batch_ids") or [])
        if b_ids:
            docs = await db.dms_v2_coupon_batches.find(
                {"id": {"$in": b_ids}}, {"_id": 0, "batch_label": 1}).to_list(500)
            labels = [d.get("batch_label", "?") for d in docs]
            parts.append("Batches: " + ", ".join(labels))
        for item in (body.get("items") or []):
            bdoc = await db.dms_v2_coupon_batches.find_one(
                {"id": item.get("batch_id")}, {"_id": 0, "batch_label": 1})
            bl = (bdoc or {}).get("batch_label", "?")
            fs, ts = item.get("from_serial"), item.get("to_serial")
            if fs and ts:
                parts.append(f"{bl} [{fs} → {ts}]")
            else:
                parts.append(f"{bl} (all)")
        if body.get("coupon_ids"):
            parts.append(f"{len(body['coupon_ids'])} selected coupons")
        return " · ".join(parts) or "Custom selection"

    @router.post("/print-mixed")
    async def print_mixed(body: Dict[str, Any] = Body(...),
                           user: dict = Depends(owner_or_accountant)):
        """
        Commercial print-ready PDF mixing DIFFERENT coupon values/types on the
        SAME 11x17in sheet (35mm round, cutting-friendly grid, auto sheet calc).
        Every successful print is saved to the Print History (re-downloadable).

        Body (any combination of):
          { "coupon_ids": ["cpn_..", ...] }
          { "batch_ids":  ["cbt_..", ...] }
          { "items": [ {"batch_id": "cbt_..", "from_serial": "AB001",
                        "to_serial": "AB050"}, ... ] }
        Optional: { "side": "front"|"back"|"both" }
        """
        import coupon_template
        import math
        side = (body.get("side") or "both").strip().lower()
        if side not in ("front", "back", "both"):
            side = "both"

        coupons = await _resolve_mixed_coupons(body)
        if not coupons:
            raise HTTPException(400, "No coupons matched the selection")

        count = len(coupons)
        sheets = max(1, math.ceil(count / COUPONS_PER_SHEET))
        pdf_bytes = coupon_template.build_print_pdf(coupons, side=side, title="mixed")

        # save print-history record (selection criteria only — small footprint,
        # re-resolved on re-download so it always reflects current QR/serials)
        selection = {
            "coupon_ids": list(body.get("coupon_ids") or []),
            "batch_ids": list(body.get("batch_ids") or []),
            "items": list(body.get("items") or []),
            "side": side,
        }
        hist = {
            "id": _nid("prh"),
            "label": await _label_for_selection(body),
            "selection": selection,
            "coupon_count": count,
            "sheet_count": sheets,
            "per_sheet": COUPONS_PER_SHEET,
            "side": side,
            "created_at": _now(),
            "created_by": user.get("id"),
            "created_by_name": user.get("name") or user.get("email"),
        }
        await db.dms_v2_coupon_print_history.insert_one({**hist})
        await _audit(user, "coupons.print_mixed", "coupon", hist["id"],
                     {"count": count, "sheets": sheets, "side": side})
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition":
                     f'attachment; filename="GOOIL_mixed_{count}_coupons_{side}.pdf"'},
        )

    @router.post("/print-mixed/preview")
    async def print_mixed_preview(body: Dict[str, Any] = Body(...),
                                   user: dict = Depends(owner_or_accountant)):
        """Compute count + sheet breakdown for a selection WITHOUT generating a PDF."""
        import math
        coupons = await _resolve_mixed_coupons(body)
        count = len(coupons)
        sheets = max(1, math.ceil(count / COUPONS_PER_SHEET)) if count else 0
        # per-sheet breakdown, e.g. [77, 77, 46]
        breakdown: List[int] = []
        remaining = count
        while remaining > 0:
            take = min(COUPONS_PER_SHEET, remaining)
            breakdown.append(take)
            remaining -= take
        return {
            "coupon_count": count,
            "sheet_count": sheets,
            "per_sheet": COUPONS_PER_SHEET,
            "breakdown": breakdown,
            "label": await _label_for_selection(body),
        }

    # ─── PRINT HISTORY — list / re-download / delete ──────────────────────────
    @router.get("/print-history")
    async def list_print_history(user: dict = Depends(owner_or_accountant)):
        docs = await db.dms_v2_coupon_print_history.find({}, {"_id": 0})\
            .sort("created_at", -1).to_list(1000)
        return {"data": docs}

    @router.get("/print-history/{hid}/download")
    async def reprint_history(hid: str, user: dict = Depends(owner_or_accountant)):
        h = _clean(await db.dms_v2_coupon_print_history.find_one({"id": hid}))
        if not h:
            raise HTTPException(404, "Print history record not found")
        import coupon_template
        sel = h.get("selection") or {}
        coupons = await _resolve_mixed_coupons(sel)
        if not coupons:
            raise HTTPException(400, "The coupons for this print no longer exist")
        side = sel.get("side") or h.get("side") or "both"
        pdf_bytes = coupon_template.build_print_pdf(coupons, side=side, title="mixed")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition":
                     f'attachment; filename="GOOIL_reprint_{len(coupons)}_coupons_{side}.pdf"'},
        )

    @router.delete("/print-history/{hid}")
    async def delete_print_history(hid: str, user: dict = Depends(owner_or_accountant)):
        h = await db.dms_v2_coupon_print_history.find_one({"id": hid}, {"_id": 0})
        if not h:
            raise HTTPException(404, "Print history record not found")
        await db.dms_v2_coupon_print_history.delete_one({"id": hid})
        await _audit(user, "coupons.print_history_deleted", "coupon", hid,
                     {"label": h.get("label"), "coupon_count": h.get("coupon_count")})
        return {"ok": True}


    # ─── Public share link (for sending PDF to printer via WhatsApp) ──────
    @router.post("/batches/{bid}/share-link")
    async def create_share_link(bid: str,
                                 body: Dict[str, Any] = Body(default={}),
                                 request: Request = None,
                                 user: dict = Depends(owner_or_accountant)):
        """
        Creates a signed, time-limited public URL that returns the printable PDF
        WITHOUT needing an auth token — so it can be shared to the printer over
        WhatsApp / Email. Link expires in 24 h.
        """
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        diameter_mm = float(body.get("diameter_mm") or 34.0)
        diameter_mm = max(20.0, min(80.0, diameter_mm))
        exp = int(datetime.utcnow().timestamp()) + 24 * 3600     # 24h

        secret = os.environ.get("APP_SECRET") \
            or os.environ.get("JWT_SECRET") \
            or "gooil-dms-share-fallback-secret"
        raw = f"{bid}|{diameter_mm}|{exp}".encode()
        sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()[:32]
        # Use '~' as delimiter — never appears in bid or float strings
        token = base64.urlsafe_b64encode(
            f"{bid}~{diameter_mm}~{exp}~{sig}".encode()).decode().rstrip("=")

        # Build absolute URL — request.base_url gives correct ingress URL
        base = str(request.base_url).rstrip("/") if request else ""
        share_url = f"{base}/api/dms/coupons/batches/public-download/{token}"
        await _audit(user, "batch.share_link_created", "batch", bid, {
            "batch_label": b["batch_label"], "diameter_mm": diameter_mm,
            "expires_at": datetime.utcfromtimestamp(exp).isoformat() + "Z",
        })
        return {
            "ok": True,
            "share_url": share_url,
            "expires_at": datetime.utcfromtimestamp(exp).isoformat() + "Z",
            "batch_label": b["batch_label"],
            "coupon_count": await db.dms_v2_coupons.count_documents({"batch_id": bid}),
            "diameter_mm": diameter_mm,
        }

    @router.get("/batches/public-download/{token}")
    async def public_download(token: str):
        """
        Public (no-auth) PDF download using a signed token from share-link.
        Used by the printer's WhatsApp — link only, no login.
        """
        try:
            padded = token + "=" * (-len(token) % 4)
            raw = base64.urlsafe_b64decode(padded).decode()
            bid, diameter_mm, exp, sig = raw.split("~", 3)
            diameter_mm = float(diameter_mm)
            exp = int(exp)
        except Exception:
            raise HTTPException(400, "Malformed share token")
        if int(datetime.utcnow().timestamp()) > exp:
            raise HTTPException(410, "Share link has expired")
        secret = os.environ.get("APP_SECRET") \
            or os.environ.get("JWT_SECRET") \
            or "gooil-dms-share-fallback-secret"
        expected = hmac.new(secret.encode(),
                            f"{bid}|{diameter_mm}|{exp}".encode(),
                            hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(403, "Invalid share signature")

        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        # reuse export_pdf logic — synthesize a fake owner user for the call
        fake_owner = {"id": "share-link", "tenant_id": b.get("tenant_id")}
        return await export_pdf(bid=bid, diameter_mm=diameter_mm,
                                per_row=None, user=fake_owner)
    @router.get("/batches/{bid}/export-xlsx")
    async def export_xlsx(bid: str, user: dict = Depends(owner_only)):
        """Excel MANIFEST for internal audit (owner-only).
        Deliberately does NOT include the QR payload, hidden_secure_id, secret_token
        or signature — those are printing/scan artifacts and should not be exported
        even to the audit team. Owner can regenerate PDF anytime.
        """
        from openpyxl import Workbook
        b = _clean(await db.dms_v2_coupon_batches.find_one({"id": bid}))
        if not b:
            raise HTTPException(404, "Batch not found")
        coupons = await db.dms_v2_coupons.find({"batch_id": bid}, {"_id": 0})\
            .sort("visible_serial", 1).to_list(200_000)
        wb = Workbook()
        ws = wb.active
        ws.title = "Coupons"
        ws.append([
            "Visible Serial", "Type", "Value", "Status", "Active", "Batch",
            "Retailer", "Distributor", "Claimed On", "Claimed By",
        ])
        for cp in coupons:
            ws.append([
                cp.get("visible_serial") or cp.get("coupon_code") or "",
                cp["coupon_type"], cp["coupon_value"],
                cp["status"], "YES" if cp.get("active") else "NO",
                b["batch_label"],
                cp.get("retailer_name") or "",
                cp.get("distributor_name") or "",
                (cp.get("claim_timestamp") or "")[:19].replace("T", " "),
                cp.get("claimed_by_user_name") or "",
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
        serial: Optional[str] = Query(None),
        active: Optional[bool] = Query(None),
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
        if serial:
            s = serial.strip().upper()
            q["$or"] = [{"visible_serial": s}, {"coupon_code": s}]
        if active is not None:
            q["active"] = bool(active)
        # Owner + Accountant see visible_serial + hidden_secure_id (unique ID),
        # but the actual crypto material (secret_token / signatures / ciphertext)
        # is ALWAYS hidden — reconstruct via /coupons/{cid}/qr-payload if needed.
        projection = {"_id": 0,
                      "secret_token": 0, "signature": 0,
                      "qr_ciphertext_b64": 0, "qr_signature_v2": 0, "qr_hash": 0}
        docs = await db.dms_v2_coupons.find(q, projection)\
            .sort("visible_serial", 1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/detail/{cid}")
    async def get_coupon(cid: str, user: dict = Depends(get_current_user)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        cp = _clean(await db.dms_v2_coupons.find_one({"id": cid}))
        if not cp:
            raise HTTPException(404, "Coupon not found")
        # Hide only the crypto material — keep visible_serial + hidden_secure_id
        for k in ("secret_token", "signature", "qr_ciphertext_b64",
                  "qr_signature_v2", "qr_hash"):
            cp.pop(k, None)
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

    # ═════════════════════════════════════════════════════════════════════════
    # BOX MANAGEMENT — production boxes link coupon ranges → distributor
    #   Flow: Generate → Print → Production → Create Box →
    #         Assign coupon range to Box → Assign Box to Distributor
    # ═════════════════════════════════════════════════════════════════════════
    async def _next_box_number() -> Tuple[str, int]:
        counter = await db.dms_v2_meta.find_one_and_update(
            {"key": "box_counter"}, {"$inc": {"value": 1}},
            upsert=True, return_document=True)
        n = int((counter or {}).get("value", 1))
        return f"BOX{n:06d}", n

    async def _distributor(did: Optional[str]) -> Dict[str, Any]:
        if not did:
            return {}
        return _clean(await db.dms_distributors.find_one({"id": did})) or {}

    @router.post("/boxes")
    async def create_box(body: Dict[str, Any] = Body(default_factory=dict),
                         user: dict = Depends(owner_or_accountant)):
        """Create a production box (auto BOX000001). Optionally assign a
        distributor at creation. Coupons are attached later via assign-coupons."""
        box_number, box_no = await _next_box_number()
        did = (body.get("distributor_id") or "").strip() or None
        dist = await _distributor(did)
        doc = {
            "id": _nid("box"),
            "box_number": box_number,
            "box_no": box_no,
            "distributor_id": did,
            "distributor_name": dist.get("name"),
            "coupon_count": 0,
            "serial_from": None,
            "serial_to": None,
            "notes": (body.get("notes") or "").strip(),
            "status": "assigned" if did else "created",
            "created_by": user["id"],
            "created_by_name": user.get("name"),
            "created_at": _now(),
            "assigned_at": _now() if did else None,
            "updated_at": _now(),
        }
        await db.dms_v2_boxes.insert_one(doc)
        await _audit(user, "box.created", "box", doc["id"],
                     {"box_number": box_number, "distributor_id": did})
        return {"ok": True, "box": _clean(doc)}

    @router.get("/boxes")
    async def list_boxes(distributor_id: Optional[str] = Query(None),
                        status: Optional[str] = Query(None),
                        user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        # distributor can only see their own boxes
        if user.get("role") in ("distributor", "distributor_accountant"):
            q["distributor_id"] = user.get("distributor_id") or user.get("id")
        elif distributor_id:
            q["distributor_id"] = distributor_id
        if status:
            q["status"] = status
        docs = await db.dms_v2_boxes.find(q, {"_id": 0}).sort("box_no", -1).to_list(5000)
        return {"data": docs, "count": len(docs)}

    @router.get("/boxes/stats")
    async def box_stats(user: dict = Depends(get_current_user)):
        """Small summary for the owner dashboard card:
        boxes created / assigned / coupons in boxes / coupons claimed."""
        boxes_total = await db.dms_v2_boxes.count_documents({})
        boxes_assigned = await db.dms_v2_boxes.count_documents(
            {"distributor_id": {"$nin": [None, ""]}})
        coupons_in_boxes = await db.dms_v2_coupons.count_documents(
            {"box_id": {"$nin": [None, ""]}})
        coupons_claimed = await db.dms_v2_coupons.count_documents({
            "box_id": {"$nin": [None, ""]},
            "status": {"$in": ["claimed", "redemption_pending", "redeemed"]},
        })
        return {
            "boxes_total": boxes_total,
            "boxes_assigned": boxes_assigned,
            "boxes_unassigned": max(boxes_total - boxes_assigned, 0),
            "coupons_in_boxes": coupons_in_boxes,
            "coupons_claimed": coupons_claimed,
        }

    @router.get("/boxes/{bid}")
    async def get_box(bid: str, user: dict = Depends(get_current_user)):
        box = _clean(await db.dms_v2_boxes.find_one({"id": bid}))
        if not box:
            raise HTTPException(404, "Box not found")
        coupons = await db.dms_v2_coupons.find(
            {"box_id": bid}, {"_id": 0, "visible_serial": 1, "coupon_type": 1,
                              "coupon_value": 1, "status": 1, "active": 1}
        ).sort("visible_serial", 1).to_list(100_000)
        return {"box": box, "coupons": coupons, "coupon_count": len(coupons)}

    @router.post("/boxes/{bid}/assign-coupons")
    async def box_assign_coupons(bid: str, body: Dict[str, Any] = Body(...),
                                user: dict = Depends(owner_or_accountant)):
        """Attach an ACTIVE coupon range (or explicit ids) to a box.
        Body: {batch_id, from_serial, to_serial} OR {coupon_ids:[...]}"""
        box = _clean(await db.dms_v2_boxes.find_one({"id": bid}))
        if not box:
            raise HTTPException(404, "Box not found")

        q: Dict[str, Any] = {}
        if body.get("coupon_ids"):
            q = {"id": {"$in": list(body["coupon_ids"])}}
        else:
            fs, ts = body.get("from_serial"), body.get("to_serial")
            if not (fs and ts):
                raise HTTPException(400, "Provide coupon_ids OR from_serial+to_serial")
            q = {"visible_serial": {"$gte": str(fs), "$lte": str(ts)}}
            if body.get("batch_id"):
                q["batch_id"] = body["batch_id"]

        coupons = await db.dms_v2_coupons.find(q, {"_id": 0}).to_list(200_000)
        if not coupons:
            raise HTTPException(400, "No coupons matched the selection")

        # only ACTIVE, not-yet-boxed coupons can be assigned
        eligible = [c for c in coupons if c.get("active")
                    and not (c.get("box_id") and c.get("box_id") != bid)]
        if not eligible:
            raise HTTPException(400,
                "No eligible coupons — they must be ACTIVE and not already in another box")

        ids = [c["id"] for c in eligible]
        set_fields: Dict[str, Any] = {
            "box_id": bid, "box_number": box["box_number"],
            "assigned_via": "box", "updated_at": _now(),
        }
        # if box already has a distributor, propagate it to the coupons
        if box.get("distributor_id"):
            set_fields["assigned_distributor_id"] = box["distributor_id"]
            set_fields["assigned_distributor_name"] = box.get("distributor_name")
            set_fields["assigned_on"] = _now()
        await db.dms_v2_coupons.update_many({"id": {"$in": ids}}, {"$set": set_fields})

        serials = sorted(c["visible_serial"] for c in eligible)
        total = await db.dms_v2_coupons.count_documents({"box_id": bid})
        await db.dms_v2_boxes.update_one({"id": bid}, {"$set": {
            "coupon_count": total,
            "serial_from": serials[0], "serial_to": serials[-1],
            "updated_at": _now(),
        }})
        await _audit(user, "box.coupons_assigned", "box", bid,
                     {"box_number": box["box_number"], "assigned": len(ids),
                      "from": serials[0], "to": serials[-1]})
        return {"ok": True, "assigned": len(ids), "box_coupon_count": total,
                "serial_from": serials[0], "serial_to": serials[-1]}

    @router.post("/boxes/{bid}/assign-distributor")
    async def box_assign_distributor(bid: str, body: Dict[str, Any] = Body(...),
                                    user: dict = Depends(owner_or_accountant)):
        """Assign the box (and therefore all its coupons) to a distributor."""
        box = _clean(await db.dms_v2_boxes.find_one({"id": bid}))
        if not box:
            raise HTTPException(404, "Box not found")
        did = (body.get("distributor_id") or "").strip()
        if not did:
            raise HTTPException(400, "distributor_id is required")
        dist = await _distributor(did)
        if not dist:
            raise HTTPException(404, "Distributor not found")
        await db.dms_v2_boxes.update_one({"id": bid}, {"$set": {
            "distributor_id": did, "distributor_name": dist.get("name"),
            "status": "assigned", "assigned_at": _now(), "updated_at": _now(),
        }})
        res = await db.dms_v2_coupons.update_many({"box_id": bid}, {"$set": {
            "assigned_distributor_id": did,
            "assigned_distributor_name": dist.get("name"),
            "assigned_on": _now(), "updated_at": _now(),
        }})
        await _audit(user, "box.distributor_assigned", "box", bid,
                     {"box_number": box["box_number"], "distributor_id": did,
                      "coupons_updated": res.modified_count})
        return {"ok": True, "distributor_id": did,
                "distributor_name": dist.get("name"),
                "coupons_updated": res.modified_count}

    @router.get("/boxes/{bid}/scan-history")
    async def box_scan_history(bid: str, user: dict = Depends(get_current_user)):
        """Per-box scan history — which coupons were claimed, by whom and where."""
        box = _clean(await db.dms_v2_boxes.find_one({"id": bid}))
        if not box:
            raise HTTPException(404, "Box not found")
        if user.get("role") in ("distributor", "distributor_accountant"):
            own = user.get("distributor_id") or user.get("id")
            if box.get("distributor_id") != own:
                raise HTTPException(403, "Not your box")
        coupons = await db.dms_v2_coupons.find(
            {"box_id": bid,
             "status": {"$in": ["claimed", "redemption_pending", "redeemed"]}},
            {"_id": 0, "visible_serial": 1, "coupon_code": 1, "coupon_type": 1,
             "coupon_value": 1, "status": 1, "retailer_name": 1, "retailer_id": 1,
             "claimed_by_user_name": 1, "claim_timestamp": 1, "claim_ip": 1,
             "claim_gps_lat": 1, "claim_gps_lng": 1, "scan_channel": 1},
        ).sort("claim_timestamp", -1).to_list(100_000)
        total = int(box.get("coupon_count") or 0)
        claimed = len(coupons)
        return {
            "box": {"id": box["id"], "box_number": box.get("box_number"),
                    "distributor_name": box.get("distributor_name"),
                    "serial_from": box.get("serial_from"),
                    "serial_to": box.get("serial_to")},
            "coupon_count": total, "claimed_count": claimed,
            "pending_count": max(total - claimed, 0), "data": coupons,
        }

    @router.get("/boxes/{bid}/label-pdf")
    async def box_label_pdf(bid: str, user: dict = Depends(owner_or_accountant)):
        """Printable production-floor label/sticker for a box:
        big Box Number + coupon serial range + distributor + Code128 barcode."""
        box = _clean(await db.dms_v2_boxes.find_one({"id": bid}))
        if not box:
            raise HTTPException(404, "Box not found")
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.colors import HexColor, black, white

        buf = BytesIO()
        W, H = A4
        c = pdfcanvas.Canvas(buf, pagesize=A4)
        gold = HexColor("#a67c00")
        c.setStrokeColor(gold); c.setLineWidth(3)
        c.rect(15 * mm, 15 * mm, W - 30 * mm, H - 30 * mm)
        c.setFillColor(gold)
        c.rect(15 * mm, H - 45 * mm, W - 30 * mm, 30 * mm, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(W / 2, H - 34 * mm, "GO OIL — PRODUCTION BOX")
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 58)
        c.drawCentredString(W / 2, H - 92 * mm, box.get("box_number") or "BOX")

        y = [H - 118 * mm]

        def line(lbl, val):
            c.setFont("Helvetica-Bold", 14); c.drawString(30 * mm, y[0], lbl)
            c.setFont("Helvetica", 14); c.drawString(85 * mm, y[0], str(val))
            y[0] -= 13 * mm

        rng = (f"{box.get('serial_from')}  ->  {box.get('serial_to')}"
               if box.get("serial_from") else "-- not assigned --")
        line("Serial Range:", rng)
        line("Coupons:", box.get("coupon_count") or 0)
        line("Distributor:", box.get("distributor_name") or "Not assigned")
        line("Status:", (box.get("status") or "").upper())
        line("Printed:", _now()[:19].replace("T", " "))

        try:
            from reportlab.graphics.barcode import code128
            bc = code128.Code128(box.get("box_number") or "BOX",
                                 barHeight=24 * mm, barWidth=0.55 * mm)
            bc.drawOn(c, (W - bc.width) / 2, 32 * mm)
            c.setFont("Helvetica", 11)
            c.drawCentredString(W / 2, 26 * mm, box.get("box_number") or "")
        except Exception:
            pass

        c.showPage(); c.save()
        buf.seek(0)
        return Response(
            content=buf.read(), media_type="application/pdf",
            headers={"Content-Disposition":
                     f'inline; filename="{box.get("box_number") or "box"}-label.pdf"'})

    # ═════════════════════════════════════════════════════════════════════════
    # RETAILER SCAN PERMISSION — owner toggle (Role Permissions)
    # ═════════════════════════════════════════════════════════════════════════
    @router.get("/scan-permission")
    async def get_scan_permission(user: dict = Depends(get_current_user)):
        s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0}) or {}
        return {"retailer_scan_enabled": bool(s.get("retailer_scan_enabled", False))}

    @router.put("/scan-permission")
    async def set_scan_permission(body: Dict[str, Any] = Body(...),
                                 user: dict = Depends(owner_only)):
        enabled = bool(body.get("enabled"))
        await db.dms_settings.update_one(
            {"id": "global"},
            {"$set": {"retailer_scan_enabled": enabled, "updated_at": _now()}},
            upsert=True)
        await _audit(user, "settings.retailer_scan_permission", "settings", "global",
                     {"enabled": enabled})
        return {"ok": True, "retailer_scan_enabled": enabled}

    # ─────────────────────────────────────────────────────────────────────────
    # READ-ONLY scan validator (shared by scan preview + retailer scan)
    # Returns (coupon, fraud_reason, box_number, effective_dist). Never mutates,
    # never logs fraud — callers decide what to do.
    # ─────────────────────────────────────────────────────────────────────────
    async def _scan_resolve(qr: Optional[str], code_in: Optional[str],
                            retailer: Dict[str, Any], distributor_id: str):
        version = _detect_qr_version(qr) if qr else ("v1" if code_in else "unknown")
        code = None
        v2_inner = None
        if qr:
            if version == "v2":
                try:
                    v2_inner = _parse_qr_v2_only(qr)
                    code = str(v2_inner.get("s") or "").upper().strip()
                except QrParseError as e:
                    return None, f"invalid_qr:{e.reason}", None, None
            elif version == "v1":
                parsed = _parse_qr(qr)
                if not parsed:
                    return None, "modified_payload", None, None
                code = parsed[0]
            else:
                return None, "online_generator_suspected", None, None
        else:
            code = (code_in or "").strip().upper()
            if not code:
                return None, "no_code", None, None

        cp = None
        if v2_inner and v2_inner.get("h"):
            cp = _clean(await db.dms_v2_coupons.find_one({"hidden_secure_id": v2_inner["h"]}))
        if not cp:
            cp = _clean(await db.dms_v2_coupons.find_one({"visible_serial": code}))
        if not cp:
            cp = _clean(await db.dms_v2_coupons.find_one({"coupon_code": code}))
        if not cp:
            return None, "invalid_code", None, None

        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]}))
        if not batch:
            return cp, "invalid_code", None, None
        if not batch.get("active") or batch.get("closed_at"):
            return cp, "inactive_batch", None, None
        if cp.get("expires_at") and cp["expires_at"] < _now():
            return cp, "expired", None, None
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            return cp, "already_claimed", None, None
        if cp["status"] in ("cancelled", "voided", "expired"):
            return cp, cp["status"], None, None
        if cp["status"] != "unused" or not cp.get("active"):
            return cp, "coupon_inactive", None, None

        # BOX → distributor validation
        box_number = None
        effective_dist = None
        if cp.get("box_id"):
            box = _clean(await db.dms_v2_boxes.find_one({"id": cp["box_id"]}))
            if box:
                box_number = box.get("box_number")
                effective_dist = box.get("distributor_id")
                if not effective_dist:
                    return cp, "box_not_assigned_to_distributor", box_number, None
        if not effective_dist:
            effective_dist = cp.get("assigned_distributor_id") or cp.get("distributor_id")
        if not effective_dist:
            return cp, "not_assigned", box_number, None
        if effective_dist != distributor_id:
            return cp, "wrong_distributor", box_number, effective_dist
        return cp, None, box_number, effective_dist

    def _scan_preview_body(user, retailer, distributor, cp, fraud_reason,
                           box_number, sales_officer_name):
        val = cp.get("coupon_value") if cp else None
        ctype = cp.get("coupon_type") if cp else None
        return {
            "logged_in_user": user.get("name") or user.get("email"),
            "user_role": user.get("role"),
            "sales_officer": sales_officer_name,
            "distributor_name": distributor.get("name") if distributor else None,
            "retailer_name": retailer.get("name") if retailer else None,
            "box_number": box_number,
            "coupon_serial": (cp.get("visible_serial") or cp.get("coupon_code")) if cp else None,
            "coupon_type": ctype,
            "coupon_value": val,
            "reward_points": val if ctype == "reward" else None,
            "fraud": bool(fraud_reason),
            "fraud_reason": fraud_reason,
        }

    @router.post("/scan/preview")
    async def scan_preview(request: Request, body: Dict[str, Any] = Body(...),
                           user: dict = Depends(salesperson_only)):
        """Read-only validation for the scan screen. Returns all display fields
        + fraud status/reason. Does NOT claim, credit or log — that happens on
        the actual /scan submit."""
        retailer_id = (body.get("retailer_id") or "").strip()
        if not retailer_id:
            raise HTTPException(400, "retailer_id is required")
        meta = _client_meta(request, body)
        retailer = _clean(await db.dms_retailers.find_one({"id": retailer_id}))
        if not retailer:
            raise HTTPException(404, "Retailer not found")
        distributor_id = retailer.get("distributor_id")
        distributor = _clean(await db.dms_distributors.find_one({"id": distributor_id})) or {}

        fraud_reason = None
        cp = None
        box_number = None
        # SO must be assigned to this distributor
        allowed = await db.dms_sp_assignments.find_one({
            "salesperson_id": user["id"], "distributor_id": distributor_id})
        if not allowed:
            fraud_reason = "so_not_assigned_to_distributor"
        else:
            cp, fraud_reason, box_number, _ = await _scan_resolve(
                body.get("qr_payload"), body.get("coupon_code"), retailer, distributor_id)

        preview = _scan_preview_body(user, retailer, distributor, cp, fraud_reason,
                                     box_number, user.get("name"))
        preview.update({"ip_address": meta.get("ip_address"),
                        "gps_lat": meta.get("gps_lat"),
                        "gps_lng": meta.get("gps_lng"),
                        "device_id": meta.get("device_id"),
                        "timestamp": _now()})
        # For a valid CASH coupon show the outstanding impact on the confirm screen.
        if cp and not fraud_reason and cp.get("coupon_type") == "cash":
            bal = await _retailer_ledger_balance(retailer_id)
            val = _round(cp.get("coupon_value") or 0)
            net_before = _round(bal["outstanding"] - bal["credit"])   # +owe / -credit
            net_after = _round(net_before - val)
            preview.update({
                "current_outstanding": bal["outstanding"],
                "current_credit": bal["credit"],
                "projected_outstanding": _round(net_after if net_after > 0 else 0.0),
                "projected_credit": _round(-net_after if net_after < 0 else 0.0),
            })
        return {"ok": not preview["fraud"], "fraud": preview["fraud"],
                "fraud_reason": fraud_reason, "preview": preview}

    @router.post("/scan")
    async def scan_coupon(request: Request,
                          body: Dict[str, Any] = Body(...),
                          user: dict = Depends(salesperson_only)):
        """
        Sales Officer scans a coupon on behalf of a retailer.

        Body: {
          qr_payload         : preferred (v2 encrypted or v1 legacy)
          OR coupon_code (+ secret_token, signature)  : v1 legacy manual entry
          retailer_id        : required
          gps_lat, gps_lng   : optional GPS coords (recorded on scan & fraud)
          device_id          : optional device fingerprint
        }

        Flow:
          1. Parse QR — reject unknown/malformed/tampered (→ fraud log)
          2. Validate retailer + auto-fetch distributor + SO assignment
          3. Decrypt v2 payload → resolve coupon
          4. Cryptographic checks: signature, batch mismatch, campaign mismatch
          5. Lookup coupon → must be status='unused', active=True
          6. Insert immutable wallet_transaction (credit)
          7. Update coupon → claimed
          8. Audit log
        """
        retailer_id = (body.get("retailer_id") or "").strip()
        if not retailer_id:
            raise HTTPException(400, "retailer_id is required")

        meta = _client_meta(request, body)

        # ── parse coupon input ──────────────────────────────────────────────
        qr = body.get("qr_payload")
        code: Optional[str] = None
        token: Optional[str] = None
        sig: Optional[str] = None
        v2_inner: Optional[Dict[str, Any]] = None
        version = _detect_qr_version(qr) if qr else ("v1" if body.get("coupon_code") else "unknown")

        if qr:
            if version == "v2":
                # decrypt + parse; catch every crypto failure with specific reason
                try:
                    v2_inner = _parse_qr_v2_only(qr)
                except QrParseError as e:
                    await _log_fraud(e.reason, (qr or "")[:64], user,
                                     retailer_id, extra={"detail": e.message},
                                     request=request, body=body)
                    raise HTTPException(400, f"Invalid QR: {e.message}")
                code = str(v2_inner.get("s") or "").upper().strip()
            elif version == "v1":
                parsed = _parse_qr(qr)
                if not parsed:
                    await _log_fraud("modified_payload", (qr or "")[:64].upper(),
                                     user, retailer_id, request=request, body=body)
                    raise HTTPException(400, "Malformed QR — not a valid GO OIL coupon")
                code, token, sig = parsed
            else:
                # totally unknown prefix — most likely online generator or foreign QR
                await _log_fraud("online_generator_suspected", (qr or "")[:64].upper(),
                                 user, retailer_id, request=request, body=body,
                                 extra={"detected_version": "unknown"})
                raise HTTPException(400, "Unrecognised QR — not a GO OIL coupon")
        else:
            code = (body.get("coupon_code") or "").strip().upper()
            token = (body.get("secret_token") or "").strip()
            sig = (body.get("signature") or "").strip()
            if not code:
                raise HTTPException(400, "coupon_code or qr_payload required")

        # ── validate retailer + Sales Officer authorization ─────────────────
        retailer = _clean(await db.dms_retailers.find_one({"id": retailer_id}))
        if not retailer:
            raise HTTPException(404, "Retailer not found")
        distributor_id = retailer.get("distributor_id")
        if not distributor_id:
            raise HTTPException(400, "Retailer has no distributor assigned")

        allowed = await db.dms_sp_assignments.find_one({
            "salesperson_id": user["id"], "distributor_id": distributor_id,
        })
        if not allowed:
            await _log_fraud("so_not_assigned_to_distributor", code, user,
                             retailer_id, distributor_id, request=request, body=body)
            raise HTTPException(403, "You are not assigned to this retailer's distributor")

        distributor = _clean(await db.dms_distributors.find_one({"id": distributor_id})) or {}

        # ── resolve coupon record ───────────────────────────────────────────
        cp: Optional[Dict[str, Any]] = None
        if v2_inner:
            # Prefer lookup by hidden_secure_id (most authoritative) — falls back to
            # visible_serial for older records that were migrated.
            hidden = v2_inner.get("h")
            if hidden:
                cp = _clean(await db.dms_v2_coupons.find_one({"hidden_secure_id": hidden}))
            if not cp:
                cp = _clean(await db.dms_v2_coupons.find_one({"visible_serial": code}))
        if not cp:
            cp = _clean(await db.dms_v2_coupons.find_one({"coupon_code": code}))
        if not cp:
            await _log_fraud("invalid_code", code or "", user,
                             retailer_id, distributor_id, request=request, body=body)
            raise HTTPException(400, "Invalid coupon code")

        # ── batch active check ─────────────────────────────────────────────
        batch = _clean(await db.dms_v2_coupon_batches.find_one({"id": cp["batch_id"]}))
        if not batch:
            await _log_fraud("invalid_code", code, user, retailer_id, distributor_id,
                             request=request, body=body, extra={"reason": "batch_missing"})
            raise HTTPException(400, "Coupon batch is missing")
        if not batch.get("active") or batch.get("closed_at"):
            await _log_fraud("inactive_batch", code, user, retailer_id, distributor_id,
                             request=request, body=body,
                             extra={"batch_label": batch.get("batch_label")})
            raise HTTPException(400, "Coupon batch is not active")

        # ── v2 signature + campaign check ───────────────────────────────────
        if v2_inner:
            expected_sig = _sign_v2(batch["hmac_secret"], v2_inner["_ct_b64"])
            if not hmac.compare_digest(expected_sig, v2_inner["_sig"]):
                await _log_fraud("invalid_signature", code, user, retailer_id, distributor_id,
                                 request=request, body=body,
                                 extra={"batch_label": batch.get("batch_label")})
                raise HTTPException(400, "Invalid coupon signature")
            # campaign / batch mismatch — payload claims a different batch than DB
            if v2_inner.get("b") and v2_inner["b"] != cp["batch_id"]:
                await _log_fraud("wrong_campaign", code, user, retailer_id, distributor_id,
                                 request=request, body=body,
                                 extra={"payload_batch": v2_inner.get("b"),
                                        "db_batch": cp["batch_id"]})
                raise HTTPException(400, "Coupon does not belong to its declared campaign")
            # type/value tamper check
            if v2_inner.get("t") and v2_inner["t"] != cp["coupon_type"]:
                await _log_fraud("modified_payload", code, user, retailer_id, distributor_id,
                                 request=request, body=body,
                                 extra={"payload_type": v2_inner.get("t"),
                                        "db_type": cp["coupon_type"]})
                raise HTTPException(400, "Coupon type mismatch")

        # ── expiry ─────────────────────────────────────────────────────────
        if cp.get("expires_at") and cp["expires_at"] < _now():
            await db.dms_v2_coupons.update_one({"id": cp["id"]},
                                               {"$set": {"status": "expired", "updated_at": _now()}})
            await _log_fraud("expired", code, user, retailer_id, distributor_id,
                             request=request, body=body)
            raise HTTPException(400, "Coupon has expired")

        # ── coupon status ──────────────────────────────────────────────────
        if cp["status"] in ("claimed", "redemption_pending", "redeemed"):
            await _log_fraud("already_claimed", code, user, retailer_id, distributor_id,
                             extra={"previous_status": cp["status"],
                                    "previously_claimed_at": cp.get("claim_timestamp"),
                                    "previously_claimed_by_retailer": cp.get("retailer_id")},
                             request=request, body=body)
            raise HTTPException(400,
                                f"Coupon already claimed on "
                                f"{(cp.get('claim_timestamp') or '')[:10]} by another retailer")
        if cp["status"] in ("cancelled", "voided", "expired"):
            await _log_fraud(cp["status"], code, user, retailer_id, distributor_id,
                             request=request, body=body)
            raise HTTPException(400, f"Coupon is {cp['status']}")
        if cp["status"] != "unused":
            await _log_fraud(f"bad_status_{cp['status']}", code, user, retailer_id, distributor_id,
                             request=request, body=body)
            raise HTTPException(400, f"Coupon cannot be claimed (status={cp['status']})")
        if not cp.get("active"):
            await _log_fraud("coupon_inactive", code, user, retailer_id, distributor_id,
                             request=request, body=body)
            raise HTTPException(400, "Coupon is inactive")

        # ── BOX-BASED ASSIGNMENT & DISTRIBUTOR FRAUD VALIDATION ─────────────
        # Real manufacturing flow: coupon → box → distributor. A coupon is
        # legitimately redeemable only if it is assigned to a box AND that box is
        # assigned to THIS retailer's distributor. Legacy coupons assigned directly
        # via order dispatch (assigned_distributor_id, no box) keep working.
        box_doc = None
        box_number = None
        effective_dist = None
        if cp.get("box_id"):
            box_doc = _clean(await db.dms_v2_boxes.find_one({"id": cp["box_id"]}))
        if box_doc:
            box_number = box_doc.get("box_number")
            effective_dist = box_doc.get("distributor_id")
            if not effective_dist:
                await _log_fraud("box_not_assigned_to_distributor", code, user,
                                 retailer_id, distributor_id, request=request, body=body,
                                 extra={"box_number": box_number})
                raise HTTPException(400, f"Coupon's box {box_number} is not assigned to a distributor")
        else:
            # no box → fall back to legacy dispatch assignment (if any)
            effective_dist = cp.get("assigned_distributor_id") or cp.get("distributor_id")
            if not effective_dist:
                await _log_fraud("not_assigned", code, user, retailer_id, distributor_id,
                                 request=request, body=body)
                raise HTTPException(400, "Coupon is not assigned to any box/distributor yet")
        if effective_dist != distributor_id:
            await _log_fraud("wrong_distributor", code, user, retailer_id, distributor_id,
                             request=request, body=body,
                             extra={"coupon_distributor": effective_dist,
                                    "scanned_distributor": distributor_id,
                                    "box_number": box_number})
            raise HTTPException(400,
                "Coupon does not belong to this retailer's distributor (possible fraud)")

        # ── v1 legacy cryptographic checks (only if v1 path) ───────────────
        if version == "v1":
            expected_sig_v1 = _sign(batch["hmac_secret"], cp["coupon_code"],
                                    cp.get("secret_token") or "")
            if token and not hmac.compare_digest(token, cp.get("secret_token") or ""):
                await _log_fraud("invalid_hidden_id", code, user, retailer_id, distributor_id,
                                 request=request, body=body)
                raise HTTPException(400, "Invalid coupon token")
            if sig and not (hmac.compare_digest(sig, expected_sig_v1)
                            and hmac.compare_digest(sig, cp.get("signature") or "")):
                await _log_fraud("invalid_signature", code, user, retailer_id, distributor_id,
                                 request=request, body=body)
                raise HTTPException(400, "Invalid coupon signature")

        # ── ATOMIC-ISH CLAIM ────────────────────────────────────────────────
        upd = await db.dms_v2_coupons.update_one(
            {"id": cp["id"], "status": "unused"},
            {"$set": {
                "status": "claimed",
                "claimed_by_user_id": user["id"],
                "claimed_by_user_name": user.get("name") or user.get("email"),
                "claimed_by_role": user.get("role"),
                "scan_channel": "salesperson_scan",
                "claim_timestamp": _now(),
                "claim_ip": meta.get("ip_address"),
                "claim_gps_lat": meta.get("gps_lat"),
                "claim_gps_lng": meta.get("gps_lng"),
                "claim_device_id": meta.get("device_id"),
                "retailer_id": retailer_id,
                "retailer_name": retailer.get("name"),
                "distributor_id": distributor_id,
                "distributor_name": distributor.get("name"),
                "scan_box_id": (box_doc or {}).get("id"),
                "scan_box_number": box_number,
                "updated_at": _now(),
            }},
        )
        if upd.modified_count != 1:
            # concurrent scan lost the race
            await _log_fraud("race_lost", code, user, retailer_id, distributor_id,
                             request=request, body=body)
            raise HTTPException(400, "Coupon has just been claimed by another scan")

        # ── FINANCIAL POSTING (cash → outstanding ledger, points → wallet) ──
        # CASH coupons reduce the Retailer ↔ Distributor outstanding (secondary
        # goods ledger) as a `coupon_credit` — auto credit carry-forward is
        # handled by the ledger summary math. POINTS/REWARD coupons credit the
        # retailer's reward (points) wallet. The two never mix.
        wallet_type = "cash" if cp["coupon_type"] == "cash" else "reward"
        tx_id: Optional[str] = None
        ledger_id: Optional[str] = None
        new_bal = 0.0
        new_outstanding = None
        new_credit = None

        if wallet_type == "cash":
            ledger_id = _nid("rle")
            await db.dms_retailer_ledger.insert_one({
                "id": ledger_id,
                "distributor_id": distributor_id,
                "retailer_id": retailer_id,
                "retailer_name": retailer.get("name"),
                "kind": "coupon_credit",
                "reference_id": cp["id"],
                "reference_no": cp["coupon_code"],
                "amount": _round(cp["coupon_value"]),   # positive; reduces outstanding
                "coupon_id": cp["id"],
                "coupon_code": cp["coupon_code"],
                "batch_id": cp["batch_id"],
                "description": f"Cash coupon {cp.get('visible_serial') or cp['coupon_code']} "
                               f"(₹{cp['coupon_value']:g})",
                "at": _now(),
                "recorded_by": user["id"],
                "recorded_by_role": user.get("role"),
                "recorded_by_name": user.get("name") or user.get("email"),
            })
            await db.dms_v2_coupons.update_one(
                {"id": cp["id"]},
                {"$set": {"retailer_ledger_id": ledger_id, "updated_at": _now()}},
            )
            bal = await _retailer_ledger_balance(retailer_id)
            new_outstanding = bal["outstanding"]
            new_credit = bal["credit"]
        else:
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
            await db.dms_v2_coupons.update_one(
                {"id": cp["id"]}, {"$set": {"wallet_transaction_id": tx_id, "updated_at": _now()}}
            )
            new_bal = await _wallet_balance(retailer_id, wallet_type)

        # audit
        await _audit(user, "coupon.claimed", "coupon", cp["id"], {
            "coupon_code": cp["coupon_code"], "coupon_type": cp["coupon_type"],
            "coupon_value": cp["coupon_value"], "retailer_id": retailer_id,
            "retailer_name": retailer.get("name"),
            "distributor_id": distributor_id,
            "distributor_name": distributor.get("name"),
            "wallet_transaction_id": tx_id,
            "retailer_ledger_id": ledger_id,
        })

        # optional retailer notification
        if notify:
            user_of_ret = await db.users.find_one({"retailer_id": retailer_id, "role": "retailer"},
                                                  {"_id": 0, "id": 1})
            if user_of_ret:
                try:
                    if wallet_type == "cash":
                        outs_txt = (f"₹{new_outstanding:g} outstanding"
                                    if (new_outstanding or 0) > 0
                                    else f"₹{new_credit:g} credit balance")
                        await notify(user_of_ret["id"], "coupon_scanned",
                                     "Cash coupon applied to your account",
                                     f"₹{cp['coupon_value']:g} adjusted by {user.get('name')} "
                                     f"\u2022 now {outs_txt}",
                                     "/dms/retailer/ledger")
                    else:
                        await notify(user_of_ret["id"], "coupon_scanned",
                                     "Points credited to your wallet",
                                     f"{cp['coupon_value']:g} points added by {user.get('name')}",
                                     "/dms/retailer/wallet")
                except Exception:
                    pass

        if wallet_type == "cash":
            if (new_outstanding or 0) > 0:
                msg = (f"₹{cp['coupon_value']:g} applied to {retailer.get('name')} \u2022 "
                       f"outstanding now ₹{new_outstanding:g}")
            else:
                msg = (f"₹{cp['coupon_value']:g} applied to {retailer.get('name')} \u2022 "
                       f"credit balance ₹{new_credit:g}")
        else:
            msg = f"{cp['coupon_value']:g} points credited to {retailer.get('name')}'s Reward Wallet"

        return {
            "ok": True,
            "coupon_code": cp["coupon_code"],
            "visible_serial": cp.get("visible_serial"),
            "coupon_type": cp["coupon_type"],
            "coupon_value": cp["coupon_value"],
            "box_number": box_number,
            "wallet_type": wallet_type,
            "new_balance": new_bal,                 # reward points balance (0 for cash)
            "new_outstanding": new_outstanding,     # retailer↔distributor outstanding (cash)
            "new_credit": new_credit,               # credit balance if overpaid (cash)
            "retailer_ledger_id": ledger_id,
            "wallet_transaction_id": tx_id,
            "retailer_name": retailer.get("name"),
            "distributor_name": distributor.get("name"),
            "fraud": False,
            "message": msg,
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

    async def _my_retailer_opt(user: dict) -> Optional[Dict[str, Any]]:
        """Like _my_retailer but returns None instead of raising when the
        retailer has no linked profile yet (used by read-only views so the UI
        shows a clean empty state instead of crashing)."""
        if user.get("role") != "retailer":
            return None
        rid = user.get("retailer_id")
        ret = None
        if rid:
            ret = _clean(await db.dms_retailers.find_one({"id": rid}))
        if not ret:
            ret = _clean(await db.dms_retailers.find_one({"user_id": user["id"]}))
        return ret

    @router.get("/retailer/wallet")
    async def retailer_wallet(user: dict = Depends(get_current_user)):
        ret = await _my_retailer_opt(user)
        if not ret:
            return {
                "retailer_id": None, "retailer_name": None, "distributor_id": None,
                "cash_wallet": {"balance": 0, "pending_redemptions": 0},
                "reward_wallet": {"balance": 0, "pending_redemptions": 0},
            }
        cash = await _wallet_balance(ret["id"], "cash")
        pts = await _wallet_balance(ret["id"], "reward")
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
        ret = await _my_retailer_opt(user)
        if not ret:
            return {"data": [], "count": 0}
        q: Dict[str, Any] = {"retailer_id": ret["id"]}
        if wallet_type: q["wallet_type"] = wallet_type
        docs = await db.dms_v2_wallet_transactions.find(q, {"_id": 0})\
            .sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/retailer/coupons")
    async def retailer_coupons(user: dict = Depends(get_current_user)):
        ret = await _my_retailer_opt(user)
        if not ret:
            return {"data": [], "count": 0}
        docs = await db.dms_v2_coupons.find(
            {"retailer_id": ret["id"]},
            {"_id": 0, "secret_token": 0, "signature": 0},
        ).sort("claim_timestamp", -1).limit(500).to_list(500)
        return {"data": docs, "count": len(docs)}

    @router.get("/retailer/redemptions")
    async def retailer_redemptions(user: dict = Depends(get_current_user)):
        ret = await _my_retailer_opt(user)
        if not ret:
            return {"data": [], "count": 0}
        docs = await db.dms_v2_redemption_requests.find({"retailer_id": ret["id"]}, {"_id": 0})\
            .sort("created_at", -1).to_list(500)
        return {"data": docs, "count": len(docs)}

    # ── RETAILER SELF-SCAN (only when owner has enabled the permission) ───────
    async def _require_retailer_scan_enabled():
        s = await db.dms_settings.find_one({"id": "global"}, {"_id": 0}) or {}
        if not bool(s.get("retailer_scan_enabled", False)):
            raise HTTPException(403, "Retailer scanning is disabled by the owner")

    @router.post("/retailer/scan/preview")
    async def retailer_scan_preview(request: Request, body: Dict[str, Any] = Body(...),
                                    user: dict = Depends(get_current_user)):
        await _require_retailer_scan_enabled()
        ret = await _my_retailer(user)
        distributor_id = ret.get("distributor_id")
        distributor = _clean(await db.dms_distributors.find_one({"id": distributor_id})) or {}
        meta = _client_meta(request, body)
        cp, fraud_reason, box_number, _ = await _scan_resolve(
            body.get("qr_payload"), body.get("coupon_code"), ret, distributor_id)
        preview = _scan_preview_body(user, ret, distributor, cp, fraud_reason,
                                     box_number, None)
        preview.update({"ip_address": meta.get("ip_address"),
                        "gps_lat": meta.get("gps_lat"), "gps_lng": meta.get("gps_lng"),
                        "device_id": meta.get("device_id"), "timestamp": _now()})
        return {"ok": not preview["fraud"], "fraud": preview["fraud"],
                "fraud_reason": fraud_reason, "preview": preview}

    @router.post("/retailer/scan")
    async def retailer_scan_submit(request: Request, body: Dict[str, Any] = Body(...),
                                   user: dict = Depends(get_current_user)):
        await _require_retailer_scan_enabled()
        ret = await _my_retailer(user)
        distributor_id = ret.get("distributor_id")
        if not distributor_id:
            raise HTTPException(400, "Your retailer profile has no distributor assigned")
        distributor = _clean(await db.dms_distributors.find_one({"id": distributor_id})) or {}
        meta = _client_meta(request, body)

        cp, fraud_reason, box_number, _ = await _scan_resolve(
            body.get("qr_payload"), body.get("coupon_code"), ret, distributor_id)
        if fraud_reason:
            await _log_fraud(fraud_reason, (cp or {}).get("visible_serial") or "unknown",
                             user, ret["id"], distributor_id, request=request, body=body,
                             extra={"box_number": box_number, "channel": "retailer_self_scan"})
            raise HTTPException(400, f"Coupon rejected — {fraud_reason.replace('_', ' ')}")

        upd = await db.dms_v2_coupons.update_one(
            {"id": cp["id"], "status": "unused"},
            {"$set": {
                "status": "claimed",
                "claimed_by_user_id": user["id"],
                "claimed_by_user_name": user.get("name") or user.get("email"),
                "claimed_by_role": user.get("role"),
                "claim_timestamp": _now(),
                "claim_ip": meta.get("ip_address"),
                "claim_gps_lat": meta.get("gps_lat"),
                "claim_gps_lng": meta.get("gps_lng"),
                "claim_device_id": meta.get("device_id"),
                "retailer_id": ret["id"], "retailer_name": ret.get("name"),
                "distributor_id": distributor_id, "distributor_name": distributor.get("name"),
                "scan_box_number": box_number, "scan_channel": "retailer_self_scan",
                "updated_at": _now(),
            }})
        if upd.modified_count != 1:
            raise HTTPException(400, "Coupon has just been claimed by another scan")

        wallet_type = "cash" if cp["coupon_type"] == "cash" else "reward"
        await _ensure_wallet(ret["id"], wallet_type)
        tx_id = _nid("wtx")
        await db.dms_v2_wallet_transactions.insert_one({
            "id": tx_id, "retailer_id": ret["id"], "distributor_id": distributor_id,
            "wallet_type": wallet_type, "kind": "credit_coupon",
            "amount": _round(cp["coupon_value"]), "coupon_id": cp["id"],
            "coupon_code": cp["coupon_code"], "batch_id": cp["batch_id"],
            "created_by": user["id"], "created_by_name": user.get("name"),
            "created_by_role": user.get("role"), "at": _now(),
        })
        await db.dms_v2_coupons.update_one({"id": cp["id"]},
            {"$set": {"wallet_transaction_id": tx_id, "updated_at": _now()}})
        await _audit(user, "coupon.claimed", "coupon", cp["id"],
                     {"coupon_code": cp["coupon_code"], "retailer_id": ret["id"],
                      "channel": "retailer_self_scan", "box_number": box_number,
                      "wallet_transaction_id": tx_id})
        new_bal = await _wallet_balance(ret["id"], wallet_type)
        return {"ok": True, "fraud": False, "box_number": box_number,
                "coupon_serial": cp.get("visible_serial"),
                "coupon_type": cp["coupon_type"], "coupon_value": cp["coupon_value"],
                "wallet_type": wallet_type, "new_balance": new_bal,
                "message": (f"₹{cp['coupon_value']:g} credited to your Cash Wallet"
                            if wallet_type == "cash"
                            else f"{cp['coupon_value']:g} points credited to your Reward Wallet")}

    # ─────────────────────────────────────────────────────────────────────────
    # DISTRIBUTOR SELF-SCAN  (coupon credited to distributor's OWN wallet)
    # ─────────────────────────────────────────────────────────────────────────
    distributor_only = _guard("distributor")

    async def _my_distributor(user: dict) -> Dict[str, Any]:
        if user.get("role") != "distributor":
            raise HTTPException(403, "Distributor only")
        did = user.get("distributor_id")
        dist = None
        if did:
            dist = _clean(await db.dms_distributors.find_one({"id": did}))
        if not dist:
            dist = _clean(await db.dms_distributors.find_one({"user_id": user["id"]}))
        if not dist:
            raise HTTPException(400, "Distributor profile not linked to your user")
        return dist

    async def _my_distributor_opt(user: dict) -> Optional[Dict[str, Any]]:
        if user.get("role") != "distributor":
            return None
        did = user.get("distributor_id")
        dist = None
        if did:
            dist = _clean(await db.dms_distributors.find_one({"id": did}))
        if not dist:
            dist = _clean(await db.dms_distributors.find_one({"user_id": user["id"]}))
        return dist

    async def _dist_wallet_balance(distributor_id: str, wallet_type: str) -> float:
        pipeline = [
            {"$match": {"distributor_id": distributor_id, "wallet_type": wallet_type}},
            {"$group": {"_id": None, "bal": {"$sum": "$amount"}}},
        ]
        rows = await db.dms_v2_dist_wallet_txns.aggregate(pipeline).to_list(1)
        return _round(rows[0]["bal"]) if rows else 0.0

    @router.get("/distributor/wallet")
    async def distributor_wallet(user: dict = Depends(get_current_user)):
        dist = await _my_distributor_opt(user)
        if not dist:
            return {"distributor_id": None, "distributor_name": None,
                    "cash_wallet": {"balance": 0}, "reward_wallet": {"balance": 0}}
        return {
            "distributor_id": dist["id"], "distributor_name": dist.get("name"),
            "cash_wallet": {"balance": await _dist_wallet_balance(dist["id"], "cash")},
            "reward_wallet": {"balance": await _dist_wallet_balance(dist["id"], "reward")},
        }

    @router.get("/distributor/transactions")
    async def distributor_transactions(limit: int = Query(200, ge=1, le=1000),
                                       user: dict = Depends(get_current_user)):
        dist = await _my_distributor_opt(user)
        if not dist:
            return {"data": [], "count": 0}
        docs = await db.dms_v2_dist_wallet_txns.find(
            {"distributor_id": dist["id"]}, {"_id": 0}
        ).sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.post("/distributor/scan/preview")
    async def distributor_scan_preview(request: Request, body: Dict[str, Any] = Body(...),
                                       user: dict = Depends(distributor_only)):
        dist = await _my_distributor(user)
        meta = _client_meta(request, body)
        cp, fraud_reason, box_number, _ = await _scan_resolve(
            body.get("qr_payload"), body.get("coupon_code"), {}, dist["id"])
        preview = _scan_preview_body(user, None, dist, cp, fraud_reason, box_number, None)
        preview.update({"ip_address": meta.get("ip_address"),
                        "gps_lat": meta.get("gps_lat"), "gps_lng": meta.get("gps_lng"),
                        "device_id": meta.get("device_id"), "timestamp": _now()})
        return {"ok": not preview["fraud"], "fraud": preview["fraud"],
                "fraud_reason": fraud_reason, "preview": preview}

    @router.post("/distributor/scan")
    async def distributor_scan_submit(request: Request, body: Dict[str, Any] = Body(...),
                                      user: dict = Depends(distributor_only)):
        dist = await _my_distributor(user)
        meta = _client_meta(request, body)
        cp, fraud_reason, box_number, _ = await _scan_resolve(
            body.get("qr_payload"), body.get("coupon_code"), {}, dist["id"])
        if fraud_reason:
            await _log_fraud(fraud_reason, (cp or {}).get("visible_serial") or "unknown",
                             user, None, dist["id"], request=request, body=body,
                             extra={"box_number": box_number, "channel": "distributor_self_scan"})
            raise HTTPException(400, f"Coupon rejected — {fraud_reason.replace('_', ' ')}")

        upd = await db.dms_v2_coupons.update_one(
            {"id": cp["id"], "status": "unused"},
            {"$set": {
                "status": "claimed",
                "claimed_by_user_id": user["id"],
                "claimed_by_user_name": user.get("name") or user.get("email"),
                "claimed_by_role": user.get("role"),
                "claim_timestamp": _now(),
                "claim_ip": meta.get("ip_address"),
                "claim_gps_lat": meta.get("gps_lat"),
                "claim_gps_lng": meta.get("gps_lng"),
                "claim_device_id": meta.get("device_id"),
                "distributor_id": dist["id"], "distributor_name": dist.get("name"),
                "scan_box_number": box_number, "scan_channel": "distributor_self_scan",
                "updated_at": _now(),
            }})
        if upd.modified_count != 1:
            raise HTTPException(400, "Coupon has just been claimed by another scan")

        wallet_type = "cash" if cp["coupon_type"] == "cash" else "reward"
        tx_id = _nid("dwtx")
        await db.dms_v2_dist_wallet_txns.insert_one({
            "id": tx_id, "distributor_id": dist["id"], "distributor_name": dist.get("name"),
            "wallet_type": wallet_type, "kind": "credit_coupon",
            "amount": _round(cp["coupon_value"]), "coupon_id": cp["id"],
            "coupon_code": cp["coupon_code"], "batch_id": cp["batch_id"],
            "created_by": user["id"], "created_by_name": user.get("name"),
            "created_by_role": user.get("role"), "at": _now(),
        })
        await db.dms_v2_coupons.update_one({"id": cp["id"]},
            {"$set": {"wallet_transaction_id": tx_id, "updated_at": _now()}})
        # Settlement: for CASH coupons, post a credit entry to the distributor's
        # Primary Ledger so it reduces their payable/outstanding to the company.
        if wallet_type == "cash":
            await db.dms_primary_ledger.insert_one({
                "id": _nid("le"),
                "distributor_id": dist["id"],
                "kind": "coupon_credit",
                "reference_no": f"CPN-{cp['coupon_code']}",
                "amount": _round(cp["coupon_value"]),
                "method": "coupon_scan",
                "description": f"Coupon {cp.get('visible_serial') or cp['coupon_code']} scanned — \u20b9{cp['coupon_value']:g} credit",
                "at": _now(),
                "recorded_by": user["id"],
                "wallet_transaction_id": tx_id,
            })
        await _audit(user, "coupon.claimed", "coupon", cp["id"],
                     {"coupon_code": cp["coupon_code"], "distributor_id": dist["id"],
                      "channel": "distributor_self_scan", "box_number": box_number,
                      "wallet_transaction_id": tx_id})
        new_bal = await _dist_wallet_balance(dist["id"], wallet_type)
        return {"ok": True, "fraud": False, "box_number": box_number,
                "coupon_serial": cp.get("visible_serial"),
                "coupon_type": cp["coupon_type"], "coupon_value": cp["coupon_value"],
                "wallet_type": wallet_type, "new_balance": new_bal,
                "message": (f"₹{cp['coupon_value']:g} credited to your Cash Wallet"
                            if wallet_type == "cash"
                            else f"{cp['coupon_value']:g} points credited to your Reward Wallet")}

    # ─────────────────────────────────────────────────────────────────────────
    # COUPON SCAN AUDIT — owner view of every scan with scanner id + designation
    # ─────────────────────────────────────────────────────────────────────────
    @router.get("/audit")
    async def coupon_scan_audit(
        limit: int = Query(300, ge=1, le=2000),
        channel: Optional[str] = Query(None),
        user: dict = Depends(owner_or_accountant),
    ):
        _ROLE_LABEL = {
            "distributor": "Distributor", "retailer": "Retailer",
            "salesperson": "Salesperson", "team_leader": "Team Leader",
            "regional_manager": "Regional Manager", "owner": "Owner",
            "owner_accountant": "Owner Accountant", "super_admin": "Super Admin",
        }
        q: Dict[str, Any] = {"claim_timestamp": {"$ne": None},
                             "claimed_by_user_id": {"$ne": None}}
        if channel:
            q["scan_channel"] = channel
        docs = await db.dms_v2_coupons.find(
            q, {"_id": 0, "id": 1, "visible_serial": 1, "coupon_code": 1,
                "coupon_type": 1, "coupon_value": 1, "status": 1,
                "claimed_by_user_id": 1, "claimed_by_user_name": 1, "claimed_by_role": 1,
                "scan_channel": 1, "claim_timestamp": 1, "retailer_id": 1,
                "retailer_name": 1, "distributor_id": 1, "distributor_name": 1,
                "batch_label": 1, "claim_gps_lat": 1, "claim_gps_lng": 1}
        ).sort("claim_timestamp", -1).limit(limit).to_list(limit)

        # resolve missing designations by user lookup (older records)
        need_ids = list({d.get("claimed_by_user_id") for d in docs
                         if not d.get("claimed_by_role") and d.get("claimed_by_user_id")})
        role_map: Dict[str, str] = {}
        if need_ids:
            urows = await db.users.find({"id": {"$in": need_ids}},
                                        {"_id": 0, "id": 1, "role": 1}).to_list(1000)
            role_map = {u["id"]: u.get("role") for u in urows}

        out = []
        for d in docs:
            role = d.get("claimed_by_role") or role_map.get(d.get("claimed_by_user_id"), "")
            out.append({
                "coupon_id": d.get("id"),
                "serial": d.get("visible_serial") or d.get("coupon_code"),
                "coupon_type": d.get("coupon_type"),
                "coupon_value": d.get("coupon_value"),
                "status": d.get("status"),
                "scanned_by_user_id": d.get("claimed_by_user_id"),
                "scanned_by_name": d.get("claimed_by_user_name"),
                "designation": _ROLE_LABEL.get(role, role or "—"),
                "role": role,
                "channel": d.get("scan_channel"),
                "retailer_name": d.get("retailer_name"),
                "distributor_name": d.get("distributor_name"),
                "batch_label": d.get("batch_label"),
                "scanned_at": d.get("claim_timestamp"),
                "gps_lat": d.get("claim_gps_lat"),
                "gps_lng": d.get("claim_gps_lng"),
            })
        return {"data": out, "count": len(out)}

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
    async def reports_fraud(user: dict = Depends(get_current_user),
                            reason: Optional[str] = Query(None),
                            distributor_id: Optional[str] = Query(None),
                            actor_id: Optional[str] = Query(None),
                            limit: int = Query(500, ge=1, le=2000)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {}
        if reason: q["reason"] = reason
        if distributor_id: q["distributor_id"] = distributor_id
        if actor_id: q["actor_id"] = actor_id
        docs = await db.dms_v2_coupon_fraud_attempts.find(q, {"_id": 0})\
            .sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/reports/fraud-dashboard")
    async def reports_fraud_dashboard(user: dict = Depends(get_current_user)):
        """Aggregated fraud dashboard for Owner / TL / RM."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin",
                                    "team_leader", "regional_manager"):
            raise HTTPException(403, "Access denied")
        from datetime import timedelta
        now_dt = datetime.now(timezone.utc)
        t7 = (now_dt - timedelta(days=7)).isoformat()
        t30 = (now_dt - timedelta(days=30)).isoformat()
        t_today = now_dt.strftime("%Y-%m-%d")

        total = await db.dms_v2_coupon_fraud_attempts.count_documents({})
        last7 = await db.dms_v2_coupon_fraud_attempts.count_documents({"at": {"$gte": t7}})
        last30 = await db.dms_v2_coupon_fraud_attempts.count_documents({"at": {"$gte": t30}})
        today = await db.dms_v2_coupon_fraud_attempts.count_documents({"at": {"$gte": t_today}})

        by_reason: Dict[str, int] = {}
        async for r in db.dms_v2_coupon_fraud_attempts.aggregate(
            [{"$group": {"_id": "$reason", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}]):
            by_reason[r["_id"] or "unknown"] = r["n"]

        by_distributor: List[Dict[str, Any]] = []
        async for r in db.dms_v2_coupon_fraud_attempts.aggregate([
            {"$match": {"distributor_id": {"$ne": None}}},
            {"$group": {"_id": "$distributor_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}, {"$limit": 20},
        ]):
            dist = await db.dms_distributors.find_one({"id": r["_id"]},
                                                       {"_id": 0, "name": 1})
            by_distributor.append({"distributor_id": r["_id"],
                                   "distributor_name": (dist or {}).get("name"),
                                   "count": r["n"]})

        by_actor: List[Dict[str, Any]] = []
        async for r in db.dms_v2_coupon_fraud_attempts.aggregate([
            {"$match": {"actor_id": {"$ne": None}}},
            {"$group": {"_id": "$actor_id",
                        "name": {"$first": "$actor_name"},
                        "role": {"$first": "$actor_role"},
                        "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}, {"$limit": 20},
        ]):
            by_actor.append({"actor_id": r["_id"], "actor_name": r.get("name"),
                             "actor_role": r.get("role"), "count": r["n"]})

        recent = await db.dms_v2_coupon_fraud_attempts.find({}, {"_id": 0})\
            .sort("at", -1).limit(20).to_list(20)
        return {
            "kpis": {"total": total, "today": today, "last7": last7, "last30": last30},
            "by_reason": by_reason,
            "by_distributor": by_distributor,
            "by_actor": by_actor,
            "recent": recent,
        }

    @router.get("/reports/generation")
    async def reports_generation(user: dict = Depends(get_current_user)):
        """Coupon generation history — one row per batch."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        rows = await db.dms_v2_coupon_batches.find(
            {}, {"_id": 0, "hmac_secret": 0}
        ).sort("created_at", -1).to_list(2000)
        return {"data": rows, "count": len(rows)}

    @router.get("/reports/activation")
    async def reports_activation(user: dict = Depends(get_current_user),
                                 limit: int = Query(500, ge=1, le=2000)):
        """Activation + deactivation events from audit log."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        docs = await db.dms_v2_coupon_audit_log.find(
            {"event": {"$in": ["batch.activated", "batch.deactivated",
                                "coupon.activated", "coupon.deactivated",
                                "coupon.range_activated", "coupon.range_deactivated"]}},
            {"_id": 0},
        ).sort("at", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/reports/unused")
    async def reports_unused(user: dict = Depends(get_current_user),
                             batch_id: Optional[str] = Query(None),
                             limit: int = Query(500, ge=1, le=2000)):
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {"status": "unused"}
        if batch_id: q["batch_id"] = batch_id
        docs = await db.dms_v2_coupons.find(
            q, {"_id": 0, "secret_token": 0, "signature": 0,
                "qr_ciphertext_b64": 0, "qr_signature_v2": 0, "qr_hash": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        count = await db.dms_v2_coupons.count_documents(q)
        return {"data": docs, "count": len(docs), "total": count}

    @router.get("/reports/inactive")
    async def reports_inactive(user: dict = Depends(get_current_user),
                               batch_id: Optional[str] = Query(None),
                               limit: int = Query(500, ge=1, le=2000)):
        """Coupons where active=False (generated but never activated, or cancelled)."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {"active": {"$ne": True}}
        if batch_id: q["batch_id"] = batch_id
        docs = await db.dms_v2_coupons.find(
            q, {"_id": 0, "secret_token": 0, "signature": 0,
                "qr_ciphertext_b64": 0, "qr_signature_v2": 0, "qr_hash": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        count = await db.dms_v2_coupons.count_documents(q)
        return {"data": docs, "count": len(docs), "total": count}

    @router.get("/reports/usage")
    async def reports_usage(user: dict = Depends(get_current_user),
                            distributor_id: Optional[str] = Query(None),
                            retailer_id: Optional[str] = Query(None),
                            limit: int = Query(500, ge=1, le=2000)):
        """Coupon usage (claimed / redeemed) history."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        q: Dict[str, Any] = {"status": {"$in": ["claimed", "redemption_pending", "redeemed"]}}
        if distributor_id: q["distributor_id"] = distributor_id
        if retailer_id: q["retailer_id"] = retailer_id
        docs = await db.dms_v2_coupons.find(
            q, {"_id": 0, "secret_token": 0, "signature": 0,
                "qr_ciphertext_b64": 0, "qr_signature_v2": 0, "qr_hash": 0}
        ).sort("claim_timestamp", -1).limit(limit).to_list(limit)
        return {"data": docs, "count": len(docs)}

    @router.get("/reports/cash-wallets")
    async def reports_cash_wallets(user: dict = Depends(get_current_user)):
        """Cash wallet balances per retailer."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        rows: List[Dict[str, Any]] = []
        total = 0.0
        async for w in db.dms_v2_retailer_wallets.find({"wallet_type": "cash"}, {"_id": 0}):
            bal = await _wallet_balance(w["retailer_id"], "cash")
            ret = await db.dms_retailers.find_one({"id": w["retailer_id"]},
                                                    {"_id": 0, "name": 1, "distributor_name": 1,
                                                     "distributor_id": 1})
            rows.append({
                "retailer_id": w["retailer_id"],
                "retailer_name": (ret or {}).get("name"),
                "distributor_id": (ret or {}).get("distributor_id"),
                "distributor_name": (ret or {}).get("distributor_name"),
                "balance": bal,
            })
            total += bal
        return {"data": rows, "count": len(rows), "total_balance": _round(total)}

    @router.get("/reports/reward-wallets")
    async def reports_reward_wallets(user: dict = Depends(get_current_user)):
        """Reward point balances per retailer."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        rows: List[Dict[str, Any]] = []
        total = 0.0
        async for w in db.dms_v2_retailer_wallets.find({"wallet_type": "reward"}, {"_id": 0}):
            bal = await _wallet_balance(w["retailer_id"], "reward")
            ret = await db.dms_retailers.find_one({"id": w["retailer_id"]},
                                                    {"_id": 0, "name": 1, "distributor_name": 1,
                                                     "distributor_id": 1})
            rows.append({
                "retailer_id": w["retailer_id"],
                "retailer_name": (ret or {}).get("name"),
                "distributor_id": (ret or {}).get("distributor_id"),
                "distributor_name": (ret or {}).get("distributor_name"),
                "balance": bal,
            })
            total += bal
        return {"data": rows, "count": len(rows), "total_balance": _round(total)}

    @router.get("/reports/distributor-outstanding")
    async def reports_distributor_outstanding(user: dict = Depends(get_current_user)):
        """Distributor-wise coupon impact: credit notes issued (which reduce
        primary ledger outstanding). Also pulls current primary_ledger outstanding
        totals so Owner can see net effect."""
        if user.get("role") not in ("owner", "owner_accountant", "super_admin", "team_leader"):
            raise HTTPException(403, "Access denied")
        rows: List[Dict[str, Any]] = []
        distributors = await db.dms_distributors.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
        for d in distributors:
            did = d["id"]
            # coupon credit notes → sum
            cn_sum = 0.0; cn_count = 0
            async for cn in db.dms_v2_credit_notes.find(
                {"distributor_id": did, "status": {"$ne": "cancelled"}},
                {"_id": 0, "amount": 1},
            ):
                cn_sum += _round(cn.get("amount", 0))
                cn_count += 1
            # primary ledger outstanding
            billed = 0.0; paid = 0.0
            async for e in db.dms_primary_ledger.find(
                {"distributor_id": did}, {"_id": 0, "kind": 1, "amount": 1},
            ):
                if e.get("kind") == "invoice":
                    billed += _round(e.get("amount", 0))
                elif e.get("kind") in ("payment", "coupon_credit"):
                    paid += _round(e.get("amount", 0))
            outstanding = _round(billed - paid)
            rows.append({
                "distributor_id": did, "distributor_name": d.get("name"),
                "credit_notes_count": cn_count,
                "credit_notes_amount": _round(cn_sum),
                "billed": _round(billed),
                "paid_incl_coupons": _round(paid),
                "outstanding": outstanding,
            })
        return {"data": rows, "count": len(rows)}

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

    # ─────────────────────────────────────────────────────────────────────────
    # Startup: indexes + one-time backfill for legacy coupons (v1 → v2 upgrade)
    # ─────────────────────────────────────────────────────────────────────────
    async def _ensure_indexes():
        try:
            await db.dms_v2_coupons.create_index("visible_serial", background=True)
            await db.dms_v2_coupons.create_index("hidden_secure_id", background=True, sparse=True)
            await db.dms_v2_coupons.create_index("coupon_code", background=True)
            await db.dms_v2_coupons.create_index("batch_id", background=True)
            await db.dms_v2_coupons.create_index("status", background=True)
            await db.dms_v2_coupons.create_index("retailer_id", background=True, sparse=True)
            await db.dms_v2_coupons.create_index("distributor_id", background=True, sparse=True)
            await db.dms_v2_coupons.create_index([("batch_id", 1), ("visible_serial", 1)],
                                                 background=True)
            await db.dms_v2_coupons.create_index([("batch_id", 1), ("status", 1)],
                                                 background=True)
            await db.dms_v2_wallet_transactions.create_index(
                [("retailer_id", 1), ("wallet_type", 1)], background=True)
            await db.dms_v2_retailer_wallets.create_index(
                [("retailer_id", 1), ("wallet_type", 1)], unique=True, background=True)
            await db.dms_v2_coupon_batches.create_index("batch_no", background=True)
            await db.dms_v2_coupon_batches.create_index("status", background=True)
            await db.dms_v2_coupon_fraud_attempts.create_index("at", background=True)
            await db.dms_v2_coupon_fraud_attempts.create_index("reason", background=True)
            await db.dms_v2_coupon_audit_log.create_index("at", background=True)
            await db.dms_v2_coupon_audit_log.create_index("entity_id", background=True)
            await db.dms_v2_redemption_requests.create_index("status", background=True)
            await db.dms_v2_redemption_requests.create_index("retailer_id", background=True)
        except Exception:
            # index creation is best-effort — collections might not exist yet
            pass

    async def _backfill_v1_coupons():
        """Backfill legacy v1 coupons with visible_serial / hidden_secure_id fields
        so they continue to work with the new schema. Idempotent."""
        try:
            # visible_serial: mirror coupon_code where missing
            await db.dms_v2_coupons.update_many(
                {"visible_serial": {"$exists": False}, "coupon_code": {"$exists": True}},
                [{"$set": {"visible_serial": "$coupon_code"}}],
            )
            # legacy coupons pre-dating v2 — mark qr_version and use secret_token as hidden id
            await db.dms_v2_coupons.update_many(
                {"qr_version": {"$exists": False}},
                {"$set": {"qr_version": "v1"}},
            )
            # For v1 rows, we won't retro-generate a UUID (would break existing QRs).
            # The scan endpoint's v1 fallback path continues to work with secret_token.
        except Exception:
            pass

    # Schedule the migrations to run asynchronously on first request via a
    # lightweight "run-once" latch (APIRouter has no lifespan of its own).
    _startup_done = {"v": False}

    async def _startup_once():
        if _startup_done["v"]:
            return
        _startup_done["v"] = True
        await _ensure_indexes()
        await _backfill_v1_coupons()

    # expose a manual admin trigger + attach to router.state for server.py
    @router.post("/_admin/reinit")
    async def _admin_reinit(user: dict = Depends(owner_only)):
        _startup_done["v"] = False
        await _startup_once()
        return {"ok": True}

    # server.py can call this via router._coupons_startup (attached below)
    router._coupons_startup = _startup_once  # type: ignore[attr-defined]

    return router


__all__ = ["build_coupons_router"]
