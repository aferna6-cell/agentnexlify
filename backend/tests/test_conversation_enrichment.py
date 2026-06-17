"""Tests for per-conversation sentiment + intent enrichment.

The LLM (call_claude_messages) is mocked throughout; no network. We assert the
classifier output is parsed, stored on the conversations row, and that every
failure mode (LLM error, malformed JSON, off-vocabulary, empty transcript,
persist failure) degrades to null without raising.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import conversation_enrichment as ce
from backend.services import conversation_enrichment_job as cej


# ---------------------------------------------------------------------------
# Pure parsers
# ---------------------------------------------------------------------------


def test_build_transcript_orders_and_labels():
    rows = [
        {"role": "user", "content": "Do you do brakes?"},
        {"role": "assistant", "content": "Yes we do."},
    ]
    out = ce.build_transcript(rows)
    assert out == "Customer: Do you do brakes?\nAssistant: Yes we do."


def test_build_transcript_skips_empty_and_truncates():
    rows = [
        {"role": "user", "content": ""},
        {"role": "user", "content": "x" * 1000},
    ]
    out = ce.build_transcript(rows)
    assert out.startswith("Customer: ")
    # truncated to _MAX_TURN_CHARS
    assert len(out) <= len("Customer: ") + ce._MAX_TURN_CHARS


def test_parse_classification_happy_path():
    out = ce.parse_classification('{"sentiment": "positive", "intent": "Booking Request"}')
    assert out == {"sentiment": "positive", "intent": "booking request"}


def test_parse_classification_tolerates_code_fence_and_prose():
    raw = 'Here you go:\n```json\n{"sentiment":"negative","intent":"complaint"}\n```'
    out = ce.parse_classification(raw)
    assert out == {"sentiment": "negative", "intent": "complaint"}


def test_parse_classification_off_vocabulary_sentiment_is_null():
    out = ce.parse_classification('{"sentiment": "furious", "intent": "complaint"}')
    assert out["sentiment"] is None
    assert out["intent"] == "complaint"


def test_parse_classification_intent_unknown_is_null():
    out = ce.parse_classification('{"sentiment": "neutral", "intent": "unknown"}')
    assert out == {"sentiment": "neutral", "intent": None}


def test_parse_classification_garbage_is_null():
    assert ce.parse_classification("not json at all") == {"sentiment": None, "intent": None}
    assert ce.parse_classification("") == {"sentiment": None, "intent": None}
    assert ce.parse_classification("{bad json}") == {"sentiment": None, "intent": None}




# ---------------------------------------------------------------------------
# enrich_conversation: classify + store + fallback
# ---------------------------------------------------------------------------


def _db_with_transcript(rows):
    """Build a MagicMock db whose chat_messages select chain returns rows and
    whose conversations update chain records the persisted values."""
    db = MagicMock()
    persisted = {}

    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.order.return_value = select_chain
    select_chain.limit.return_value = select_chain
    select_chain.gte.return_value = select_chain
    select_chain.execute.return_value = SimpleNamespace(data=rows)

    update_chain = MagicMock()

    def _update(values):
        persisted.update(values)
        return update_chain

    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = SimpleNamespace(data=[{}])

    table = MagicMock()
    table.select.return_value = select_chain
    table.update.side_effect = _update
    db.table.return_value = table
    return db, persisted


async def test_enrich_conversation_classifies_and_stores():
    rows = [{"role": "user", "content": "I want to book an appointment"}]
    db, persisted = _db_with_transcript(rows)

    fake = SimpleNamespace(text='{"sentiment": "positive", "intent": "booking request"}')
    with patch.object(ce, "call_claude_messages", new=AsyncMock(return_value=fake)) as mock_llm:
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    mock_llm.assert_awaited_once()
    assert result == {"sentiment": "positive", "intent": "booking request"}
    assert persisted == {"sentiment": "positive", "intent": "booking request"}


async def test_enrich_conversation_llm_failure_falls_back_to_null():
    rows = [{"role": "user", "content": "hi"}]
    db, persisted = _db_with_transcript(rows)

    with patch.object(ce, "call_claude_messages", new=AsyncMock(side_effect=RuntimeError("boom"))):
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    assert result == {"sentiment": None, "intent": None}
    # nothing persisted when both values are null
    assert persisted == {}


async def test_enrich_conversation_empty_transcript_skips_llm():
    db, persisted = _db_with_transcript([])

    with patch.object(ce, "call_claude_messages", new=AsyncMock()) as mock_llm:
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    mock_llm.assert_not_awaited()
    assert result == {"sentiment": None, "intent": None}
    assert persisted == {}


async def test_enrich_conversation_missing_ids_returns_null():
    result = await ce.enrich_conversation("", "sess-1", db=MagicMock())
    assert result == {"sentiment": None, "intent": None}


async def test_enrich_conversation_transcript_load_failure_returns_null():
    db = MagicMock()
    db.table.side_effect = RuntimeError("supabase down")

    with patch.object(ce, "call_claude_messages", new=AsyncMock()) as mock_llm:
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    mock_llm.assert_not_awaited()
    assert result == {"sentiment": None, "intent": None}


async def test_enrich_conversation_persist_failure_does_not_raise():
    rows = [{"role": "user", "content": "hello"}]
    db = MagicMock()

    select_chain = MagicMock()
    select_chain.eq.return_value = select_chain
    select_chain.order.return_value = select_chain
    select_chain.limit.return_value = select_chain
    select_chain.execute.return_value = SimpleNamespace(data=rows)

    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.side_effect = RuntimeError("db down")

    table = MagicMock()
    table.select.return_value = select_chain
    table.update.return_value = update_chain
    db.table.return_value = table

    fake = SimpleNamespace(text='{"sentiment": "neutral", "intent": "hours question"}')
    with patch.object(ce, "call_claude_messages", new=AsyncMock(return_value=fake)):
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    # classification still returned even though persist raised internally
    assert result == {"sentiment": "neutral", "intent": "hours question"}


async def test_enrich_conversation_partial_classification_only_writes_resolved():
    rows = [{"role": "user", "content": "yo"}]
    db, persisted = _db_with_transcript(rows)

    fake = SimpleNamespace(text='{"sentiment": "neutral", "intent": "unknown"}')
    with patch.object(ce, "call_claude_messages", new=AsyncMock(return_value=fake)):
        result = await ce.enrich_conversation("tenant-1", "sess-1", db=db)

    assert result == {"sentiment": "neutral", "intent": None}
    # only the non-null sentiment is persisted; null intent never clobbers
    assert persisted == {"sentiment": "neutral"}


# ---------------------------------------------------------------------------
# Batch job
# ---------------------------------------------------------------------------


def _job_db(pending_rows):
    db = MagicMock()
    chain = MagicMock()
    chain.is_.return_value = chain
    chain.lte.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = SimpleNamespace(data=pending_rows)
    table = MagicMock()
    table.select.return_value = chain
    db.table.return_value = table
    return db


async def test_run_pending_enrichment_processes_each_row():
    pending = [
        {"client_id": "t1", "session_id": "s1", "last_message_at": "2026-06-01T00:00:00Z"},
        {"client_id": "t1", "session_id": "s2", "last_message_at": "2026-06-01T00:00:00Z"},
    ]
    db = _job_db(pending)

    enrich = AsyncMock(return_value={"sentiment": "positive", "intent": "pricing question"})
    with patch.object(cej, "get_service_supabase", return_value=db), patch.object(
        cej, "enrich_conversation", new=enrich
    ):
        status = await cej.run_pending_enrichment()

    assert enrich.await_count == 2
    assert "classified 2/2" in status


async def test_run_pending_enrichment_nothing_pending():
    db = _job_db([])
    with patch.object(cej, "get_service_supabase", return_value=db):
        status = await cej.run_pending_enrichment()
    assert "nothing pending" in status


async def test_run_pending_enrichment_lookup_failure_returns_status():
    db = MagicMock()
    db.table.side_effect = RuntimeError("query blew up")
    with patch.object(cej, "get_service_supabase", return_value=db):
        status = await cej.run_pending_enrichment()
    assert "lookup failed" in status


async def test_run_pending_enrichment_skips_rows_missing_ids():
    pending = [
        {"client_id": None, "session_id": "s1", "last_message_at": "2026-06-01T00:00:00Z"},
        {"client_id": "t1", "session_id": "s2", "last_message_at": "2026-06-01T00:00:00Z"},
    ]
    db = _job_db(pending)
    enrich = AsyncMock(return_value={"sentiment": "positive", "intent": "pricing question"})
    with patch.object(cej, "get_service_supabase", return_value=db), patch.object(
        cej, "enrich_conversation", new=enrich
    ):
        status = await cej.run_pending_enrichment()

    # only the row with both ids is enriched
    assert enrich.await_count == 1
    assert "classified 1/2" in status


async def test_run_pending_enrichment_one_row_failure_continues():
    pending = [
        {"client_id": "t1", "session_id": "s1", "last_message_at": "2026-06-01T00:00:00Z"},
        {"client_id": "t1", "session_id": "s2", "last_message_at": "2026-06-01T00:00:00Z"},
    ]
    db = _job_db(pending)

    async def _enrich(client_id, session_id, db=None):
        if session_id == "s1":
            raise RuntimeError("classify failed")
        return {"sentiment": "neutral", "intent": "hours question"}

    with patch.object(cej, "get_service_supabase", return_value=db), patch.object(
        cej, "enrich_conversation", new=_enrich
    ):
        status = await cej.run_pending_enrichment()

    # one failed, one classified
    assert "classified 1/2" in status
