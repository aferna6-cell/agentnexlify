"""Tests for CSV lead import batching.

New leads must be inserted in ONE batched insert (not one insert per row),
with a per-row fallback when the batch fails. Existing-email rows still
update individually. Uses the JWT + mock-supabase pattern from
test_documents.py.
"""

import os
os.environ["TESTING"] = "1"

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_jwt(tenant_id="t1", role="owner", secret="test-secret-key-for-jwt"):
    from jose import jwt
    payload = {
        "tenant_id": tenant_id, "sub": tenant_id, "email": "o@e.com",
        "plan": "professional", "business_name": "Test Biz", "role": role,
        "is_team_member": False,
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def test_client(mock_settings):
    mock_settings.sentry_dsn = None
    mock_settings.supabase_service_key = "fake-key"
    db_mock = MagicMock()
    patches = [
        patch("backend.models.database.get_supabase", return_value=db_mock),
        patch("backend.routers.auth.get_service_supabase", return_value=db_mock),
        patch("backend.routers.auth.settings", mock_settings),
        patch("backend.routers.leads.get_service_supabase", return_value=db_mock),
        patch("backend.routers.leads.fire_event_background"),
    ]
    started = [p.start() for p in patches]
    fire_event_mock = started[4]
    from backend.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client, db_mock, fire_event_mock
    for p in patches:
        p.stop()


_CSV = "name,email,phone\nAlice,alice@e.com,111\nBob,bob@e.com,222\nCara,cara@e.com,333\n"


def _post_csv(client, csv_text):
    return client.post(
        "/api/v1/leads/t1/import",
        files={"file": ("leads.csv", csv_text.encode(), "text/csv")},
        headers={"Authorization": f"Bearer {_make_jwt()}"},
    )


class TestImportBatching:
    def test_new_leads_inserted_in_single_batch(self, test_client):
        client, db, fire_event_mock = test_client
        insert_payloads = []

        def mock_table(name):
            table = MagicMock()
            for m in ["select", "insert", "update", "eq", "in_", "limit", "order"]:
                getattr(table, m).return_value = table

            if name == "leads":
                def record_insert(rows):
                    insert_payloads.append(rows)
                    return table

                table.insert.side_effect = record_insert

                def execute_side_effect():
                    res = MagicMock()
                    if insert_payloads:
                        last = insert_payloads[-1]
                        rows = last if isinstance(last, list) else [last]
                        res.data = [
                            {"id": f"l{n}", "name": r.get("name"), "email": r.get("email")}
                            for n, r in enumerate(rows)
                        ]
                    else:
                        res.data = []  # dedup select → no existing leads
                    return res

                table.execute.side_effect = execute_side_effect
                return table

            result = MagicMock()
            result.data = []
            table.execute.return_value = result
            return table

        db.table = mock_table

        resp = _post_csv(client, _CSV)
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] == 3
        assert body["updated"] == 0
        assert body["total_errors"] == 0
        # ONE batched insert containing all 3 rows
        batch_attempts = [p for p in insert_payloads if isinstance(p, list)]
        assert len(insert_payloads) == 1
        assert len(batch_attempts) == 1
        assert len(batch_attempts[0]) == 3
        # lead.created fired once per created lead
        assert fire_event_mock.call_count == 3

    def test_batch_failure_falls_back_to_per_row(self, test_client):
        client, db, fire_event_mock = test_client
        insert_payloads = []

        def mock_table(name):
            table = MagicMock()
            for m in ["select", "insert", "update", "eq", "in_", "limit", "order"]:
                getattr(table, m).return_value = table

            if name == "leads":
                def record_insert(rows):
                    insert_payloads.append(rows)
                    return table

                table.insert.side_effect = record_insert

                def execute_side_effect():
                    res = MagicMock()
                    if not insert_payloads:
                        res.data = []  # dedup select
                        return res
                    last = insert_payloads[-1]
                    if isinstance(last, list):
                        raise RuntimeError("batch insert rejected")
                    res.data = [{"id": "l1", "name": last.get("name"), "email": last.get("email")}]
                    return res

                table.execute.side_effect = execute_side_effect
                return table

            result = MagicMock()
            result.data = []
            table.execute.return_value = result
            return table

        db.table = mock_table

        resp = _post_csv(client, _CSV)
        assert resp.status_code == 200
        body = resp.json()
        # Batch failed → per-row fallback inserted all 3 individually
        assert body["created"] == 3
        # 1 batch attempt + 3 per-row attempts
        batch_attempts = [p for p in insert_payloads if isinstance(p, list)]
        row_attempts = [p for p in insert_payloads if isinstance(p, dict)]
        assert len(batch_attempts) == 1
        assert len(row_attempts) == 3
        assert fire_event_mock.call_count == 3

    def test_existing_email_rows_update_not_insert(self, test_client):
        client, db, fire_event_mock = test_client
        insert_payloads = []
        update_count = {"n": 0}

        def mock_table(name):
            table = MagicMock()
            for m in ["select", "insert", "eq", "in_", "limit", "order"]:
                getattr(table, m).return_value = table

            if name == "leads":
                def record_insert(rows):
                    insert_payloads.append(rows)
                    return table

                def record_update(_payload):
                    update_count["n"] += 1
                    return table

                table.insert.side_effect = record_insert
                table.update.side_effect = record_update

                def execute_side_effect():
                    res = MagicMock()
                    if not insert_payloads:
                        # dedup select → Alice already exists
                        res.data = [{"id": "existing1", "email": "alice@e.com"}]
                        return res
                    last = insert_payloads[-1]
                    rows = last if isinstance(last, list) else [last]
                    res.data = [
                        {"id": f"new{n}", "name": r.get("name"), "email": r.get("email")}
                        for n, r in enumerate(rows)
                    ]
                    return res

                table.execute.side_effect = execute_side_effect
                return table

            table.update.return_value = table
            result = MagicMock()
            result.data = []
            table.execute.return_value = result
            return table

        db.table = mock_table

        resp = _post_csv(client, _CSV)
        assert resp.status_code == 200
        body = resp.json()
        assert body["updated"] == 1
        assert body["created"] == 2
        batch_attempts = [p for p in insert_payloads if isinstance(p, list)]
        assert len(batch_attempts) == 1
        assert len(batch_attempts[0]) == 2  # Bob + Cara only
        assert update_count["n"] == 1
        assert fire_event_mock.call_count == 2
