"""Vault wiring in the OAuth integration services (GH #266 step 2).

google_calendar / m365_calendar / hubspot_tenant must route reads through
decrypt_integration_row and writes through encrypt_oauth_tokens. With no
encryption key configured (prod today) both are strict no-ops, so these tests
assert the wiring is invoked, not the crypto (covered in the vault tests).
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services import google_calendar, hubspot_tenant, m365_calendar

SERVICES = [google_calendar, m365_calendar, hubspot_tenant]


def _db_with_row(row):
    result = MagicMock()
    result.data = [row] if row is not None else []
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = result
    db = MagicMock()
    db.table.return_value = chain
    return db, chain


@pytest.mark.parametrize("svc", SERVICES, ids=lambda s: s.__name__.split(".")[-1])
def test_get_integration_routes_through_decrypt(svc):
    row = {"id": "i-1", "access_token": "plain-at", "access_token_enc": None}
    db, _ = _db_with_row(row)
    with patch.object(svc, "get_service_supabase", return_value=db), patch.object(
        svc, "decrypt_integration_row", side_effect=lambda r: dict(r, marked=True)
    ) as dec:
        out = svc.get_integration("t1")
    dec.assert_called_once()
    assert out["marked"] is True


@pytest.mark.parametrize("svc", SERVICES, ids=lambda s: s.__name__.split(".")[-1])
def test_get_integration_none_when_no_row(svc):
    db, _ = _db_with_row(None)
    with patch.object(svc, "get_service_supabase", return_value=db):
        assert svc.get_integration("t1") is None


@pytest.mark.parametrize("svc", SERVICES, ids=lambda s: s.__name__.split(".")[-1])
def test_save_integration_routes_through_encrypt(svc):
    db, chain = _db_with_row(None)  # no existing row -> insert path
    with patch.object(svc, "get_service_supabase", return_value=db), patch.object(
        svc, "encrypt_oauth_tokens", side_effect=lambda p: dict(p, enc_marker=True)
    ) as enc:
        svc.save_integration(
            tenant_id="t1",
            access_token="at",
            refresh_token="rt",
            token_expiry="2026-07-14T00:00:00+00:00",
        )
    enc.assert_called_once()
    inserted = chain.insert.call_args.args[0]
    assert inserted["enc_marker"] is True
    assert inserted["access_token"] == "at"  # plaintext retained pre-sunset


@pytest.mark.parametrize("svc", SERVICES, ids=lambda s: s.__name__.split(".")[-1])
def test_save_integration_updates_existing_row(svc):
    existing = {"id": "i-9", "access_token": "old"}
    db, chain = _db_with_row(existing)
    with patch.object(svc, "get_service_supabase", return_value=db):
        svc.save_integration(
            tenant_id="t1",
            access_token="new-at",
            refresh_token="new-rt",
            token_expiry="2026-07-14T00:00:00+00:00",
            metadata={"scope": "calendar"},
        )
    updated = chain.update.call_args.args[0]
    assert updated["access_token"] == "new-at"
    assert updated["metadata"] == {"scope": "calendar"}
