"""Enforceable AI budget for widget.extract_tags.

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages_sync →
  record_ai_usage (release on provider error or record failure).
  llm_runtime does not record.
- Hard cap and missing/unloadable tenant policy block before the provider.
  The helper returns []; it must not raise into lead capture or the visitor
  chat reply.
- Purchased usage packs are honored because the tenant row passed to reserve
  includes id.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Repeated eligible lead-capture turns reserve and record independently.
- Metering does not schedule new extract_tags calls. The helper still runs
  only from _capture_leads_from_session after email or phone is found, and
  conversations with fewer than 2 messages still skip Claude.
- New logs/errors are tenant id + session id + counts only. No conversation
  text, customer PII, credentials, tag payloads, or provider exception payload.

Run: pytest backend/tests/test_widget_extract_tags_usage_guard.py -q
"""

import logging
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks

from backend.routers import widget_chat_effects, widget_lead_helpers as extract
from backend.routers.widget_lead_helpers import EXTRACT_TAGS_MAX_TOKENS
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.tests.fake_supabase import db, run
from backend.tests.test_widget_chat_pipeline import _req, _tenant, _widget

_TENANT_ID = "t-extract-tags-budget"
_SESSION_ID = "sess-extract-tags-001"
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}
_MESSAGES = [
    {"role": "user", "content": "Hi, this is Cara Diaz at cara@example.com"},
    {"role": "assistant", "content": "Hello Cara"},
    {"role": "user", "content": "Need a kitchen remodel quote at +15555550100"},
]
_TAGS_JSON = '["interested in: kitchen remodel", "budget: high"]'
_NO_CONTACT_MESSAGES = [
    {"role": "user", "content": "Just browsing kitchens"},
    {"role": "assistant", "content": "Happy to help when you are ready."},
]


def _fixture(**extra_tables):
    rows = {"tenants": [_TENANT]}
    rows.update(extra_tables)
    return db(rows)


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="guard_unavailable",
    )


def _claude_result(text=_TAGS_JSON):
    result = MagicMock()
    result.text = text
    result.input_tokens = 80
    result.output_tokens = 16
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    result.duration_ms = 8
    return result


def _ok_claude(**kwargs):
    return _claude_result()


def _assert_no_secrets(text: str) -> None:
    blob = text.lower()
    assert "cara@example.com" not in blob
    assert "cara diaz" not in blob
    assert "sk-ant" not in blob
    assert "anthropic_api_key" not in blob
    assert "anx_" not in blob
    assert "+15555550100" not in blob
    assert "kitchen remodel" not in blob
    assert "need a kitchen" not in blob
    assert "interested in:" not in blob
    assert "budget: high" not in blob


def _run(**kwargs):
    return extract._extract_tags_from_conversation(
        kwargs.get("tenant_id", _TENANT_ID),
        kwargs.get("session_id", _SESSION_ID),
        kwargs.get("messages", _MESSAGES),
    )


def _patch_db(fixture=None):
    return patch.object(
        extract, "get_service_supabase", return_value=fixture or _fixture()
    )


# --- reserve / record / release ---------------------------------------------


def test_short_transcript_skips_reserve_and_provider():
    provider = MagicMock(side_effect=_ok_claude)
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens") as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=provider),
        patch.object(extract, "record_ai_usage") as record,
    ):
        result = _run(messages=_MESSAGES[:1])
    assert result == []
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()


def test_hard_cap_blocks_before_provider():
    provider = MagicMock(side_effect=_ok_claude)
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_blocked) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=provider),
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        result = _run()
    assert result == []
    reserve.assert_called_once()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["operation"] == "widget.extract_tags"
    assert reserve.call_args.kwargs["session_id"] == _SESSION_ID
    assert reserve.call_args.kwargs["estimated_tokens"] >= EXTRACT_TAGS_MAX_TOKENS


