"""Tests for widget booking-token auth (#120 security core).

Deterministic — secret + now injected. Runs standalone:
    python3 -m pytest backend/tests/test_widget_booking_auth.py -v --noconftest
"""

from datetime import datetime, timedelta, timezone

from backend.services import widget_booking_auth as auth

SECRET = "tenant_api_key_secret_value"
NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# mint + verify round-trip                                                     #
# --------------------------------------------------------------------------- #
def test_mint_then_verify_roundtrip_returns_claims():
    token = auth.mint_booking_token(SECRET, now=NOW, jti="fixed-jti")
    claims = auth.verify_booking_token(token, SECRET, now=NOW)
    assert claims is not None
    assert claims["jti"] == "fixed-jti"
    assert claims["scope"] == "widget_booking"


def test_verify_within_window_ok():
    token = auth.mint_booking_token(SECRET, now=NOW)
    # 4 minutes later — still inside the 5-minute window
    later = NOW + timedelta(minutes=4)
    assert auth.verify_booking_token(token, SECRET, now=later) is not None


# --------------------------------------------------------------------------- #
# rejection paths (all -> None -> 401)                                          #
# --------------------------------------------------------------------------- #
def test_expired_token_rejected():
    token = auth.mint_booking_token(SECRET, now=NOW)
    # 6 minutes later — past the 5-minute expiry
    later = NOW + timedelta(minutes=6)
    assert auth.verify_booking_token(token, SECRET, now=later) is None


def test_exactly_at_expiry_is_rejected():
    token = auth.mint_booking_token(SECRET, ttl_seconds=300, now=NOW)
    at_exp = NOW + timedelta(seconds=300)
    assert auth.verify_booking_token(token, SECRET, now=at_exp) is None


def test_wrong_secret_rejected():
    token = auth.mint_booking_token(SECRET, now=NOW)
    assert auth.verify_booking_token(token, "different-secret", now=NOW) is None


def test_tampered_token_rejected():
    token = auth.mint_booking_token(SECRET, now=NOW)
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")
    assert auth.verify_booking_token(tampered, SECRET, now=NOW) is None


def test_garbage_token_rejected():
    assert auth.verify_booking_token("not.a.jwt", SECRET, now=NOW) is None
    assert auth.verify_booking_token("", SECRET, now=NOW) is None


# --------------------------------------------------------------------------- #
# jti hourly rate limit                                                        #
# --------------------------------------------------------------------------- #
def test_jti_allows_up_to_limit_then_blocks():
    jti = "rate-jti-1"
    for i in range(1, 6):  # 5 allowed
        allowed, count = auth.check_jti_rate(jti, now=NOW)
        assert allowed is True, i
        assert count == i
    # 6th within the same hour is blocked
    allowed, count = auth.check_jti_rate(jti, now=NOW)
    assert allowed is False
    assert count == 6


def test_jti_resets_next_hour():
    jti = "rate-jti-2"
    for _ in range(6):
        auth.check_jti_rate(jti, now=NOW)
    # next hour — counter resets
    next_hour = NOW + timedelta(hours=1)
    allowed, count = auth.check_jti_rate(jti, now=next_hour)
    assert allowed is True
    assert count == 1


def test_distinct_jtis_are_independent():
    a_allowed, _ = auth.check_jti_rate("jti-A", now=NOW)
    b_allowed, _ = auth.check_jti_rate("jti-B", now=NOW)
    assert a_allowed and b_allowed
