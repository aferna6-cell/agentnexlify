"""GH #266 step 2 — every `integrations` token reader routes rows through the
vault overlay (`decrypt_integration_row`) instead of trusting the plaintext
columns.

The vault itself is covered to 100% in test_integration_key_vault.py; these
tests pin the WIRING at the two readers that previously bypassed it
(twilio_tenant.get_integration, os_actions.gbp._load_gbp), so the
plaintext-column sunset cannot silently break them.
"""

from unittest.mock import MagicMock, patch

from backend.services import twilio_tenant
from backend.services.os_actions import gbp


class _Chain:
    def __init__(self, result):
        self._result = result

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _method(*args, **kwargs):
            if name == "execute":
                return self._result
            return self

        return _method


def _seed_rows(mock_supabase, rows):
    tbl = MagicMock()
    tbl.select.side_effect = lambda *a, **k: _Chain(MagicMock(data=rows))
    mock_supabase.table.side_effect = lambda name: tbl


class TestTwilioTenantReader:
    def test_get_integration_routes_through_vault(self, mock_supabase):
        raw = {
            "tenant_id": "t1",
            "provider": "twilio_byo",
            "access_token": "ACplain",
            "refresh_token": "authplain",
            "metadata": {"phone_number": "+15550001111"},
        }
        overlaid = {**raw, "access_token": "ACdecrypted"}
        _seed_rows(mock_supabase, [raw])
        with patch(
            "backend.services.twilio_tenant.decrypt_integration_row",
            return_value=overlaid,
        ) as vault:
            row = twilio_tenant.get_integration("t1")
        vault.assert_called_once_with(raw)
        assert row["access_token"] == "ACdecrypted"

    def test_get_integration_none_when_no_row(self, mock_supabase):
        _seed_rows(mock_supabase, [])
        assert twilio_tenant.get_integration("t1") is None


class TestGbpReader:
    def test_load_gbp_routes_through_vault(self, mock_supabase):
        raw = {
            "access_token": "plain-token",
            "access_token_enc": b"\\x00",
            "metadata": {"location_id": "loc1", "account_id": "acc1"},
        }
        overlaid = {**raw, "access_token": "decrypted-token"}
        _seed_rows(mock_supabase, [raw])
        with patch(
            "backend.services.os_actions.gbp.decrypt_integration_row",
            return_value=overlaid,
        ) as vault:
            result = gbp._load_gbp("t1")
        vault.assert_called_once_with(raw)
        assert result == {
            "access_token": "decrypted-token",
            "account_id": "acc1",
            "location_id": "loc1",
        }

    def test_load_gbp_selects_encrypted_column(self, mock_supabase):
        captured = {}
        tbl = MagicMock()

        def _select(*args, **kwargs):
            captured["cols"] = args[0] if args else ""
            return _Chain(MagicMock(data=[]))

        tbl.select.side_effect = _select
        mock_supabase.table.return_value = tbl
        mock_supabase.table.side_effect = None
        assert gbp._load_gbp("t1") is None
        assert "access_token_enc" in captured["cols"]

    def test_load_gbp_none_when_incomplete(self, mock_supabase):
        raw = {"access_token": "tok", "metadata": {}}
        _seed_rows(mock_supabase, [raw])
        with patch(
            "backend.services.os_actions.gbp.decrypt_integration_row",
            return_value=raw,
        ):
            assert gbp._load_gbp("t1") is None