def test_repeated_eligible_turns_reserve_and_record_independently():
    """Each post-email capture turn is its own reserve/record; one result is not double-counted."""
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        first = _run(session_id="sess-cycle-1")
        second = _run(session_id="sess-cycle-2")
    assert first == ["interested in: kitchen remodel", "budget: high"]
    assert second == ["interested in: kitchen remodel", "budget: high"]
    assert reserve.call_count == 2
    assert provider.call_count == 2
    assert record.call_count == 2
    release.assert_not_called()
    sessions = [c.kwargs["session_id"] for c in reserve.call_args_list]
    assert sessions == ["sess-cycle-1", "sess-cycle-2"]
    recorded_sessions = [c.kwargs["session_id"] for c in record.call_args_list]
    assert recorded_sessions == ["sess-cycle-1", "sess-cycle-2"]


def test_success_records_usage_once_and_returns_tags():
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        result = _run()
    assert result == ["interested in: kitchen remodel", "budget: high"]
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == "widget.extract_tags"
    assert recorded["session_id"] == _SESSION_ID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 80
    assert recorded["result"].output_tokens == 16
    assert provider.call_args.kwargs["max_tokens"] == EXTRACT_TAGS_MAX_TOKENS
    assert provider.call_args.kwargs["operation"] == "widget.extract_tags"
    assert provider.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_empty_or_non_json_provider_result_still_records_and_returns_empty():
    """Tag fallback stays empty-list; Claude spend is still recorded once."""
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(extract, "call_claude_messages_sync", return_value=_claude_result("not-json")),
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        result = _run()
    assert result == []
    record.assert_called_once()
    release.assert_not_called()

    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(extract, "call_claude_messages_sync", return_value=_claude_result("[]")),
        patch.object(extract, "record_ai_usage") as record_empty,
        patch.object(extract, "release_ai_token_reservation") as release_empty,
    ):
        empty = _run()
    assert empty == []
    record_empty.assert_called_once()
    release_empty.assert_not_called()


def test_provider_error_releases_reservation_without_raising(caplog):
    def boom(**kwargs):
        raise RuntimeError("claude down secret=anthropic_api_key customer=cara@example.com")

    with caplog.at_level(logging.WARNING):
        with (
            _patch_db(),
            patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=boom),
            patch.object(extract, "record_ai_usage") as record,
            patch.object(extract, "release_ai_token_reservation") as release,
        ):
            result = _run()
    assert result == []
    assert "provider error" in caplog.text
    _assert_no_secrets(caplog.text)
    reserve.assert_called_once()
    record.assert_not_called()
    release.assert_called_once()
    assert release.call_args.args[0].allowed is True
    assert release.call_args.args[0].reason != "guard_unavailable"


def test_purchased_usage_pack_is_honored_on_reserve():
    """Tenant id must reach reserve so resolve_ai_usage_policy can add packs."""
    captured = {}

    def capture_reserve(*, tenant, estimated_tokens, operation, session_id):
        captured["tenant"] = tenant
        captured["estimated_tokens"] = estimated_tokens
        captured["operation"] = operation
        return _allowed(estimated_tokens=estimated_tokens)

    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=capture_reserve),
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude),
        patch.object(extract, "record_ai_usage"),
        patch(
            "backend.services.ai_usage_guard._sum_usage_packs", return_value=1_000_000
        ),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
    ):
        rpc_limit = {}

        def fake_rpc(name, params=None):
            if name == "reserve_ai_token_budget":
                rpc_limit["hard"] = params["p_hard_limit_tokens"]
            result = MagicMock()
            result.data = True
            chain = MagicMock()
            chain.execute.return_value = result
            return chain

        mock_supa.return_value.rpc.side_effect = fake_rpc
        from backend.services.ai_usage_guard import reserve_ai_tokens

        reservation = reserve_ai_tokens(
            tenant={"id": _TENANT_ID, "plan": "agent_os"},
            estimated_tokens=500,
            operation="widget.extract_tags",
            session_id=_SESSION_ID,
        )
        _run()

    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["tenant"]["plan"] == "agent_os"
    assert reservation.allowed is True
    # agent_os baseline 5M + 1M pack
    assert rpc_limit["hard"] == 6_000_000


