"""Router tests for /api/v1/integrations/keys (GH #132).

Calls the route coroutines directly with a claims dict (tenant from JWT, never
body) and monkeypatched vault + health-checker + a fake supabase client. Runs
in CI; local import may fail on missing deps — expected.
"""

import asyncio

import pytest
from fastapi import HTTPException

from backend.models.integration_key import SaveIntegrationKeyRequest
from backend.routers import integration_keys as ik

CLAIMS = {"tenant_id": "ten1"}


# --------------------------------------------------------------------------- #
# Fake supabase
# --------------------------------------------------------------------------- #


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self._db = db
        self._table = table
        self._op = "select"

    def select(self, *a, **k):
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, *a, **k):
        return self

    def in_(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._op == "delete":
            self._db.deletes.append(self._table)
            return _Result([])
        return _Result(list(self._db.rows.get(self._table, [])))


class _FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or {}
        self.deletes = []

    def table(self, name):
        return _Query(self, name)


def _use_db(monkeypatch, db):
    monkeypatch.setattr(ik, "get_service_supabase", lambda: db)


# --------------------------------------------------------------------------- #
# _overall_status
# --------------------------------------------------------------------------- #


def test_overall_status_levels():
    assert ik._overall_status([{"health": "green"}, {"health": "green"}]) == "healthy"
    assert ik._overall_status([{"health": "green"}, {"health": "yellow"}]) == "needs_attention"
    assert ik._overall_status([{"health": "green"}, {"health": "red"}]) == "not_ready"


# --------------------------------------------------------------------------- #
# POST /keys
# --------------------------------------------------------------------------- #


def test_save_key_happy(monkeypatch):
    monkeypatch.setattr(
        ik, "save_integration_key",
        lambda **kw: {"provider": "stripe", "masked": "ab••••yz", "enc_key_version": 1},
    )
    monkeypatch.setattr(
        ik, "check_provider",
        lambda t, p: {"health": "green", "detail": "OK", "last_verified_at": None},
    )
    out = asyncio.run(
        ik.save_key(SaveIntegrationKeyRequest(provider="Stripe", plaintext="k"), CLAIMS)
    )
    assert out.saved is True
    assert out.verified == "green"
    assert out.masked == "ab••••yz"


def test_save_key_rejects_unknown_provider():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ik.save_key(SaveIntegrationKeyRequest(provider="paypal", plaintext="k"), CLAIMS)
        )
    assert exc.value.status_code == 422


# --------------------------------------------------------------------------- #
# GET /keys
# --------------------------------------------------------------------------- #


def test_list_keys(monkeypatch):
    _use_db(monkeypatch, _FakeDB(rows={"integrations": [{"provider": "stripe", "metadata": {}}]}))
    monkeypatch.setattr(ik, "load_integration_key", lambda t, p: "secretvalue")
    monkeypatch.setattr(ik, "mask_key", lambda s: "se••••ue")
    monkeypatch.setattr(
        ik, "check_provider",
        lambda t, p: {"health": "green", "detail": "OK", "last_verified_at": "2026-06-15T00:00:00Z"},
    )
    out = asyncio.run(ik.list_keys(CLAIMS))
    assert len(out) == 1
    assert out[0]["provider"] == "stripe"
    assert out[0]["masked_key"] == "se••••ue"
    assert out[0]["health"] == "green"


# --------------------------------------------------------------------------- #
# DELETE /keys/{provider}
# --------------------------------------------------------------------------- #


def test_delete_stripe_active_subscription_409(monkeypatch):
    _use_db(
        monkeypatch,
        _FakeDB(rows={"tenants": [{"stripe_subscription_id": "sub_1", "plan_status": "active"}]}),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ik.delete_key("stripe", CLAIMS))
    assert exc.value.status_code == 409


def test_delete_stripe_no_active_subscription_ok(monkeypatch):
    db = _FakeDB(rows={"tenants": [{"stripe_subscription_id": "", "plan_status": "canceled"}]})
    _use_db(monkeypatch, db)
    out = asyncio.run(ik.delete_key("stripe", CLAIMS))
    assert out["deleted"] is True
    assert "integrations" in db.deletes


def test_delete_twilio_ok(monkeypatch):
    db = _FakeDB()
    _use_db(monkeypatch, db)
    out = asyncio.run(ik.delete_key("twilio", CLAIMS))
    assert out["deleted"] is True
    assert "integrations" in db.deletes


def test_delete_rejects_unknown_provider():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ik.delete_key("paypal", CLAIMS))
    assert exc.value.status_code == 422


# --------------------------------------------------------------------------- #
# POST /keys/{provider}/verify  (rate-limited; disable limiter for the unit test)
# --------------------------------------------------------------------------- #


def test_verify_key(monkeypatch):
    monkeypatch.setattr(ik.limiter, "enabled", False)
    monkeypatch.setattr(
        ik, "check_provider",
        lambda t, p: {"health": "green", "detail": "OK", "last_verified_at": None},
    )
    out = asyncio.run(ik.verify_key(object(), "resend", CLAIMS))
    assert out["health"] == "green"
    assert out["detail"] == "OK"


def test_verify_key_rejects_unknown_provider(monkeypatch):
    monkeypatch.setattr(ik.limiter, "enabled", False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(ik.verify_key(object(), "paypal", CLAIMS))
    assert exc.value.status_code == 422


# --------------------------------------------------------------------------- #
# GET /health
# --------------------------------------------------------------------------- #


def test_integrations_health_aggregate(monkeypatch):
    monkeypatch.setattr(
        ik, "check_all_providers",
        lambda t: [
            {"provider": "stripe", "health": "green", "detail": "OK", "last_verified_at": None},
            {"provider": "twilio", "health": "yellow", "detail": "test", "last_verified_at": None},
            {"provider": "resend", "health": "green", "detail": "OK", "last_verified_at": None},
            {"provider": "google_calendar", "health": "green", "detail": "OK", "last_verified_at": None},
        ],
    )
    out = asyncio.run(ik.integrations_health(CLAIMS))
    assert out.overall == "needs_attention"
    assert len(out.providers) == 4
