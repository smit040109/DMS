"""
VayuERP — Multi-tenancy foundation.

Provides:
  * `current_tenant_id` — request-scoped contextvar (set by middleware from JWT).
  * `TenantScopedDatabase` / `TenantScopedCollection` — motor wrappers that
    auto-inject `{"tenant_id": <tid>}` on every read/write/aggregation.
  * `TENANT_EXEMPT_COLLECTIONS` — platform-level collections that must NOT
    be filtered (e.g. `tenants`, `platform_users`, `platform_settings`).
  * Helpers to switch tenant context in background jobs / super-admin queries.
  * Migration helper `backfill_tenant_id(raw_db, tenant_id, exempt)`.

Design goal: keep the *entire* existing GO OIL codebase untouched, and get
full tenant isolation by just wrapping `db` once at bootstrap.

Future switch to database-per-tenant: replace `TenantScopedDatabase` with a
factory that returns `client[f"tenant_{tid}"]` — router code stays identical.
"""
from __future__ import annotations

import copy
import logging
from contextvars import ContextVar
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("vayuerp.tenancy")

# ---------- Contextvars -------------------------------------------------
# `current_tenant_id`   : the tenant scope for the active request
# `bypass_tenant_scope` : set True by super-admin/platform-owner paths that
#                         must query ACROSS tenants (still explicit — never
#                         bleeds between requests).
current_tenant_id: ContextVar[Optional[str]] = ContextVar("current_tenant_id", default=None)
bypass_tenant_scope: ContextVar[bool] = ContextVar("bypass_tenant_scope", default=False)

# Sentinel — the default tenant that GO OIL data is migrated into.
DEFAULT_TENANT_ID = "tnt-gooil"
DEFAULT_TENANT_SLUG = "gooil"

# Collections that are PLATFORM-level and must never be tenant-filtered.
TENANT_EXEMPT_COLLECTIONS = {
    "tenants",
    "platform_users",
    "platform_settings",
    "platform_audit_log",
    "platform_announcements",
    "platform_feature_flags",
    "subscriptions",          # subscription rows are tenant-owned but managed by platform owner
    "subscription_plans",
    "platform_invoices",
    "platform_payments",
    "platform_usage",
    "platform_events",
    "modules_catalog",
    "api_keys",               # api_keys ARE tenant-owned but we filter manually
    "webhooks",
    "webhook_deliveries",
    "backups",
    "tenant_migrations",
}

# Special: some collections ARE tenant-owned but the tenant_id column stores
# the OWNER tenant explicitly and reads by super-admin need to bypass.
# For now, subscriptions/api_keys/webhooks/backups keep their own tenant_id
# but are exempt from the auto-filter (queries pass tenant_id manually).


# ---------- Small helpers -----------------------------------------------
def _merge_tenant_filter(filter_: Any, tid: Optional[str]) -> Dict[str, Any]:
    """Return a NEW filter dict that includes `tenant_id`.

    * If bypass is active or tid is None, returns filter_ unchanged.
    * If filter_ already targets tenant_id, we DO NOT override (super-admin
      code paths need to force a specific tenant).
    """
    if bypass_tenant_scope.get():
        return filter_ if isinstance(filter_, dict) else (filter_ or {})
    if tid is None:
        return filter_ if isinstance(filter_, dict) else (filter_ or {})
    if not isinstance(filter_, dict):
        return {"tenant_id": tid}
    if "tenant_id" in filter_:
        return filter_
    return {**filter_, "tenant_id": tid}


def _stamp_tenant(doc: Dict[str, Any], tid: Optional[str]) -> Dict[str, Any]:
    if tid is None or bypass_tenant_scope.get():
        return doc
    if "tenant_id" not in doc:
        doc["tenant_id"] = tid
    return doc


def _tenant_match_stage(tid: Optional[str]) -> Optional[Dict[str, Any]]:
    if tid is None or bypass_tenant_scope.get():
        return None
    return {"$match": {"tenant_id": tid}}