def test_guard_unavailable_allows_call_without_persisting():
    """Valid tenant loaded, reserve RPC down: shared widget-chat fail-open."""
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_unavailable) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        result = _run()
    assert result == ["interested in: kitchen remodel", "budget: high"]
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    assert record.call_args.kwargs["reservation"].reason == "guard_unavailable"
    assert record.call_args.kwargs["reservation"].allowed is True
    release.assert_not_called()


def test_missing_tenant_row_fails_closed_before_provider(caplog):
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(extract, "get_service_supabase", return_value=db({})),
            patch.object(extract, "reserve_ai_tokens") as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
            patch.object(extract, "record_ai_usage") as record,
            patch.object(extract, "release_ai_token_reservation") as release,
        ):
            result = _run()
    assert result == []
    assert "failing closed before provider" in caplog.text
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    _assert_no_secrets(caplog.text)


def test_tenant_lookup_error_fails_closed_before_provider(caplog):
    class BoomDb:
        def table(self, name):
            if name == "tenants":
                raise RuntimeError(
                    "db down secret=anthropic_api_key customer=cara@example.com "
                    "phone=+15555550100 tag=kitchen remodel"
                )
            return db({}).table(name)

    with caplog.at_level(logging.WARNING):
        with (
            patch.object(extract, "get_service_supabase", return_value=BoomDb()),
            patch.object(extract, "reserve_ai_tokens") as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
            patch.object(extract, "record_ai_usage") as record,
            patch.object(extract, "release_ai_token_reservation") as release,
        ):
            result = _run()
    assert result == []
    assert "tenant load failed" in caplog.text
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    _assert_no_secrets(caplog.text)


def test_supabase_client_error_fails_closed_before_provider(caplog):
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(
                extract,
                "get_service_supabase",
                side_effect=RuntimeError(
                    "supabase down secret=anthropic_api_key customer=cara@example.com"
                ),
            ),
            patch.object(extract, "reserve_ai_tokens") as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        ):
            result = _run()
    assert result == []
    assert "tenant load failed" in caplog.text
    reserve.assert_not_called()
    provider.assert_not_called()
    _assert_no_secrets(caplog.text)


def test_metered_call_metadata_is_ids_and_counts_only():
    seen = []

    def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(extract, "call_claude_messages_sync", side_effect=capture_claude),
        patch.object(extract, "record_ai_usage"),
    ):
        _run()
    meta = seen[0]["metadata"]
    assert set(meta) == {"tenant_id", "session_id", "message_count"}
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["session_id"] == _SESSION_ID
    assert meta["message_count"] == len(_MESSAGES)
    _assert_no_secrets(str(meta))


def test_record_ai_usage_releases_reservation_on_persist_failure():
    reservation = _allowed()
    with (
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        recorded = record_ai_usage(
            reservation=reservation,
            result=_claude_result(),
            operation="widget.extract_tags",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )
    assert recorded is None
    release.assert_called_once_with(reservation)


def test_extract_path_releases_when_record_rpc_fails():
    reservation = _allowed()

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", return_value=reservation),
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage", side_effect=fail_record),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        result = _run()
    assert result == ["interested in: kitchen remodel", "budget: high"]
    provider.assert_called_once()
    release.assert_called_once_with(reservation)


def test_provider_and_budget_logs_do_not_leak_secrets(caplog):
    def boom(**kwargs):
        raise RuntimeError("provider boom cara@example.com anthropic_api_key +15555550100")

    with caplog.at_level(logging.WARNING):
        with (
            _patch_db(),
            patch.object(extract, "reserve_ai_tokens", side_effect=_allowed),
            patch.object(extract, "call_claude_messages_sync", side_effect=boom),
            patch.object(extract, "record_ai_usage"),
            patch.object(extract, "release_ai_token_reservation"),
        ):
            _run()
        with (
            _patch_db(),
            patch.object(extract, "reserve_ai_tokens", side_effect=_blocked),
            patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude),
        ):
            _run()
    _assert_no_secrets(caplog.text)
    assert "RuntimeError" not in caplog.text
    assert "provider boom" not in caplog.text


