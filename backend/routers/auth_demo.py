"""Public live-demo login — drops a visitor into the demo sandbox tenant.

POST /api/v1/auth/demo-login issues a short-lived JWT (role="demo") for the
tenant flagged ``is_demo``. No credentials involved.

Demo JWTs can read the tenant surface and mutate allowlisted ingress
(auth / widget / webhooks / public book). All other POST/PUT/PATCH/DELETE
calls are blocked centrally by ``DemoRoleBlockMiddleware`` (GH #669). Money
and destructive routers under allowlisted prefixes still carry
``Depends(block_demo_role)`` as belt-and-suspenders. Outbound sends no-op
via ``demo_guard``. Demo data resets nightly.

Optional query param:
  vertical — one of "plumbing", "salon", "financial_services".
  Absent or unrecognised value defaults to "plumbing".
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from jose import jwt
from pydantic import BaseModel

from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.routers.auth import _JWT_ALGORITHM, _jwt_secret
from backend.services.activity import log_activity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth-demo"])

# Demo sessions are short — visitors explore, they don't live here.
_DEMO_TOKEN_HOURS = 2

# Valid vertical slugs.  Pattern used for validation.
_VERTICAL_RE = re.compile(r"^(plumbing|salon|financial_services)$")
_DEFAULT_VERTICAL = "plumbing"


class DemoLoginResponse(BaseModel):
    tenant_id: str
    token: str
    business_name: str
    plan: str
    demo: bool = True


@router.post("/demo-login", response_model=DemoLoginResponse)
@limiter.limit("10/minute")
async def demo_login(
    request: Request,
    vertical: str = Query(default=_DEFAULT_VERTICAL, description="Demo vertical slug"),
):
    """Issue a 2-hour demo-role session for the requested vertical sandbox tenant.

    If ``vertical`` is absent or does not match a known slug, falls back to
    the plumbing demo.
    """
    # Validate + normalise vertical
    if not _VERTICAL_RE.match(vertical):
        logger.info(
            "demo-login: unknown vertical=%r, falling back to %s", vertical, _DEFAULT_VERTICAL
        )
        vertical = _DEFAULT_VERTICAL

    db = get_service_supabase()

    # Look up the demo tenant for the requested vertical via its owner_email.
    # owner_email pattern: demo-{vertical}@agentnexlify-demo.local
    owner_email = f"demo-{vertical}@agentnexlify-demo.local"
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, plan, business_type")
            .eq("is_demo", True)
            .eq("owner_email", owner_email)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("demo-login: tenant lookup failed for vertical=%s", vertical)
        raise HTTPException(status_code=503, detail="Demo temporarily unavailable")

    if not result.data:
        # Vertical not seeded yet — fall back to any is_demo tenant
        logger.warning(
            "demo-login: no demo tenant found for vertical=%s (email=%s), "
            "falling back to first is_demo tenant",
            vertical, owner_email,
        )
        try:
            fallback = (
                db.table("tenants")
                .select("id, business_name, plan, business_type")
                .eq("is_demo", True)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.exception("demo-login: fallback tenant lookup failed")
            raise HTTPException(status_code=503, detail="Demo temporarily unavailable")

        if not fallback.data:
            raise HTTPException(status_code=404, detail="Demo is not set up yet")

        result = fallback

    tenant = result.data[0]
    tenant_id = str(tenant["id"])
    payload = {
        "tenant_id": tenant_id,
        "sub": tenant_id,
        "email": "demo@agentnexlify.com",
        "plan": tenant.get("plan") or "professional",
        "business_name": tenant.get("business_name") or "Demo Business",
        "role": "demo",
        "is_team_member": False,
        "business_type": tenant.get("business_type") or vertical,
        "exp": datetime.now(timezone.utc) + timedelta(hours=_DEMO_TOKEN_HOURS),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)

    # Conversion analytics: count demo sessions/day. Swallows errors.
    log_activity(
        tenant_id=tenant_id,
        activity_type="demo_login",
        description=f"Public live-demo session started (vertical={vertical})",
    )

    return DemoLoginResponse(
        tenant_id=tenant_id,
        token=token,
        business_name=tenant.get("business_name") or "Demo Business",
        plan=tenant.get("plan") or "professional",
    )
