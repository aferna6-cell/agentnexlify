"""Unit tests for the Agent OS inbound bridge.

Covers the three invariants from
``plans/agent-os-connectors-inbound_plan.md`` Phase 2 §Tests:

  1. Toggle OFF -> bridge_widget returns None, no os_thread / os_message
     inserts, orchestrator never called.
  2. Toggle ON  -> bridge_widget creates an os_thread, appends an
     os_message with ``source_ref='widget:<provider_message_id>'``, and
     calls ``process_user_turn``.
  3. Replay of the same provider_message_id  -> idempotent: returns
     None, no duplicate insert, orchestrator not called a second time.

The bridge is exercised at the public entry point. Internal helpers
(``_already_ingested``, ``_resolve_or_create_thread``,
``_append_inbound_message``) are reached transparently through
``_bridge_common``; the test monkeypatches them so we don't need a real
Supabase client.
"""

from typing import Any

import pytest

from backend.services import os_inbound_bridge


class _FakeDB:
    """Stand-in for the Supabase client. Only needed for identity passthrough."""

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return "<FakeDB>"


@pytest.fixture
def fake_db() -> _FakeDB:
    return _FakeDB()


def _patch_toggle(monkeypatch: pytest.MonkeyPatch, enabled: bool) -> None:
    monkeypatch.setattr(
        os_inbound_bridge,
        "is_bridge_enabled",
        lambda db, client_id, source: enabled,
    )


def _patch_helpers(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ingested_refs: set[str],
    thread_id: str = "thread-abc",
    inserts: list[dict[str, Any]] | None = None,
) -> dict[str, list]:
    """Stub the DB-touching helpers. Returns lists the test can assert on."""
    calls: dict[str, list] = {
        "already_ingested": [],
        "resolve_thread": [],
        "append_message": [],
        "process_turn": [],
    }

    def fake_already_ingested(db, client_id, source_ref):
        calls["already_ingested"].append((client_id, source_ref))
        return source_ref in ingested_refs

    def fake_resolve_or_create_thread(
        db, *, client_id, source, source_thread_id, sender_metadata
    ):
        calls["resolve_thread"].append(
            {
                "client_id": client_id,
                "source": source,
                "source_thread_id": source_thread_id,
                "sender_metadata": sender_metadata,
            }
        )
        return {"id": thread_id, "source": source, "title": "Widget conversation"}

    def fake_append_inbound_message(
        db, *, client_id, thread_id, user_content, inbound_kind, source_ref
    ):
        row = {
            "id": f"msg-{len(calls['append_message']) + 1}",
            "thread_id": thread_id,
            "role": "user",
            "content": user_content,
            "inbound_kind": inbound_kind,
            "source_ref": source_ref,
        }
        calls["append_message"].append(row)
        if inserts is not None:
            inserts.append(row)
        return row

    async def fake_process_user_turn(
        db, client_id, t_id, user_message_row, background_tasks=None
    ):
        calls["process_turn"].append(
            {
                "client_id": client_id,
                "thread_id": t_id,
                "user_message_id": user_message_row["id"],
                "background_tasks": background_tasks,
            }
        )
        return {
            "user_message": user_message_row,
            "assistant_message": None,
            "action": "answer",
            "agent_runs": [],
        }

    monkeypatch.setattr(os_inbound_bridge, "_already_ingested", fake_already_ingested)
    monkeypatch.setattr(
        os_inbound_bridge,
        "_resolve_or_create_thread",
        fake_resolve_or_create_thread,
    )
    monkeypatch.setattr(
        os_inbound_bridge,
        "_append_inbound_message",
        fake_append_inbound_message,
    )
    monkeypatch.setattr(os_inbound_bridge, "process_user_turn", fake_process_user_turn)
    return calls


class _EmptyQuery:
    """Supabase query-builder stub whose ``execute`` returns no rows.

    Mirrors the fluent ``.select().eq().limit().execute()`` chain so
    ``get_bridge_config`` exercises its "missing row -> defaults" path.
    """

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        return type("_Result", (), {"data": []})()


