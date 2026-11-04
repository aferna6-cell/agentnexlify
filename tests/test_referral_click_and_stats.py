"""CI coverage for public referral links and click acknowledgements.

A valid anx_ key and an unknown one must return the same status and body.
An unknown key inserts no row. NULL or anx_ codes fall back to a link with
no ref, and the response never contains anx_.
"""

import logging
import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key-for-jwt")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-jwt")

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt

from backend.main import app
from backend.services.referral import referral_click_metrics

ROOT = Path(__file__).resolve().parents[1]
WIDGET_COPIES = (
    ROOT / "widget" / "agentnexlify-widget.js",
    ROOT / "frontend" / "public" / "widget" / "agentnexlify-widget.js",
    ROOT / "landing-page-v2" / "widget" / "agentnexlify-widget.js",
)
VALID_KEY = "anx_valid_widget_key_abc"
UNKNOWN_KEY = "anx_unknown_widget_key_zz"
PUBLIC_CODE = "ab12cd34"
TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _auth_headers():
    token = jwt.encode(
        {
            "tenant_id": TENANT_ID,
            "email": "owner@test.com",
            "plan": "growth",
            "business_name": "Test",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret-key-for-jwt",
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


class _Result:
    def __init__(self, data=None, count=0):
        self.data = data if data is not None else []
        self.count = count


class _Table:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.op = "select"
        self.payload = None
        self.filters = []

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def gte(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self.op == "insert":
            self.db.inserts.append(dict(self.payload))
            return _Result([])
        if self.name == "widget_configs":
            key = dict(self.filters).get("api_key")
            rows = [row for row in self.db.widgets if row.get("api_key") == key]
            return _Result(rows)
        if self.name == "tenants":
            wanted = dict(self.filters)
            if "id" in wanted:
                rows = [row for row in self.db.tenants if row.get("id") == wanted["id"]]
                return _Result(rows, count=len(rows))
            return _Result([], 0)
        if self.name == "referral_clicks":
            return _Result([], 0)
        if self.name == "referral_rewards":
            return _Result([], 0)
        return _Result([], 0)


class _DB:
    def __init__(self, *, widgets, tenants):
        self.widgets = widgets
        self.tenants = tenants
        self.inserts = []

    def table(self, name):
        return _Table(self, name)


def _client():
    return TestClient(app)


def test_widget_copies_are_byte_identical():
    blobs = [path.read_bytes() for path in WIDGET_COPIES]
    assert blobs[0] == blobs[1] == blobs[2]
    powered = blobs[0].split(b"anx-powered")[1][:400]
    assert b"encodeURIComponent(API_KEY)" not in powered
    assert b"ref=${" not in powered


def test_migration_202_does_not_add_a_second_unique_index():
    sql = (ROOT / "migrations" / "203_public_referral_codes.sql").read_text()
    assert "CREATE UNIQUE INDEX" not in sql
    assert "tenants_referral_code_key" in sql


def test_my_stats_never_returns_anx_for_null_or_widget_key():
    cases = (None, "", "anx_stored_widget_key")
    for raw in cases:
        db = _DB(
            widgets=[{"tenant_id": TENANT_ID, "api_key": VALID_KEY}],
            tenants=[{"id": TENANT_ID, "referral_code": raw}],
        )
        with patch("backend.routers.referral.get_service_supabase", return_value=db):
            response = _client().get("/api/v1/referral/my-stats", headers=_auth_headers())
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ref_code"] == ""
        assert "ref=" not in body["share_link"]
        assert "anx_" not in response.text
        assert all("anx_" not in str(value) for value in body.values())


def test_my_stats_public_code_link_has_no_widget_key():
    db = _DB(
        widgets=[{"tenant_id": TENANT_ID, "api_key": VALID_KEY}],
        tenants=[{"id": TENANT_ID, "referral_code": PUBLIC_CODE}],
    )
    with patch("backend.routers.referral.get_service_supabase", return_value=db):
        response = _client().get("/api/v1/referral/my-stats", headers=_auth_headers())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ref_code"] == PUBLIC_CODE
    assert f"ref={PUBLIC_CODE}" in body["share_link"]
    assert "anx_" not in response.text


def test_click_valid_and_unknown_anx_keys_return_the_same_body():
    db = _DB(
        widgets=[{"api_key": VALID_KEY, "tenant_id": TENANT_ID}],
        tenants=[{"id": TENANT_ID, "referral_code": PUBLIC_CODE}],
    )
    with patch("backend.routers.referral.get_service_supabase", return_value=db):
        client = _client()
        unknown = client.post(
            "/api/v1/referral/click",
            json={"ref": UNKNOWN_KEY, "path": "/pricing", "referrer": "https://example.com"},
        )
        assert db.inserts == []
        valid = client.post(
            "/api/v1/referral/click",
            json={"ref": VALID_KEY, "path": "/pricing", "referrer": "https://example.com"},
        )

    assert unknown.status_code == valid.status_code
    assert unknown.json() == valid.json()
    assert unknown.text == valid.text
    assert unknown.json() == {"ok": True}
    assert "anx_" not in unknown.text
    assert len(db.inserts) == 1
    assert db.inserts[0]["ref_tenant_id"] == PUBLIC_CODE
    assert VALID_KEY not in str(db.inserts[0])
    assert UNKNOWN_KEY not in str(db.inserts[0])


def test_pre_202_valid_click_is_recorded_and_logged(caplog):
    """A real key with no public code must not be dropped while returning ok.

    The click is stored under the tenant id, an error is logged, and
    referral_click_unrecordable_total increments. The widget key is not stored.
    """
    before = referral_click_metrics["referral_click_unrecordable_total"]
    for raw_code in (None, VALID_KEY):
        db = _DB(
            widgets=[{"api_key": VALID_KEY, "tenant_id": TENANT_ID}],
            tenants=[{"id": TENANT_ID, "referral_code": raw_code}],
        )
        with caplog.at_level(logging.ERROR, logger="backend.services.referral"):
            with patch("backend.routers.referral.get_service_supabase", return_value=db):
                response = _client().post(
                    "/api/v1/referral/click",
                    json={"ref": VALID_KEY, "path": "/pricing", "referrer": ""},
                )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert len(db.inserts) == 1
        assert db.inserts[0]["ref_tenant_id"] == TENANT_ID
        assert "anx_" not in str(db.inserts[0])
        assert "anx_" not in response.text
    assert referral_click_metrics["referral_click_unrecordable_total"] == before + 2
    errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert any("referral_click_unrecordable" in record.message for record in errors)
    assert any("metric=referral_click_unrecordable_total" in record.message for record in errors)
