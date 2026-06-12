"""Public live-demo login — drops a visitor into the demo sandbox tenant.

POST /api/v1/auth/demo-login issues a short-lived JWT (role="demo") for the
tenant flagged ``is_demo``. No credentials involved; the token grants the
normal tenant surface EXCEPT routers guarded by ``block_demo_role``
(billing, phone provisioning, account deletion), and all outbound sends
no-op via ``demo_guard``. Demo data resets nightly.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
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


class DemoLoginResponse(BaseModel):
    tenant_id: str
    token: str
    business_name: str
    plan: str
    demo: bool = True


@router.post("/demo-login", response_model=DemoLoginResponse)
@limiter.limit("10/minute")
async def demo_login(request: Request):
    """Issue a 2-hour demo-role session for the live-demo sandbox tenant."""
    db = get_service_supabase()
    try:
        result = (
            db.table("tenants")
            .select("id, business_name, plan, business_type")
            .eq("is_demo", True)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("demo-login: tenant lookup failed")
        raise HTTPException(status_code=503, detail="Demo temporarily unavailable")

    if not result.data:
        raise HTTPException(status_code=404, detail="Demo is not set up yet")

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
        "business_type": tenant.get("business_type") or "plumbing",
        "exp": datetime.now(timezone.utc) + timedelta(hours=_DEMO_TOKEN_HOURS),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm=_JWT_ALGORITHM)

    # Conversion analytics: count demo sessions/day. Swallows errors.
    log_activity(
        tenant_id=tenant_id,
        activity_type="demo_login",
        description="Public live-demo session started",
    )

    return DemoLoginResponse(
        tenant_id=tenant_id,
        token=token,
        business_name=tenant.get("business_name") or "Demo Business",
        plan=tenant.get("plan") or "professional",
    )
