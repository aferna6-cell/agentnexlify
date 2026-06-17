"""Unit tests for the Front Desk Health analytics endpoint.

Covers:
- Response shape (all expected keys present).
- Capture rate + sentiment + intent + KB-gap aggregation from conversation rows.
- Pre-migration zero-fallback: when the sentiment/intent columns do not exist,
  the first select raises and the handler retries without them, returning zeros
  for the breakdowns while still reporting count + capture rate.
- A hard DB failure returns zeros, never a 500.
- Tenant verification runs (verify_tenant raises -> handler raises).

The handler is exercised directly (not through the ASGI app) with a chained
supabase-py builder stub so the test stays a fast, deterministic unit test.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.routers.analytics import front_desk_health as fdh

_TENANT = "00000000-0000-0000-0000-000000000001"
_CLAIMS = {"tenant_id": _TENANT}


class _Builder:
    """Chained supabase-py builder stub.

    ``rows`` is the canned conversations data. When ``fail_with_columns`` is set
    and the select string contains "sentiment", execute() raises -- emulating a
    pre-migration database missing the sentiment/intent columns. The handler's
    retry select (without those columns) then succeeds.
    """

    def __init__(self, rows, fail_with_columns):
        self._rows = rows
        self._fail_with_columns = fail_with_columns
        self._selected_optional = False

    def select(self, columns="*", **kwargs):
        self._selected_optional = "sentiment" in columns
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._fail_with_columns and self._selected_optional:
            raise RuntimeError("column conversations.sentiment does not exist")
        return SimpleNamespace(data=self._rows, count=len(self._rows))


def _run(rows, *, fail_with_columns=False, raise_always=False):
    db = MagicMock(name="db")

    def _table(_name):
        if raise_always:
            b = MagicMock()
            b.select.return_value = b
            b.eq.return_value = b
            b.gte.return_value = b
            b.limit.return_value = b
            b.execute.side_effect = RuntimeError("db down")
            return b
        return _Builder(rows, fail_with_columns)

    # tenant_table wraps db.table; the stub builder ignores the scope wrapper,
    # so patch tenant_table to return our builder directly.
    with patch.object(fdh, "get_service_supabase", return_value=db), patch.object(
        fdh, "tenant_table", side_effect=lambda _db, _t, _tid: _table(_t)
    ), patch.object(fdh, "verify_tenant"), patch.object(
        fdh, "_get_cached", return_value=None
    ), patch.object(fdh, "_set_cache"):
        return asyncio.run(
            fdh.get_front_desk_health(_TENANT, period="30d", claims=_CLAIMS)
        )


def test_shape_has_all_keys():
    result = _run([])
    for key in (
        "period",
        "total_conversations",
        "leads_captured",
        "capture_rate",
        "sentiment_breakdown",
        "top_intents",
        "kb_gap_count",
        "classification_available",
    ):
        assert key in result
    assert result["sentiment_breakdown"] == {
        "positive": 0,
        "neutral": 0,
        "negative": 0,
    }
    assert result["top_intents"] == []


def test_capture_rate_and_aggregation():
    rows = [
        {"id": "1", "lead_captured": True, "sentiment": "positive", "intent": "booking request"},
        {"id": "2", "lead_captured": False, "sentiment": "neutral", "intent": "pricing question"},
        {"id": "3", "lead_captured": False, "sentiment": "negative", "intent": "complaint"},
        {"id": "4", "lead_captured": True, "sentiment": "positive", "intent": "booking request"},
    ]
    result = _run(rows)

    assert result["total_conversations"] == 4
    assert result["leads_captured"] == 2
    assert result["capture_rate"] == 50.0
    assert result["sentiment_breakdown"] == {"positive": 2, "neutral": 1, "negative": 1}
    # Top intent is the most common one.
    assert result["top_intents"][0] == {"intent": "booking request", "count": 2}
    # KB gap: negative sentiment + no lead captured -> 1.
    assert result["kb_gap_count"] == 1
    assert result["classification_available"] is True


def test_kb_gap_excludes_negative_with_lead():
    rows = [
        {"id": "1", "lead_captured": True, "sentiment": "negative", "intent": "complaint"},
    ]
    result = _run(rows)
    # Negative but a lead WAS captured -> not counted as a KB gap.
    assert result["kb_gap_count"] == 0


def test_pre_migration_zero_fallback():
    # The first select (with sentiment/intent) raises; the handler retries with
    # only id + lead_captured. Count + capture rate still work; breakdowns zero.
    rows = [
        {"id": "1", "lead_captured": True},
        {"id": "2", "lead_captured": False},
    ]
    result = _run(rows, fail_with_columns=True)

    assert result["total_conversations"] == 2
    assert result["leads_captured"] == 1
    assert result["capture_rate"] == 50.0
    assert result["sentiment_breakdown"] == {"positive": 0, "neutral": 0, "negative": 0}
    assert result["top_intents"] == []
    assert result["kb_gap_count"] == 0
    assert result["classification_available"] is False


def test_hard_db_failure_returns_zeros():
    result = _run([], raise_always=True)
    assert result["total_conversations"] == 0
    assert result["capture_rate"] == 0.0
    assert result["kb_gap_count"] == 0


def test_verify_tenant_is_enforced():
    db = MagicMock(name="db")
    with patch.object(fdh, "get_service_supabase", return_value=db), patch.object(
        fdh, "_get_cached", return_value=None
    ), patch.object(
        fdh, "verify_tenant", side_effect=PermissionError("forbidden")
    ) as verify:
        with pytest.raises(PermissionError):
            asyncio.run(
                fdh.get_front_desk_health(_TENANT, period="30d", claims=_CLAIMS)
            )
        verify.assert_called_once_with(_CLAIMS, _TENANT)
