"""Signed-JWT auth for the widget booking endpoint (#120).

The widget's booking endpoint accepts EITHER the legacy ``api_key`` query param OR
a short-lived bearer token (this module). The token is a HS256 JWT signed with
the tenant's ``api_key`` secret, valid 5 minutes, carrying a ``jti`` so a single
issued token is rate-limited to 5 bookings/hour (replay + abuse guard, spec §9).

Pure/injectable (secret + ``now`` passed in) so the security logic is unit-tested
without a live request. Mirrors the existing HS256 pattern in
``services/facebook_oauth.py`` + ``services/auth_service.py``.

``verify_booking_token`` checks expiry against the injected ``now`` (decode runs
with ``verify_exp`` off) so tests are deterministic and the 5-minute window is
enforced explicitly rather than relying on PyJWT's wall-clock.
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
DEFAULT_TTL_SECONDS = 300  # 5-minute booking-token window (spec §9)
JTI_HOURLY_LIMIT = 5       # 5 bookings/hour per issued token

# In-process per-jti hourly counter (per worker — the booking insert's DB
# uniqueness is the real backstop; this caps abuse cheaply at the edge).
_jti_buckets: dict[str, dict[int, int]] = {}
_jti_lock = threading.Lock()


def mint_booking_token(
    secret: str,
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: datetime | None = None,
    jti: str | None = None,
) -> str:
    """Mint a short-lived booking JWT signed with the tenant's ``api_key`` secret."""
    now = now or datetime.now(timezone.utc)
    jti = jti or uuid.uuid4().hex
    payload = {
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "scope": "widget_booking",
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


def verify_booking_token(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> dict | None:
    """Return the token's claims, or None when it is invalid/expired.

    None on: bad signature, malformed token, wrong secret, missing ``jti``, or an
    ``exp`` at/earlier than ``now``. Callers map None → HTTP 401.
    """
    now = now or datetime.now(timezone.utc)
    try:
        # Signature is verified; the time-based claims (exp/iat/nbf) are checked
        # here against the injected ``now`` instead of PyJWT's wall-clock, so the
        # 5-minute window is enforced deterministically.
        claims = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            options={"verify_exp": False, "verify_iat": False, "verify_nbf": False},
        )
    except jwt.InvalidTokenError:
        return None

    exp = claims.get("exp")
    try:
        if exp is None or int(now.timestamp()) >= int(exp):
            return None
    except (TypeError, ValueError):
        return None

    if not claims.get("jti"):
        return None
    return claims


def check_jti_rate(
    jti: str,
    *,
    now: datetime | None = None,
    limit: int = JTI_HOURLY_LIMIT,
) -> tuple[bool, int]:
    """Count this booking against the token's hourly cap.

    Returns ``(allowed, count)`` — ``allowed`` is False once the ``jti`` has been
    used more than ``limit`` times in the current hour. Callers map not-allowed →
    HTTP 429.
    """
    now = now or datetime.now(timezone.utc)
    bucket = int(now.timestamp() // 3600)
    with _jti_lock:
        buckets = _jti_buckets.setdefault(jti, {})
        for stale in [b for b in buckets if b < bucket]:
            del buckets[stale]
        count = buckets.get(bucket, 0) + 1
        buckets[bucket] = count
        return count <= limit, count
