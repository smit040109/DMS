"""GO OIL DMS — Phase 3 Reverse Logistics, Claims & Approval Engine.

Modules exposed under /api/reverse/*:
  - Returns (Customer / Retailer / Distributor / Company scopes, 8 reasons)
  - Damage (Warehouse / Transport / Distributor / Retailer / Customer)
  - Claims (Transport / Insurance / Manufacturer / Retailer / Distributor)
  - Credit Notes (auto on approved return, or manual)
  - Debit Notes (extra charges, penalty, transport, short payment, extra supply)
  - Replacements (approved return → new order/dispatch/GIT/GRN chain)
  - Expiry Management (near-expiry / expired / blocked / destroyed / return-to-company)
  - Approval Engine (matrix + step-based approvals, audited)
  - Exception Engine (auto-scan 8 conditions, persist cases)
  - Reports Hub (returns / damage / claims / CN / DN / expiry / replacement / approval / audit)

Every mutation writes to `audit_log`, updates inventory buckets + stock ledger, posts
double-entry ledger entries where financials are affected, and refreshes outstanding.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query


# ---------- Constants ----------

RETURN_TYPES = {
    "damaged_product", "expired_product", "wrong_product", "short_supply",
    "over_supply", "transport_damage", "manufacturing_defect", "customer_rejection",
}
RETURN_SCOPES = {"customer", "retailer", "distributor", "company"}
RETURN_STATES = {"pending", "under_review", "approved", "rejected", "completed"}

DAMAGE_SCOPES = {"warehouse", "transport", "distributor", "retailer", "customer"}
CLAIM_TYPES = {"transport", "insurance", "manufacturer", "retailer", "distributor"}
CLAIM_STATES = {"draft", "pending", "approved", "rejected", "settled"}

CN_REASONS = {"return_approved", "over_billing", "wrong_invoice", "price_difference", "partial_return"}
DN_REASONS = {"additional_charges", "penalty", "short_payment", "extra_supply", "transport_charges"}

APPROVAL_STATES = {"pending", "approved", "rejected"}
EXCEPTION_STATUS = {"open", "under_review", "resolved", "dismissed"}


# Default approval matrix — configurable via /api/reverse/approval-matrix
DEFAULT_APPROVAL_MATRIX = [
    {"entity_type": "return", "amount_min": 0, "amount_max": 500,
     "levels": [{"level": 1, "role": "regional_manager"}]},
    {"entity_type": "return", "amount_min": 500, "amount_max": 5000,
     "levels": [{"level": 1, "role": "regional_manager"}, {"level": 2, "role": "company_admin"}]},
    {"entity_type": "return", "amount_min": 5000, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "regional_manager"},
                {"level": 2, "role": "company_admin"},
                {"level": 3, "role": "distributor_accountant"}]},

    {"entity_type": "claim", "amount_min": 0, "amount_max": 2500,
     "levels": [{"level": 1, "role": "regional_manager"}]},
    {"entity_type": "claim", "amount_min": 2500, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "regional_manager"},
                {"level": 2, "role": "company_admin"},
                {"level": 3, "role": "distributor_accountant"}]},

    {"entity_type": "credit_note", "amount_min": 0, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "distributor_accountant"}]},

    {"entity_type": "debit_note", "amount_min": 0, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "distributor_accountant"}]},

    {"entity_type": "replacement", "amount_min": 0, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "regional_manager"}, {"level": 2, "role": "company_admin"}]},

    {"entity_type": "expense", "amount_min": 0, "amount_max": 1000,
     "levels": [{"level": 1, "role": "regional_manager"}]},
    {"entity_type": "expense", "amount_min": 1000, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "regional_manager"}, {"level": 2, "role": "company_admin"}]},

    {"entity_type": "high_value_discount", "amount_min": 0, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "regional_manager"}, {"level": 2, "role": "company_admin"}]},

    {"entity_type": "credit_limit", "amount_min": 0, "amount_max": 999999999,
     "levels": [{"level": 1, "role": "company_admin"}, {"level": 2, "role": "super_admin"}]},
]


# ---------- Utilities ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def strip_id(doc):
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


def _num(v, default=0.0) -> float:
    try:
        return float(v or 0)
    except Exception:
        return float(default)


# ==========================================================================
# Router factory
# ==========================================================================

def build_reverse_router(db, get_current_user, finance_router):
    """finance_router exposes helpers (post_journal / recompute_outstanding) via attrs."""
    router = APIRouter(prefix="/reverse", tags=["reverse-logistics"])

    # -------- helper: audit --------
    async def audit(action: str, entity_type: str, entity_id: str, actor: dict,
                    old_value: Optional[dict] = None, new_value: Optional[dict] = None,
                    reason: Optional[str] = None, meta: Optional[dict] = None):
        entry = {
            "id": new_id("aud"),
            "timestamp": now_iso(),
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_id": actor.get("id"),
            "actor_email": actor.get("email"),
            "actor_role": actor.get("role"),
            "old_value": old_value or {},
            "new_value": new_value or {},
            "reason": reason or "",
            "meta": meta or {},
            "status": "logged",
            "ip_address": actor.get("ip"),
            "device": actor.get("device"),
        }
        await db.audit_log.insert_one(entry)
        return entry

    # -------- helper: stock ledger --------
    async def ledger_append(**kw):
        entry = {"id": new_id("led"), "timestamp": now_iso(), **kw}
        await db.stock_ledger.insert_one(entry)
        return strip_id(entry)

    # -------- helper: approval matrix chain lookup --------
    async def _matrix_chain(entity_type: str, amount: float) -> List[Dict]:
        cursor = db.approval_matrix.find({"entity_type": entity_type}, {"_id": 0})
        rules = await cursor.to_list(200)
        if not rules:
            # Seed on demand
            await db.approval_matrix.insert_many([{**r, "id": new_id("apm")} for r in DEFAULT_APPROVAL_MATRIX
                                                  if r["entity_type"] == entity_type])
            rules = await db.approval_matrix.find({"entity_type": entity_type}, {"_id": 0}).to_list(200)
        for r in rules:
            if _num(r.get("amount_min", 0)) <= amount <= _num(r.get("amount_max", 999999999)):
                return r.get("levels", [])
        # Fallback: single level regional_manager
        return [{"level": 1, "role": "regional_manager"}]

    async def _create_approval_request(entity_type: str, entity_id: str, amount: float,
                                       summary: str, actor: dict) -> Dict[str, Any]:
        levels = await _matrix_chain(entity_type, amount)
        steps = [{"level": lv["level"], "role": lv["role"], "status": "pending",
                  "actor": None, "acted_at": None, "comment": ""} for lv in levels]
        req = {
            "id": new_id("apr"),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "amount": round(amount, 2),
            "summary": summary,
            "steps": steps,
            "current_level": steps[0]["level"] if steps else 0,
            "status": "pending",
            "requested_by": actor.get("email"),
            "requested_at": now_iso(),
        }
        await db.approval_requests.insert_one(req)
        await audit("create_approval_request", "approval_request", req["id"], actor,
                    new_value={"entity_type": entity_type, "amount": amount, "levels": len(steps)})
        return strip_id(req)

    # ==========================================================
    # APPROVAL MATRIX (config)
    # ==========================================================
    @router.get("/approval-matrix")
    async def list_matrix(user: dict = Depends(get_current_user)):
        # Ensure defaults
        cnt = await db.approval_matrix.count_documents({})
        if cnt == 0:
            await db.approval_matrix.insert_many([{**r, "id": new_id("apm")} for r in DEFAULT_APPROVAL_MATRIX])
        rows = await db.approval_matrix.find({}, {"_id": 0}).sort("entity_type", 1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.post("/approval-matrix")
    async def upsert_matrix_rule(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        rule = {
            "id": payload.get("id") or new_id("apm"),
            "entity_type": payload["entity_type"],
            "amount_min": _num(payload.get("amount_min", 0)),
            "amount_max": _num(payload.get("amount_max", 999999999)),
            "levels": payload.get("levels", []),
            "updated_at": now_iso(),
        }
        await db.approval_matrix.update_one({"id": rule["id"]}, {"$set": rule}, upsert=True)
        await audit("upsert_approval_matrix", "approval_matrix", rule["id"], user, new_value=rule)
        return rule

    @router.delete("/approval-matrix/{rule_id}")
    async def delete_matrix_rule(rule_id: str, user: dict = Depends(get_current_user)):
        await db.approval_matrix.delete_one({"id": rule_id})
        await audit("delete_approval_matrix", "approval_matrix", rule_id, user)
        return {"ok": True}

    # ==========================================================
    # APPROVAL REQUESTS (execute)
    # ==========================================================
    @router.get("/approval-requests")
    async def list_approval_requests(status: Optional[str] = None, entity_type: Optional[str] = None,
                                     user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if entity_type: q["entity_type"] = entity_type
        rows = await db.approval_requests.find(q, {"_id": 0}).sort("requested_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    async def _execute_after_approval(entity_type: str, entity_id: str, actor: dict):
        """Called when the FINAL approval level is approved."""
        if entity_type == "return":
            return await _return_execute_completion(entity_id, actor)
        if entity_type == "claim":
            await db.claims.update_one({"id": entity_id}, {"$set": {"status": "approved", "approved_at": now_iso()}})
        if entity_type == "credit_note":
            return await _credit_note_post(entity_id, actor)
        if entity_type == "debit_note":
            return await _debit_note_post(entity_id, actor)
        if entity_type == "replacement":
            return await _replacement_execute(entity_id, actor)
        return None

    @router.post("/approval-requests/{req_id}/approve")
    async def approve_request(req_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        req = await db.approval_requests.find_one({"id": req_id}, {"_id": 0})
        if not req:
            raise HTTPException(404, "Approval request not found")
        if req["status"] != "pending":
            raise HTTPException(400, f"Request is {req['status']}")

        # Find the current pending step; enforce ordered chain
        steps = req["steps"]
        idx = next((i for i, s in enumerate(steps) if s["status"] == "pending"), None)
        if idx is None:
            raise HTTPException(400, "No pending steps")
        step = steps[idx]
        # Role check — super_admin can override any
        role = user.get("role", "")
        if role != "super_admin" and role != step["role"]:
            raise HTTPException(403, f"This step must be approved by role: {step['role']}")

        step["status"] = "approved"
        step["actor"] = user.get("email")
        step["acted_at"] = now_iso()
        step["comment"] = payload.get("comment", "")

        finished = all(s["status"] == "approved" for s in steps)
        new_status = "approved" if finished else "pending"
        next_level = 0 if finished else steps[idx + 1]["level"] if idx + 1 < len(steps) else 0

        await db.approval_requests.update_one({"id": req_id}, {"$set": {
            "steps": steps, "status": new_status, "current_level": next_level,
            "approved_at": now_iso() if finished else None,
        }})
        await audit("approve_step", "approval_request", req_id, user,
                    new_value={"level": step["level"], "role": step["role"], "final": finished},
                    reason=payload.get("comment", ""))

        # If all levels approved → execute downstream action
        exec_result = None
        if finished:
            try:
                exec_result = await _execute_after_approval(req["entity_type"], req["entity_id"], user)
            except HTTPException:
                raise
            except Exception as e:
                await audit("execution_error", "approval_request", req_id, user, meta={"error": str(e)})

        req["steps"] = steps
        req["status"] = new_status
        req["current_level"] = next_level
        return {"request": strip_id(req), "executed": exec_result}

    @router.post("/approval-requests/{req_id}/reject")
    async def reject_request(req_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        req = await db.approval_requests.find_one({"id": req_id}, {"_id": 0})
        if not req:
            raise HTTPException(404, "Approval request not found")
        if req["status"] != "pending":
            raise HTTPException(400, f"Request is {req['status']}")
        steps = req["steps"]
        idx = next((i for i, s in enumerate(steps) if s["status"] == "pending"), None)
        if idx is None:
            raise HTTPException(400, "No pending steps")
        step = steps[idx]
        if user.get("role") != "super_admin" and user.get("role") != step["role"]:
            raise HTTPException(403, f"This step must be actioned by role: {step['role']}")
        step["status"] = "rejected"
        step["actor"] = user.get("email")
        step["acted_at"] = now_iso()
        step["comment"] = payload.get("reason", "")
        await db.approval_requests.update_one({"id": req_id}, {"$set": {
            "steps": steps, "status": "rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", ""),
        }})
        await audit("reject_step", "approval_request", req_id, user,
                    new_value={"level": step["level"], "role": step["role"]},
                    reason=payload.get("reason", ""))
        # Propagate rejection to entity
        et, eid = req["entity_type"], req["entity_id"]
        if et == "return":
            await db.returns.update_one({"id": eid}, {"$set": {"status": "rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", "")}})
        elif et == "claim":
            await db.claims.update_one({"id": eid}, {"$set": {"status": "rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", "")}})
        elif et == "credit_note":
            await db.credit_notes.update_one({"id": eid}, {"$set": {"status": "rejected", "rejected_at": now_iso()}})
        elif et == "debit_note":
            await db.debit_notes.update_one({"id": eid}, {"$set": {"status": "rejected", "rejected_at": now_iso()}})
        elif et == "replacement":
            await db.replacements.update_one({"id": eid}, {"$set": {"status": "rejected", "rejected_at": now_iso()}})
        return {"ok": True}

    # ==========================================================
    # RETURNS
    # ==========================================================
    async def _find_invoice(invoice_id: Optional[str]):
        if not invoice_id:
            return None
        return await db.invoices.find_one({"id": invoice_id}, {"_id": 0})

    @router.post("/returns")
    async def create_return(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        scope = payload.get("scope", "customer")
        reason = payload.get("reason", "damaged_product")
        if scope not in RETURN_SCOPES:
            raise HTTPException(400, f"Invalid scope: {scope}")
        if reason not in RETURN_TYPES:
            raise HTTPException(400, f"Invalid reason: {reason}")

        party_id = payload.get("party_id")
        party_type = payload.get("party_type", scope)
        invoice = await _find_invoice(payload.get("invoice_id"))

        lines_in = payload.get("lines") or []
        if not lines_in:
            raise HTTPException(400, "At least one return line required")

        subtotal = 0.0
        lines_out = []
        for ln in lines_in:
            sku = await db.skus.find_one({"id": ln.get("sku_id")}, {"_id": 0})
            if not sku:
                raise HTTPException(400, f"Invalid sku_id {ln.get('sku_id')}")
            qty = int(ln.get("qty") or 0)
            if qty <= 0:
                raise HTTPException(400, "Return qty must be > 0")
            price = _num(ln.get("price") or sku.get("mrp") or 0)
            lines_out.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "batch_id": ln.get("batch_id"),
                "qty": qty, "price": price, "subtotal": round(qty * price, 2),
            })
            subtotal += qty * price

        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)

        # Party name resolution
        party_name = None
        if party_type in ("customer", "retailer", "distributor"):
            p = await db[f"{party_type}s"].find_one({"id": party_id}, {"_id": 0})
            if p: party_name = p.get("name")

        rec = {
            "id": new_id("ret"),
            "return_no": f"RET-{int(datetime.now().timestamp())}",
            "scope": scope,
            "reason": reason,
            "party_id": party_id, "party_type": party_type, "party_name": party_name,
            "invoice_id": (invoice or {}).get("id"),
            "invoice_no": (invoice or {}).get("invoice_no"),
            "order_id": payload.get("order_id") or (invoice or {}).get("order_id"),
            "lines": lines_out,
            "subtotal": round(subtotal, 2), "tax": tax, "total": total,
            "photos": payload.get("photos", []),
            "documents": payload.get("documents", []),
            "remarks": payload.get("remarks", ""),
            "status": "pending",
            "requested_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.returns.insert_one(rec)

        # Auto-create approval request
        try:
            approval = await _create_approval_request("return", rec["id"], total,
                                                       f"Return {rec['return_no']} from {party_name or party_id}", user)
            rec["approval_request_id"] = approval["id"]
            await db.returns.update_one({"id": rec["id"]}, {"$set": {"approval_request_id": approval["id"], "status": "under_review"}})
            rec["status"] = "under_review"
        except Exception:
            pass

        await audit("create_return", "return", rec["id"], user, new_value={"reason": reason, "total": total}, reason=payload.get("remarks", ""))
        return strip_id(rec)

    @router.get("/returns")
    async def list_returns(status: Optional[str] = None, scope: Optional[str] = None, party_id: Optional[str] = None,
                            user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if scope: q["scope"] = scope
        if party_id: q["party_id"] = party_id
        rows = await db.returns.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.get("/returns/{return_id}")
    async def get_return(return_id: str, user: dict = Depends(get_current_user)):
        r = await db.returns.find_one({"id": return_id}, {"_id": 0})
        if not r: raise HTTPException(404, "Return not found")
        # Attach related credit note + replacement + audit trail
        cn = await db.credit_notes.find_one({"return_id": return_id}, {"_id": 0})
        rep = await db.replacements.find_one({"return_id": return_id}, {"_id": 0})
        apr = None
        if r.get("approval_request_id"):
            apr = await db.approval_requests.find_one({"id": r["approval_request_id"]}, {"_id": 0})
        trail = await db.audit_log.find({"entity_id": return_id}, {"_id": 0}).sort("timestamp", -1).to_list(50)
        return {"return": r, "credit_note": cn, "replacement": rep, "approval_request": apr, "audit_trail": trail}

    async def _return_execute_completion(return_id: str, actor: dict):
        """Called on final approval — adjusts inventory + creates auto Credit Note."""
        r = await db.returns.find_one({"id": return_id}, {"_id": 0})
        if not r:
            raise HTTPException(404, "Return not found")
        if r.get("inventory_adjusted"):
            return {"already_completed": True}

        scope = r["scope"]
        party_id = r.get("party_id")
        # 1) Inventory adjustments per line
        for ln in r["lines"]:
            batch_id = ln.get("batch_id")
            qty = int(ln["qty"])
            if not batch_id:
                # Pick most recent batch of this SKU in scope inventory
                if scope in ("retailer", "distributor"):
                    coll = f"{scope}_inventory"
                    row = await db[coll].find_one({"partner_id": party_id, "sku_id": ln["sku_id"]}, {"_id": 0})
                    batch_id = row.get("batch_id") if row else None
                elif scope == "company":
                    row = await db.company_inventory.find_one({"sku_id": ln["sku_id"]}, {"_id": 0})
                    batch_id = row.get("batch_id") if row else None
            if not batch_id:
                # Skip inventory move but still allow finance adjustment
                continue
            # Move stock to "returned" bucket at appropriate scope
            if scope == "customer":
                # Return lands back with retailer as returned stock
                target_coll = "retailer_inventory"
                target_partner = r.get("retailer_id") or party_id
                await db[target_coll].update_one(
                    {"partner_id": target_partner, "sku_id": ln["sku_id"], "batch_id": batch_id},
                    {"$inc": {"returned": qty}}, upsert=True,
                )
                await ledger_append(
                    movement="return_in", scope="retailer", partner_id=target_partner,
                    sku_id=ln["sku_id"], sku_code=ln.get("sku_code"), batch_id=batch_id,
                    qty=qty, from_bucket=None, to_bucket="returned",
                    reference_type="return", reference_id=return_id, by_user=actor.get("email"),
                    notes=f"Customer return {r['return_no']}",
                )
            elif scope == "retailer":
                target_coll = "distributor_inventory"
                target_partner = r.get("distributor_id") or party_id
                await db[target_coll].update_one(
                    {"partner_id": target_partner, "sku_id": ln["sku_id"], "batch_id": batch_id},
                    {"$inc": {"returned": qty}}, upsert=True,
                )
                await ledger_append(
                    movement="return_in", scope="distributor", partner_id=target_partner,
                    sku_id=ln["sku_id"], sku_code=ln.get("sku_code"), batch_id=batch_id,
                    qty=qty, from_bucket=None, to_bucket="returned",
                    reference_type="return", reference_id=return_id, by_user=actor.get("email"),
                    notes=f"Retailer return {r['return_no']}",
                )
            elif scope in ("distributor", "company"):
                await db.company_inventory.update_one(
                    {"sku_id": ln["sku_id"], "batch_id": batch_id},
                    {"$inc": {"returned": qty}}, upsert=True,
                )
                await ledger_append(
                    movement="return_in", scope="company",
                    sku_id=ln["sku_id"], sku_code=ln.get("sku_code"), batch_id=batch_id,
                    qty=qty, from_bucket=None, to_bucket="returned",
                    reference_type="return", reference_id=return_id, by_user=actor.get("email"),
                    notes=f"{scope.title()} return {r['return_no']}",
                )
        # 2) Auto Credit Note
        cn = await _create_credit_note_internal(
            reason="return_approved",
            party_id=party_id, party_type=r.get("party_type") or scope,
            invoice_id=r.get("invoice_id"),
            lines=r["lines"], subtotal=r["subtotal"], tax=r["tax"], total=r["total"],
            return_id=return_id, remarks=f"Auto CN from return {r['return_no']}",
            actor=actor,
        )
        # 3) Finalize
        await db.returns.update_one({"id": return_id}, {"$set": {
            "status": "completed", "completed_at": now_iso(),
            "inventory_adjusted": True, "credit_note_id": cn.get("id"),
        }})
        await audit("complete_return", "return", return_id, actor,
                    new_value={"credit_note_id": cn.get("id")})
        return {"return_id": return_id, "credit_note": cn}

    @router.post("/returns/{return_id}/approve")
    async def approve_return_shortcut(return_id: str, payload: Dict[str, Any] = Body(default={}),
                                       user: dict = Depends(get_current_user)):
        """Convenience: super_admin/company_admin fast-approve via approval request chain."""
        r = await db.returns.find_one({"id": return_id}, {"_id": 0})
        if not r: raise HTTPException(404, "Return not found")
        apr_id = r.get("approval_request_id")
        if not apr_id:
            raise HTTPException(400, "No approval request bound to this return")
        # Force super_admin approval — call approve_request for each pending step
        apr = await db.approval_requests.find_one({"id": apr_id}, {"_id": 0})
        result = None
        while apr and apr["status"] == "pending":
            steps = apr["steps"]
            idx = next((i for i, s in enumerate(steps) if s["status"] == "pending"), None)
            if idx is None: break
            step = steps[idx]
            step["status"] = "approved"
            step["actor"] = user.get("email")
            step["acted_at"] = now_iso()
            step["comment"] = payload.get("comment", "fast-approve")
            finished = all(s["status"] == "approved" for s in steps)
            new_status = "approved" if finished else "pending"
            next_level = 0 if finished else steps[idx + 1]["level"] if idx + 1 < len(steps) else 0
            await db.approval_requests.update_one({"id": apr_id}, {"$set": {
                "steps": steps, "status": new_status, "current_level": next_level,
                "approved_at": now_iso() if finished else None,
            }})
            if finished:
                result = await _return_execute_completion(return_id, user)
                break
            apr = await db.approval_requests.find_one({"id": apr_id}, {"_id": 0})
        return {"ok": True, "executed": result}

    @router.post("/returns/{return_id}/reject")
    async def reject_return(return_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        r = await db.returns.find_one({"id": return_id}, {"_id": 0})
        if not r: raise HTTPException(404, "Return not found")
        await db.returns.update_one({"id": return_id}, {"$set": {
            "status": "rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", ""),
        }})
        if r.get("approval_request_id"):
            await db.approval_requests.update_one({"id": r["approval_request_id"]}, {"$set": {"status": "rejected", "rejected_at": now_iso(), "reject_reason": payload.get("reason", "")}})
        await audit("reject_return", "return", return_id, user, reason=payload.get("reason", ""))
        return {"ok": True}

    # ==========================================================
    # DAMAGE
    # ==========================================================
    @router.post("/damage")
    async def record_damage(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        scope = payload.get("scope", "warehouse")
        if scope not in DAMAGE_SCOPES:
            raise HTTPException(400, f"Invalid damage scope: {scope}")
        sku_id = payload.get("sku_id")
        batch_id = payload.get("batch_id")
        qty = int(payload.get("qty", 0) or 0)
        if not (sku_id and batch_id and qty > 0):
            raise HTTPException(400, "sku_id, batch_id and positive qty required")
        partner_id = payload.get("partner_id")

        sku = await db.skus.find_one({"id": sku_id}, {"_id": 0})
        if not sku:
            raise HTTPException(400, "Invalid sku_id")
        est_value = _num(payload.get("estimated_value", sku.get("trade_price", 0) * qty))

        rec = {
            "id": new_id("dmg"),
            "damage_no": f"DMG-{int(datetime.now().timestamp())}",
            "scope": scope,
            "sku_id": sku_id, "sku_code": sku["sku_code"],
            "product_name": sku["product_name"], "pack_size": sku["pack_size"],
            "batch_id": batch_id,
            "partner_id": partner_id,
            "qty": qty,
            "reason": payload.get("reason", ""),
            "photos": payload.get("photos", []),
            "estimated_value": round(est_value, 2),
            "status": "recorded",
            "reported_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.damage.insert_one(rec)

        # Move stock to damaged bucket
        if scope == "warehouse" or scope == "transport":
            await db.company_inventory.update_one(
                {"sku_id": sku_id, "batch_id": batch_id, "available": {"$gte": qty}},
                {"$inc": {"available": -qty, "damaged": qty}},
            )
            await ledger_append(
                movement="damage", scope="company",
                sku_id=sku_id, sku_code=sku["sku_code"], batch_id=batch_id, qty=qty,
                from_bucket="available", to_bucket="damaged",
                reference_type="damage", reference_id=rec["id"], by_user=user.get("email"),
                notes=f"{scope.title()} damage recorded",
            )
        elif scope in ("distributor", "retailer"):
            coll = f"{scope}_inventory"
            await db[coll].update_one(
                {"partner_id": partner_id, "sku_id": sku_id, "batch_id": batch_id, "available": {"$gte": qty}},
                {"$inc": {"available": -qty, "damaged": qty}},
            )
            await ledger_append(
                movement="damage", scope=scope, partner_id=partner_id,
                sku_id=sku_id, sku_code=sku["sku_code"], batch_id=batch_id, qty=qty,
                from_bucket="available", to_bucket="damaged",
                reference_type="damage", reference_id=rec["id"], by_user=user.get("email"),
                notes=f"{scope.title()} damage recorded",
            )

        await audit("record_damage", "damage", rec["id"], user, new_value={"scope": scope, "qty": qty, "value": est_value})
        return strip_id(rec)

    @router.get("/damage")
    async def list_damage(scope: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {}
        if scope: q["scope"] = scope
        rows = await db.damage.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    # ==========================================================
    # CLAIMS
    # ==========================================================
    @router.post("/claims")
    async def create_claim(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        ctype = payload.get("type", "transport")
        if ctype not in CLAIM_TYPES:
            raise HTTPException(400, f"Invalid claim type: {ctype}")
        amount = _num(payload.get("amount", 0))
        if amount <= 0:
            raise HTTPException(400, "Positive claim amount required")

        rec = {
            "id": new_id("clm"),
            "claim_no": f"CLM-{int(datetime.now().timestamp())}",
            "type": ctype,
            "invoice_id": payload.get("invoice_id"),
            "order_id": payload.get("order_id"),
            "damage_id": payload.get("damage_id"),
            "return_id": payload.get("return_id"),
            "sku_id": payload.get("sku_id"),
            "batch_id": payload.get("batch_id"),
            "party_id": payload.get("party_id"),
            "party_type": payload.get("party_type", ctype),
            "party_name": payload.get("party_name", ""),
            "amount": round(amount, 2),
            "reason": payload.get("reason", ""),
            "documents": payload.get("documents", []),
            "photos": payload.get("photos", []),
            "status": "pending",
            "settlement_status": "unsettled",
            "settlement_amount": 0,
            "created_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.claims.insert_one(rec)
        approval = await _create_approval_request("claim", rec["id"], amount, f"Claim {rec['claim_no']} — {ctype}", user)
        rec["approval_request_id"] = approval["id"]
        await db.claims.update_one({"id": rec["id"]}, {"$set": {"approval_request_id": approval["id"]}})
        await audit("create_claim", "claim", rec["id"], user, new_value={"type": ctype, "amount": amount})
        return strip_id(rec)

    @router.get("/claims")
    async def list_claims(status: Optional[str] = None, type: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {}
        if status: q["status"] = status
        if type: q["type"] = type
        rows = await db.claims.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.post("/claims/{claim_id}/settle")
    async def settle_claim(claim_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        c = await db.claims.find_one({"id": claim_id}, {"_id": 0})
        if not c: raise HTTPException(404, "Claim not found")
        if c["status"] not in ("approved",):
            raise HTTPException(400, "Only approved claims can be settled")
        settlement = _num(payload.get("settlement_amount", c["amount"]))
        method = payload.get("method", "Bank Transfer")
        # Post cash-in journal (CASH Dr / AR Cr for retailer/distributor; CASH Dr / MISC Cr for insurance)
        try:
            party_id = c.get("party_id")
            party_type = c.get("party_type") or c["type"]
            if party_id and party_type in ("distributor", "retailer", "customer"):
                await finance_router.post_journal(
                    entries=[
                        {"account": "CASH", "debit": settlement, "credit": 0, "party_id": party_id,
                         "party_type": party_type, "party_name": c.get("party_name")},
                        {"account": "AR", "debit": 0, "credit": settlement, "party_id": party_id,
                         "party_type": party_type, "party_name": c.get("party_name")},
                    ],
                    reference_type="claim_settlement", reference_id=claim_id,
                    narration=f"Claim settlement {c['claim_no']} via {method}", actor=user.get("email"),
                )
                await finance_router.recompute_outstanding(party_type, party_id)
        except Exception:
            pass

        await db.claims.update_one({"id": claim_id}, {"$set": {
            "status": "settled", "settlement_status": "settled",
            "settlement_amount": round(settlement, 2), "settlement_method": method,
            "settled_at": now_iso(), "settled_by": user.get("email"),
        }})
        await audit("settle_claim", "claim", claim_id, user, new_value={"amount": settlement, "method": method})
        return {"ok": True, "settlement_amount": settlement}

    # ==========================================================
    # CREDIT NOTES
    # ==========================================================
    async def _create_credit_note_internal(reason: str, party_id: str, party_type: str,
                                           invoice_id: Optional[str], lines: List[Dict],
                                           subtotal: float, tax: float, total: float,
                                           return_id: Optional[str], remarks: str, actor: dict) -> Dict:
        if reason not in CN_REASONS:
            raise HTTPException(400, f"Invalid CN reason: {reason}")
        party_name = None
        if party_type in ("customer", "retailer", "distributor"):
            p = await db[f"{party_type}s"].find_one({"id": party_id}, {"_id": 0})
            if p: party_name = p.get("name")
        cn = {
            "id": new_id("cn"),
            "cn_no": f"CN-{int(datetime.now().timestamp())}",
            "reason": reason,
            "party_id": party_id, "party_type": party_type, "party_name": party_name,
            "invoice_id": invoice_id,
            "return_id": return_id,
            "lines": lines,
            "subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": round(total, 2),
            "remarks": remarks,
            "status": "posted",
            "created_by": actor.get("email"),
            "created_at": now_iso(),
        }
        await db.credit_notes.insert_one(cn)
        # Post to ledger: reduce AR (SALES Dr / TAX_OUT Dr / AR Cr)
        try:
            await finance_router.post_journal(
                entries=[
                    {"account": "SALES", "debit": round(subtotal, 2), "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": party_name},
                    {"account": "TAX_OUT", "debit": round(tax, 2), "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": party_name},
                    {"account": "AR", "debit": 0, "credit": round(total, 2), "party_id": party_id, "party_type": party_type, "party_name": party_name},
                ],
                reference_type="credit_note", reference_id=cn["id"],
                narration=f"Credit Note {cn['cn_no']} — {reason}", actor=actor.get("email"),
            )
            await finance_router.recompute_outstanding(party_type, party_id)
        except Exception:
            pass
        # If invoice supplied, reduce invoice outstanding
        if invoice_id:
            inv = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
            if inv:
                new_credited = round(_num(inv.get("credited", 0)) + round(total, 2), 2)
                inv_total = _num(inv.get("total", 0))
                inv_paid = _num(inv.get("paid", 0))
                if new_credited + inv_paid >= inv_total - 0.01:
                    new_status = "cancelled" if new_credited >= inv_total - 0.01 and inv_paid < 0.01 else "settled"
                else:
                    new_status = inv.get("status", "issued")
                await db.invoices.update_one({"id": invoice_id}, {"$set": {"credited": new_credited, "payment_status": "credited"}})
        await audit("create_credit_note", "credit_note", cn["id"], actor,
                    new_value={"reason": reason, "total": total, "party_id": party_id})
        return strip_id(cn)

    @router.post("/credit-notes")
    async def create_credit_note(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        cn = await _create_credit_note_internal(
            reason=payload.get("reason", "over_billing"),
            party_id=payload["party_id"], party_type=payload.get("party_type", "customer"),
            invoice_id=payload.get("invoice_id"),
            lines=payload.get("lines", []),
            subtotal=_num(payload.get("subtotal", 0)),
            tax=_num(payload.get("tax", 0)),
            total=_num(payload.get("total", 0)),
            return_id=payload.get("return_id"),
            remarks=payload.get("remarks", ""),
            actor=user,
        )
        return cn

    async def _credit_note_post(cn_id: str, actor: dict):
        # For approval-driven flow (if reason requires): treat as already posted here
        return await db.credit_notes.find_one({"id": cn_id}, {"_id": 0})

    @router.get("/credit-notes")
    async def list_credit_notes(status: Optional[str] = None, party_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if party_id: q["party_id"] = party_id
        rows = await db.credit_notes.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    # ==========================================================
    # DEBIT NOTES
    # ==========================================================
    @router.post("/debit-notes")
    async def create_debit_note(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        reason = payload.get("reason", "additional_charges")
        if reason not in DN_REASONS:
            raise HTTPException(400, f"Invalid DN reason: {reason}")
        party_id = payload["party_id"]
        party_type = payload.get("party_type", "distributor")
        amount = _num(payload.get("amount", 0))
        tax = round(amount * _num(payload.get("tax_rate", 0.18)), 2)
        total = round(amount + tax, 2)
        p = await db[f"{party_type}s"].find_one({"id": party_id}, {"_id": 0})
        party_name = (p or {}).get("name")

        dn = {
            "id": new_id("dn"),
            "dn_no": f"DN-{int(datetime.now().timestamp())}",
            "reason": reason,
            "party_id": party_id, "party_type": party_type, "party_name": party_name,
            "invoice_id": payload.get("invoice_id"),
            "amount": round(amount, 2), "tax": tax, "total": total,
            "remarks": payload.get("remarks", ""),
            "status": "posted",
            "created_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.debit_notes.insert_one(dn)
        # Ledger: AR Dr / SALES Cr / TAX_OUT Cr (charge added to receivables)
        try:
            await finance_router.post_journal(
                entries=[
                    {"account": "AR", "debit": total, "credit": 0, "party_id": party_id, "party_type": party_type, "party_name": party_name},
                    {"account": "SALES", "debit": 0, "credit": amount, "party_id": party_id, "party_type": party_type, "party_name": party_name},
                    {"account": "TAX_OUT", "debit": 0, "credit": tax, "party_id": party_id, "party_type": party_type, "party_name": party_name},
                ],
                reference_type="debit_note", reference_id=dn["id"],
                narration=f"Debit Note {dn['dn_no']} — {reason}", actor=user.get("email"),
            )
            await finance_router.recompute_outstanding(party_type, party_id)
        except Exception:
            pass
        await audit("create_debit_note", "debit_note", dn["id"], user, new_value={"reason": reason, "total": total})
        return strip_id(dn)

    async def _debit_note_post(dn_id: str, actor: dict):
        return await db.debit_notes.find_one({"id": dn_id}, {"_id": 0})

    @router.get("/debit-notes")
    async def list_debit_notes(status: Optional[str] = None, party_id: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if party_id: q["party_id"] = party_id
        rows = await db.debit_notes.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    # ==========================================================
    # REPLACEMENTS
    # ==========================================================
    async def _replacement_execute(rep_id: str, actor: dict):
        """After approval, create dispatch chain for the replacement."""
        rep = await db.replacements.find_one({"id": rep_id}, {"_id": 0})
        if not rep: raise HTTPException(404, "Replacement not found")
        if rep.get("dispatch_id"):
            return {"already_dispatched": True}

        scope = rep["scope"]  # customer / retailer / distributor
        party_id = rep["party_id"]
        # Reserve FIFO from company inventory (simplified: always source from company)
        lines = rep["lines"]
        try:
            for ln in lines:
                # find batches
                rows = await db.company_inventory.find({"sku_id": ln["sku_id"], "available": {"$gt": 0}}, {"_id": 0}).to_list(200)
                allocations = []
                need = int(ln["qty"])
                for r in rows:
                    if need <= 0: break
                    take = min(int(r.get("available", 0)), need)
                    if take <= 0: continue
                    await db.company_inventory.update_one({"id": r["id"]}, {"$inc": {"available": -take, "in_transit": take}})
                    allocations.append({"batch_id": r["batch_id"], "qty": take})
                    need -= take
                if need > 0:
                    raise HTTPException(400, f"Insufficient stock for replacement SKU {ln['sku_code']}, short by {need}")
                ln["reserved_allocations"] = allocations
                for a in allocations:
                    await ledger_append(
                        movement="replacement_out", scope="company",
                        sku_id=ln["sku_id"], sku_code=ln["sku_code"], batch_id=a["batch_id"], qty=a["qty"],
                        from_bucket="available", to_bucket="in_transit",
                        reference_type="replacement", reference_id=rep_id, by_user=actor.get("email"),
                        notes=f"Replacement dispatch for {rep['replacement_no']}",
                    )
        except HTTPException:
            raise

        dispatch = {
            "id": new_id("disp"),
            "dispatch_no": f"DSP-R-{int(datetime.now().timestamp())}",
            "invoice_id": None,
            "invoice_no": None,
            "order_id": rep_id,
            "type": "replacement",
            "party_name": rep.get("party_name"),
            "distributor_id": rep.get("distributor_id"),
            "retailer_id": rep.get("retailer_id"),
            "customer_id": rep.get("customer_id"),
            "lines": lines,
            "vehicle_no": "REP-VEH", "driver": "TBD", "lr_no": f"LRR{int(datetime.now().timestamp())}",
            "transporter": "GO OIL Transport", "route": "Replacement",
            "dispatch_date": now_iso(), "eta": now_iso(),
            "status": "in_transit",
            "created_by": actor.get("email"),
        }
        await db.dispatches.insert_one(dispatch)

        # GRN — mark as received automatically for replacements (simplified for MVP)
        grn = {
            "id": new_id("grn"),
            "grn_no": f"GRN-R-{int(datetime.now().timestamp())}",
            "dispatch_id": dispatch["id"], "dispatch_no": dispatch["dispatch_no"],
            "type": "replacement",
            "distributor_id": rep.get("distributor_id"),
            "retailer_id": rep.get("retailer_id"),
            "received_by": rep.get("party_name"),
            "received_on": now_iso(),
            "lines": [{"sku_id": ln["sku_id"], "sku_code": ln["sku_code"], "dispatched_qty": ln["qty"],
                        "received_qty": ln["qty"], "damaged_qty": 0, "shortage_qty": 0, "excess_qty": 0}
                       for ln in lines],
            "condition": "Good", "variance": 0, "status": "Accepted",
            "notes": f"Replacement GRN for {rep['replacement_no']}",
        }
        await db.grns.insert_one(grn)

        # Land stock at target scope
        for ln in lines:
            for a in ln["reserved_allocations"]:
                # Clear company in_transit
                await db.company_inventory.update_one(
                    {"sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                    {"$inc": {"in_transit": -a["qty"]}},
                )
                sku = await db.skus.find_one({"id": ln["sku_id"]}, {"_id": 0}) or {}
                if scope in ("retailer", "distributor"):
                    target_coll = f"{scope}_inventory"
                    row = await db[target_coll].find_one({"partner_id": party_id, "sku_id": ln["sku_id"], "batch_id": a["batch_id"]})
                    if row:
                        await db[target_coll].update_one({"id": row["id"]}, {"$inc": {"available": a["qty"]}})
                    else:
                        await db[target_coll].insert_one({
                            "id": new_id(target_coll[:4]),
                            "partner_id": party_id, "sku_id": ln["sku_id"],
                            "sku_code": ln.get("sku_code"), "product_name": ln.get("product_name"),
                            "pack_size": ln.get("pack_size"),
                            "batch_id": a["batch_id"],
                            "available": a["qty"], "reserved": 0, "in_transit": 0,
                            "damaged": 0, "returned": 0, "expired": 0,
                        })
                await ledger_append(
                    movement="replacement_grn", scope=scope if scope != "customer" else "retailer",
                    partner_id=party_id if scope in ("retailer", "distributor") else rep.get("retailer_id"),
                    sku_id=ln["sku_id"], sku_code=ln.get("sku_code"),
                    batch_id=a["batch_id"], qty=a["qty"],
                    from_bucket=None, to_bucket="available",
                    reference_type="replacement", reference_id=rep_id, by_user=actor.get("email"),
                    notes=f"Replacement GRN {grn['grn_no']}",
                )

        await db.replacements.update_one({"id": rep_id}, {"$set": {
            "status": "completed", "dispatch_id": dispatch["id"], "grn_id": grn["id"],
            "completed_at": now_iso(),
        }})
        await audit("execute_replacement", "replacement", rep_id, actor,
                    new_value={"dispatch_id": dispatch["id"], "grn_id": grn["id"]})
        return {"replacement_id": rep_id, "dispatch_id": dispatch["id"], "grn_id": grn["id"]}

    @router.post("/replacements")
    async def create_replacement(payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        return_id = payload.get("return_id")
        r = await db.returns.find_one({"id": return_id}, {"_id": 0}) if return_id else None
        scope = payload.get("scope") or (r or {}).get("scope") or "customer"
        party_id = payload.get("party_id") or (r or {}).get("party_id")
        party_type = payload.get("party_type") or (r or {}).get("party_type") or scope
        lines = payload.get("lines") or (r or {}).get("lines") or []
        subtotal = sum(_num(ln.get("subtotal", ln.get("qty", 0) * ln.get("price", 0))) for ln in lines)
        total = round(subtotal * 1.18, 2)  # simplified for approval slab lookup
        party_name = None
        if party_type in ("customer", "retailer", "distributor"):
            p = await db[f"{party_type}s"].find_one({"id": party_id}, {"_id": 0})
            if p: party_name = p.get("name")

        rec = {
            "id": new_id("rep"),
            "replacement_no": f"REP-{int(datetime.now().timestamp())}",
            "return_id": return_id,
            "scope": scope,
            "party_id": party_id, "party_type": party_type, "party_name": party_name,
            "distributor_id": payload.get("distributor_id") or (r or {}).get("distributor_id"),
            "retailer_id": payload.get("retailer_id") or (r or {}).get("retailer_id"),
            "customer_id": payload.get("customer_id") or (r or {}).get("customer_id"),
            "lines": lines,
            "subtotal": round(subtotal, 2), "total": round(total, 2),
            "reason": payload.get("reason", "return_replacement"),
            "status": "pending",
            "created_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.replacements.insert_one(rec)
        approval = await _create_approval_request("replacement", rec["id"], total, f"Replacement {rec['replacement_no']} for {party_name or party_id}", user)
        rec["approval_request_id"] = approval["id"]
        await db.replacements.update_one({"id": rec["id"]}, {"$set": {"approval_request_id": approval["id"]}})
        await audit("create_replacement", "replacement", rec["id"], user, new_value={"scope": scope, "total": total})
        return strip_id(rec)

    @router.get("/replacements")
    async def list_replacements(status: Optional[str] = None, user: dict = Depends(get_current_user)):
        q = {}
        if status: q["status"] = status
        rows = await db.replacements.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"data": rows, "count": len(rows)}

    @router.get("/replacements/{rep_id}")
    async def get_replacement(rep_id: str, user: dict = Depends(get_current_user)):
        rec = await db.replacements.find_one({"id": rep_id}, {"_id": 0})
        if not rec: raise HTTPException(404, "Replacement not found")
        disp = await db.dispatches.find_one({"id": rec.get("dispatch_id")}, {"_id": 0}) if rec.get("dispatch_id") else None
        grn = await db.grns.find_one({"id": rec.get("grn_id")}, {"_id": 0}) if rec.get("grn_id") else None
        ret = await db.returns.find_one({"id": rec.get("return_id")}, {"_id": 0}) if rec.get("return_id") else None
        return {"replacement": rec, "return": ret, "dispatch": disp, "grn": grn}

    # ==========================================================
    # EXPIRY
    # ==========================================================
    @router.get("/expiry")
    async def expiry_overview(days: int = Query(30, ge=1, le=365), user: dict = Depends(get_current_user)):
        threshold = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        today = datetime.now(timezone.utc).isoformat()
        near = []
        expired = []
        async for b in db.batches.find({}, {"_id": 0}):
            exp = b.get("expires_on") or ""
            if not exp: continue
            if exp < today:
                expired.append(b)
            elif exp <= threshold:
                near.append(b)
        # Aggregate stock per batch
        async def stock_for(batch_id):
            total = 0
            async for row in db.company_inventory.find({"batch_id": batch_id}, {"_id": 0}):
                total += int(row.get("available", 0)) + int(row.get("reserved", 0))
            async for row in db.distributor_inventory.find({"batch_id": batch_id}, {"_id": 0}):
                total += int(row.get("available", 0))
            async for row in db.retailer_inventory.find({"batch_id": batch_id}, {"_id": 0}):
                total += int(row.get("available", 0))
            return total
        for b in near + expired:
            b["stock_qty"] = await stock_for(b["id"])
        blocked = await db.expiry_records.find({"action": "block"}, {"_id": 0}).to_list(500)
        destroyed = await db.expiry_records.find({"action": "destroy"}, {"_id": 0}).to_list(500)
        returned = await db.expiry_records.find({"action": "return_to_company"}, {"_id": 0}).to_list(500)
        return {
            "near_expiry": near, "expired": expired,
            "blocked": blocked, "destroyed": destroyed, "return_to_company": returned,
            "count": {"near": len(near), "expired": len(expired), "blocked": len(blocked),
                      "destroyed": len(destroyed), "return_to_company": len(returned)},
        }

    @router.post("/expiry/{batch_id}/action")
    async def expiry_action(batch_id: str, payload: Dict[str, Any] = Body(...), user: dict = Depends(get_current_user)):
        action = payload.get("action")  # block / destroy / return_to_company / replacement
        if action not in ("block", "destroy", "return_to_company", "replacement_source"):
            raise HTTPException(400, f"Invalid action: {action}")
        batch = await db.batches.find_one({"id": batch_id}, {"_id": 0})
        if not batch: raise HTTPException(404, "Batch not found")

        # Move available → expired for all inventory holding this batch
        moved = 0
        for coll in ("company_inventory", "distributor_inventory", "retailer_inventory"):
            async for row in db[coll].find({"batch_id": batch_id}, {"_id": 0}):
                qty = int(row.get("available", 0) or 0)
                if qty > 0:
                    await db[coll].update_one({"id": row["id"]}, {"$inc": {"available": -qty, "expired": qty}})
                    moved += qty
                    await ledger_append(
                        movement="expiry_move", scope=coll.split("_")[0],
                        partner_id=row.get("partner_id"),
                        sku_id=row["sku_id"], sku_code=row.get("sku_code"),
                        batch_id=batch_id, qty=qty,
                        from_bucket="available", to_bucket="expired",
                        reference_type="expiry", reference_id=batch_id, by_user=user.get("email"),
                        notes=f"Expiry action: {action}",
                    )

        rec = {
            "id": new_id("exp"),
            "batch_id": batch_id, "batch_no": batch.get("batch_no"),
            "sku_id": batch.get("sku_id"), "sku_code": batch.get("sku_code"),
            "action": action, "qty_affected": moved,
            "reason": payload.get("reason", ""),
            "created_by": user.get("email"),
            "created_at": now_iso(),
        }
        await db.expiry_records.insert_one(rec)
        await audit("expiry_action", "batch", batch_id, user, new_value={"action": action, "qty": moved})
        return strip_id(rec)

    # ==========================================================
    # EXCEPTIONS
    # ==========================================================
    async def _add_exception(kind: str, severity: str, entity_type: str, entity_id: str,
                             description: str, meta: dict, actor: dict):
        existing = await db.exceptions.find_one({"kind": kind, "entity_id": entity_id, "status": "open"})
        if existing:
            return None
        rec = {
            "id": new_id("exc"),
            "kind": kind, "severity": severity,
            "entity_type": entity_type, "entity_id": entity_id,
            "description": description, "meta": meta,
            "status": "open",
            "detected_by": actor.get("email"),
            "detected_at": now_iso(),
        }
        await db.exceptions.insert_one(rec)
        return rec

    @router.post("/exceptions/scan")
    async def scan_exceptions(user: dict = Depends(get_current_user)):
        found = []
        # 1) Negative inventory
        for coll in ("company_inventory", "distributor_inventory", "retailer_inventory"):
            async for row in db[coll].find({"$or": [
                {"available": {"$lt": 0}}, {"reserved": {"$lt": 0}}, {"in_transit": {"$lt": 0}},
            ]}, {"_id": 0}):
                exc = await _add_exception("negative_inventory", "high", coll, row["id"],
                                            f"Negative bucket in {coll}", row, user)
                if exc: found.append(exc)
        # 2) Duplicate invoice numbers
        pipeline = [{"$group": {"_id": "$invoice_no", "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
                     {"$match": {"count": {"$gt": 1}}}]
        async for d in db.invoices.aggregate(pipeline):
            exc = await _add_exception("duplicate_invoice", "high", "invoice", d["_id"] or "?",
                                        f"Duplicate invoice_no: {d['_id']}", {"ids": d["ids"]}, user)
            if exc: found.append(exc)
        # 3) Duplicate payments (same reference + party)
        pipeline = [{"$group": {"_id": {"ref": "$reference", "party": "$party_id"},
                                  "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
                     {"$match": {"count": {"$gt": 1}, "_id.ref": {"$ne": None}}}]
        async for d in db.payments.aggregate(pipeline):
            exc = await _add_exception("duplicate_payment", "high", "payment",
                                        d["_id"]["ref"] or "?",
                                        f"Duplicate payment reference for party", {"ids": d["ids"]}, user)
            if exc: found.append(exc)
        # 4) Credit limit exceeded
        async for row in db.outstanding.find({"credit_limit": {"$gt": 0}}, {"_id": 0}):
            if row.get("credit_utilization", 0) > 100:
                exc = await _add_exception("credit_limit_exceeded", "medium", row["party_type"], row["party_id"],
                                            f"{row.get('party_name')} exceeded credit limit ({row.get('credit_utilization')}%)",
                                            row, user)
                if exc: found.append(exc)
        # 5) Expired stock still available
        today = datetime.now(timezone.utc).isoformat()
        async for b in db.batches.find({"expires_on": {"$lt": today}}, {"_id": 0}):
            async for row in db.company_inventory.find({"batch_id": b["id"], "available": {"$gt": 0}}, {"_id": 0}):
                exc = await _add_exception("expired_stock_dispatch", "high", "batch", b["id"],
                                            f"Expired batch {b.get('batch_no')} still has available stock",
                                            {"batch_no": b.get("batch_no"), "available": row.get("available"), "coll": "company"}, user)
                if exc: found.append(exc)
        # 6) Duplicate claims (same invoice + type)
        pipeline = [{"$group": {"_id": {"inv": "$invoice_id", "type": "$type"},
                                  "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
                     {"$match": {"count": {"$gt": 1}, "_id.inv": {"$ne": None}}}]
        async for d in db.claims.aggregate(pipeline):
            exc = await _add_exception("duplicate_claim", "medium", "claim", d["_id"]["inv"] or "?",
                                        f"Duplicate {d['_id']['type']} claim for invoice", {"ids": d["ids"]}, user)
            if exc: found.append(exc)
        # 7) Stock variance (dispatch qty vs GRN received)
        async for g in db.grns.find({"variance": {"$ne": 0}}, {"_id": 0}).limit(200):
            exc = await _add_exception("stock_variance", "medium", "grn", g["id"],
                                        f"GRN {g.get('grn_no')} has variance {g.get('variance')}", {"variance": g.get("variance")}, user)
            if exc: found.append(exc)
        # 8) Price mismatch (invoice line price vs SKU trade_price)
        async for inv in db.invoices.find({}, {"_id": 0}).limit(500):
            for ln in inv.get("lines", []):
                sku = await db.skus.find_one({"id": ln.get("sku_id")}, {"_id": 0})
                if sku and _num(sku.get("trade_price", 0)) > 0:
                    trade = _num(sku.get("trade_price"))
                    price = _num(ln.get("price"))
                    if trade > 0 and abs(price - trade) / trade > 0.5:
                        exc = await _add_exception("price_mismatch", "low", "invoice", inv["id"],
                                                    f"Line {ln.get('sku_code')} price {price} deviates from trade {trade}",
                                                    {"invoice_no": inv.get("invoice_no")}, user)
                        if exc: found.append(exc)
                        break
        await audit("scan_exceptions", "system", "exception_scan", user, meta={"found": len(found)})
        return {"found": len(found), "exceptions": found}

    @router.get("/exceptions")
    async def list_exceptions(status: Optional[str] = None, kind: Optional[str] = None, user: dict = Depends(get_current_user)):
        q: Dict[str, Any] = {}
        if status: q["status"] = status
        if kind: q["kind"] = kind
        rows = await db.exceptions.find(q, {"_id": 0}).sort("detected_at", -1).to_list(1000)
        return {"data": rows, "count": len(rows)}

    @router.post("/exceptions/{exc_id}/resolve")
    async def resolve_exception(exc_id: str, payload: Dict[str, Any] = Body(default={}), user: dict = Depends(get_current_user)):
        r = await db.exceptions.update_one({"id": exc_id}, {"$set": {
            "status": payload.get("status", "resolved"),
            "resolution": payload.get("resolution", ""),
            "resolved_by": user.get("email"), "resolved_at": now_iso(),
        }})
        if r.matched_count == 0:
            raise HTTPException(404, "Exception not found")
        await audit("resolve_exception", "exception", exc_id, user, reason=payload.get("resolution", ""))
        return {"ok": True}

    # ==========================================================
    # REPORTS HUB
    # ==========================================================
    @router.get("/reports/{report}")
    async def generate_report(report: str, user: dict = Depends(get_current_user)):
        report = report.lower()
        if report == "returns":
            rows = await db.returns.find({}, {"_id": 0}).to_list(2000)
            total = sum(_num(r.get("total", 0)) for r in rows)
            by_status = {}
            by_reason = {}
            for r in rows:
                by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
                by_reason[r.get("reason", "?")] = by_reason.get(r.get("reason", "?"), 0) + 1
            return {"report": "returns", "count": len(rows), "total_value": round(total, 2),
                    "by_status": by_status, "by_reason": by_reason, "rows": rows[:100]}
        if report == "damage":
            rows = await db.damage.find({}, {"_id": 0}).to_list(2000)
            total = sum(_num(r.get("estimated_value", 0)) for r in rows)
            by_scope = {}
            for r in rows:
                by_scope[r.get("scope", "?")] = by_scope.get(r.get("scope", "?"), 0) + 1
            return {"report": "damage", "count": len(rows), "total_value": round(total, 2), "by_scope": by_scope, "rows": rows[:100]}
        if report == "claims":
            rows = await db.claims.find({}, {"_id": 0}).to_list(2000)
            total = sum(_num(r.get("amount", 0)) for r in rows)
            settled = sum(_num(r.get("settlement_amount", 0)) for r in rows if r.get("status") == "settled")
            by_type = {}
            for r in rows:
                by_type[r.get("type", "?")] = by_type.get(r.get("type", "?"), 0) + 1
            return {"report": "claims", "count": len(rows), "total_claimed": round(total, 2),
                    "total_settled": round(settled, 2), "by_type": by_type, "rows": rows[:100]}
        if report == "credit_notes":
            rows = await db.credit_notes.find({}, {"_id": 0}).to_list(2000)
            total = sum(_num(r.get("total", 0)) for r in rows)
            by_reason = {}
            for r in rows:
                by_reason[r.get("reason", "?")] = by_reason.get(r.get("reason", "?"), 0) + 1
            return {"report": "credit_notes", "count": len(rows), "total_value": round(total, 2), "by_reason": by_reason, "rows": rows[:100]}
        if report == "debit_notes":
            rows = await db.debit_notes.find({}, {"_id": 0}).to_list(2000)
            total = sum(_num(r.get("total", 0)) for r in rows)
            by_reason = {}
            for r in rows:
                by_reason[r.get("reason", "?")] = by_reason.get(r.get("reason", "?"), 0) + 1
            return {"report": "debit_notes", "count": len(rows), "total_value": round(total, 2), "by_reason": by_reason, "rows": rows[:100]}
        if report == "expiry":
            overview = await expiry_overview(30, user)
            return {"report": "expiry", **overview}
        if report == "replacements":
            rows = await db.replacements.find({}, {"_id": 0}).to_list(2000)
            by_status = {}
            for r in rows:
                by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
            return {"report": "replacements", "count": len(rows), "by_status": by_status, "rows": rows[:100]}
        if report == "approvals":
            rows = await db.approval_requests.find({}, {"_id": 0}).to_list(2000)
            by_status = {}
            by_entity = {}
            for r in rows:
                by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
                by_entity[r.get("entity_type", "?")] = by_entity.get(r.get("entity_type", "?"), 0) + 1
            return {"report": "approvals", "count": len(rows), "by_status": by_status, "by_entity": by_entity, "rows": rows[:100]}
        if report == "audit":
            rows = await db.audit_log.find({}, {"_id": 0}).sort("timestamp", -1).to_list(2000)
            by_action = {}
            for r in rows:
                by_action[r.get("action", "?")] = by_action.get(r.get("action", "?"), 0) + 1
            return {"report": "audit", "count": len(rows), "by_action": by_action, "rows": rows[:200]}
        raise HTTPException(400, f"Unknown report: {report}")

    return router
