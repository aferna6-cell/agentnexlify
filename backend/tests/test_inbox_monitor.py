"""Tests for the inbox-monitor poll loop (Phase 2 — Gmail connector + triage).

Contracts:
  - Only tenants with the email bridge toggled on are polled
  - First poll (no history cursor) reseeds via list_recent_message_ids +
    get_profile; a returned HISTORY_EXPIRED sentinel triggers the same
    reseed path
  - Every new message is fed through os_inbound_bridge.bridge_email with
    the right args; bridge_email's own idempotency (None return) means a
    re-poll of the same message is a no-op here, never double-counted
  - Self-sent messages are skipped before bridging
  - auto_reply-tagged messages still bridge (evidence) but skip triage
  - Triage runs only for messages that were actually bridged (not skipped)
  - The gmail history_id cursor advances after a poll pass
  - A failure in one tenant's poll never stops the loop for the rest
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import inbox_monitor

TENANT_A = "00000000-0000-0000-0000-00000000000a"
TENANT_B = "00000000-0000-0000-0000-00000000000b"


def _integrations_result(rows):
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    return chain


def _fake_db(rows):
    db = MagicMock()
    db.table.return_value = _integrations_result(rows)
    return db


def _parsed_email(**overrides):
    base = {
        "provider_message_id": "msg-1",
        "thread_id": "thread-1",
        "sender_email": "customer@example.com",
        "sender_name": "Customer",
        "recipient": "support@tenant.com",
        "subject": "Question",
        "body_text": "Do you offer weekend appointments?",
        "headers": {},
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_poll_skips_tenant_when_bridge_disabled(monkeypatch):
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {"history_id": "100"}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: False
    )
    poll_tenant = AsyncMock()
    monkeypatch.setattr(inbox_monitor, "_poll_tenant", poll_tenant)

    total = await inbox_monitor.run_inbox_poll()

    assert total == 0
    poll_tenant.assert_not_called()


@pytest.mark.asyncio
async def test_poll_query_failure_returns_zero(monkeypatch):
    db = MagicMock()
    db.table.side_effect = RuntimeError("supabase down")
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)

    total = await inbox_monitor.run_inbox_poll()
    assert total == 0


@pytest.mark.asyncio
async def test_first_poll_with_no_history_id_reseeds(monkeypatch):
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_profile", lambda t: {"historyId": "500"}
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "list_recent_message_ids", lambda t, max_results=20: ["m1"]
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_message", lambda t, mid: _parsed_email()
    )
    monkeypatch.setattr(
        inbox_monitor.inbound_email_verify, "is_auto_reply", lambda headers: False
    )
    bridge_email = AsyncMock(
        return_value={
            "user_message": {"thread_id": "os-thread-1"},
            "action": "answer",
        }
    )
    monkeypatch.setattr(inbox_monitor.os_inbound_bridge, "bridge_email", bridge_email)
    triage = AsyncMock(return_value={"category": "answerable", "action": "drafted"})
    monkeypatch.setattr(inbox_monitor.inbox_triage, "triage_inbound_email", triage)
    update_metadata = MagicMock()
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", update_metadata)

    total = await inbox_monitor.run_inbox_poll()

    assert total == 1
    bridge_email.assert_awaited_once()
    call_kwargs = bridge_email.call_args.kwargs
    assert call_kwargs["client_id"] == TENANT_A
    assert call_kwargs["email_thread_id"] == "thread-1"
    assert call_kwargs["provider_message_id"] == "msg-1"
    assert call_kwargs["inbound_kind"] == "normal"
    triage.assert_awaited_once()
    triage_kwargs = triage.call_args.kwargs
    assert triage_kwargs["tenant"] == TENANT_A
    assert triage_kwargs["os_thread_id"] == "os-thread-1"
    update_metadata.assert_called_once()
    updates = update_metadata.call_args.args[1]
    assert updates["history_id"] == "500"


@pytest.mark.asyncio
async def test_uses_history_cursor_when_present(monkeypatch):
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {"history_id": "100"}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    list_history = MagicMock(return_value=(["m2"], "150"))
    monkeypatch.setattr(inbox_monitor.gmail_connector, "list_history", list_history)
    reseed_called = MagicMock()
    monkeypatch.setattr(inbox_monitor.gmail_connector, "get_profile", reseed_called)
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_message", lambda t, mid: _parsed_email(provider_message_id=mid)
    )
    monkeypatch.setattr(
        inbox_monitor.inbound_email_verify, "is_auto_reply", lambda headers: False
    )
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge,
        "bridge_email",
        AsyncMock(return_value={"user_message": {"thread_id": "t1"}, "action": "answer"}),
    )
    monkeypatch.setattr(
        inbox_monitor.inbox_triage, "triage_inbound_email", AsyncMock(return_value={})
    )
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", MagicMock())

    total = await inbox_monitor.run_inbox_poll()

    assert total == 1
    list_history.assert_called_once_with(TENANT_A, "100")
    reseed_called.assert_not_called()


@pytest.mark.asyncio
async def test_expired_history_falls_back_to_reseed(monkeypatch):
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {"history_id": "100"}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector,
        "list_history",
        MagicMock(return_value=([], "history_expired")),
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_profile", lambda t: {"historyId": "999"}
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "list_recent_message_ids", lambda t, max_results=20: []
    )
    update_metadata = MagicMock()
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", update_metadata)

    total = await inbox_monitor.run_inbox_poll()

    assert total == 0
    updates = update_metadata.call_args.args[1]
    assert updates["history_id"] == "999"


@pytest.mark.asyncio
async def test_self_sent_message_is_skipped(monkeypatch):
    db = _fake_db(
        [{"tenant_id": TENANT_A, "metadata": {"history_id": "100", "email_address": "Owner@Tenant.com"}}]
    )
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "list_history", lambda t, since: (["m1"], "200")
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector,
        "get_message",
        lambda t, mid: _parsed_email(sender_email="owner@tenant.com"),
    )
    bridge_email = AsyncMock()
    monkeypatch.setattr(inbox_monitor.os_inbound_bridge, "bridge_email", bridge_email)
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", MagicMock())

    total = await inbox_monitor.run_inbox_poll()

    assert total == 0
    bridge_email.assert_not_called()


@pytest.mark.asyncio
async def test_auto_reply_bridges_but_skips_triage(monkeypatch):
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {"history_id": "100"}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "list_history", lambda t, since: (["m1"], "200")
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector,
        "get_message",
        lambda t, mid: _parsed_email(headers={"auto-submitted": "auto-replied"}),
    )
    monkeypatch.setattr(
        inbox_monitor.inbound_email_verify, "is_auto_reply", lambda headers: True
    )
    bridge_email = AsyncMock(
        return_value={"user_message": {"thread_id": "t1"}, "action": "skipped_auto_reply"}
    )
    monkeypatch.setattr(inbox_monitor.os_inbound_bridge, "bridge_email", bridge_email)
    triage = AsyncMock()
    monkeypatch.setattr(inbox_monitor.inbox_triage, "triage_inbound_email", triage)
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", MagicMock())

    total = await inbox_monitor.run_inbox_poll()

    assert total == 1  # still counted as ingested evidence
    bridge_email.assert_awaited_once()
    call_kwargs = bridge_email.call_args.kwargs
    assert call_kwargs["inbound_kind"] == "auto_reply"
    triage.assert_not_called()


@pytest.mark.asyncio
async def test_already_ingested_message_not_counted(monkeypatch):
    """bridge_email returning None (idempotent re-poll) must not count or triage."""
    db = _fake_db([{"tenant_id": TENANT_A, "metadata": {"history_id": "100"}}])
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "list_history", lambda t, since: (["m1"], "200")
    )
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_message", lambda t, mid: _parsed_email()
    )
    monkeypatch.setattr(
        inbox_monitor.inbound_email_verify, "is_auto_reply", lambda headers: False
    )
    bridge_email = AsyncMock(return_value=None)
    monkeypatch.setattr(inbox_monitor.os_inbound_bridge, "bridge_email", bridge_email)
    triage = AsyncMock()
    monkeypatch.setattr(inbox_monitor.inbox_triage, "triage_inbound_email", triage)
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", MagicMock())

    total = await inbox_monitor.run_inbox_poll()

    assert total == 0
    triage.assert_not_called()


@pytest.mark.asyncio
async def test_per_tenant_error_isolated(monkeypatch):
    """Tenant A blows up during list_history; tenant B still gets polled."""
    db = _fake_db(
        [
            {"tenant_id": TENANT_A, "metadata": {"history_id": "100"}},
            {"tenant_id": TENANT_B, "metadata": {"history_id": "200"}},
        ]
    )
    monkeypatch.setattr(inbox_monitor, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge, "is_bridge_enabled", lambda db, t, source: True
    )

    def flaky_list_history(tenant_id, since):
        if tenant_id == TENANT_A:
            raise RuntimeError("gmail api down for tenant A")
        return (["m1"], "999")

    monkeypatch.setattr(inbox_monitor.gmail_connector, "list_history", flaky_list_history)
    monkeypatch.setattr(
        inbox_monitor.gmail_connector, "get_message", lambda t, mid: _parsed_email()
    )
    monkeypatch.setattr(
        inbox_monitor.inbound_email_verify, "is_auto_reply", lambda headers: False
    )
    monkeypatch.setattr(
        inbox_monitor.os_inbound_bridge,
        "bridge_email",
        AsyncMock(return_value={"user_message": {"thread_id": "t1"}, "action": "answer"}),
    )
    monkeypatch.setattr(
        inbox_monitor.inbox_triage, "triage_inbound_email", AsyncMock(return_value={})
    )
    monkeypatch.setattr(inbox_monitor.gmail_connector, "update_metadata", MagicMock())

    total = await inbox_monitor.run_inbox_poll()

    # Tenant A's failure is swallowed; tenant B's one message still counts.
    assert total == 1
