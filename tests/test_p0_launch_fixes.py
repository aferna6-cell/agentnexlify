"""Coverage for the 2026-07-09 launch-audit P0 fixes.

Covers the new branches added by the P0 remediation:
- appointments.ical_feed no longer emits customer PII (security H1)
- auth._provision_tenant_account rolls back the orphan tenant on failure (C2)
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Security H1 — iCal feed must not leak customer PII
# ---------------------------------------------------------------------------


def _table_mock(responses):
    """db.table(name) -> chainable mock whose .execute().data = responses[name]."""
    def mock_table(name):
        table = MagicMock()
        for method in (
            "select", "insert", "update", "delete", "eq", "neq",
            "gte", "lte", "gt", "lt", "limit", "order",
        ):
            getattr(table, method).return_value = table
        result = MagicMock()
        result.data = responses.get(name, [])
        table.execute.return_value = result
        return table

    db = MagicMock()
    db.table = mock_table
    return db


def test_ical_feed_omits_customer_pii():
    """The iCal feed is authenticated only by the public widget key, so it must
    return appointment time-blocks + status ONLY — never customer name/email/
    phone/notes."""
    from fastapi.testclient import TestClient

    db = _table_mock({
        "widget_configs": [{"tenant_id": "tenant-ical-1"}],
        "tenants": [{"business_name": "Acme Dental"}],
        "appointments": [{
            "id": "appt-1",
            "start_time": "2026-07-11T09:00:00Z",
            "end_time": "2026-07-11T10:00:00Z",
            "status": "confirmed",
        }],
    })

    with patch("backend.routers.appointments.get_service_supabase", return_value=db):
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/api/v1/appointments/tenant-ical-1/ical?key=anx_public_key")

    assert resp.status_code == 200
    body = resp.text
    # Calendar renders, but with a generic summary and no PII fields.
    assert "BEGIN:VCALENDAR" in body
    assert "SUMMARY:Appointment" in body
    assert "Email:" not in body
    assert "Phone:" not in body
    assert "Notes:" not in body


def test_ical_feed_rejects_bad_key():
    """An api_key that resolves to no widget_config is rejected (403)."""
    from fastapi.testclient import TestClient

    db = _table_mock({"widget_configs": []})
    with patch("backend.routers.appointments.get_service_supabase", return_value=db):
        from backend.main import app
        client = TestClient(app)
        resp = client.get("/api/v1/appointments/tenant-x/ical?key=nope")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Reliability C2 — signup rolls back the orphan tenant on provisioning failure
# ---------------------------------------------------------------------------


def _provision_db(*, widget_configs_fails: bool, delete_fails: bool = False):
    """db mock: tenants dedup->empty, insert->row; widget_configs insert fails.

    tenants db.table() calls happen in order: 1=dedup SELECT (no existing),
    2=INSERT (returns the new row), 3=DELETE (rollback). No conditional UPDATE
    fires because the test passes no phone/website_url. When delete_fails is set,
    the rollback DELETE itself raises (exercises the nested-except log path).
    """
    state = {"tenants_calls": 0, "deleted": False}

    def mock_table(name):
        table = MagicMock()
        for method in ("select", "insert", "update", "delete", "eq", "limit"):
            getattr(table, method).return_value = table

        if name == "tenants":
            state["tenants_calls"] += 1
            n = state["tenants_calls"]
            if n >= 3:  # the rollback DELETE
                state["deleted"] = True
                if delete_fails:
                    table.execute.side_effect = RuntimeError("delete boom")
                    return table
            r = MagicMock()
            r.data = [{"id": "tenant-new-1"}] if n == 2 else []
            table.execute.return_value = r
        elif name == "widget_configs" and widget_configs_fails:
            table.execute.side_effect = RuntimeError("boom")
        else:
            r = MagicMock()
            r.data = []
            table.execute.return_value = r
        return table

    db = MagicMock()
    db.table = mock_table
    return db, state


def test_provision_rolls_back_tenant_on_widget_config_failure():
    """C2: when widget_configs insert fails after the tenant row is created,
    the tenant is deleted (no orphan) and a 500 is raised."""
    from fastapi import HTTPException
    import backend.routers.auth as auth

    db, state = _provision_db(widget_configs_fails=True)
    with patch("backend.routers.auth.get_service_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            auth._provision_tenant_account(
                business_name="Acme",
                owner_name="Owner",
                email="owner@example.com",
                password_hash="x",
                industry="dental",
                city="Austin",
            )
    assert exc.value.status_code == 500
    assert state["deleted"], "orphan tenant row must be deleted on rollback"


def test_provision_rollback_delete_failure_still_raises_500():
    """If the rollback DELETE itself fails, provisioning still surfaces a 500
    (the nested-except only logs; it does not swallow the outer failure)."""
    from fastapi import HTTPException
    import backend.routers.auth as auth

    db, state = _provision_db(widget_configs_fails=True, delete_fails=True)
    with patch("backend.routers.auth.get_service_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc:
            auth._provision_tenant_account(
                business_name="Acme",
                owner_name="Owner",
                email="owner2@example.com",
                password_hash="x",
                industry="dental",
                city="Austin",
            )
    assert exc.value.status_code == 500
    assert state["deleted"], "rollback DELETE must be attempted even if it fails"
