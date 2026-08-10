"""
One-shot demo data seeder for the GO OIL DMS (tenant: tnt-dms-oil).

Reuses the (previously disabled) seed helpers in dms_seed.py so the shapes match
exactly what the current dashboards / endpoints read, then adds a realistic
salesperson PUNCH + GPS TRAIL for the Live Tracking feature.

Idempotent: clears DMS business collections (keeps login users) then re-seeds.

Run:  cd /app/backend && python /app/scripts/seed_dms_demo.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app/backend")

from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient
import dms_seed as S

DMS = S.DMS_TENANT_ID

BUSINESS_COLLECTIONS = [
    "dms_distributors", "dms_retailers", "dms_ret_mode", "dms_products", "dms_categories",
    "dms_price_batches", "dms_price_circulars", "dms_owner_inventory", "dms_retailer_prices",
    "dms_primary_orders", "dms_secondary_orders", "dms_secondary_sales", "dms_bills",
    "dms_ebills", "dms_sp_assignments", "dms_tl_assignments", "dms_rm_assignments",
    "dms_terms", "dms_godowns", "dms_godown_inventory", "dms_stock_transfers",
    "dms_punch", "dms_sp_pings", "dms_punch_reopen",
    "dms_primary_ledger", "dms_secondary_ledger",
]


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # 1. Map existing DMS users email -> id
    ids = {}
    async for u in db.users.find({"tenant_id": DMS}, {"_id": 0, "id": 1, "email": 1}):
        ids[u["email"]] = u["id"]
    print(f"[seed] found {len(ids)} DMS users")
    if "distributor1@gooil.com" not in ids:
        print("[seed] ERROR: DMS users not seeded. Start backend first.")
        return

    # 2. Clean business collections (keep users) — idempotent
    for c in BUSINESS_COLLECTIONS:
        await db[c].delete_many({})
    await db.users.update_many(
        {"tenant_id": DMS},
        {"$unset": {"distributor_id": "", "retailer_id": "", "last_gps": "", "last_active_at": ""}},
    )
    print("[seed] cleared business collections")

    # 3. Run the tested seed helpers (shapes match live endpoints)
    await S.ensure_dms_tenant(db)
    await S._seed_settings(db)
    await S._seed_products_and_circular(db)
    dist_ids = await S._seed_distributors_and_retailers(db, ids)
    await S._seed_inventory_and_retailer_prices(db, dist_ids)
    await S._seed_assignments(db, ids)
    await S._seed_sample_terms(db)
    await S._seed_sample_bills(db, ids, dist_ids)
    await S._seed_godowns_with_stock(db)
    print("[seed] core business data seeded")

    # 4. Salesperson PUNCH-IN + GPS TRAIL across Delhi (Live Tracking + multi-day)
    sp = ids.get("salesperson@gooil.com")
    if sp:
        now = datetime.now(timezone.utc)

        def iso(dt):
            return dt.isoformat()

        # Base route: distributor1 -> retailer1 (Karol Bagh) -> retailer2 (Rohini).
        # Passes within 200m of each shop so "visited" registers on the latest day.
        base_route = [
            (28.6139, 77.2090),  # distributor1 (Delhi) — start
            (28.6180, 77.2110),
            (28.6250, 77.2135),
            (28.6350, 77.2150),
            (28.6448, 77.2167),  # retailer1 — Sharma Auto Parts (Karol Bagh)
            (28.6600, 77.1750),
            (28.6850, 77.1350),
            (28.7100, 77.1000),
            (28.7300, 77.0750),
            (28.7495, 77.0567),  # retailer2 — Verma Motors (Rohini)
        ]

        total_pings = 0
        # Seed the last 7 days. Day 0 = today (exact base route so "visited" is clean),
        # older days get a small per-day offset so the routes differ for comparison.
        for day_ago in range(0, 7):
            day_dt = now - timedelta(days=day_ago)
            day = day_dt.strftime("%Y-%m-%d")
            # per-day drift (0 for today)
            off_lat = 0.0 if day_ago == 0 else (0.004 * day_ago * (1 if day_ago % 2 else -1))
            off_lng = 0.0 if day_ago == 0 else (0.006 * day_ago * (-1 if day_ago % 2 else 1))
            route = [(lat + off_lat, lng + off_lng) for (lat, lng) in base_route]
            n = len(route)

            in_at = day_dt.replace(hour=9, minute=0, second=0, microsecond=0)
            out_at = None if day_ago == 0 else day_dt.replace(hour=17, minute=30, second=0, microsecond=0)
            end_ping = now if day_ago == 0 else in_at + timedelta(hours=8, minutes=30)

            await db.dms_punch.insert_one({
                "id": S._nid("pn"),
                "tenant_id": DMS,
                "salesperson_id": sp,
                "date": day,
                "in_at": iso(in_at),
                "out_at": iso(out_at) if out_at else None,
                "gps_in": {"lat": route[0][0], "lng": route[0][1]},
                "gps_out": ({"lat": route[-1][0], "lng": route[-1][1]} if out_at else None),
            })

            pings = []
            for i, (lat, lng) in enumerate(route):
                t = in_at + timedelta(seconds=int((end_ping - in_at).total_seconds() * i / max(1, n - 1)))
                pings.append({
                    "id": S._nid("png"),
                    "tenant_id": DMS,
                    "salesperson_id": sp,
                    "lat": float(lat),
                    "lng": float(lng),
                    "accuracy": 12.0,
                    "speed": 18.0,
                    "date": day,
                    "created_at": iso(t),
                })
            await db.dms_sp_pings.insert_many(pings)
            total_pings += len(pings)

        # mark salesperson live at last point of today's route
        last = base_route[-1]
        await db.users.update_one({"id": sp}, {"$set": {
            "last_active_at": iso(now),
            "last_gps": {"lat": last[0], "lng": last[1], "at": iso(now)},
        }})
        print(f"[seed] salesperson punch + {total_pings} GPS pings seeded across 7 days")
    else:
        print("[seed] WARN: salesperson user not found — skipped tracking seed")

    # 5. Report counts
    print("\n[seed] final counts:")
    for c in ["dms_distributors", "dms_retailers", "dms_products", "dms_price_batches",
              "dms_bills", "dms_primary_orders", "dms_sp_pings", "dms_punch", "dms_godowns"]:
        try:
            print(f"  {c}: {await db[c].count_documents({})}")
        except Exception as e:
            print(f"  {c}: ERR {e}")
    print("\n[seed] DONE")


if __name__ == "__main__":
    asyncio.run(main())
