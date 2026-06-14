"""Provider-specific inbound-email payload parsers.

Each provider ships its own webhook shape. This module normalizes
Postmark (JSON body) and Mailgun (form-encoded) into a single
``ParsedEmail`` dict so the webhook route stays small and the bridge
layer never branches on provider.

Spec: ``specs/agent-os-connectors-inbound_spec.md`` §Email
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 4.2
"""

import json
import logging
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class ParsedEmail(TypedDict, total=False):
    """Normalized inbound email shape consumed by ``bridge_email``.

    ``provider_message_id`` anchors idempotency (source_ref).
    ``thread_id`` is the dedup key for ``os_threads``; we prefer the
    In-Reply-To chain root so reply threads collapse to one OS thread.
    ``headers`` is lower-cased for the auto-reply detector.
    """

    provider_message_id: str
    thread_id: str
    sender_email: str
    sender_name: str
    recipient: str
    subject: str
    body_text: str
    headers: dict[str, str]


def parse_postmark(payload: dict[str, Any]) -> ParsedEmail:
    """Parse a Postmark Inbound JSON payload into ``ParsedEmail``.

    Reference: https://postmarkapp.com/developer/webhooks/inbound-webhook
    Postmark headers arrive as a list of ``{Name, Value}`` dicts; we
    flatten them to a lower-cased dict for case-insensitive matching.
    """
    headers_list = payload.get("Headers") or []
    headers = {
        str(h.get("Name", "")).lower(): str(h.get("Value", ""))
        for h in headers_list
        if isinstance(h, dict)
    }

    message_id = payload.get("MessageID") or headers.get("message-id") or ""
    in_reply_to = headers.get("in-reply-to") or ""
    references = headers.get("references") or ""
    thread_id = _pick_thread_id(message_id, in_reply_to, references)

    return ParsedEmail(
        provider_message_id=str(message_id),
        thread_id=thread_id,
        sender_email=str(payload.get("From") or "").strip(),
        sender_name=str(payload.get("FromName") or "").strip(),
        recipient=str(
            payload.get("OriginalRecipient") or payload.get("To") or ""
        ).strip(),
        subject=str(payload.get("Subject") or "").strip(),
        body_text=str(payload.get("TextBody") or payload.get("HtmlBody") or ""),
        headers=headers,
    )


def parse_mailgun(form: dict[str, Any]) -> ParsedEmail:
    """Parse a Mailgun signed-webhook form payload into ``ParsedEmail``.

    Reference: https://documentation.mailgun.com/en/latest/user_manual.html#receiving-forwarding-and-storing-messages
    Mailgun ships per-header form fields AND a ``message-headers`` JSON
    blob. The JSON blob is canonical (preserves duplicate headers); we
    prefer it when present and fall back to flat fields.
    """
    headers = _parse_mailgun_headers(form.get("message-headers"))

    message_id = (
        form.get("Message-Id")
        or form.get("message-id")
        or headers.get("message-id")
        or ""
    )
    in_reply_to = headers.get("in-reply-to") or form.get("In-Reply-To") or ""
    references = headers.get("references") or form.get("References") or ""
    thread_id = _pick_thread_id(str(message_id), str(in_reply_to), str(references))

    return ParsedEmail(
        provider_message_id=str(message_id),
        thread_id=thread_id,
        sender_email=str(form.get("sender") or form.get("from") or "").strip(),
        sender_name=str(form.get("From") or "").strip(),
        recipient=str(form.get("recipient") or form.get("To") or "").strip(),
        subject=str(form.get("subject") or form.get("Subject") or "").strip(),
        body_text=str(form.get("body-plain") or form.get("body-html") or ""),
        headers=headers,
    )


def _parse_mailgun_headers(raw: Any) -> dict[str, str]:
    """Mailgun ``message-headers`` is a JSON-encoded list of [name, value] pairs."""
    if not raw:
        return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("parse_mailgun: message-headers not valid JSON")
            return {}
    if not isinstance(raw, list):
        return {}
    out: dict[str, str] = {}
    for entry in raw:
        if isinstance(entry, list | tuple) and len(entry) >= 2:
            name, value = entry[0], entry[1]
            out[str(name).lower()] = str(value)
    return out


def _pick_thread_id(message_id: str, in_reply_to: str, references: str) -> str:
    """Pick the email thread anchor.

    Prefer the references-chain root (oldest ancestor) so the whole
    conversation lands on one ``os_thread``. Fall back to In-Reply-To
    (immediate parent), then to the message's own ID (new thread).
    """
    refs = [r.strip() for r in references.split() if r.strip()]
    if refs:
        return refs[0]
    if in_reply_to.strip():
        return in_reply_to.strip()
    return message_id.strip()
