"""Inbound-email webhook signature verification.

Each provider authenticates webhooks differently. Centralized here so the
bridge route can dispatch by provider name without branching on header
shapes inline.

Postmark
--------
We use Postmark's HMAC option (Server -> Settings -> "Sign webhooks with
HMAC"). Postmark sends ``X-Postmark-Webhook-Hmac`` whose value is the
base64-encoded HMAC-SHA256 of the raw request body using the configured
secret. URL-secrecy alone is NOT considered authentication for Agent OS
bridges — owner toggles can ingest customer messages, so we require a
verifiable signature.

Mailgun
-------
Mailgun inbound webhooks include three form fields:
``timestamp``, ``token``, ``signature``. The signature is HMAC-SHA256 of
``timestamp + token`` using the Mailgun signing key. A short replay
window (5 min) protects against accidental retries from old captures.

Spec: ``specs/agent-os-connectors-inbound_spec.md`` §Security
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 4.1
"""

import base64
import hashlib
import hmac
import logging
import time
from typing import Literal

logger = logging.getLogger(__name__)

EmailProvider = Literal["postmark", "mailgun"]

# Reject Mailgun payloads older than 5 minutes — protects against replay
# of an already-processed (and idempotency-anchored) message.
_MAILGUN_REPLAY_WINDOW_SECONDS = 300


def verify_postmark(body: bytes, signature_header: str, secret: str) -> bool:
    """Verify a Postmark inbound webhook signature.

    ``body`` must be the *raw* request body bytes — JSON re-serialization
    will break the HMAC. ``signature_header`` is the value of
    ``X-Postmark-Webhook-Hmac``. ``secret`` is the configured per-server
    HMAC secret (``POSTMARK_WEBHOOK_SECRET`` env).
    """
    if not secret or not signature_header:
        return False
    try:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        expected_b64 = base64.b64encode(expected).decode()
        return hmac.compare_digest(signature_header, expected_b64)
    except Exception:
        logger.warning("verify_postmark: comparison raised", exc_info=True)
        return False


def verify_mailgun(
    timestamp: str,
    token: str,
    signature: str,
    signing_key: str,
    now: float | None = None,
) -> bool:
    """Verify a Mailgun inbound webhook signature.

    Mailgun's signed-webhooks format: HMAC-SHA256 of ``timestamp + token``
    using ``signing_key``, hex-encoded. ``now`` is injectable so tests can
    pin replay-window behavior without freezing the global clock.
    """
    if not signing_key or not timestamp or not token or not signature:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    if now is None:
        now = time.time()
    if abs(now - ts) > _MAILGUN_REPLAY_WINDOW_SECONDS:
        return False

    try:
        expected = hmac.new(
            signing_key.encode(),
            f"{timestamp}{token}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except Exception:
        logger.warning("verify_mailgun: comparison raised", exc_info=True)
        return False


def is_auto_reply(headers: dict[str, str] | None) -> bool:
    """Detect auto-replies / OOO via RFC 3834 + provider headers.

    Header keys are matched case-insensitively. Auto-replies still get
    stored (the orchestrator wants the evidence) but with
    ``inbound_kind='auto_reply'`` so the routing layer can skip them.
    """
    if not headers:
        return False
    # Build a case-insensitive view once
    lowered = {k.lower(): str(v) for k, v in headers.items()}

    auto_submitted = lowered.get("auto-submitted", "").lower()
    if auto_submitted and auto_submitted != "no":
        return True

    precedence = lowered.get("precedence", "").lower()
    if precedence in {"auto_reply", "bulk", "junk", "list"}:
        return True

    if lowered.get("x-autoreply", "").lower() in {"yes", "true", "1"}:
        return True
    if lowered.get("x-autorespond"):
        return True
    if "auto-reply" in lowered.get("x-mailer", "").lower():
        return True

    return False
