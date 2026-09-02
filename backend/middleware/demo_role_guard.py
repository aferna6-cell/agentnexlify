"""Central demo-role mutation guard (GH #669).

Demo JWTs (`role=demo` from POST /api/v1/auth/demo-login) may explore the
sandbox but must not hit money/destructive/general mutating dashboard APIs.
Rather than sprinkling ``Depends(block_demo_role)`` across ~100 routers, this
ASGI middleware blocks POST/PUT/PATCH/DELETE when the verified Bearer token
has ``role == "demo"``, unless the path matches an explicit allowlist
(auth flows, inbound webhooks, public widget/book surfaces).

Router-level ``block_demo_role`` on billing/phone/account-deletion stays as
belt-and-suspenders for money surfaces that share the ``/api/v1/auth`` prefix
with the allowlist.
"""

import logging

from jose import JWTError, jwt
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from backend.services.auth_service import _JWT_ALGORITHM, _jwt_secret

logger = logging.getLogger(__name__)

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Paths demo tenants may still mutate (or that are public ingress). Keep
# prefixes trailing-slash-safe via startswith checks below.
DEMO_MUTATION_ALLOWLIST_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth",  # demo-login, password reset, google oauth; money sub-routes still Depends-guarded
    "/api/v1/webhooks",
    "/api/v1/twilio",
    "/api/v1/widget",
    "/api/widget",
    "/api/v1/widget-health",
    "/api/v1/forms/public",
    "/api/v1/book",
)

DEMO_BLOCK_DETAIL = "Not available in demo mode — sign up to use this feature"


def path_is_demo_mutation_allowed(path: str) -> bool:
    """True when a mutating request may proceed even for role=demo."""
    for prefix in DEMO_MUTATION_ALLOWLIST_PREFIXES:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            return True
    return False


def _demo_role_from_authorization(authorization: str) -> bool:
    """Return True only when a verified Bearer JWT has role=demo.

    Missing/invalid/expired tokens return False so the route's own auth
    dependency remains the source of 401 responses.
    """
    if not authorization.startswith("Bearer "):
        return False
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return False
    try:
        claims = jwt.decode(token, _jwt_secret(), algorithms=[_JWT_ALGORITHM])
    except JWTError:
        return False
    return claims.get("role") == "demo"


class DemoRoleBlockMiddleware:
    """ASGI middleware: 403 demo-role mutations outside the allowlist."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        if method not in MUTATING_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "") or ""
        if path_is_demo_mutation_allowed(path):
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        authorization = headers.get("authorization", "")
        if not _demo_role_from_authorization(authorization):
            await self.app(scope, receive, send)
            return

        logger.info("demo-role mutation blocked method=%s path=%s", method, path)
        response = JSONResponse(
            status_code=403,
            content={"detail": DEMO_BLOCK_DETAIL},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
            },
        )
        await response(scope, receive, send)
