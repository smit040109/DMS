"""One-off purge: remove ALL demo business data but KEEP all login accounts.

Run:  python /app/backend/purge_demo_data.py
"""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

TENANT = "tnt-dms-oil"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_env():
    env = {}
    p = Path(__file__).with_name(".env")
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


BUSINESS_COLLECTIONS = [
    "dms_categories", "dms_products", "dms_price_batches", "dms_price_circulars",
    "dms_owner_inventory", "dms_distributor_inventory", "dms_stock_ledger",
    "dms_distributors", "dms_retailers", "dms_retailer_prices", "dms_ret_mode",
    "dms_dist_visibility", "dms_retailer_visibility",
    "dms_primary_orders", "dms_secondary_orders", "dms_ebills", "dms_retailer_bills",
    "dms_primary_ledger", "dms_secondary_ledger", "dms_attachments", "dms_pending",
    "dms_notifications",
    "dms_tl_assignments", "dms_sp_assignments", "dms_rm_assignments",
    "dms_punch", "dms_gps_pings", "dms_visits",
    "dms_coupons", "dms_coupon_batches", "dms_coupon_fraud", "dms_coupon_fraud_attempts",
    "dms_v2_coupon_batches", "dms_v2_coupons",
    "dms_v2_retailer_wallets", "dms_v2_wallet_transactions",
    "dms_v2_redemption_requests", "dms_v2_credit_notes",
    "dms_v2_dispatch_advices", "dms_v2_coupon_audit_log",
    "dms_v2_coupon_fraud_attempts", "dms_v2_meta", "dms_v2_boxes",
    "dms_expenses",
    "dms_bank_accounts", "dms_bank_transactions",
    "dms_cash_register", "dms_cheques",
    "dms_loan_accounts", "dms_loan_transactions",
    "dms_godowns", "dms_godown_inventory", "dms_stock_transfers",
    "dms_retailer_pending",
    "dms_documents",
    "dms_access_logs",
    "dms_boxes",  # legacy, if any
]


async def main():
    env = _load_env()
    mongo = env.get("MONGO_URL") or os.environ.get("MONGO_URL")
    dbname = env.get("DB_NAME") or os.environ.get("DB_NAME")
    if not mongo or not dbname:
        raise SystemExit("MONGO_URL / DB_NAME not found in backend/.env")

    client = AsyncIOMotorClient(mongo)
    db = client[dbname]

    print(f"Connected to DB={dbname}")
    users_before = await db.users.count_documents({"tenant_id": TENANT})
    print(f"Users (tenant) before: {users_before}")

    deleted = {}
    for coll in BUSINESS_COLLECTIONS:
        try:
            r = await db[coll].delete_many({})
            if r.deleted_count:
                deleted[coll] = r.deleted_count
        except Exception as e:
            print(f"  ! {coll}: {e}")

    # Clean settings → fresh default (single global doc)
    await db.dms_settings.delete_many({})
    await db.dms_settings.insert_one({
        "id": "global", "tenant_id": TENANT,
        "gst_pct": 0.0, "company_name": "GO OIL Lubricants",
        "retailer_scan_enabled": False,
        "created_at": _now(), "updated_at": _now(),
    })

    # dms_meta: keep only the seed_marker, drop counters (box/coupon numbering resets)
    await db.dms_meta.delete_many({"id": {"$ne": "seed_marker"}})

    # KEEP all users, but clear dangling links to deleted distributor/retailer records
    ur = await db.users.update_many(
        {"tenant_id": TENANT},
        {"$set": {"distributor_id": None, "retailer_id": None}},
    )

    users_after = await db.users.count_documents({"tenant_id": TENANT})

    print("\n=== PURGE COMPLETE ===")
    print("Collections cleared:")
    for k, v in sorted(deleted.items()):
        print(f"   {k}: {v}")
    print(f"User links cleared: {ur.modified_count}")
    print(f"Users (tenant) after: {users_after}  (login accounts preserved)")
    print("Settings reset to clean default (GST 0%, retailer scan OFF).")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
