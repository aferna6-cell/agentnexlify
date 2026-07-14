"""Appointment reminders — cron trigger + per-tenant settings toggle.

Reminder scheduling happens inside ``backend.services.booking.create_appointment``
(fired right after a booking confirms). This router exposes the two
operational surfaces on top of that:
  - ``POST /run`` — admin-secret-protected. Called by the scheduled job /
    cron to send everything currently due. Same auth pattern as
    ``backend/routers/admin_health.py`` (X-Api-Secret header,
    ``hmac.compare_digest``).
  - ``GET/PUT /settings/{tenant_id}`` — JWT-protected dashboard toggle for
    ``tenants.appointment_reminders_enabled`` (migration 165).
"""

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services.appointment_reminders import send_due_reminders

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/appointments/reminders", tags=["appointment-reminders"])


def _admin_secret() -> str:
    admin_secret = getattr(settings, "admin_api_secret_key", "")
    if isinstance(admin_secret, str) and admin_secret:
        return admin_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""


def _verify_admin_secret(x_api_secret: str | None) -> None:
    """Verify caller has the platform admin secret. Raises 401 on failure."""
    admin_secret = _admin_secret()
    if (
        not admin_secret
        or not x_api_secret
        or not hmac.compare_digest(x_api_secret, admin_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid admin secret")


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


class ReminderSettingsResponse(BaseModel):
    tenant_id: str
    enabled: bool


class ReminderSettingsUpdateRequest(BaseModel):
    enabled: bool


@router.post("/run")
@limiter.limit("10/minute")
async def run_due_reminders(request: Request, x_api_secret: str | None = Header(None)):
    """Send every appointment reminder whose scheduled_for time has arrived.

    Cron entrypoint — not tenant-scoped, processes every due reminder across
    all tenants in one call. Protected by the platform admin secret.
    """
    _verify_admin_secret(x_api_secret)
    try:
        counts = await send_due_reminders()
    except Exception:
        logger.exception("run_due_reminders: send_due_reminders failed")
        raise HTTPException(status_code=500, detail="Failed to run appointment reminders")
    return counts


@router.get("/settings/{tenant_id}", response_model=ReminderSettingsResponse)
async def get_reminder_settings(
    tenant_id: str, claims: dict = Depends(_get_current_tenant)
):
    """Get whether appointment reminders are enabled for this tenant."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    try:
        result = (
            db.table("tenants")
            .select("appointment_reminders_enabled")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception(
            "get_reminder_settings: query failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to load reminder settings")

    enabled = True
    if result.data:
        value = result.data[0].get("appointment_reminders_enabled")
        enabled = value is not False

    return ReminderSettingsResponse(tenant_id=tenant_id, enabled=enabled)


@router.put("/settings/{tenant_id}", response_model=ReminderSettingsResponse)
async def update_reminder_settings(
    tenant_id: str,
    req: ReminderSettingsUpdateRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Enable or disable appointment reminders for this tenant."""
    _verify_tenant(claims, tenant_id)
    db = get_service_supabase()
    try:
        db.table("tenants").update(
            {"appointment_reminders_enabled": req.enabled}
        ).eq("id", tenant_id).execute()
    except Exception:
        logger.exception(
            "update_reminder_settings: update failed for tenant %s", tenant_id
        )
        raise HTTPException(status_code=500, detail="Failed to update reminder settings")

    return ReminderSettingsResponse(tenant_id=tenant_id, enabled=req.enabled)
