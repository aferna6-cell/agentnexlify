"""Twilio webhook endpoints — missed call text-back and inbound SMS handling.

When a call goes unanswered, Twilio hits our missed-call webhook.
We auto-text the caller and track the SMS conversation.
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from backend.config import settings
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.services import sms_compliance
from backend.services.activity import log_activity
from backend.services.twilio_service import format_textback_message, send_sms

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/twilio", tags=["twilio-webhooks"])

# Default text-back message
DEFAULT_TEXTBACK = (
    "Hi! Sorry we missed your call at {business_name}. "
    "How can we help? Reply here and we'll get back to you right away."
)

# Personalized text-back when caller is a known lead
PERSONALIZED_TEXTBACK = (
    "Hi {first_name}! Sorry we missed your call at {business_name}. "
    "How can we help? Reply here and we'll get back to you right away."
)

# Replay window: reject Twilio webhooks older than this many seconds
_REPLAY_WINDOW_SECONDS = 300  # 5 minutes


def _verify_twilio_signature(request: Request, body: bytes) -> bool:
    """Verify Twilio webhook signature (X-Twilio-Signature header)."""
    if not settings.twilio_auth_token:
        return False
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False
    url = str(request.url)
    # Twilio computes HMAC-SHA1 over URL + sorted POST params
    try:
        params = dict(x.split("=", 1) for x in body.decode().split("&") if "=" in x)
        from urllib.parse import unquote_plus

        params = {k: unquote_plus(v) for k, v in params.items()}
    except Exception:
        params = {}
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    expected = hmac.new(
        settings.twilio_auth_token.encode(),
        data.encode(),
        hashlib.sha1,
    ).digest()
    import base64

    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(signature, expected_b64)


# Per-worker cache of SMS-enabled tenants, keyed by last-10-digit phone.
# Mirrors the existing 5-min widget/config cache pattern (CLAUDE.md). A 60s TTL
# keeps newly-configured notification numbers fresh enough for SMS/voice
# routing while turning the former O(N) per-webhook scan into an O(1) lookup,
# and removes the limit(50) that silently dropped tenants past the 50th. (GH #98)
_TENANT_PHONE_SELECT = (
    "id, business_name, notification_phone, sms_notifications_enabled, plan, "
    "textback_enabled, textback_message, textback_quiet_start, textback_quiet_end"
)
_TENANT_PHONE_INDEX: dict[str, dict] = {}
_TENANT_PHONE_INDEX_AT: float = 0.0
_TENANT_PHONE_INDEX_TTL = 60.0


def _phone_key(phone: str | None) -> str:
    """Last 10 digits with all separators stripped — the match key.

    Equivalent to the previous endswith(last-10) heuristic but order-free.
    """
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-10:]


def _refresh_tenant_phone_index() -> None:
    """Rebuild the phone->tenant index from all SMS-enabled tenants (no cap)."""
    global _TENANT_PHONE_INDEX, _TENANT_PHONE_INDEX_AT
    db = get_service_supabase()
    result = (
        db.table("tenants")
        .select(_TENANT_PHONE_SELECT)
        .eq("sms_notifications_enabled", True)
        .execute()
    )
    index: dict[str, dict] = {}
    for tenant in result.data or []:
        key = _phone_key(tenant.get("notification_phone"))
        if key:
            index[key] = tenant
    _TENANT_PHONE_INDEX = index
    _TENANT_PHONE_INDEX_AT = time.monotonic()


def _find_tenant_by_phone(phone: str) -> dict | None:
    """Look up a tenant by configured notification_phone (last-10-digit match).

    Backed by a per-worker 60s cache so inbound SMS/voice webhooks no longer run
    an O(N) scan per request and no longer silently drop tenants past a
    limit(50) cap. (GH #98)
    """
    key = _phone_key(phone)
    if not key:
        return None
    now = time.monotonic()
    if not _TENANT_PHONE_INDEX or (now - _TENANT_PHONE_INDEX_AT) > _TENANT_PHONE_INDEX_TTL:
        try:
            _refresh_tenant_phone_index()
        except Exception:
            # Never let a lookup failure 500 the webhook; degrade to no-match.
            logger.warning("Failed to refresh tenant phone index", exc_info=True)
    return _TENANT_PHONE_INDEX.get(key)


def _get_automation(tenant_id: str, automation_type: str) -> dict | None:
    """Fetch automation row for (tenant_id, type). Returns None if not found."""
    try:
        db = get_service_supabase()
        result = (
            db.table("automations")
            .select("id, tenant_id, type, is_enabled, config, runs_total")
            .eq("tenant_id", tenant_id)
            .eq("type", automation_type)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "Failed to fetch automation tenant=%s type=%s",
            tenant_id,
            automation_type,
            exc_info=True,
        )
        return None


def _find_lead_by_phone(tenant_id: str, phone: str) -> dict | None:
    """Return existing lead row for caller phone, or None."""
    try:
        db = get_service_supabase()
        result = (
            db.table("leads")
            .select("id, name, phone")
            .eq("client_id", tenant_id)
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        logger.warning(
            "Lead lookup failed tenant=%s phone=<masked>", tenant_id, exc_info=True
        )
        return None


def _insert_missed_call_row(
    tenant_id: str,
    call_sid: str,
    sms_sid: str | None,
    from_phone: str,
    to_phone: str,
    template_id: str,
    status: str,
    lead_id: str | None = None,
) -> None:
    """INSERT a row into missed_call_texts. Silently swallows errors."""
    try:
        db = get_service_supabase()
        row = {
            "tenant_id": tenant_id,
            "call_sid": call_sid,
            "sms_sid": sms_sid,
            "from_phone": from_phone,
            "to_phone": to_phone,
            "template_id": template_id,
            "status": status,
        }
        if lead_id:
            row["converted_to_lead_id"] = lead_id
        db.table("missed_call_texts").insert(row).execute()
    except Exception:
        logger.warning(
            "Failed to insert missed_call_texts row tenant=%s", tenant_id, exc_info=True
        )


def _increment_runs_total(tenant_id: str, automation_type: str) -> None:
    """Increment automations.runs_total for (tenant_id, type). Silently swallows errors."""
    try:
        db = get_service_supabase()
        # Fetch current value, then update (Supabase JS client supports rpc increment;
        # Python client requires read-then-write)
        result = (
            db.table("automations")
            .select("id, runs_total")
            .eq("tenant_id", tenant_id)
            .eq("type", automation_type)
            .limit(1)
            .execute()
        )
        if result.data:
            row = result.data[0]
            db.table("automations").update({"runs_total": row["runs_total"] + 1}).eq(
                "id", row["id"]
            ).execute()
    except Exception:
        logger.warning(
            "Failed to increment runs_total tenant=%s type=%s",
            tenant_id,
            automation_type,
            exc_info=True,
        )


def _parse_twilio_timestamp(ts_str: str) -> datetime | None:
    """Parse Twilio Timestamp param into aware UTC datetime. Returns None on failure."""
    if not ts_str:
        return None
    # Twilio format: "2026-04-22T12:00:00+0000" or "Wed, 22 Apr 2026 12:00:00 +0000"
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S+0000",
        "%a, %d %b %Y %H:%M:%S %z",
    ):
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


@router.post("/missed-call")
@limiter.limit("30/minute")
async def handle_missed_call(request: Request):
    """Twilio voice webhook — triggered when a call goes unanswered.

    Phase 1 additions:
    - Reads automations row; skips if is_enabled=False or not found.
    - Replay window: rejects calls with Timestamp older than 5 minutes.
    - On send success: inserts missed_call_texts row, logs activity,
      increments automations.runs_total.
    - On send failure: logs warning only (Phase 4 will add retry queue).
    """
    body = await request.body()

    # Verify Twilio signature to prevent forged requests
    if not _verify_twilio_signature(request, body):
        logger.warning("Twilio signature verification failed for missed-call webhook")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # Parse form data
    try:
        from urllib.parse import parse_qs

        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    caller = params.get("From", "")
    called = params.get("To", "")
    call_status = params.get("CallStatus", "")
    call_sid = params.get("CallSid", "")
    timestamp_str = params.get("Timestamp", "")

    if not caller:
        return PlainTextResponse("OK")

    # Only handle missed/no-answer calls
    if call_status not in ("no-answer", "busy", "failed", "canceled"):
        return PlainTextResponse("OK")

    # Replay window: reject forged/replayed requests older than 5 minutes
    call_ts = _parse_twilio_timestamp(timestamp_str)
    if call_ts is not None:
        age_seconds = (datetime.now(timezone.utc) - call_ts).total_seconds()
        if age_seconds > _REPLAY_WINDOW_SECONDS:
            logger.warning(
                "Missed-call replay window exceeded: age=%.0fs caller=%s",
                age_seconds,
                caller,
            )
            return PlainTextResponse("OK")

    logger.info("Missed call from %s to %s (status: %s)", caller, called, call_status)

    # Find the tenant this call was for
    tenant = _find_tenant_by_phone(called)
    if not tenant:
        logger.warning("Missed call to %s — no matching tenant found", called)
        return PlainTextResponse("OK")

    business_name = tenant.get("business_name") or "us"
    tenant_id = tenant["id"]

    # Check if text-back is enabled for this tenant (legacy flag)
    if not tenant.get("textback_enabled", False):
        logger.info("Text-back disabled for tenant %s, skipping", tenant_id)
        return PlainTextResponse("OK")

    # Check automations table: must have is_enabled=True row
    automation = _get_automation(tenant_id, "missed_call_textback")
    if not automation:
        logger.info(
            "No missed_call_textback automation row for tenant %s, skipping", tenant_id
        )
        return PlainTextResponse("OK")
    if not automation.get("is_enabled", False):
        logger.info(
            "missed_call_textback automation disabled for tenant %s, skipping",
            tenant_id,
        )
        return PlainTextResponse("OK")

    # Check quiet hours
    quiet_start = tenant.get("textback_quiet_start")  # e.g. "22:00"
    quiet_end = tenant.get("textback_quiet_end")  # e.g. "07:00"
    if quiet_start and quiet_end:
        now_utc = datetime.now(timezone.utc)
        hour_now = now_utc.hour * 100 + now_utc.minute
        try:
            qs = int(quiet_start.replace(":", ""))
            qe = int(quiet_end.replace(":", ""))
            if qs > qe:  # Overnight quiet hours (e.g., 22:00 - 07:00)
                if hour_now >= qs or hour_now < qe:
                    logger.info(
                        "Quiet hours active for tenant %s (%s-%s), skipping text-back",
                        tenant_id,
                        quiet_start,
                        quiet_end,
                    )
                    return PlainTextResponse("OK")
            elif qs <= hour_now < qe:
                logger.info(
                    "Quiet hours active for tenant %s, skipping text-back", tenant_id
                )
                return PlainTextResponse("OK")
        except ValueError:
            pass  # Malformed quiet hours, proceed with text-back

    # Personalization: look up existing lead for caller
    existing_lead = _find_lead_by_phone(tenant_id, caller)
    lead_id = existing_lead["id"] if existing_lead else None

    # Build message: personalized if we have a name, else default
    template_id = (automation.get("config") or {}).get("template_id", "default")
    custom_msg = tenant.get("textback_message")
    if existing_lead and existing_lead.get("name"):
        first_name = existing_lead["name"].split()[0]
        template = PERSONALIZED_TEXTBACK
        message = template.format(first_name=first_name, business_name=business_name)
    elif custom_msg and custom_msg.strip():
        message = format_textback_message(custom_msg, business_name)
    else:
        message = format_textback_message(DEFAULT_TEXTBACK, business_name)

    # TCPA: never text a caller who opted out (STOP) for this tenant.
    if sms_compliance.is_suppressed(get_service_supabase(), tenant_id, caller):
        logger.info(
            "Text-back suppressed — caller %s opted out for tenant %s", caller, tenant_id
        )
        return PlainTextResponse("OK")

    # Frequency cap: one text-back per caller per 24h (margin + anti-spam).
    if sms_compliance.recently_messaged(get_service_supabase(), tenant_id, caller):
        logger.info(
            "Text-back skipped — already texted %s within 24h (tenant %s)",
            caller,
            tenant_id,
        )
        return PlainTextResponse("OK")

    sent_result = await send_sms(to=caller, body=message)

    # send_sms returns bool (legacy) or (bool, sms_sid) tuple
    if isinstance(sent_result, tuple):
        sent, sms_sid = sent_result
    else:
        sent = sent_result
        sms_sid = None

    if sent:
        logger.info("Text-back sent to %s for tenant %s", caller, tenant_id)

        # Insert missed_call_texts row
        _insert_missed_call_row(
            tenant_id=tenant_id,
            call_sid=call_sid,
            sms_sid=sms_sid,
            from_phone=caller,
            to_phone=called,
            template_id=template_id,
            status="sent",
            lead_id=lead_id,
        )

        # Log activity event
        log_activity(
            tenant_id=tenant_id,
            activity_type="missed_call_textback",
            description=f"Missed call from {caller} — auto text-back sent",
            metadata={
                "caller": caller,
                "called": called,
                "call_sid": call_sid,
                "sms_sid": sms_sid,
                "template_id": template_id,
                "status": call_status,
            },
        )

        # Increment automation run counter
        _increment_runs_total(tenant_id, "missed_call_textback")

        # Create/update lead from caller phone (existing behavior preserved)
        if not existing_lead:
            db = get_service_supabase()
            db.table("leads").insert(
                {
                    "client_id": tenant_id,
                    "phone": caller,
                    "status": "new",
                    "areas_of_interest": "missed call — text-back sent",
                }
            ).execute()
            logger.info(
                "Created lead from missed call: %s for tenant %s", caller, tenant_id
            )

    else:
        # Phase 1: log warning only. Phase 4 will add pending_automations retry queue.
        logger.warning(
            "Text-back send FAILED for tenant %s caller=%s — skipping row insert",
            tenant_id,
            caller,
        )
        _insert_missed_call_row(
            tenant_id=tenant_id,
            call_sid=call_sid,
            sms_sid=None,
            from_phone=caller,
            to_phone=called,
            template_id=template_id,
            status="failed",
            lead_id=lead_id,
        )

    return PlainTextResponse("OK")


@router.post("/sms-reply")
@limiter.limit("60/minute")
async def handle_inbound_sms(request: Request):
    """DEPRECATED — migrated to ``POST /api/v1/os/inbound/sms``.

    Returns 410 Gone after signature verification. Tenants must update
    their Twilio Messaging webhook URL to point at
    ``/api/v1/os/inbound/sms`` so inbound SMS flows through the Agent OS
    (``os_messages`` + orchestrator) instead of the legacy
    ``chat_messages`` AI-reply path.

    Signature verification stays in place so the deprecation surface is
    not exposed to forged probes. Every hit is logged with caller +
    destination numbers for operational visibility into which tenants
    still need to migrate.
    """
    body = await request.body()

    if not _verify_twilio_signature(request, body):
        logger.warning("Twilio signature verification failed for sms-reply webhook")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    try:
        from urllib.parse import parse_qs

        params = {k: v[0] for k, v in parse_qs(body.decode()).items()}
    except Exception:
        params = {}

    logger.warning(
        "LEGACY /api/v1/twilio/sms-reply hit — tenant must migrate to "
        "/api/v1/os/inbound/sms (from=%s to=%s sid=%s)",
        params.get("From", ""),
        params.get("To", ""),
        params.get("MessageSid", ""),
    )

    raise HTTPException(
        status_code=410,
        detail="Endpoint migrated to /api/v1/os/inbound/sms",
    )