# --- lead-capture callers: frequency, persistence, visitor chat -------------


def test_no_contact_capture_does_not_call_extract_tags():
    """Metering must not invent extract_tags calls for conversations without email/phone."""
    extract_spy = MagicMock(return_value=["should not run"])
    with (
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=_NO_CONTACT_MESSAGES,
        ),
        patch.object(extract, "_extract_tags_from_conversation", extract_spy),
        patch.object(extract, "get_service_supabase", return_value=MagicMock()),
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
    ):
        run(
            extract._capture_leads_from_session(
                _TENANT_ID, _SESSION_ID, "conv-no-contact"
            )
        )
    extract_spy.assert_not_called()
    provider.assert_not_called()


def test_existing_lead_capture_threads_tenant_and_persists_tags():
    """Post-email existing-lead path still extracts once and writes leads.tags."""
    update_sink = []

    def fake_update(db_obj, table, tenant_id, payload):
        update_sink.append((table, tenant_id, payload))
        chain = MagicMock()
        chain.eq.return_value.execute.return_value = MagicMock(data=[])
        return chain

    select_chain = MagicMock()
    select_chain.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "lead-existing-1",
                "name": "Cara",
                "phone": None,
                "areas_of_interest": None,
                "conversation_summary": None,
            }
        ]
    )

    with (
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=_MESSAGES,
        ),
        patch.object(extract, "get_service_supabase", return_value=_fixture()),
        patch.object(extract, "tenant_select", return_value=select_chain),
        patch.object(extract, "tenant_update", side_effect=fake_update),
        patch.object(extract, "log_activity"),
        patch.object(extract, "fire_event_background"),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
    ):
        run(
            extract._capture_leads_from_session(
                _TENANT_ID, _SESSION_ID, "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            )
        )
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["session_id"] == _SESSION_ID
    tag_updates = [
        payload
        for table, tenant_id, payload in update_sink
        if table == "leads" and "tags" in payload
    ]
    assert tag_updates == [
        {"tags": ["interested in: kitchen remodel", "budget: high"]}
    ]


def test_blocked_extract_does_not_raise_into_lead_capture_or_visitor_effects():
    """Lead capture still runs after email; hard-capped extract_tags stays background-only."""
    bg = BackgroundTasks()
    prior = [
        {"role": "user", "content": "Hi, this is Cara Diaz at cara@example.com"},
        {"role": "assistant", "content": "Hello Cara"},
    ]
    has_contact = widget_chat_effects.schedule_post_response_effects(
        bg,
        tenant=_tenant(id=_TENANT_ID),
        widget=_widget(),
        req=_req(message="Need a kitchen remodel quote", session_id=_SESSION_ID),
        conversation_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        messages=prior,
        assistant_text="I can help with that.",
        saved_rows=[{"id": "row-1", "role": "user"}],
    )
    assert has_contact is True
    capture_tasks = [
        task for task in bg.tasks if task.func is extract._capture_leads_from_session
    ]
    assert len(capture_tasks) == 1
    extract_direct = [
        task for task in bg.tasks if task.func is extract._extract_tags_from_conversation
    ]
    assert extract_direct == []

    select_chain = MagicMock()
    select_chain.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "id": "lead-existing-2",
                "name": "Cara",
                "phone": None,
                "areas_of_interest": None,
                "conversation_summary": None,
            }
        ]
    )
    provider = MagicMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=_MESSAGES,
        ),
        patch.object(extract, "get_service_supabase", return_value=_fixture()),
        patch.object(extract, "tenant_select", return_value=select_chain),
        patch.object(extract, "tenant_update", return_value=MagicMock()),
        patch.object(extract, "log_activity"),
        patch.object(extract, "fire_event_background"),
        patch.object(extract, "reserve_ai_tokens", side_effect=_blocked),
        patch.object(extract, "call_claude_messages_sync", side_effect=provider),
    ):
        capture_tasks[0].func(*capture_tasks[0].args, **capture_tasks[0].kwargs)
    provider.assert_not_called()