# ---------- Tenant-scoped collection wrapper ----------------------------
class TenantScopedCollection:
    """Minimal proxy over motor's AsyncIOMotorCollection that auto-scopes
    every operation to the current tenant. Only the methods currently used
    by the codebase are wrapped explicitly; every other attribute falls
    through to the raw collection.

    IMPORTANT: `find` returns the raw motor Cursor with tenant filter applied
    at call site, so `.to_list`, `.sort`, etc. all continue to work.
    """

    __slots__ = ("_raw", "_name", "_exempt")

    def __init__(self, raw_collection: Any, name: str, exempt: bool):
        self._raw = raw_collection
        self._name = name
        self._exempt = exempt

    # -- internal helpers -------------------------------------------------
    def _tid(self) -> Optional[str]:
        if self._exempt:
            return None
        return current_tenant_id.get()

    def _f(self, filter_: Any = None) -> Dict[str, Any]:
        return _merge_tenant_filter(filter_ or {}, self._tid())

    # -- read -------------------------------------------------------------
    def find(self, filter_: Any = None, *args, **kwargs):
        return self._raw.find(self._f(filter_), *args, **kwargs)

    async def find_one(self, filter_: Any = None, *args, **kwargs):
        return await self._raw.find_one(self._f(filter_), *args, **kwargs)

    async def count_documents(self, filter_: Any = None, **kwargs):
        return await self._raw.count_documents(self._f(filter_), **kwargs)

    async def distinct(self, key: str, filter_: Any = None, **kwargs):
        return await self._raw.distinct(key, self._f(filter_), **kwargs)

    def aggregate(self, pipeline: List[Dict[str, Any]], *args, **kwargs):
        match = _tenant_match_stage(self._tid() if not self._exempt else None)
        if match is not None:
            pipeline = [match, *pipeline]
        return self._raw.aggregate(pipeline, *args, **kwargs)

    # -- write ------------------------------------------------------------
    async def insert_one(self, document: Dict[str, Any], **kwargs):
        _stamp_tenant(document, self._tid())
        return await self._raw.insert_one(document, **kwargs)

    async def insert_many(self, documents: Iterable[Dict[str, Any]], **kwargs):
        tid = self._tid()
        stamped = [_stamp_tenant(d, tid) for d in documents]
        return await self._raw.insert_many(stamped, **kwargs)

    async def update_one(self, filter_: Any, update: Any, **kwargs):
        # For upsert, ensure the new doc receives tenant_id.
        if kwargs.get("upsert") and self._tid() is not None:
            update = _inject_tenant_into_setoninsert(update, self._tid())
        return await self._raw.update_one(self._f(filter_), update, **kwargs)

    async def update_many(self, filter_: Any, update: Any, **kwargs):
        if kwargs.get("upsert") and self._tid() is not None:
            update = _inject_tenant_into_setoninsert(update, self._tid())
        return await self._raw.update_many(self._f(filter_), update, **kwargs)

    async def delete_one(self, filter_: Any, **kwargs):
        return await self._raw.delete_one(self._f(filter_), **kwargs)

    async def delete_many(self, filter_: Any, **kwargs):
        return await self._raw.delete_many(self._f(filter_), **kwargs)

    async def replace_one(self, filter_: Any, replacement: Dict[str, Any], **kwargs):
        _stamp_tenant(replacement, self._tid())
        return await self._raw.replace_one(self._f(filter_), replacement, **kwargs)

    async def find_one_and_update(self, filter_: Any, update: Any, **kwargs):
        return await self._raw.find_one_and_update(self._f(filter_), update, **kwargs)

    # -- index / admin (pass-through) -------------------------------------
    async def create_index(self, *args, **kwargs):
        return await self._raw.create_index(*args, **kwargs)

    async def create_indexes(self, *args, **kwargs):
        return await self._raw.create_indexes(*args, **kwargs)

    async def drop(self, *args, **kwargs):
        return await self._raw.drop(*args, **kwargs)

    # -- unknown -> passthrough ------------------------------------------
    def __getattr__(self, item):
        return getattr(self._raw, item)


