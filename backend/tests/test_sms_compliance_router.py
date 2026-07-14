"""Tests for the SMS compliance dashboard router (GH #385).

Covers the acceptance criteria from the issue:
  - GET /api/v1/sms-compliance/opt-outs returns paginated, MASKED numbers
  - GET /api/v1/sms-compliance/stats returns the opt-out count
  - POST /opt-out and /opt-in record via the sms_compliance service
  - invalid phone → 400, missing/bad auth → 401/422
"""

from unittest.mock import MagicMock, patch

from backend.tests.conftest import _make_auth_token

TENANT_ID = "00000000-0000-0000-0000-000000000001"
BASE = "/api/v1/sms-compliance"


def _auth_headers(tenant_id=TENANT_ID):
    token = _make_auth_token(tenant_id)
    return {"Authorization": f"Bearer {token}"}


def _wire_list_result(mock_supabase, rows, count):
    result = MagicMock()
    result.data = rows
    result.count = count
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.execute.return_value = result
    mock_supabase.table.return_value = chain
    return chain


class TestListOptOuts:
    def test_requires_auth(self, client):
        resp = client.get(f"{BASE}/opt-outs")
        assert resp.status_code in (401, 422)

    def test_masks_phone_numbers(self, client, mock_supabase):
        _wire_list_result(
            mock_supabase,
            rows=[
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "phone_last10": "9145551234",
                    "source": "sms_stop",
                    "created_at": "2026-07-01T00:00:00+00:00",
                }
            ],
            count=1,
        )
        resp = client.get(f"{BASE}/opt-outs", headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["phone_masked"] == "***-***-1234"
        # Full number must never appear anywhere in the response
        assert "9145551234" not in resp.text

    def test_empty_ledger(self, client, mock_supabase):
        _wire_list_result(mock_supabase, rows=[], count=0)
        resp = client.get(f"{BASE}/opt-outs", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_scopes_query_to_client_id(self, client, mock_supabase):
        chain = _wire_list_result(mock_supabase, rows=[], count=0)
        client.get(f"{BASE}/opt-outs", headers=_auth_headers())
        # sms_opt_outs is a client_id table (CLAUDE.md invariant #1)
        chain.eq.assert_called_with("client_id", TENANT_ID)


class TestStats:
    def test_returns_count(self, client, mock_supabase):
        _wire_list_result(mock_supabase, rows=[], count=7)
        resp = client.get(f"{BASE}/stats", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"total_opt_outs": 7}


class TestManualOverrides:
    def test_opt_out_records(self, client, mock_supabase):
        with patch("backend.routers.sms_compliance.record_opt_out") as rec:
            resp = client.post(
                f"{BASE}/opt-out",
                headers=_auth_headers(),
                json={"phone": "+1 (914) 555-1234"},
            )
        assert resp.status_code == 200, resp.text
        rec.assert_called_once()
        args, kwargs = rec.call_args
        assert args[1] == TENANT_ID
        assert args[2] == "+1 (914) 555-1234"
        assert kwargs.get("source") == "manual_dashboard"

    def test_opt_in_records(self, client, mock_supabase):
        with patch("backend.routers.sms_compliance.record_opt_in") as rec:
            resp = client.post(
                f"{BASE}/opt-in",
                headers=_auth_headers(),
                json={"phone": "9145551234"},
            )
        assert resp.status_code == 200, resp.text
        rec.assert_called_once()

    def test_invalid_phone_rejected(self, client, mock_supabase):
        resp = client.post(
            f"{BASE}/opt-out", headers=_auth_headers(), json={"phone": "n/a"}
        )
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.post(f"{BASE}/opt-out", json={"phone": "9145551234"})
        assert resp.status_code in (401, 422)
