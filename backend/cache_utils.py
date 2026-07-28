"""In-memory TTL cache for expensive read-only endpoints.

Designed for a single-worker Uvicorn deployment (matches supervisor config: --workers 1).
For horizontal scale, swap for Redis without changing call sites.
"""
from __future__ import annotations
import time
import asyncio
import functools
import hashlib
import json
from typing import Any, Callable, Awaitable


class TTLCache:
    def __init__(self, default_ttl: float = 30.0, max_entries: int = 512):
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._default_ttl = default_ttl
        self._max_entries = max_entries

    def _key(self, ns: str, args: tuple, kwargs: dict) -> str:
        try:
            raw = json.dumps({"a": list(args), "k": kwargs}, default=str, sort_keys=True)
        except Exception:
            raw = repr((args, kwargs))
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"{ns}::{digest}"

    async def get(self, key: str) -> Any | None:
        now = time.monotonic()
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            exp, val = entry
            if exp < now:
                self._store.pop(key, None)
                return None
            return val

    async def set(self, key: str, val: Any, ttl: float | None = None) -> None:
        exp = time.monotonic() + (ttl if ttl is not None else self._default_ttl)
        async with self._lock:
            if len(self._store) >= self._max_entries:
                # naive eviction: drop expired first, then oldest
                now = time.monotonic()
                expired = [k for k, (e, _) in self._store.items() if e < now]
                for k in expired[:64]:
                    self._store.pop(k, None)
                if len(self._store) >= self._max_entries:
                    oldest = sorted(self._store.items(), key=lambda kv: kv[1][0])[:64]
                    for k, _ in oldest:
                        self._store.pop(k, None)
            self._store[key] = (exp, val)

    async def clear(self, ns_prefix: str | None = None) -> None:
        async with self._lock:
            if ns_prefix is None:
                self._store.clear()
            else:
                for k in list(self._store.keys()):
                    if k.startswith(ns_prefix + "::"):
                        self._store.pop(k, None)


# Shared instance for analytics endpoints
analytics_cache = TTLCache(default_ttl=30.0, max_entries=256)


def ttl_cache(namespace: str, ttl: float = 30.0, cache: TTLCache | None = None):
    """Decorator for async functions returning JSON-serialisable results.

    NOTE: request/user/db positional args are hashed via repr(), so user-specific data
    should be captured through kwargs or the user's role/id explicitly.

    Tenant-aware: the current tenant_id (from tenancy.current_tenant_id contextvar)
    is included in the cache key so tenant A's cached response never leaks to tenant B.
    """
    _cache = cache or analytics_cache

    def deco(fn: Callable[..., Awaitable[Any]]):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            # ignore FastAPI's user dict from key to avoid per-user cache blowup
            safe_kwargs = {k: v for k, v in kwargs.items() if k != "user"}
            # include tenant scope in namespace to guarantee isolation
            try:
                from tenancy import current_tenant_id  # local import to avoid cycles
                tid = current_tenant_id.get() or "_platform"
            except Exception:
                tid = "_unknown"
            key = _cache._key(f"{namespace}:{tid}", args, safe_kwargs)
            cached = await _cache.get(key)
            if cached is not None:
                return cached
            result = await fn(*args, **kwargs)
            await _cache.set(key, result, ttl)
            return result
        return wrapper
    return deco
