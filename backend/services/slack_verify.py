"""Slack request signature verification for the agent-team events endpoint.

Slack signs every request with HMAC-SHA256 over
``v0:{X-Slack-Request-Timestamp}:{raw body}`` using the app's signing
secret, and ships the result as ``X-Slack-Signature`` (``v0=<hex>``).

Reference: https://api.slack.com/authentication/verifying-requests-from-slack

Two properties matter here and are enforced separately:

1. **Authenticity** — the HMAC must match. Without this, anyone who finds
   the public webhook URL can make the bot spend Anthropic credits.
2. **Freshness** — the timestamp must be within ``max_age_seconds``. A
   captured request stays validly signed forever otherwise, so a replay
   would let an attacker re-trigger an old prompt indefinitely. Slack's
   own guidance is a 5-minute window.
"""

import hashlib
import hmac
import logging
import time

logger = logging.getLogger(__name__)

_MAX_AGE_SECONDS = 300


def verify_slack_signature(
    *,
    raw_body: bytes,
    timestamp: str,
    signature: str,
    signing_secret: str,
    max_age_seconds: int = _MAX_AGE_SECONDS,
    now: float | None = None,
) -> bool:
    """Verify a Slack ``X-Slack-Signature`` header against the raw body.

    ``raw_body`` must be the exact bytes Slack sent — re-serializing the
    parsed JSON changes key order and whitespace and breaks the HMAC.

    Returns False on any missing/oversized/malformed input. Never raises.
    """
    if not signing_secret or not signature or not timestamp:
        return False

    try:
        sent_at = float(timestamp)
    except (TypeError, ValueError):
        return False

    current = time.time() if now is None else now
    if abs(current - sent_at) > max_age_seconds:
        logger.warning(
            "slack signature rejected: stale timestamp age=%.0fs max=%ds",
            abs(current - sent_at),
            max_age_seconds,
        )
        return False

    basestring = b"v0:" + timestamp.encode("utf-8") + b":" + raw_body
    digest = hmac.new(
        signing_secret.encode("utf-8"), basestring, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"v0={digest}", signature)
