"""Voice phone routing + plan gating helpers.

Extracted from backend/routers/calls.py (god-file split, audit 2026-07-22
H2). Pure lookup/plan logic shared by the Twilio voice webhooks: which
tenant owns the called line, whether that tenant gets the live AI loop,
and lead find-or-create for callers. Underscore names kept - existing
callers and tests import them as-is (same convention as voice_twiml.py
and voice_call_summary.py).
"""

import logging

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)

# Live AI answering is an agent_os feature (full platform plan, $99.99/mo).
# Grandfathered professional/enterprise contracts are also included.
# Lower tiers (chatbot, free) get voicemail mode (recording -> transcription
# -> recovery draft) UNLESS the $49.99/mo voice add-on subscription is active
# (tenants.voice_addon_active, migration 194 — set by the Stripe webhook).
# See CLAUDE.md plan names + docs/dev-knowledge/schema-log.md.
_AI_VOICE_PLANS = {"agent_os", "agent_os_managed", "professional", "enterprise"}


def _ai_voice_mode(tenant: dict) -> bool:
    """True when this tenant's calls get the live AI loop instead of voicemail."""
    return bool(tenant.get("voice_ai_enabled")) and (
        (tenant.get("plan") or "free") in _AI_VOICE_PLANS
        or bool(tenant.get("voice_addon_active"))
    )


def _find_or_create_lead(db, tenant_id: str, caller: str, note: str) -> str | None:
    """Find lead by caller phone or create one. None on failure (never raises)."""
    try:
        existing = (
            db.table("leads")
            .select("id")
            .eq("client_id", tenant_id)
            .eq("phone", caller)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]["id"]
        created = (
            db.table("leads")
            .insert(
                {
                    "client_id": tenant_id,
                    "phone": caller,
                    "status": "new",
                    "areas_of_interest": note,
                }
            )
            .execute()
        )
        return created.data[0]["id"] if created.data else None
    except Exception:
        logger.exception(
            "Failed to find/create lead for caller tenant=%s", tenant_id
        )
        return None


_TENANT_PHONE_SELECT = (
    "id, business_name, business_type, owner_email, notification_phone, "
    "twilio_number, sms_notifications_enabled, plan, voice_ai_enabled, "
    "voice_addon_active"
)


def _find_tenant_by_phone(phone: str) -> dict | None:
    """Look up the tenant whose line was called.

    Primary path: exact indexed match on tenants.twilio_number - the dedicated
    provisioned-AI-line column (migration 164). Twilio delivers E.164 and the
    provisioning flow stores E.164, so equality holds.

    Fallback: the legacy suffix scan against notification_phone for tenants
    configured before twilio_number existed. The scan is capped defensively
    but only runs when the indexed lookup missed. (G3 Phase 2 - replaces the
    unconditional limit(50) scan that silently broke at tenant #51.)
    """
    db = get_service_supabase()

    try:
        exact = (
            db.table("tenants")
            .select(_TENANT_PHONE_SELECT)
            .eq("twilio_number", phone)
            .limit(1)
            .execute()
        )
        if exact.data:
            return exact.data[0]
    except Exception:
        logger.warning(
            "twilio_number exact lookup failed for %s - falling back to scan",
            phone,
            exc_info=True,
        )

    # Paginate the fallback scan instead of a silent 200-row cap (audit
    # 2026-07-14 L4 — same silent-miss bug class as the limit(50) fixed in
    # #51: tenant #201+ was unroutable). Stored phone formats vary (spaces,
    # dashes), so the normalized suffix compare stays in Python.
    norm_phone = phone.replace(" ", "").replace("-", "")
    page_size = 1000
    offset = 0
    while True:
        try:
            result = (
                db.table("tenants")
                .select(_TENANT_PHONE_SELECT)
                .range(offset, offset + page_size - 1)
                .execute()
            )
        except Exception:
            logger.exception("Failed to query tenants for phone lookup: %s", phone)
            return None

        rows = result.data or []
        for tenant in rows:
            for tenant_phone in (tenant.get("twilio_number"), tenant.get("notification_phone")):
                if not tenant_phone:
                    continue
                # Normalize for comparison (strip spaces, dashes)
                norm_tenant = tenant_phone.replace(" ", "").replace("-", "")
                if norm_tenant.endswith(norm_phone[-10:]) or norm_phone.endswith(norm_tenant[-10:]):
                    return tenant

        if len(rows) < page_size:
            return None
        offset += page_size