def test_widget_bridge_defaults_off(monkeypatch, fake_db):
    """Regression: a tenant with no bridge config must NOT have the widget
    bridged into Agent OS. Agent OS is a dashboard tool — defaulting the
    public customer widget on hijacked every visitor reply. Opt-in only.
    """
    monkeypatch.setattr(
        os_inbound_bridge, "tenant_table", lambda db, table, client_id: _EmptyQuery()
    )

    cfg = os_inbound_bridge.get_bridge_config(fake_db, "tenant-no-config")
    assert cfg["widget_enabled"] is False
    assert (
        os_inbound_bridge.is_bridge_enabled(fake_db, "tenant-no-config", "widget")
        is False
    )


@pytest.mark.asyncio
async def test_bridge_widget_toggle_off_skips_everything(monkeypatch, fake_db):
    _patch_toggle(monkeypatch, enabled=False)
    calls = _patch_helpers(monkeypatch, ingested_refs=set())

    result = await os_inbound_bridge.bridge_widget(
        db=fake_db,
        client_id="tenant-1",
        conversation_id="conv-1",
        provider_message_id="chatmsg-1",
        user_content="hello",
    )

    assert result is None
    assert calls["already_ingested"] == []
    assert calls["resolve_thread"] == []
    assert calls["append_message"] == []
    assert calls["process_turn"] == []


@pytest.mark.asyncio
async def test_bridge_widget_toggle_on_creates_thread_and_runs_turn(
    monkeypatch, fake_db
):
    _patch_toggle(monkeypatch, enabled=True)
    calls = _patch_helpers(monkeypatch, ingested_refs=set())

    result = await os_inbound_bridge.bridge_widget(
        db=fake_db,
        client_id="tenant-1",
        conversation_id="conv-1",
        provider_message_id="chatmsg-1",
        user_content="hi there",
        sender_metadata={"session_id": "sess-1"},
    )

    assert result is not None
    assert result["action"] == "answer"

    assert calls["already_ingested"] == [("tenant-1", "widget:chatmsg-1")]

    assert calls["resolve_thread"] == [
        {
            "client_id": "tenant-1",
            "source": "widget",
            "source_thread_id": "conv-1",
            "sender_metadata": {"session_id": "sess-1"},
        }
    ]

    assert len(calls["append_message"]) == 1
    appended = calls["append_message"][0]
    assert appended["role"] == "user"
    assert appended["content"] == "hi there"
    assert appended["inbound_kind"] == "normal"
    assert appended["source_ref"] == "widget:chatmsg-1"
    assert appended["thread_id"] == "thread-abc"

    assert len(calls["process_turn"]) == 1
    turn = calls["process_turn"][0]
    assert turn["client_id"] == "tenant-1"
    assert turn["thread_id"] == "thread-abc"
    assert turn["background_tasks"] is None  # bridge runs inline


@pytest.mark.asyncio
async def test_bridge_widget_replay_is_idempotent(monkeypatch, fake_db):
    """Second call with the same provider_message_id must short-circuit."""
    _patch_toggle(monkeypatch, enabled=True)
    inserts: list[dict[str, Any]] = []
    calls = _patch_helpers(monkeypatch, ingested_refs=set(), inserts=inserts)

    first = await os_inbound_bridge.bridge_widget(
        db=fake_db,
        client_id="tenant-1",
        conversation_id="conv-1",
        provider_message_id="chatmsg-1",
        user_content="hi",
    )
    assert first is not None
    assert len(inserts) == 1

    # Simulate the UNIQUE index now containing the source_ref by swapping
    # the ingested_refs check to return True for the replay.
    monkeypatch.setattr(
        os_inbound_bridge,
        "_already_ingested",
        lambda db, client_id, source_ref: source_ref == "widget:chatmsg-1",
    )

    replay = await os_inbound_bridge.bridge_widget(
        db=fake_db,
        client_id="tenant-1",
        conversation_id="conv-1",
        provider_message_id="chatmsg-1",
        user_content="hi",
    )

    assert replay is None
    # No additional inserts and no additional orchestrator turn.
    assert len(inserts) == 1
    assert len(calls["process_turn"]) == 1
