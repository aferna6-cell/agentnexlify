"""Tests for GET /api/v1/referral/my-stats."""

import pytest
from unittest.mock import MagicMock, patch

from backend.tests.conftest import _make_auth_token


TENANT_ID = "00000000-0000-0000-0000-000000000001"
PUBLIC_CODE = "ab12cd34"
LEGACY_KEY = "anx_test_api_key_abc123"
STATS_URL = "/api/v1/referral/my-stats"


def _auth_headers(tenant_id=TENANT_ID):
    token = _make_auth_token(tenant_id)
    return {"Authorization": f"Bearer {token}"}


def _mock_chain(
    mock_supabase,
    *,
    referral_code=PUBLIC_CODE,
    wc_data=None,
    total_count,
    last_7d_count,
    last_30d_count,
    signups_count=0,
):
    """Sequence the DB calls inside get_my_referral_stats.

    With a legacy anx_ key present the order is:
      1. tenants.referral_code
      2. widget_configs.api_key
      3-4. clicks total (public, then legacy — legacy mocked as 0)
      5-6. clicks 7d
      7-8. clicks 30d
      9. signups referred_by
      10. signups legacy key (mocked as 0)
      11. referral_rewards
    """
    if wc_data is None:
        wc_data = [{"api_key": LEGACY_KEY}]

    def _make_result(data, count):
        r = MagicMock()
        r.data = data
        r.count = count
        return r

    zero = _make_result([], 0)
    tenant_result = _make_result([{"referral_code": referral_code}], 1)
    wc_result = _make_result(wc_data, len(wc_data))
    has_legacy = bool(wc_data and str(wc_data[0].get("api_key") or "").startswith("anx_"))
    rewards_result = _make_result([], 0)

    sequence = [tenant_result, wc_result]
    if has_legacy:
        sequence.extend([
            _make_result([], total_count),
            zero,
            _make_result([], last_7d_count),
            zero,
            _make_result([], last_30d_count),
            zero,
            _make_result([], signups_count),
            zero,
            rewards_result,
        ])
    else:
        sequence.extend([
            _make_result([], total_count),
            _make_result([], last_7d_count),
            _make_result([], last_30d_count),
            _make_result([], signups_count),
            rewards_result,
        ])

    execute_mock = MagicMock(side_effect=sequence)

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.limit.return_value = chain
    chain.execute = execute_mock

    mock_supabase.table.return_value = chain
    return execute_mock


class TestGetMyReferralStats:
    """GET /api/v1/referral/my-stats"""

    def test_no_auth_returns_422(self, client):
        """Missing Authorization header → 422 (required header absent)."""
        resp = client.get(STATS_URL)
        assert resp.status_code in (401, 422)

    def test_invalid_token_returns_401(self, client):
        """Malformed token → 401."""
        resp = client.get(STATS_URL, headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401

    def test_happy_path_returns_stats(self, client, mock_supabase):
        """Valid auth + widget config → correct counts and share_link."""
        _mock_chain(
            mock_supabase,
            wc_data=[{"api_key": LEGACY_KEY}],
            total_count=42,
            last_7d_count=10,
            last_30d_count=30,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert body["ref_code"] == PUBLIC_CODE
        assert body["share_link"] == f"https://agentnexlify.com?ref={PUBLIC_CODE}&utm_source=widget"
        assert LEGACY_KEY not in resp.text
        assert body["total_clicks"] == 42
        assert body["clicks_last_7d"] == 10
        assert body["clicks_last_30d"] == 30

    def test_secret_shaped_code_falls_back_to_link_without_ref(self, client, mock_supabase):
        """NULL or anx_ codes (pre-202 rows) do not leak and have no ref=."""
        _mock_chain(
            mock_supabase,
            referral_code=LEGACY_KEY,
            wc_data=[],
            total_count=0,
            last_7d_count=0,
            last_30d_count=0,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ref_code"] == ""
        assert "ref=" not in body["share_link"]
        assert "anx_" not in resp.text

    def test_zero_clicks_returns_zeros(self, client, mock_supabase):
        """Widget exists but no clicks yet → all counts 0."""
        _mock_chain(
            mock_supabase,
            wc_data=[{"api_key": LEGACY_KEY}],
            total_count=0,
            last_7d_count=0,
            last_30d_count=0,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_clicks"] == 0
        assert body["clicks_last_7d"] == 0
        assert body["clicks_last_30d"] == 0

    def test_db_error_on_widget_lookup_returns_500(self, client, mock_supabase):
        """DB failure when fetching widget_configs → 500."""
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.side_effect = Exception("DB connection error")
        mock_supabase.table.return_value = chain

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 500

    def test_db_error_on_click_aggregation_returns_500(self, client, mock_supabase):
        """DB failure during click count queries → 500."""
        tenant_result = MagicMock()
        tenant_result.data = [{"referral_code": PUBLIC_CODE}]
        tenant_result.count = 1
        wc_result = MagicMock()
        wc_result.data = [{"api_key": LEGACY_KEY}]
        wc_result.count = 1

        execute_mock = MagicMock(side_effect=[
            tenant_result,
            wc_result,
            Exception("DB error on count"),
        ])

        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.limit.return_value = chain
        chain.execute = execute_mock

        mock_supabase.table.return_value = chain

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 500

    def test_response_schema_fields_present(self, client, mock_supabase):
        """Response contains all expected fields, including referral-reward earnings.

        rewards_count + rewards_earned_cents added 2026-06-23 with the referral
        reward feature (flat $20 credit to the referrer on the referee's first
        paid invoice). The contract intentionally grew — keys updated to match.
        """
        _mock_chain(
            mock_supabase,
            wc_data=[{"api_key": LEGACY_KEY}],
            total_count=5,
            last_7d_count=2,
            last_30d_count=4,
            signups_count=3,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {
            "ref_code", "share_link", "total_clicks",
            "clicks_last_7d", "clicks_last_30d", "referred_signups",
            "rewards_count", "rewards_earned_cents",
        }

    def test_referred_signups_count_returned(self, client, mock_supabase):
        """(c) my-stats returns referred_signups count from tenants table."""
        _mock_chain(
            mock_supabase,
            wc_data=[{"api_key": LEGACY_KEY}],
            total_count=100,
            last_7d_count=20,
            last_30d_count=60,
            signups_count=7,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["referred_signups"] == 7

    def test_referred_signups_zero_when_none(self, client, mock_supabase):
        """referred_signups is 0 when no tenants have referred_by_widget_key set."""
        _mock_chain(
            mock_supabase,
            wc_data=[{"api_key": LEGACY_KEY}],
            total_count=10,
            last_7d_count=3,
            last_30d_count=8,
            signups_count=0,
        )

        resp = client.get(STATS_URL, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["referred_signups"] == 0
