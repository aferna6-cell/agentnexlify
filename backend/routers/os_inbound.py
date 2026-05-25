"""Agent OS inbound bridges — owner-gated toggle + inbound webhooks.

Two surfaces:
  - Tenant-facing config: GET ``/bridge-config`` (any role),
    POST ``/bridge-toggle`` (owner-only).
  - Provider-facing webhooks: POST ``/email/{provider}`` (Postmark,
    Mailgun). Signature-verified, tenant resolved by recipient address.

Both backed by ``backend.services.os_inbound_bridge``. Webhooks dispatch
into ``bridge_email`` via ``BackgroundTasks`` so signed-webhook senders
get a fast 200 (5s retry budget).

Spec: ``specs/agent-os-connectors-inbound_spec.md``
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 3 + 4
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.config import settings
from backend.dependencies import _get_current_tenant, require_role
from backend.models.database import get_service_supabase
from backend.services import (
    inbound_email_parser,
    inbound_email_verify,
    os_inbound_bridge,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os/inbound", tags=["agent-os"])


BridgeSource = Literal["widget", "email", "sms", "facebook"]
EmailProvider = Literal["postmark", "mailgun"]


class BridgeToggleRequest(BaseModel):
    source: BridgeSource
    enabled: bool


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
