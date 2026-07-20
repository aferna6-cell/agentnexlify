"""Activity CSV export (enterprise-audit item 7) — shape + masking contracts."""

import asyncio
from unittest.mock import MagicMock, patch

from backend.routers import activity_export


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, calls):
        self._rows = rows
        self._calls = calls

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._calls.append((name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows, calls):
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(rows, calls)
    return db


class TestRenderCsv:
    def test_columns_and_metadata_json(self):
        csv_text = activity_export.render_csv(
            [
                {
                    "created_at": "2026-07-20T10:00:00Z",
                    "activity_type": "sms_sent",
                    "description": "Sent booking reminder",
                    "lead_id": "lead-1",
                    "metadata": {"channel": "sms"},
                }
            ]
        )
        lines = csv_text.strip().splitlines()
        assert lines[0] == "created_at,activity_type,description,lead_id,metadata"
        assert "sms_sent" in lines[1]
        assert '""channel"": ""sms""' in lines[1]

    def test_phone_masked_in_metadata(self):
        csv_text = activity_export.render_csv(
            [
                {
                    "created_at": "2026-07-20T10:00:00Z",
                    "activity_type": "call",
                    "description": "Inbound call",
                    "lead_id": None,
                    "metadata": {"caller": "+12345557890"},
                }
            ]
        )
        assert "5557890" not in csv_text.replace("****", "")
        assert "****7890" in csv_text

    def test_empty_rows_yield_header_only(self):
        assert activity_export.render_csv([]).strip() == (
            "created_at,activity_type,description,lead_id,metadata"
        )


class TestExportEndpoint:
    def test_export_scopes_to_tenant_and_returns_csv(self):
        calls: list = []
        rows = [
            {
                "created_at": "2026-07-20T10:00:00Z",
                "activity_type": "lead_created",
                "description": "New lead",
                "lead_id": "l1",
                "metadata": {},
            }
        ]
        with patch.object(
            activity_export, "get_service_supabase", return_value=_db(rows, calls)
        ):
            response = asyncio.run(
                activity_export.export_activity(claims={"tenant_id": "t-42"})
            )
        assert response.media_type == "text/csv"
        assert ("eq", ("tenant_id", "t-42")) in calls
        assert "attachment" in response.headers["content-disposition"]

    def test_invalid_since_rejected(self):
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as err:
            asyncio.run(
                activity_export.export_activity(
                    claims={"tenant_id": "t-42"}, since="not-a-date"
                )
            )
        assert err.value.status_code == 422

    def test_pagination_stops_on_short_page(self):
        calls: list = []
        rows = [
            {
                "created_at": "2026-07-20T10:00:00Z",
                "activity_type": "x",
                "description": "y",
                "lead_id": None,
                "metadata": {},
            }
        ]
        db = _db(rows, calls)
        fetched = activity_export._fetch_rows(db, "t-1", None, None)
        assert len(fetched) == 1
        # One page only — the short page ended the loop.
        assert sum(1 for name, _ in calls if name == "range") == 1
