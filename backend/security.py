"""GO OIL DMS — Security module.

Provides:
  - Rate limiter (slowapi) — used specifically on /auth/login and /auth/register
  - Security headers middleware
  - RBAC role-guard dependency (require_roles)
  - CORS origins parsing from env
  - Startup env validation

Kept intentionally small and dependency-light so it can be reused in Docker/K8s deployments.
"""
from __future__ import annotations
import os
import logging
from typing import Iterable, Callable, Awaitable
from fastapi import Depends, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger("gooil.dms.security")


# ---------- Env validation ----------
class EnvironmentError_(Exception):
    pass


def validate_env() -> dict:
    """Validate required environment variables at startup. Fail fast if missing/weak."""
    errors: list[str] = []
    warnings: list[str] = []

    required = ["MONGO_URL", "DB_NAME", "JWT_SECRET"]
    for k in required:
        if not os.environ.get(k):
            errors.append(f"Missing required env: {k}")

    secret = os.environ.get("JWT_SECRET", "")
    if secret and len(secret) < 32:
        errors.append(f"JWT_SECRET must be at least 32 chars (currently {len(secret)}).")

    admin_pw = os.environ.get("ADMIN_PASSWORD", "")
    if admin_pw and len(admin_pw) < 8:
        warnings.append(f"ADMIN_PASSWORD is only {len(admin_pw)} chars; consider ≥12.")

    cors = os.environ.get("CORS_ORIGINS", "*")
    if cors.strip() == "*":
        warnings.append("CORS_ORIGINS is '*' — safe for dev only. Set explicit origins for production.")

    for w in warnings:
        logger.warning(f"[env] {w}")
    if errors:
        for e in errors:
            logger.error(f"[env] {e}")
        raise EnvironmentError_("; ".join(errors))

    return {"cors": cors, "warnings": warnings}


def parse_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


# ---------- Rate limiter ----------
# key_func: use client IP (respects X-Forwarded-For via slowapi.util.get_remote_address)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # no global default; we opt-in per endpoint
    storage_uri="memory://",
)


# ---------- Security headers ----------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers on every response.

    NOTE: HSTS is disabled here because the app is often served behind a load balancer that
    terminates TLS; enable via env if you own the edge.
    """

    def __init__(self, app, enable_hsts: bool = False):
        super().__init__(app)
        self.enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        if self.enable_hsts:
            headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response


# ---------- RBAC ----------
# Role hierarchy — super_admin implicitly has every role.
ROLE_HIERARCHY = {
    "super_admin": {"super_admin", "company_admin", "regional_manager", "sales_executive",
                    "distributor", "distributor_accountant", "retailer", "customer"},
    "company_admin": {"company_admin", "regional_manager", "sales_executive"},
    "regional_manager": {"regional_manager", "sales_executive"},
    "sales_executive": {"sales_executive"},
    "distributor": {"distributor"},
    "distributor_accountant": {"distributor_accountant"},
    "retailer": {"retailer"},
    "customer": {"customer"},
}


def _has_role(user_role: str, allowed: Iterable[str]) -> bool:
    allowed_set = set(allowed)
    if user_role in allowed_set:
        return True
    granted = ROLE_HIERARCHY.get(user_role, {user_role})
    return bool(granted & allowed_set)


def require_roles(*roles: str):
    """FastAPI dependency factory — allows only listed roles (super_admin always allowed).

    Usage:
      @router.post("/x")
      async def endpoint(user = Depends(require_roles('company_admin', 'regional_manager'))):
          ...
    """
    allowed = set(roles) | {"super_admin"}

    async def _dep(request: Request):
        # We need access to the current user — cannot import server.get_current_user here without
        # circular imports, so we duck-type by inspecting request.state.user (populated by wrapper) or
        # fall back to reading the JWT directly.
        user = getattr(request.state, "user", None)
        if not user:
            # Minimal fallback: reject if not attached
            raise HTTPException(status_code=401, detail="Not authenticated")
        role = user.get("role")
        if not _has_role(role, allowed):
            raise HTTPException(status_code=403, detail=f"Role '{role}' not permitted for this action")
        return user

    return _dep


def role_guard(current_user_dep):
    """Alternative helper — wraps the app's existing get_current_user dependency.

    Because our routers accept an injected user dict via Depends(get_current_user),
    this helper gives us a role-checking version without touching the router signature.

        require_admin = role_guard(get_current_user)('super_admin','company_admin')
    """
    def factory(*roles: str):
        allowed = set(roles) | {"super_admin"}

        async def _dep(user: dict = Depends(current_user_dep)):
            role = user.get("role")
            if not _has_role(role, allowed):
                raise HTTPException(status_code=403,
                                     detail=f"Role '{role}' not permitted for this action")
            return user

        return _dep

    return factory
