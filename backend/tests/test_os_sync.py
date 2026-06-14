"""Unit tests for os_sync registry + foundation.

Spec: agent-os-rehaul (migration 127 + backend/services/os_sync/).

Focus:
- Registry auto-discovers leads handler via SPEC import.
- ``run_sync`` writes status, cursor, and rows_seen_total tenant-scoped.
- ``run_sync`` short-circuits when state_row.enabled is False.
- Unknown source returns status='error' and persists last_error.
- Handler exception is caught and recorded as status='error'.
- Tenant scope uses client_id for os_sync_state.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


from backend.services.os_sync import all_syncs, get_sync, run_sync
from backend.services.os_sync.base import (
    SyncContext,
    SyncResult,
    SyncSpec,
)

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_STATE_ID = "30000000-0000-0000-0000-00000000abcd"


def _stub_supabase(state_row: dict | None = None):
    """Mimic the chained supabase-py builder used by tenant_table()."""
    builder = MagicMock(name="builder")
    builder.select.return_value = builder
    builder.update.return_value = builder
    builder.insert.return_value = builder
    builder.delete.return_value = builder
    builder.eq.return_value = builder
    builder.gt.return_value = builder
    builder.limit.return_value = builder
    builder.order.return_value = builder
    builder.execute.return_value = SimpleNamespace(
        data=[state_row] if state_row else []
    )
    db = MagicMock(name="db")
    db.table.return_value = builder
    return db, builder


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_discovers_leads_handler():
    syncs = all_syncs()
    assert "leads" in syncs
    spec = syncs["leads"]
    assert isinstance(spec, SyncSpec)
    assert spec.name == "leads"
    assert callable(spec.run)


def test_get_sync_returns_none_for_unknown():
    assert get_sync("does.not.exist") is None


def test_get_sync_returns_spec_for_known():
    spec = get_sync("leads")
    assert spec is not None
    assert spec.name == "leads"


# ---------------------------------------------------------------------------
# run_sync background-task harness
# ---------------------------------------------------------------------------


def test_run_sync_marks_unknown_source_error():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "not.a.real.source",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    with patch("backend.services.os_sync.get_service_supabase", return_value=db):
        result = asyncio.run(run_sync(_CLIENT_A, "not.a.real.source"))
    assert result.status == "error"
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    assert any(
        u.get("status") == "error" for u in update_calls
    ), "error status update not recorded"


def test_run_sync_invokes_handler_run_and_persists_cursor():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
        "last_seen_cursor": None,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.name = "leads"
    stub_handler.run = AsyncMock(
        return_value=SyncResult(
            status="ok",
            rows_seen=5,
            new_cursor="2026-05-25T12:00:00+00:00",
        )
    )
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        result = asyncio.run(run_sync(_CLIENT_A, "leads"))
    assert result.status == "ok"
    assert result.rows_seen == 5
    stub_handler.run.assert_awaited_once()
    ctx_arg = stub_handler.run.call_args.args[0]
    assert isinstance(ctx_arg, SyncContext)
    assert ctx_arg.client_id == _CLIENT_A
    assert ctx_arg.source == "leads"
    assert ctx_arg.backfill is False
    # Cursor + rows_seen_total must persist.
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    final = [u for u in update_calls if u.get("status") == "idle"]
    assert final, "idle status not persisted on success"
    last = final[-1]
    assert last["last_seen_cursor"] == "2026-05-25T12:00:00+00:00"
    assert last["rows_seen_total"] == 5


def test_run_sync_propagates_handler_exception_as_error():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        result = asyncio.run(run_sync(_CLIENT_A, "leads"))
    assert result.status == "error"
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    fail = [u for u in update_calls if u.get("status") == "error"]
    assert fail, "exception did not trigger error status write"
    assert "boom" in (fail[-1].get("last_error") or "")


def test_run_sync_propagates_backfill_flag():
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
        "last_seen_cursor": "2026-05-01T00:00:00+00:00",
    }
    db, _ = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(return_value=SyncResult(status="ok"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        asyncio.run(run_sync(_CLIENT_A, "leads", backfill=True))
    ctx_arg = stub_handler.run.call_args.args[0]
    assert ctx_arg.backfill is True


# ---------------------------------------------------------------------------
# Tenant scoping
# ---------------------------------------------------------------------------


def test_run_sync_uses_client_id_for_os_sync_state_scope():
    """tenant_table('os_sync_state', client_id) must scope by client_id."""
    state_row = {
        "id": _STATE_ID,
        "client_id": _CLIENT_A,
        "source": "leads",
        "enabled": True,
        "status": "idle",
        "rows_seen_total": 0,
    }
    db, builder = _stub_supabase(state_row=state_row)
    stub_handler = MagicMock(spec=SyncSpec)
    stub_handler.run = AsyncMock(return_value=SyncResult(status="ok"))
    with patch("backend.services.os_sync.get_service_supabase", return_value=db), patch(
        "backend.services.os_sync.get_sync", return_value=stub_handler
    ):
        asyncio.run(run_sync(_CLIENT_A, "leads"))
    # tenant_table injects .eq(client_id, _CLIENT_A) on every chained query.
    eq_args = [c.args for c in builder.eq.call_args_list]
    flat = [a for tpl in eq_args for a in tpl]
    assert _CLIENT_A in flat, "client_id never used in scoping filter"


# ---------------------------------------------------------------------------
# leads SPEC contract
# ---------------------------------------------------------------------------


def test_leads_spec_metadata():
    from backend.services.os_sync.leads import SPEC

    assert SPEC.name == "leads"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == []


def test_leads_summarize_handles_minimal_row():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead({"id": "x", "name": "Alice"})
    assert "Alice" in text
    assert text.startswith("Lead:")


def test_leads_summarize_handles_unnamed_row():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead({"id": "x"})
    assert "Unnamed lead" in text


def test_leads_summarize_includes_status_and_temperature():
    from backend.services.os_sync.leads import _summarize_lead

    text = _summarize_lead(
        {
            "id": "x",
            "name": "Bob",
            "status": "qualified",
            "lead_temperature": "hot",
            "lead_score": 87,
        }
    )
    assert "status=qualified" in text
    assert "temperature=hot" in text
    assert "score=87" in text


# ---------------------------------------------------------------------------
# appointments SPEC contract
# ---------------------------------------------------------------------------


def test_registry_includes_appointments():
    syncs = all_syncs()
    assert "appointments" in syncs
    spec = syncs["appointments"]
    assert isinstance(spec, SyncSpec)
    assert callable(spec.run)
    assert spec.required_connectors == []


def test_appointments_spec_metadata():
    from backend.services.os_sync.appointments import SPEC

    assert SPEC.name == "appointments"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == []


def test_appointments_summarize_handles_minimal_row():
    from backend.services.os_sync.appointments import _summarize_appointment

    text = _summarize_appointment({"id": "x"})
    assert "Unnamed customer" in text


def test_appointments_summarize_includes_all_fields():
    from backend.services.os_sync.appointments import _summarize_appointment

    text = _summarize_appointment(
        {
            "id": "x",
            "customer_name": "Alice",
            "customer_email": "a@b.com",
            "customer_phone": "+15551234",
            "start_time": "2026-06-01T15:00:00+00:00",
            "status": "booked",
            "service_type": "haircut",
            "notes": "long hair, trim only",
        }
    )
    assert "Alice" in text
    assert "service=haircut" in text
    assert "start=2026-06-01T15:00:00+00:00" in text
    assert "status=booked" in text
    assert "email=a@b.com" in text
    assert "phone=+15551234" in text
    assert "long hair" in text


# ---------------------------------------------------------------------------
# kb SPEC contract
# ---------------------------------------------------------------------------


def test_registry_includes_kb():
    syncs = all_syncs()
    assert "kb" in syncs
    spec = syncs["kb"]
    assert isinstance(spec, SyncSpec)
    assert callable(spec.run)
    assert spec.required_connectors == []


def test_kb_spec_metadata():
    from backend.services.os_sync.kb import SPEC

    assert SPEC.name == "kb"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == []


def test_kb_split_into_chunks_empty_input():
    from backend.services.os_sync.kb import _split_into_chunks

    assert _split_into_chunks("") == []
    assert _split_into_chunks("   \n\n   ") == []


def test_kb_split_into_chunks_small_input_returns_single_chunk():
    from backend.services.os_sync.kb import _split_into_chunks

    chunks = _split_into_chunks("Para one.\n\nPara two.")
    assert len(chunks) == 1
    assert "Para one." in chunks[0]
    assert "Para two." in chunks[0]


def test_kb_split_into_chunks_oversized_paragraph_splits():
    from backend.services.os_sync.kb import _split_into_chunks, _CHUNK_MAX_CHARS

    big = "Sentence. " * 400  # ~4000 chars, single paragraph
    assert len(big) > _CHUNK_MAX_CHARS
    chunks = _split_into_chunks(big)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.strip()


def test_kb_hash_content_is_deterministic():
    from backend.services.os_sync.kb import _hash_content

    a = _hash_content("alpha", "beta")
    b = _hash_content("alpha", "beta")
    assert a == b
    c = _hash_content("alpha", "gamma")
    assert a != c


def test_kb_hash_content_separator_prevents_collision():
    from backend.services.os_sync.kb import _hash_content

    # "ab" + "" should NOT collide with "a" + "b" because of separator
    a = _hash_content("ab", "")
    b = _hash_content("a", "b")
    assert a != b


# ---------------------------------------------------------------------------
# conversations SPEC contract
# ---------------------------------------------------------------------------


def test_registry_includes_conversations():
    syncs = all_syncs()
    assert "conversations" in syncs
    spec = syncs["conversations"]
    assert isinstance(spec, SyncSpec)
    assert callable(spec.run)
    assert spec.required_connectors == []


def test_conversations_spec_metadata():
    from backend.services.os_sync.conversations import SPEC

    assert SPEC.name == "conversations"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == []


def test_conversations_group_by_session_groups_correctly():
    from backend.services.os_sync.conversations import _group_by_session

    rows = [
        {"session_id": "s1", "role": "user", "content": "hi"},
        {"session_id": "s1", "role": "assistant", "content": "hello"},
        {"session_id": "s2", "role": "user", "content": "hey"},
    ]
    grouped = _group_by_session(rows)
    assert set(grouped.keys()) == {"s1", "s2"}
    assert len(grouped["s1"]) == 2
    assert len(grouped["s2"]) == 1


def test_conversations_group_by_session_skips_missing_session_id():
    from backend.services.os_sync.conversations import _group_by_session

    rows = [
        {"session_id": None, "role": "user", "content": "orphan"},
        {"session_id": "s1", "role": "user", "content": "hi"},
    ]
    grouped = _group_by_session(rows)
    assert list(grouped.keys()) == ["s1"]


def test_conversations_render_transcript_skips_empty_content():
    from backend.services.os_sync.conversations import _render_transcript

    text = _render_transcript(
        [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "  "},
            {"role": "user", "content": "hello"},
        ]
    )
    assert text == "user: hello"


def test_conversations_render_transcript_respects_char_budget():
    from backend.services.os_sync.conversations import (
        _render_transcript,
        _MAX_SUMMARY_INPUT_CHARS,
    )

    long_content = "x" * 500
    msgs = [{"role": "user", "content": long_content} for _ in range(50)]
    text = _render_transcript(msgs)
    assert len(text) <= _MAX_SUMMARY_INPUT_CHARS + 100  # rough headroom


def test_conversations_render_transcript_uses_default_role_when_missing():
    from backend.services.os_sync.conversations import _render_transcript

    text = _render_transcript([{"role": "", "content": "hi"}])
    assert "user: hi" in text


# ---------------------------------------------------------------------------
# google_calendar SPEC contract
# ---------------------------------------------------------------------------


def test_registry_includes_google_calendar():
    syncs = all_syncs()
    assert "google_calendar" in syncs
    spec = syncs["google_calendar"]
    assert isinstance(spec, SyncSpec)
    assert callable(spec.run)
    assert spec.required_connectors == ["google_calendar"]


def test_google_calendar_spec_metadata():
    from backend.services.os_sync.google_calendar import SPEC

    assert SPEC.name == "google_calendar"
    assert isinstance(SPEC, SyncSpec)
    assert callable(SPEC.run)
    assert SPEC.required_connectors == ["google_calendar"]


def test_google_calendar_summarize_handles_minimal_event():
    from backend.services.os_sync.google_calendar import _summarize_event

    text = _summarize_event({})
    assert "Untitled event" in text


def test_google_calendar_summarize_includes_all_fields():
    from backend.services.os_sync.google_calendar import _summarize_event

    text = _summarize_event(
        {
            "id": "evt-1",
            "summary": "Team sync",
            "start": {"dateTime": "2026-06-01T15:00:00Z"},
            "end": {"dateTime": "2026-06-01T15:30:00Z"},
            "location": "Zoom",
            "status": "tentative",
            "attendees": [
                {"email": "a@b.com"},
                {"email": "c@d.com"},
            ],
            "description": "weekly standup",
        }
    )
    assert "Team sync" in text
    assert "start=2026-06-01T15:00:00Z" in text
    assert "end=2026-06-01T15:30:00Z" in text
    assert "location=Zoom" in text
    assert "status=tentative" in text
    assert "a@b.com" in text
    assert "c@d.com" in text
    assert "weekly standup" in text


def test_google_calendar_summarize_omits_confirmed_status():
    from backend.services.os_sync.google_calendar import _summarize_event

    text = _summarize_event(
        {
            "summary": "Meeting",
            "status": "confirmed",
        }
    )
    assert "status=" not in text


def test_google_calendar_summarize_uses_all_day_date_when_no_dateTime():
    from backend.services.os_sync.google_calendar import _summarize_event

    text = _summarize_event(
        {
            "summary": "Holiday",
            "start": {"date": "2026-07-04"},
            "end": {"date": "2026-07-05"},
        }
    )
    assert "start=2026-07-04" in text
    assert "end=2026-07-05" in text
