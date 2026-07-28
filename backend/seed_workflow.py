"""Runs the complete DMS workflow once at startup to produce a realistic
transactional chain — batches → company inventory → primary orders → invoices →
dispatches → GRNs → distributor inventory → secondary orders → secondary invoices →
secondary dispatches → retailer GRNs → retailer inventory.

Only runs if `primary_orders` collection is empty (idempotent).
"""
from __future__ import annotations
import random
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger("gooil.dms.seed_workflow")

random.seed(2026)


async def run_seed_workflow(db, workflow_router_functions=None):
    """workflow_router_functions can be passed to invoke the exact API code path.
    For simplicity we replicate the minimal chain directly using low-level Mongo writes."""
    if await db.primary_orders.count_documents({}) > 0:
        log.info("Workflow seed skipped — primary_orders already populated")
        return

    # Use direct HTTP-style helpers via importing workflow builder
    # Simpler: call the same helpers by importing the module and building a fake ctx
    from workflow import build_workflow_router
    from fastapi import Depends

    # Stand-alone helpers copy — we replicate the logic inline for speed.
    from workflow import now_iso, new_id, strip_id

    fake_user = {"id": "usr-seed", "email": "seed@gooil.com", "role": "company_admin"}

    # ------- STEP 1: Create batches for a subset of SKUs -------
    skus = await db.skus.find({}, {"_id": 0}).to_list(200)
    if not skus:
        log.warning("No SKUs found — cannot seed workflow")
        return

    warehouses = await db.warehouses.find({}, {"_id": 0}).to_list(20)
    if not warehouses:
        return
    wh_ids = [w["id"] for w in warehouses]

    # Clear the existing (random) batches + inventory + orders — we're rebuilding
    for coll in ("batches", "inventory", "primary_orders", "secondary_orders",
                 "invoices", "dispatches", "grns", "company_inventory",
                 "distributor_inventory", "retailer_inventory", "stock_ledger"):
        await db[coll].delete_many({})

    picked_skus = random.sample(skus, k=min(30, len(skus)))
    batches_created = []
    for i, sku in enumerate(picked_skus):
        # 2 batches per SKU (older + newer for FIFO demo)
        for j in range(2):
            batch = {
                "id": new_id("batch"),
                "batch_no": f"B2026{i:03d}{j}",
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "manufactured_on": now_iso() if j else "2025-06-01T00:00:00+00:00",
                "expires_on": "2027-12-31T00:00:00+00:00",
                "batch_quantity": random.randint(400, 1200),
                "quantity": 0,
                "quality_status": "Approved",
                "status": "stocked_in",
                "warehouse_id": random.choice(wh_ids),
                "stocked_in": True,
                "created_at": now_iso(),
            }
            batch["quantity"] = batch["batch_quantity"]
            await db.batches.insert_one(batch)
            # Company inventory row
            await db.company_inventory.insert_one({
                "id": new_id("cinv"),
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "batch_id": batch["id"], "warehouse_id": batch["warehouse_id"],
                "available": batch["batch_quantity"], "reserved": 0, "in_transit": 0,
                "damaged": 0, "returned": 0, "expired": 0,
            })
            await db.stock_ledger.insert_one({
                "id": new_id("led"), "timestamp": now_iso(),
                "movement": "stock_in", "scope": "company",
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "batch_id": batch["id"], "qty": batch["batch_quantity"],
                "from_bucket": None, "to_bucket": "available",
                "reference_type": "batch", "reference_id": batch["id"],
                "by_user": "seed@gooil.com",
                "notes": f"Seed stock-in for batch {batch['batch_no']}",
            })
            batches_created.append(batch)
    log.info(f"Seeded {len(batches_created)} batches with company inventory")

    # ------- STEP 2: Create primary orders (mix of statuses) -------
    distributors = await db.distributors.find({}, {"_id": 0}).to_list(50)
    if not distributors:
        return

    # Simple aggregate stock lookup
    async def avail_by_sku(sku_id):
        total = 0
        async for row in db.company_inventory.find({"sku_id": sku_id}, {"_id": 0}):
            total += int(row.get("available", 0) or 0)
        return total

    async def reserve_fifo_company(sku_id, qty):
        rows = await db.company_inventory.find({"sku_id": sku_id, "available": {"$gt": 0}}, {"_id": 0}).to_list(50)
        bids = [r["batch_id"] for r in rows]
        bmap = {}
        async for b in db.batches.find({"id": {"$in": bids}}, {"_id": 0}):
            bmap[b["id"]] = b
        rows.sort(key=lambda r: bmap.get(r["batch_id"], {}).get("manufactured_on", ""))
        allocs, need = [], qty
        for r in rows:
            if need <= 0: break
            take = min(r["available"], need)
            if take <= 0: continue
            await db.company_inventory.update_one({"id": r["id"]}, {"$inc": {"available": -take, "reserved": take}})
            allocs.append({"batch_id": r["batch_id"], "qty": take})
            need -= take
        return allocs

    sku_pool = picked_skus
    orders_made = []
    for i in range(24):
        dist = random.choice(distributors)
        n_lines = random.randint(2, 5)
        lines = []
        subtotal = 0
        for sku in random.sample(sku_pool, k=n_lines):
            qty = random.randint(10, 80)
            avail = await avail_by_sku(sku["id"])
            if avail < qty: qty = max(5, avail // 2)
            if qty <= 0: continue
            price = float(sku.get("trade_price") or 500)
            lines.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "qty": qty, "price": price, "subtotal": qty * price,
                "reserved_allocations": [],
            })
            subtotal += qty * price
        if not lines: continue
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)
        status = random.choices(
            ["pending_approval", "approved", "invoiced", "dispatched", "completed", "rejected"],
            weights=[3, 3, 3, 3, 6, 1],
        )[0]
        order = {
            "id": new_id("po"),
            "order_no": f"PO-{20000 + i}",
            "type": "primary",
            "distributor_id": dist["id"], "party_id": dist["id"],
            "party_name": dist["name"], "party_type": "Distributor",
            "branch_id": dist.get("branch_id"),
            "lines": lines, "line_items": len(lines),
            "subtotal": round(subtotal, 2), "tax": tax, "total": total,
            "status": "pending_approval",
            "stock_check": [{"sku_id": ln["sku_id"], "sku_code": ln["sku_code"], "requested": ln["qty"], "available": await avail_by_sku(ln["sku_id"]), "ok": True} for ln in lines],
            "credit_check": {"credit_limit": dist.get("credit_limit", 0), "outstanding": dist.get("outstanding", 0), "ok": True},
            "sla": random.choice(["1h", "3h", "5h", "12h"]),
            "placed_on": now_iso(), "created_at": now_iso(), "created_by": "seed@gooil.com",
        }
        await db.primary_orders.insert_one(order)
        orders_made.append((order, status))

    # Progress through workflow for each order
    for order, target_status in orders_made:
        if target_status == "rejected":
            await db.primary_orders.update_one({"id": order["id"]}, {"$set": {"status": "rejected"}})
            continue
        # approve → reserve stock
        updated_lines = []
        for ln in order["lines"]:
            allocs = await reserve_fifo_company(ln["sku_id"], ln["qty"])
            ln["reserved_allocations"] = allocs
            updated_lines.append(ln)
            for a in allocs:
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "reserve", "scope": "company",
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": "available", "to_bucket": "reserved",
                    "reference_type": "primary_order", "reference_id": order["id"],
                    "by_user": "seed@gooil.com",
                    "notes": f"Reserved for {order['order_no']}",
                })
        await db.primary_orders.update_one({"id": order["id"]}, {"$set": {"status": "approved", "lines": updated_lines, "approved_at": now_iso()}})
        if target_status == "approved":
            continue
        # generate invoice
        inv = {
            "id": new_id("inv"),
            "invoice_no": f"INV-{20000 + random.randint(0, 9999)}",
            "order_id": order["id"], "order_no": order["order_no"],
            "type": "primary",
            "distributor_id": order["distributor_id"],
            "party_id": order["distributor_id"], "party_name": order["party_name"],
            "branch_id": order["branch_id"],
            "lines": updated_lines,
            "subtotal": order["subtotal"], "tax": order["tax"], "total": order["total"],
            "paid": 0, "status": "issued",
            "issued_on": now_iso(), "due_on": now_iso(), "created_by": "seed@gooil.com",
        }
        await db.invoices.insert_one(inv)
        await db.primary_orders.update_one({"id": order["id"]}, {"$set": {"status": "invoiced", "invoice_id": inv["id"]}})
        if target_status == "invoiced":
            continue
        # dispatch
        for ln in updated_lines:
            for a in ln["reserved_allocations"]:
                await db.company_inventory.update_one(
                    {"sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                    {"$inc": {"reserved": -a["qty"], "in_transit": a["qty"]}},
                )
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "dispatch_out", "scope": "company",
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": "reserved", "to_bucket": "in_transit",
                    "reference_type": "invoice", "reference_id": inv["id"],
                    "by_user": "seed@gooil.com",
                    "notes": f"Dispatch for {inv['invoice_no']}",
                })
        dispatch = {
            "id": new_id("disp"),
            "dispatch_no": f"DSP-{30000 + random.randint(0, 9999)}",
            "invoice_id": inv["id"], "invoice_no": inv["invoice_no"],
            "order_id": order["id"], "type": "primary",
            "party_name": order["party_name"],
            "distributor_id": order["distributor_id"],
            "lines": updated_lines,
            "vehicle_no": f"LG-{random.randint(100,999)}-{chr(random.randint(65,90))}{chr(random.randint(65,90))}",
            "driver": random.choice(["Musa A.", "Tunde O.", "Ahmed B.", "Femi K."]),
            "lr_no": f"LR{random.randint(100000, 999999)}",
            "transporter": "GO OIL Logistics",
            "route": random.choice(["Lagos → Abuja", "Lagos → Ibadan", "PH → Aba", "Kano → Kaduna"]),
            "distance_km": random.randint(150, 900),
            "dispatch_date": now_iso(), "eta": now_iso(),
            "status": "in_transit",
        }
        await db.dispatches.insert_one(dispatch)
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": "dispatched", "dispatch_id": dispatch["id"]}})
        await db.primary_orders.update_one({"id": order["id"]}, {"$set": {"status": "dispatched"}})
        if target_status == "dispatched":
            continue
        # receive GRN → distributor inventory
        received_lines = []
        for ln in updated_lines:
            for a in ln["reserved_allocations"]:
                await db.company_inventory.update_one(
                    {"sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                    {"$inc": {"in_transit": -a["qty"]}},
                )
                # add to distributor inventory
                existing = await db.distributor_inventory.find_one({"partner_id": order["distributor_id"], "sku_id": ln["sku_id"], "batch_id": a["batch_id"]})
                if existing:
                    await db.distributor_inventory.update_one({"id": existing["id"]}, {"$inc": {"available": a["qty"]}})
                else:
                    await db.distributor_inventory.insert_one({
                        "id": new_id("dinv"),
                        "partner_id": order["distributor_id"], "sku_id": ln["sku_id"],
                        "sku_code": ln["sku_code"], "product_name": ln["product_name"],
                        "pack_size": ln["pack_size"], "batch_id": a["batch_id"],
                        "available": a["qty"], "reserved": 0, "in_transit": 0,
                        "damaged": 0, "returned": 0, "expired": 0,
                    })
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "grn_in", "scope": "distributor",
                    "partner_id": order["distributor_id"],
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": None, "to_bucket": "available",
                    "reference_type": "dispatch", "reference_id": dispatch["id"],
                    "by_user": "seed@gooil.com",
                    "notes": f"GRN receipt from {dispatch['dispatch_no']}",
                })
            received_lines.append({
                "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                "dispatched_qty": ln["qty"], "received_qty": ln["qty"],
                "damaged_qty": 0, "shortage_qty": 0, "excess_qty": 0,
            })
        grn = {
            "id": new_id("grn"),
            "grn_no": f"GRN-{40000 + random.randint(0, 9999)}",
            "dispatch_id": dispatch["id"], "dispatch_no": dispatch["dispatch_no"],
            "type": "primary",
            "distributor_id": order["distributor_id"],
            "received_by": order["party_name"], "received_on": now_iso(),
            "lines": received_lines,
            "condition": "Good", "variance": 0,
            "status": "Accepted",
        }
        await db.grns.insert_one(grn)
        await db.dispatches.update_one({"id": dispatch["id"]}, {"$set": {"status": "delivered", "grn_id": grn["id"]}})
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": "delivered"}})
        await db.primary_orders.update_one({"id": order["id"]}, {"$set": {"status": "completed"}})

    log.info(f"Seeded {len(orders_made)} primary orders + downstream artifacts")

    # ------- STEP 3: Secondary orders (retailer → distributor) -------
    retailers = await db.retailers.find({}, {"_id": 0}).to_list(60)

    async def dist_avail(dist_id, sku_id):
        total = 0
        async for r in db.distributor_inventory.find({"partner_id": dist_id, "sku_id": sku_id}, {"_id": 0}):
            total += int(r.get("available", 0) or 0)
        return total

    async def reserve_fifo_dist(dist_id, sku_id, qty):
        rows = await db.distributor_inventory.find({"partner_id": dist_id, "sku_id": sku_id, "available": {"$gt": 0}}, {"_id": 0}).to_list(50)
        bids = [r["batch_id"] for r in rows]
        bmap = {}
        async for b in db.batches.find({"id": {"$in": bids}}, {"_id": 0}):
            bmap[b["id"]] = b
        rows.sort(key=lambda r: bmap.get(r["batch_id"], {}).get("manufactured_on", ""))
        allocs, need = [], qty
        for r in rows:
            if need <= 0: break
            take = min(r["available"], need)
            if take <= 0: continue
            await db.distributor_inventory.update_one({"id": r["id"]}, {"$inc": {"available": -take, "reserved": take}})
            allocs.append({"batch_id": r["batch_id"], "qty": take})
            need -= take
        return allocs

    sec_orders_made = 0
    for i in range(30):
        ret = random.choice(retailers)
        dist_id = ret.get("distributor_id")
        if not dist_id: continue
        # pick skus the distributor actually has
        dist_skus = await db.distributor_inventory.find({"partner_id": dist_id, "available": {"$gt": 0}}, {"_id": 0}).to_list(30)
        if not dist_skus: continue
        picks = random.sample(dist_skus, k=min(3, len(dist_skus)))
        lines = []
        subtotal = 0
        for row in picks:
            sku = await db.skus.find_one({"id": row["sku_id"]}, {"_id": 0})
            if not sku: continue
            qty = min(random.randint(3, 20), row["available"])
            if qty <= 0: continue
            price = float(sku.get("mrp") or 800)
            lines.append({
                "sku_id": sku["id"], "sku_code": sku["sku_code"],
                "product_name": sku["product_name"], "pack_size": sku["pack_size"],
                "qty": qty, "price": price, "subtotal": qty * price,
                "reserved_allocations": [],
            })
            subtotal += qty * price
        if not lines: continue
        tax = round(subtotal * 0.18, 2)
        total = round(subtotal + tax, 2)
        target = random.choices(
            ["pending_approval", "approved", "invoiced", "dispatched", "completed"],
            weights=[3, 2, 3, 3, 8],
        )[0]
        order = {
            "id": new_id("so"),
            "order_no": f"SO-{40000 + i}",
            "type": "secondary",
            "distributor_id": dist_id, "retailer_id": ret["id"],
            "party_id": ret["id"], "party_name": ret["name"], "party_type": "Retailer",
            "branch_id": ret.get("branch_id"),
            "lines": lines, "line_items": len(lines),
            "subtotal": round(subtotal, 2), "tax": tax, "total": total,
            "status": "pending_approval",
            "stock_check": [{"sku_id": ln["sku_id"], "requested": ln["qty"], "ok": True} for ln in lines],
            "credit_check": {"ok": True},
            "sla": random.choice(["1h", "3h", "6h"]),
            "placed_on": now_iso(), "created_at": now_iso(),
        }
        await db.secondary_orders.insert_one(order)
        # approve
        updated_lines = []
        for ln in lines:
            allocs = await reserve_fifo_dist(dist_id, ln["sku_id"], ln["qty"])
            ln["reserved_allocations"] = allocs
            updated_lines.append(ln)
            for a in allocs:
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "reserve", "scope": "distributor",
                    "partner_id": dist_id,
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": "available", "to_bucket": "reserved",
                    "reference_type": "secondary_order", "reference_id": order["id"],
                    "notes": f"Reserved for {order['order_no']}",
                })
        await db.secondary_orders.update_one({"id": order["id"]}, {"$set": {"status": "approved", "lines": updated_lines}})
        if target == "approved":
            sec_orders_made += 1; continue
        inv = {
            "id": new_id("inv"),
            "invoice_no": f"INV-{50000 + random.randint(0, 9999)}",
            "order_id": order["id"], "order_no": order["order_no"],
            "type": "secondary",
            "distributor_id": dist_id, "retailer_id": ret["id"],
            "party_id": ret["id"], "party_name": ret["name"],
            "branch_id": order["branch_id"], "lines": updated_lines,
            "subtotal": order["subtotal"], "tax": order["tax"], "total": order["total"],
            "paid": 0, "status": "issued",
            "issued_on": now_iso(), "due_on": now_iso(),
        }
        await db.invoices.insert_one(inv)
        await db.secondary_orders.update_one({"id": order["id"]}, {"$set": {"status": "invoiced", "invoice_id": inv["id"]}})
        if target == "invoiced":
            sec_orders_made += 1; continue
        # dispatch → retailer
        for ln in updated_lines:
            for a in ln["reserved_allocations"]:
                await db.distributor_inventory.update_one(
                    {"partner_id": dist_id, "sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                    {"$inc": {"reserved": -a["qty"], "in_transit": a["qty"]}},
                )
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "dispatch_out", "scope": "distributor",
                    "partner_id": dist_id,
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": "reserved", "to_bucket": "in_transit",
                    "reference_type": "invoice", "reference_id": inv["id"],
                    "notes": f"Dispatch to retailer",
                })
        dsp = {
            "id": new_id("disp"),
            "dispatch_no": f"DSP-{50000 + random.randint(0, 9999)}",
            "invoice_id": inv["id"], "invoice_no": inv["invoice_no"],
            "order_id": order["id"], "type": "secondary",
            "party_name": ret["name"],
            "distributor_id": dist_id, "retailer_id": ret["id"],
            "lines": updated_lines,
            "vehicle_no": f"LG-{random.randint(100,999)}-{chr(random.randint(65,90))}{chr(random.randint(65,90))}",
            "driver": random.choice(["Chidi K.", "Ade M.", "Bala N."]),
            "lr_no": f"LR{random.randint(100000, 999999)}",
            "transporter": "Distributor Fleet",
            "route": f"{ret.get('city','Lagos')} local",
            "distance_km": random.randint(5, 60),
            "dispatch_date": now_iso(), "eta": now_iso(),
            "status": "in_transit",
        }
        await db.dispatches.insert_one(dsp)
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": "dispatched", "dispatch_id": dsp["id"]}})
        await db.secondary_orders.update_one({"id": order["id"]}, {"$set": {"status": "dispatched"}})
        if target == "dispatched":
            sec_orders_made += 1; continue
        # receive GRN → retailer inventory
        received_lines = []
        for ln in updated_lines:
            for a in ln["reserved_allocations"]:
                await db.distributor_inventory.update_one(
                    {"partner_id": dist_id, "sku_id": ln["sku_id"], "batch_id": a["batch_id"]},
                    {"$inc": {"in_transit": -a["qty"]}},
                )
                existing = await db.retailer_inventory.find_one({"partner_id": ret["id"], "sku_id": ln["sku_id"], "batch_id": a["batch_id"]})
                if existing:
                    await db.retailer_inventory.update_one({"id": existing["id"]}, {"$inc": {"available": a["qty"]}})
                else:
                    await db.retailer_inventory.insert_one({
                        "id": new_id("rinv"),
                        "partner_id": ret["id"], "sku_id": ln["sku_id"],
                        "sku_code": ln["sku_code"], "product_name": ln["product_name"],
                        "pack_size": ln["pack_size"], "batch_id": a["batch_id"],
                        "available": a["qty"], "reserved": 0, "in_transit": 0,
                        "damaged": 0, "returned": 0, "expired": 0,
                    })
                await db.stock_ledger.insert_one({
                    "id": new_id("led"), "timestamp": now_iso(),
                    "movement": "grn_in", "scope": "retailer",
                    "partner_id": ret["id"],
                    "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                    "batch_id": a["batch_id"], "qty": a["qty"],
                    "from_bucket": None, "to_bucket": "available",
                    "reference_type": "dispatch", "reference_id": dsp["id"],
                    "notes": "Retailer received via GRN",
                })
            received_lines.append({
                "sku_id": ln["sku_id"], "sku_code": ln["sku_code"],
                "dispatched_qty": ln["qty"], "received_qty": ln["qty"],
                "damaged_qty": 0, "shortage_qty": 0, "excess_qty": 0,
            })
        grn = {
            "id": new_id("grn"),
            "grn_no": f"GRN-{60000 + random.randint(0, 9999)}",
            "dispatch_id": dsp["id"], "dispatch_no": dsp["dispatch_no"],
            "type": "secondary",
            "distributor_id": dist_id, "retailer_id": ret["id"],
            "received_by": ret["name"], "received_on": now_iso(),
            "lines": received_lines,
            "condition": "Good", "variance": 0, "status": "Accepted",
        }
        await db.grns.insert_one(grn)
        await db.dispatches.update_one({"id": dsp["id"]}, {"$set": {"status": "delivered", "grn_id": grn["id"]}})
        await db.invoices.update_one({"id": inv["id"]}, {"$set": {"status": "delivered"}})
        await db.secondary_orders.update_one({"id": order["id"]}, {"$set": {"status": "completed"}})
        sec_orders_made += 1

    log.info(f"Seeded {sec_orders_made} secondary orders with retailer inventory chain")
