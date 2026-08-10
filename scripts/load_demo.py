import asyncio, os, sys
from pathlib import Path
from dotenv import load_dotenv
sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
import dms_seed

async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    raw_db = client[os.environ["DB_NAME"]]
    # remove marker so the (renamed) full demo seed runs
    await raw_db.dms_meta.delete_many({"id": "seed_marker"})
    await dms_seed._seed_dms_full_demo_DISABLED(raw_db)
    # report
    for c in ["dms_products","dms_distributors","dms_retailers","dms_primary_orders",
              "dms_secondary_orders","dms_ebills","dms_retailer_bills","dms_owner_inventory",
              "dms_distributor_inventory","dms_tl_assignments","dms_sp_assignments",
              "dms_rm_assignments","dms_godowns","users"]:
        print(c, await raw_db[c].count_documents({}))

asyncio.run(main())
