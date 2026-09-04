"""Enforceable AI budget for widget.extract_action_items.

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages_sync →
  record_ai_usage (release on provider error or record failure).
  llm_runtime does not record.
- Hard cap and missing/unloadable tenant policy block before the provider.
  The background task returns; it must not raise into the visitor chat reply.
- Purchased usage packs are honored because the tenant row passed to reserve
  includes id.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Repeated extraction trigger cycles reserve and record independently.
- New logs/errors are tenant id + session id + counts only. No conversation
  text, customer PII, credentials, or provider exception payload.

Run: pytest backend/tests/test_widget_extract_action_items_usage_guard.py -q
"""

import logging
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks

from backend.routers import widget_chat_effects, widget_lead_helpers as extract
from backend.routers.widget_lead_helpers import ACTION_ITEM_MAX_TOKENS
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.tests.fake_supabase import db
from backend.tests.test_widget_chat_pipeline import _req, _tenant, _widget

_TENANT_ID = "t-action-budget"
_SESSION_ID = "sess-action-001"
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}
_MESSAGES = [
    {"role": "user", "content": "Hi, this is Cara Diaz at cara@example.com"},
    {"role": "assistant", "content": "Hello Cara"},
    {"role": "user", "content": "Please send a quote to +15555550100"},
    {"role": "assistant", "content": "I can prepare that."},
    {"role": "user", "content": "Follow up tomorrow"},
    {"role": "assistant", "content": "Will do"},
]
_ITEMS_JSON = (
    '[{"description": "Send quote", "priority": "high", "due_hint": "tomorrow"}]'
)


def _fixture():
    return db(
        {
            "tenants": [_TENANT],
            "conversations": [{"id": "conv-action-1"}],
        }
    )


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 700),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 700),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 700),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="guard_unavailable",
    )


def _claude_result(text=_ITEMS_JSON):
    result = MagicMock()
    result.text = text
    result.input_tokens = 80
    result.output_tokens = 30
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    result.duration_ms = 12
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
    assert "send a quote" not in blob
    assert "follow up tomorrow" not in blob


def _run(**kwargs):
    return extract._extract_action_items(
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
        result = _run(messages=_MESSAGES[:2])
    assert result is None
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
        _run()
    reserve.assert_called_once()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["operation"] == "widget.extract_action_items"
    assert reserve.call_args.kwargs["session_id"] == _SESSION_ID
    assert reserve.call_args.kwargs["estimated_tokens"] >= ACTION_ITEM_MAX_TOKENS


def test_repeated_trigger_cycles_reserve_and_record_independently():
    """Each scheduled extraction is its own reserve/record; one result is not double-counted."""
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        _run(session_id="sess-cycle-1")
        _run(session_id="sess-cycle-2")
    assert reserve.call_count == 2
    assert provider.call_count == 2
    assert record.call_count == 2
    release.assert_not_called()
    sessions = [c.kwargs["session_id"] for c in reserve.call_args_list]
    assert sessions == ["sess-cycle-1", "sess-cycle-2"]
    recorded_sessions = [c.kwargs["session_id"] for c in record.call_args_list]
    assert recorded_sessions == ["sess-cycle-1", "sess-cycle-2"]


def test_success_records_usage_once():
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(extract, "record_ai_usage") as record,
        patch.object(extract, "release_ai_token_reservation") as release,
    ):
        _run()
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == "widget.extract_action_items"
    assert recorded["session_id"] == _SESSION_ID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 80
    assert recorded["result"].output_tokens == 30
    assert provider.call_args.kwargs["max_tokens"] == ACTION_ITEM_MAX_TOKENS
    assert provider.call_args.kwargs["operation"] == "widget.extract_action_items"


def test_provider_error_releases_reservation_without_raising(caplog):
    def boom(**kwargs):
        raise RuntimeError("claude down secret=sk-ant-test customer=cara@example.com")

    with caplog.at_level(logging.WARNING):
        with (
            _patch_db(),
            patch.object(extract, "reserve_ai_tokens", side_effect=_allowed) as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=boom),
            patch.object(extract, "record_ai_usage") as record,
            patch.object(extract, "release_ai_token_reservation") as release,
        ):
            result = _run()
    assert result is None
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
            estimated_tokens=700,
            operation="widget.extract_action_items",
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
    assert result is None
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
    assert result is None
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
                    "phone=+15555550100"
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
    assert result is None
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
                    "supabase down secret=sk-ant-test customer=cara@example.com"
                ),
            ),
            patch.object(extract, "reserve_ai_tokens") as reserve,
            patch.object(extract, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        ):
            result = _run()
    assert result is None
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
            operation="widget.extract_action_items",
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
    assert result is None
    provider.assert_called_once()
    release.assert_called_once_with(reservation)


def test_provider_and_budget_logs_do_not_leak_secrets(caplog):
    def boom(**kwargs):
        raise RuntimeError("provider boom cara@example.com sk-ant-test +15555550100")

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


def test_blocked_extraction_does_not_raise_into_visitor_effects():
    """Background extraction must not turn a successful widget reply into a failure."""
    bg = BackgroundTasks()
    prior = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "need a quote"},
        {"role": "assistant", "content": "sure"},
        {"role": "user", "content": "tomorrow works"},
        {"role": "assistant", "content": "ok"},
    ]
    has_contact = widget_chat_effects.schedule_post_response_effects(
        bg,
        tenant=_tenant(id=_TENANT_ID),
        widget=_widget(),
        req=_req(message="Please send it", session_id=_SESSION_ID),
        conversation_id="conv-p-action",
        messages=prior,
        assistant_text="I will follow up.",
        saved_rows=[{"id": "row-1", "role": "user"}],
    )
    assert has_contact is False
    extract_tasks = [
        task for task in bg.tasks if task.func is extract._extract_action_items
    ]
    assert len(extract_tasks) == 1

    provider = MagicMock(side_effect=_ok_claude)
    with (
        _patch_db(),
        patch.object(extract, "reserve_ai_tokens", side_effect=_blocked),
        patch.object(extract, "call_claude_messages_sync", side_effect=provider),
    ):
        extract_tasks[0].func(*extract_tasks[0].args, **extract_tasks[0].kwargs)
    provider.assert_not_called()
