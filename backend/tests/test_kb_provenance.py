"""Tests for KB article provenance (issue #70).

Covers the pure provenance helpers (source footer, stale warning, bulk merge,
citation increment) and the widget prompt wiring that surfaces them.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from backend.services.kb_provenance import (
    STALE_AFTER_DAYS,
    merge_provenance,
    provenance_suffix,
    record_citations,
)

_NOW = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _iso(days_ago: int) -> str:
    return (_NOW - timedelta(days=days_ago)).isoformat()


class TestProvenanceSuffix:
    def test_fresh_article_shows_source_no_warning(self):
        art = {"source_url": "https://kb.example.com/x", "last_validated": _iso(5)}
        suffix = provenance_suffix(art, now=_NOW)
        assert "Source: https://kb.example.com/x" in suffix
        assert "last verified 2026-07-16" in suffix
        assert "outdated" not in suffix

    def test_stale_article_triggers_warning(self):
        art = {"source_url": "https://kb.example.com/x", "last_validated": _iso(STALE_AFTER_DAYS + 1)}
        suffix = provenance_suffix(art, now=_NOW)
        assert "⚠ KB article may be outdated" in suffix

    def test_boundary_not_stale_at_threshold(self):
        # Exactly STALE_AFTER_DAYS old is NOT stale (strictly greater-than).
        art = {"last_validated": _iso(STALE_AFTER_DAYS)}
        assert "outdated" not in provenance_suffix(art, now=_NOW)

    def test_no_source_no_date_is_empty(self):
        assert provenance_suffix({"title": "x"}, now=_NOW) == ""

    def test_source_urls_array_fallback(self):
        art = {"source_urls": ["https://a.example.com", "https://b.example.com"]}
        suffix = provenance_suffix(art, now=_NOW)
        assert "Source: https://a.example.com" in suffix

    def test_datetime_last_validated_accepted(self):
        art = {"last_validated": _NOW - timedelta(days=STALE_AFTER_DAYS + 2)}
        assert "outdated" in provenance_suffix(art, now=_NOW)

    def test_z_suffix_timestamp_parsed(self):
        art = {"last_validated": "2026-07-16T00:00:00Z"}
        suffix = provenance_suffix(art, now=_NOW)
        assert "last verified 2026-07-16" in suffix


class TestMergeProvenance:
    def test_merges_by_id(self):
        db = MagicMock()
        db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {
                "id": "art-1",
                "source_urls": ["https://src/1"],
                "last_validated": _iso(3),
                "citation_count": 7,
            }
        ]
        rows = [{"id": "art-1", "title": "T", "summary": "S"}]
        merged = merge_provenance(db, rows)
        assert merged[0]["source_url"] == "https://src/1"
        assert merged[0]["citation_count"] == 7
        assert merged[0]["last_validated"] == _iso(3)

    def test_fail_open_on_db_error(self):
        db = MagicMock()
        db.table.return_value.select.return_value.in_.return_value.execute.side_effect = RuntimeError("db down")
        rows = [{"id": "art-1", "title": "T"}]
        merged = merge_provenance(db, rows)
        assert merged == [{"id": "art-1", "title": "T"}]  # unchanged, no crash

    def test_overwrites_fts_stub_columns(self):
        # FTS RPC (mig 155) hands rows with source_url=None/last_validated=None/
        # citation_count=0 already set — merge must overwrite, not keep the stubs.
        db = MagicMock()
        db.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "art-1", "source_urls": ["https://real/1"], "last_validated": _iso(1), "citation_count": 42}
        ]
        rows = [{"id": "art-1", "source_url": None, "last_validated": None, "citation_count": 0}]
        merged = merge_provenance(db, rows)
        assert merged[0]["source_url"] == "https://real/1"
        assert merged[0]["last_validated"] == _iso(1)
        assert merged[0]["citation_count"] == 42

    def test_empty_rows_short_circuit(self):
        db = MagicMock()
        assert merge_provenance(db, []) == []
        db.table.assert_not_called()


class _CapturingDB:
    """Records the exact RPC payload record_citations emits (observable state)."""

    def __init__(self, fail: bool = False):
        self.calls: list = []
        self._fail = fail

    def rpc(self, name, params):
        self.calls.append((name, params))
        return self

    def execute(self):
        if self._fail:
            raise RuntimeError("rpc down")
        return self


class TestRecordCitations:
    def test_increments_via_rpc_with_ids(self):
        db = _CapturingDB()
        record_citations(db, [{"id": "art-1"}, {"id": "art-2"}, {"no_id": True}])
        # Observable outcome: exactly one increment RPC carrying only the real ids.
        assert db.calls == [("increment_kb_citations", {"article_ids": ["art-1", "art-2"]})]

    def test_no_ids_no_call(self):
        db = _CapturingDB()
        record_citations(db, [{"no_id": True}])
        assert db.calls == []  # nothing emitted when there are no ids

    def test_fail_open_on_rpc_error(self):
        db = _CapturingDB(fail=True)
        record_citations(db, [{"id": "art-1"}])
        # The RPC was attempted (observable), and the error was swallowed (no raise).
        assert db.calls == [("increment_kb_citations", {"article_ids": ["art-1"]})]


class TestPromptWiring:
    """Integration: the widget system prompt surfaces the provenance footer."""

    def test_stale_article_warning_in_prompt(self):
        from backend.routers.widget_chat_helpers import _build_system_prompt

        stale = {
            "id": "art-1",
            "title": "Leaky Faucet",
            "summary": "How to fix it",
            "source_url": "https://kb.example.com/faucet",
            "last_validated": (datetime.now(timezone.utc) - timedelta(days=STALE_AFTER_DAYS + 30)).isoformat(),
        }
        prompt = _build_system_prompt(
            tenant={"business_name": "Acme Plumbing", "business_type": "plumbing"},
            faq_entries=[],
            kb_article_refs=[stale],
        )
        assert "KB_ARTICLE_REFERENCES" in prompt
        assert "Source: https://kb.example.com/faucet" in prompt
        assert "⚠ KB article may be outdated" in prompt
