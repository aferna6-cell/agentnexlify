"""Twilio inbound-SMS signature verification.

Twilio signs the webhook URL + sorted POST params with HMAC-SHA1 using
the account auth token as the key. The expected signature ships as the
``X-Twilio-Signature`` header (base64). We bind to the FULL URL the
provider hit (scheme + host + path + query), so any tampering of the
target URL invalidates the signature.

Reference:
    https://www.twilio.com/docs/usage/webhooks/webhooks-security

Spec: ``specs/agent-os-connectors-inbound_spec.md`` §SMS
Plan: ``plans/agent-os-connectors-inbound_plan.md`` Phase 5.1
"""

import base64
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def verify_twilio(
    url: str,
    form: dict[str, str],
    signature: str,
    auth_token: str,
) -> bool:
    """Verify a Twilio webhook signature.

    Spec: HMAC-SHA1 over ``url + "".join(f"{k}{v}" for k,v in sorted(form))``
    using ``auth_token`` as the HMAC key, base64-encoded, compared to
    ``X-Twilio-Signature``.

    Returns False on any missing input — never raises.
    """
    if not auth_token or not signature or not url:
        return False

    payload = url + "".join(f"{k}{form[k]}" for k in sorted(form))
    digest = hmac.new(
        auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(signature, expected)


_STOP_KEYWORDS = {"stop", "unsubscribe", "cancel", "stopall", "end", "quit"}


def is_stop_keyword(body: str) -> bool:
    """True if the SMS body is an opt-out keyword (case-insensitive, trimmed).

    Twilio carrier-level filters also catch STOP, but we mirror the keyword
    list so we can flip ``leads.unsubscribed`` for our own automations.
    Only match when the message IS the keyword — not when it contains it
    (otherwise legitimate replies like "STOP by the shop tomorrow" trip).
    """
    if not body:
        return False
    return body.strip().lower() in _STOP_KEYWORDS