def _inject_tenant_into_setoninsert(update: Any, tid: str) -> Any:
    """Ensure upsert operations stamp tenant_id on the newly inserted doc.

    Prefers `$setOnInsert.tenant_id`. If $set already includes tenant_id we
    leave the caller's intent alone. Only mutates a shallow copy.
    """
    if not isinstance(update, dict):
        return update
    up = copy.copy(update)
    setter = dict(up.get("$setOnInsert") or {})
    if "tenant_id" not in setter and "tenant_id" not in (up.get("$set") or {}):
        setter["tenant_id"] = tid
        up["$setOnInsert"] = setter
    return up


# ---------- Tenant-scoped database wrapper ------------------------------
class TenantScopedDatabase:
    """Wraps AsyncIOMotorDatabase. `db[name]` returns a `TenantScopedCollection`."""

    __slots__ = ("_raw", "_exempt")

    def __init__(self, raw_db: Any, exempt: Optional[Iterable[str]] = None):
        self._raw = raw_db
        self._exempt = set(exempt or TENANT_EXEMPT_COLLECTIONS)

    # dict-style access mirrors motor
    def __getitem__(self, name: str) -> TenantScopedCollection:
        return TenantScopedCollection(self._raw[name], name, name in self._exempt)

    def __getattr__(self, name: str):
        """Route attribute-style access (`db.branches`) through the tenant
        wrapper too. Only fall through to raw for things that aren't valid
        collection names (starting with underscore or matching known motor
        methods).
        """
        # motor DB methods that must pass through raw
        if name.startswith("_") or name in {
            "command", "list_collection_names", "list_collections",
            "create_collection", "drop_collection", "with_options",
            "client", "name", "codec_options", "read_preference",
            "read_concern", "write_concern",
        }:
            return getattr(self._raw, name)
        # otherwise treat as collection name
        return self[name]

    @property
    def raw(self):
        return self._raw

    # explicit raw-collection accessor for platform paths that need to bypass
    def raw_collection(self, name: str):
        return self._raw[name]


# ---------- Context managers --------------------------------------------
class scope_tenant:
    """`async with scope_tenant("tnt-abc"): ...` — temporarily sets the
    current tenant. Used for background jobs and platform-owner code paths
    that need to run something on behalf of one specific tenant.
    """

    def __init__(self, tenant_id: Optional[str]):
        self._new = tenant_id
        self._tok = None

    def __enter__(self):
        self._tok = current_tenant_id.set(self._new)
        return self

    def __exit__(self, *exc):
        current_tenant_id.reset(self._tok)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *exc):
        return self.__exit__(*exc)


class bypass_scope:
    """`with bypass_scope(): ...` — read/write across all tenants.

    ONLY use inside platform_owner-authenticated endpoints or migrations.
    """

    def __init__(self):
        self._tok = None

    def __enter__(self):
        self._tok = bypass_tenant_scope.set(True)
        return self

    def __exit__(self, *exc):
        bypass_tenant_scope.reset(self._tok)


# ---------- Migration: backfill tenant_id -------------------------------
async def backfill_tenant_id(raw_db, tenant_id: str, exempt: Iterable[str]) -> Dict[str, int]:
    """One-time (idempotent) migration: stamp `tenant_id = <tenant_id>` on
    every document across every collection that is missing one.

    Skips collections in `exempt` (platform-level) and skips system.* colls.
    Returns a report `{collection: updated_count}`.
    """
    exempt_set = set(exempt or [])
    report: Dict[str, int] = {}
    names = await raw_db.list_collection_names()
    for coll_name in names:
        if coll_name.startswith("system."):
            continue
        if coll_name in exempt_set:
            continue
        res = await raw_db[coll_name].update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {"tenant_id": tenant_id}},
        )
        if res.modified_count:
            report[coll_name] = res.modified_count
    return report


async def ensure_tenant_indexes(raw_db, exempt: Iterable[str]) -> List[str]:
    """Create a `tenant_id` index on every tenant-owned collection.

    Returns list of collections indexed. Safe / idempotent.
    """
    exempt_set = set(exempt or [])
    created: List[str] = []
    names = await raw_db.list_collection_names()
    for coll_name in names:
        if coll_name.startswith("system.") or coll_name in exempt_set:
            continue
        try:
            await raw_db[coll_name].create_index("tenant_id")
            created.append(coll_name)
        except Exception as e:
            logger.warning(f"tenant index failed for {coll_name}: {e}")
    return created
