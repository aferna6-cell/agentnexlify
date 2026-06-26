"""Agent OS inbound bridges — owner-gated toggle + inbound webhooks.

Three surfaces:
  - Tenant-facing config: GET ``/bridge-config`` (any role),
    POST ``/bridge-toggle`` (owner-only).
  - Email webhooks: POST ``/email/{provider}`` (Postmark, Mailgun).
    Signature-verified, tenant resolved by recipient address.
  - SMS webhook: POST ``/sms`` (Twilio). Signature-verified, tenant
    resolved by ``To`` number, STOP keyword flips ``leads.unsubscribed``.

Backed by ``backend.services.os_inbound_bridge``. Webhooks dispatch into
``bridge_email`` / ``bridge_sms`` via ``BackgroundTasks`` so signed-webhook
senders get a fast 200/200-TwiML (5s retry budget).

Spec: ``specs/agent-os-connectors-inbound_spec.md``
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 3 + 4 + 5
"""

import logging
from xml.sax import saxutils
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import unquote_plus

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services import (
    inbound_email_parser,
    inbound_email_verify,
    inbound_sms_verify,
    os_inbound_bridge,
    os_sms_approval,
    sms_compliance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os/inbound", tags=["agent-os"])


BridgeSource = Literal["widget", "email", "sms", "facebook"]
EmailProvider = Literal["postmark", "mailgun"]

# Empty TwiML — tells Twilio we acknowledge but don't reply via TwiML.
# Outbound replies (if any) go through the orchestrator + outbound channel.
_EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response/>'


class BridgeToggleRequest(BaseModel):
    source: BridgeSource
    enabled: bool


class BridgeConfigRequest(BaseModel):
    """Partial bridge config update — set non-toggle fields.

    All fields optional; only included keys are written. Use ``None`` to
    clear a field (e.g. unset ``email_inbound_address`` when rotating).
    """

    email_inbound_address: str | None = None
    email_provider: EmailProvider | None = None


@router.get("/bridge-config")
async def get_bridge_config(
    claims: dict = Depends(_get_current_tenant),
) -> dict[str, Any]:
    """Return current merged bridge config for the caller's tenant.

    Read access is open to any authenticated tenant user so the settings
    UI can render the toggle row regardless of role.
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return os_inbound_bridge.get_bridge_config(db, client_id)


@router.post("/bridge-toggle")
async def set_bridge_toggle(
    req: BridgeToggleRequest,
    claims: dict = Depends(require_role("owner")),
) -> dict[str, Any]:
    """Flip a per-source bridge on or off. Owner-only.

    Bridges fan-in customer messages from external channels into the OS
    inbox — flipping one on starts persisting (and routing) inbound
    widget/email/sms/facebook traffic, so we gate this to the owner role
    the same way other consequential channel switches are gated.
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()
    return os_inbound_bridge.set_bridge_toggle(db, client_id, req.source, req.enabled)


@router.post("/bridge-config")
async def set_bridge_config(
    req: BridgeConfigRequest,
    claims: dict = Depends(require_role("owner")),
) -> dict[str, Any]:
    """Set non-toggle bridge config fields (email_inbound_address, email_provider).

    Owner-only — same gating as ``bridge-toggle`` since changing the
    inbound address re-routes which tenant claims a given recipient.

    Only includes fields the client explicitly sent in the request body
    (using ``model_fields_set``) so callers can patch one field at a time
    without clobbering the other. A field with value ``None`` is honored
    as an explicit clear (different from "field absent").
    """
    client_id = claims["tenant_id"]
    db = get_service_supabase()

    updates: dict[str, Any] = {
        field: getattr(req, field) for field in req.model_fields_set
    }
    if not updates:
        # Nothing to change — return current state so the UI can refresh
        # without a separate GET round-trip.
        return os_inbound_bridge.get_bridge_config(db, client_id)

    try:
        return os_inbound_bridge.set_bridge_config(db, client_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Inbound email webhook (Phase 4.2)
# ---------------------------------------------------------------------------


@router.post("/email/{provider}")
async def inbound_email_webhook(
    provider: EmailProvider,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Receive an inbound email from Postmark or Mailgun.

    Order is load-bearing — verify signature against the RAW body BEFORE
    parsing/branching on any payload field. An attacker who can post
    arbitrary JSON to this endpoint must not be able to influence
    tenant resolution.

    Flow:
      1. Read raw body bytes (Postmark HMAC binds to raw body).
      2. Verify provider signature → 401 on mismatch / missing secret.
      3. Parse payload to ``ParsedEmail``.
      4. Resolve tenant by recipient → 404 if no tenant owns this address.
      5. Tag auto-reply via RFC 3834 headers.
      6. Enqueue ``bridge_email`` on ``BackgroundTasks`` → return 200.
    """
    raw_body = await request.body()

    if provider == "postmark":
        if not _verify_postmark_request(request, raw_body):
            raise HTTPException(status_code=401, detail="Invalid Postmark signature")
        try:
            payload = await request.json()
        except Exception as exc:
            logger.warning("inbound_email_webhook: postmark JSON parse failed: %s", exc)
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
        parsed = inbound_email_parser.parse_postmark(payload)
    else:
        form = await request.form()
        form_dict = {k: form.get(k) for k in form.keys()}
        if not _verify_mailgun_request(form_dict):
            raise HTTPException(status_code=401, detail="Invalid Mailgun signature")
        parsed = inbound_email_parser.parse_mailgun(form_dict)

    recipient = parsed.get("recipient", "")
    if not recipient:
        raise HTTPException(status_code=400, detail="Missing recipient address")

    db = get_service_supabase()
    client_id = os_inbound_bridge.resolve_tenant_by_inbound_email(db, recipient)
    if not client_id:
        # Unknown inbound address — bounce so retried deliveries stop
        # but don't leak which addresses we know about.
        raise HTTPException(status_code=404, detail="Unknown recipient")

    provider_message_id = parsed.get("provider_message_id") or ""
    if not provider_message_id:
        raise HTTPException(status_code=400, detail="Missing message id")

    headers = parsed.get("headers") or {}
    inbound_kind = (
        "auto_reply" if inbound_email_verify.is_auto_reply(headers) else "normal"
    )

    sender_metadata = {
        "from": parsed.get("sender_email", ""),
        "from_name": parsed.get("sender_name", ""),
        "subject": parsed.get("subject", ""),
        "provider": provider,
    }

    background_tasks.add_task(
        _bridge_email_safe,
        client_id=client_id,
        email_thread_id=parsed.get("thread_id") or provider_message_id,
        provider_message_id=provider_message_id,
        user_content=parsed.get("body_text", ""),
        sender_metadata=sender_metadata,
        inbound_kind=inbound_kind,
    )

    return {"status": "accepted", "inbound_kind": inbound_kind}


def _verify_postmark_request(request: Request, raw_body: bytes) -> bool:
    """Postmark binds HMAC to the raw body; header is X-Postmark-Webhook-Hmac."""
    secret = settings.postmark_webhook_secret
    if not secret:
        logger.warning(
            "postmark webhook hit without POSTMARK_WEBHOOK_SECRET configured"
        )
        return False
    signature = request.headers.get("X-Postmark-Webhook-Hmac", "")
    return inbound_email_verify.verify_postmark(raw_body, signature, secret)


def _verify_mailgun_request(form: dict[str, Any]) -> bool:
    """Mailgun signs timestamp+token; signing key lives in MAILGUN_SIGNING_KEY."""
    signing_key = settings.mailgun_signing_key
    if not signing_key:
        logger.warning("mailgun webhook hit without MAILGUN_SIGNING_KEY configured")
        return False
    return inbound_email_verify.verify_mailgun(
        timestamp=str(form.get("timestamp") or ""),
        token=str(form.get("token") or ""),
        signature=str(form.get("signature") or ""),
        signing_key=signing_key,
    )


async def _bridge_email_safe(
    *,
    client_id: str,
    email_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any],
    inbound_kind: str,
) -> None:
    """BackgroundTasks wrapper: never let bridge errors escape the task.

    The webhook already returned 200 — raising here would surface as an
    unhandled exception in the worker log without any retry path. Log
    and move on; idempotency on ``source_ref`` lets the provider safely
    re-deliver.
    """
    try:
        db = get_service_supabase()
        await os_inbound_bridge.bridge_email(
            db=db,
            client_id=client_id,
            email_thread_id=email_thread_id,
            provider_message_id=provider_message_id,
            user_content=user_content,
            sender_metadata=sender_metadata,
            inbound_kind=inbound_kind,  # type: ignore[arg-type]
        )
    except Exception:
        logger.exception(
            "bridge_email failed: client_id=%s provider_message_id=%s",
            client_id,
            provider_message_id,
        )


# ---------------------------------------------------------------------------
# Inbound SMS webhook (Phase 5.1)
# ---------------------------------------------------------------------------


@router.post("/sms")
async def inbound_sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> PlainTextResponse:
    """Receive an inbound SMS from Twilio.

    Order is load-bearing — sig verify BEFORE any branching on form fields.
    Twilio waits 5s before retrying; bridge runs in ``BackgroundTasks`` so
    we return TwiML immediately.

    Flow:
      1. Read raw body, parse form params.
      2. Verify Twilio signature (URL + sorted form params, HMAC-SHA1).
         403 on mismatch — Twilio gets the error and stops retrying.
      3. Resolve tenant by ``To`` number → 404 if no tenant owns it.
      4. STOP keyword (case-insensitive equality) → flip
         ``leads.unsubscribed = true`` for any lead with this phone in
         the resolved client, and dispatch as ``system_notice`` so the
         orchestrator skips an automated reply.
      5. Enqueue ``bridge_sms`` on ``BackgroundTasks``.
      6. Return empty TwiML (Twilio expects ``application/xml``).
    """
    body = await request.body()
    form = _parse_twilio_form(body)

    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")
    auth_token = settings.twilio_auth_token
    if not auth_token:
        logger.warning("twilio sms webhook hit without TWILIO_AUTH_TOKEN configured")
        raise HTTPException(status_code=403, detail="Twilio signature unverifiable")
    if not inbound_sms_verify.verify_twilio(url, form, signature, auth_token):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    to_number = form.get("To", "")
    from_number = form.get("From", "")
    body_text = form.get("Body", "")
    message_sid = form.get("MessageSid", "")
    if not to_number or not message_sid:
        raise HTTPException(status_code=400, detail="Missing To or MessageSid")

    db = get_service_supabase()
    client_id = os_inbound_bridge.resolve_tenant_by_inbound_phone(db, to_number)
    if not client_id:
        # Twilio retries 11x over ~24h on non-2xx — 404 stops the retry storm
        # without leaking which numbers we own.
        raise HTTPException(status_code=404, detail="Unknown destination number")

    is_stop = inbound_sms_verify.is_stop_keyword(body_text)
    inbound_kind = "system_notice" if is_stop else "normal"

    # Approve-by-text: an exact command keyword (YES/NO/...) from the
    # tenant's own notification_phone acts on the newest pending draft and
    # replies inline via TwiML. Non-commands and non-owner senders fall
    # through to the normal bridge. Checked before STOP so an owner's "NO"
    # is a dismissal, not an unsubscribe.
    owner_reply = await os_sms_approval.handle_owner_sms(
        db, client_id, from_number, body_text
    )
    if owner_reply is not None:
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response><Message>'
            + saxutils.escape(owner_reply)
            + "</Message></Response>",
            media_type="application/xml",
        )

    if is_stop and from_number:
        _flip_lead_unsubscribed(db, client_id, from_number)
        # Durable opt-out so suppression is honored even for non-lead numbers.
        sms_compliance.record_opt_out(db, client_id, from_number, source="sms_stop")
    elif from_number and sms_compliance.classify_inbound(body_text) == "opt_in":
        # START / UNSTOP — re-subscribe.
        sms_compliance.record_opt_in(db, client_id, from_number)

    sender_metadata = {
        "from": from_number,
        "to": to_number,
        "provider": "twilio",
        "stop_keyword": is_stop,
    }

    background_tasks.add_task(
        _bridge_sms_safe,
        client_id=client_id,
        sms_thread_id=f"{from_number}:{to_number}",
        provider_message_id=message_sid,
        user_content=body_text,
        sender_metadata=sender_metadata,
        inbound_kind=inbound_kind,
    )

    return PlainTextResponse(_EMPTY_TWIML, media_type="application/xml")


def _parse_twilio_form(body: bytes) -> dict[str, str]:
    """Parse ``application/x-www-form-urlencoded`` body into a dict.

    Twilio sig is HMAC over URL + sorted POST params — the form values
    used in the HMAC must match what Twilio sent (URL-decoded).
    """
    out: dict[str, str] = {}
    if not body:
        return out
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        return out
    for pair in decoded.split("&"):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        out[unquote_plus(k)] = unquote_plus(v)
    return out


def _flip_lead_unsubscribed(db: Any, client_id: str, from_phone: str) -> None:
    """Flip ``leads.unsubscribed = true`` for matching phone in this client.

    Phone matching uses last-10-digits because Twilio sends E.164 and
    leads can be stored in any user-entered format. Automation
    orchestrator (``orchestrator.py``) and rule engine
    (``rule_engine.py``) both gate outreach on this flag, so flipping
    it here is sufficient to stop further messages.
    """
    try:
        needle = _last_10_digits(from_phone)
        if not needle:
            return
        result = (
            db.table("leads")
            .select("id, phone")
            .eq("client_id", client_id)
            .filter("phone", "not.is", "null")
            .execute()
        )
        rows = result.data or []
        matched_ids = [
            r["id"]
            for r in rows
            if r.get("phone") and _last_10_digits(r["phone"]) == needle
        ]
        if not matched_ids:
            return
        now_iso = datetime.now(timezone.utc).isoformat()
        (
            db.table("leads")
            .update({"unsubscribed": True, "unsubscribed_at": now_iso})
            .in_("id", matched_ids)
            .execute()
        )
        logger.info(
            "sms STOP keyword flipped unsubscribed on %d leads client=%s",
            len(matched_ids),
            client_id,
        )
    except Exception:
        # STOP handling is best-effort — we already accepted the message
        # and Twilio carrier-level STOP also fires. Don't crash on DB blips.
        logger.exception(
            "_flip_lead_unsubscribed failed client=%s phone=%s",
            client_id,
            from_phone,
        )


def _last_10_digits(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


async def _bridge_sms_safe(
    *,
    client_id: str,
    sms_thread_id: str,
    provider_message_id: str,
    user_content: str,
    sender_metadata: dict[str, Any],
    inbound_kind: str,
) -> None:
    """BackgroundTasks wrapper: never let bridge errors escape the task.

    TwiML already returned — raising would surface as unhandled exception
    in worker logs with no retry path. ``source_ref`` idempotency lets
    Twilio safely re-deliver if it ever does retry.
    """
    try:
        db = get_service_supabase()
        await os_inbound_bridge.bridge_sms(
            db=db,
            client_id=client_id,
            sms_thread_id=sms_thread_id,
            provider_message_id=provider_message_id,
            user_content=user_content,
            sender_metadata=sender_metadata,
            inbound_kind=inbound_kind,  # type: ignore[arg-type]
        )
    except Exception:
        logger.exception(
            "bridge_sms failed: client_id=%s provider_message_id=%s",
            client_id,
            provider_message_id,
        )
