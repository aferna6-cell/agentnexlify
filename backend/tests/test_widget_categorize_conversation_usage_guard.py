"""Enforceable AI budget for widget.categorize_conversation.

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages_sync →
  record_ai_usage (release on provider error or record failure).
  llm_runtime does not record.
- Hard cap and missing/unloadable tenant policy block before the provider.
  The background task returns; it must not raise into the visitor chat reply.
- Tag-definition lookup failure (or an empty enabled list) still uses
  SYSTEM_TAGS and is not a budget miss — provider may still run.
- Purchased usage packs are honored because the tenant row passed to reserve
  includes id.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Repeated categorization trigger cycles reserve and record independently.
- New logs/errors are tenant id + session id + counts only. No conversation
  text, customer PII, credentials, tag payloads, or provider exception payload.

Run: pytest backend/tests/test_widget_categorize_conversation_usage_guard.py -q
"""

import logging
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks

from backend.routers import widget_chat_effects, widget_lead_helpers as categorize
from backend.routers.widget_lead_helpers import CATEGORIZE_MAX_TOKENS, SYSTEM_TAGS
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.tests.fake_supabase import db
from backend.tests.test_widget_chat_pipeline import _req, _tenant, _widget

_TENANT_ID = "t-categorize-budget"
_SESSION_ID = "sess-categorize-001"
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}
_CUSTOM_TAG = "Kitchen Remodel"
_MESSAGES = [
    {"role": "user", "content": "Hi, this is Cara Diaz at cara@example.com"},
    {"role": "assistant", "content": "Hello Cara"},
    {"role": "user", "content": "Need a kitchen remodel quote at +15555550100"},
    {"role": "assistant", "content": "I can help with that."},
]
_TAGS_JSON = '["New Lead"]'


def _fixture(**extra_tables):
    rows = {
        "tenants": [_TENANT],
        "conversations": [
            {"id": "conv-categorize-1", "session_id": _SESSION_ID, "tags": ["handoff"]}
        ],
    }
    rows.update(extra_tables)
    return db(rows)


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 400),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 400),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 400),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="guard_unavailable",
    )


def _claude_result(text=_TAGS_JSON):
    result = MagicMock()
    result.text = text
    result.input_tokens = 60
    result.output_tokens = 12
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
    assert "new lead" not in blob
    assert "pricing question" not in blob


def _run(**kwargs):
    return categorize._categorize_conversation(
        kwargs.get("tenant_id", _TENANT_ID),
        kwargs.get("session_id", _SESSION_ID),
        kwargs.get("messages", _MESSAGES),
    )


def _patch_db(fixture=None):
    return patch.object(
        categorize, "get_service_supabase", return_value=fixture or _fixture()
    )


# --- reserve / record / release ---------------------------------------------


def test_short_transcript_skips_reserve_and_provider():
    provider = MagicMock(side_effect=_ok_claude)
    with (
        _patch_db(),
        patch.object(categorize, "reserve_ai_tokens") as reserve,
        patch.object(categorize, "call_claude_messages_sync", side_effect=provider),
        patch.object(categorize, "record_ai_usage") as record,
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
        patch.object(categorize, "reserve_ai_tokens", side_effect=_blocked) as reserve,
        patch.object(categorize, "call_claude_messages_sync", side_effect=provider),
        patch.object(categorize, "record_ai_usage") as record,
        patch.object(categorize, "release_ai_token_reservation") as release,
    ):
        _run()
    reserve.assert_called_once()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["operation"] == "widget.categorize_conversation"
    assert reserve.call_args.kwargs["session_id"] == _SESSION_ID
    assert reserve.call_args.kwargs["estimated_tokens"] >= CATEGORIZE_MAX_TOKENS


def test_repeated_trigger_cycles_reserve_and_record_independently():
    """Each scheduled categorization is its own reserve/record; one result is not double-counted."""
    with (
        _patch_db(),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(categorize, "record_ai_usage") as record,
        patch.object(categorize, "release_ai_token_reservation") as release,
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
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(categorize, "record_ai_usage") as record,
        patch.object(categorize, "release_ai_token_reservation") as release,
    ):
        _run()
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == "widget.categorize_conversation"
    assert recorded["session_id"] == _SESSION_ID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 60
    assert recorded["result"].output_tokens == 12
    assert provider.call_args.kwargs["max_tokens"] == CATEGORIZE_MAX_TOKENS
    assert provider.call_args.kwargs["operation"] == "widget.categorize_conversation"
    assert provider.call_args.kwargs["model"] == "claude-sonnet-4-6"


def test_success_merges_valid_tags_onto_conversation():
    fixture = _fixture()
    with (
        _patch_db(fixture),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude),
        patch.object(categorize, "record_ai_usage"),
    ):
        _run()
    updates = [
        args[0]
        for table, method, args in fixture._sink
        if table == "conversations" and method == "update"
    ]
    assert len(updates) == 1
    merged = set(updates[0]["tags"])
    assert "New Lead" in merged
    assert "handoff" in merged


def test_tag_definition_lookup_failure_uses_system_tags(caplog):
    """Tag-definition fetch failure is not a budget miss; SYSTEM_TAGS still apply."""

    class TagBoomDb:
        def __init__(self):
            self._inner = _fixture()
            self._sink = self._inner._sink

        def table(self, name):
            if name == "tenant_tag_definitions":
                raise RuntimeError(
                    "tag defs down secret=anthropic_api_key customer=cara@example.com "
                    "tag=Kitchen Remodel"
                )
            return self._inner.table(name)

    seen = []

    def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with caplog.at_level(logging.WARNING):
        with (
            patch.object(categorize, "get_service_supabase", return_value=TagBoomDb()),
            patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed) as reserve,
            patch.object(categorize, "call_claude_messages_sync", side_effect=capture_claude) as provider,
            patch.object(categorize, "record_ai_usage") as record,
        ):
            _run()
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    prompt = seen[0]["system"]
    for tag in SYSTEM_TAGS:
        assert tag in prompt
    _assert_no_secrets(caplog.text)


def test_empty_tag_definitions_use_system_tags():
    seen = []

    def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with (
        _patch_db(_fixture(tenant_tag_definitions=[])),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(categorize, "call_claude_messages_sync", side_effect=capture_claude),
        patch.object(categorize, "record_ai_usage"),
    ):
        _run()
    prompt = seen[0]["system"]
    for tag in SYSTEM_TAGS:
        assert tag in prompt


def test_custom_tag_definitions_are_used_not_system_fallback():
    seen = []

    def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result(text=f'["{_CUSTOM_TAG}"]')

    fixture = _fixture(
        tenant_tag_definitions=[{"tag_name": _CUSTOM_TAG, "is_enabled": True}]
    )
    with (
        _patch_db(fixture),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(categorize, "call_claude_messages_sync", side_effect=capture_claude),
        patch.object(categorize, "record_ai_usage"),
    ):
        _run()
    prompt = seen[0]["system"]
    assert _CUSTOM_TAG in prompt
    assert "New Lead" not in prompt
    updates = [
        args[0]
        for table, method, args in fixture._sink
        if table == "conversations" and method == "update"
    ]
    assert updates
    assert _CUSTOM_TAG in updates[0]["tags"]


def test_provider_error_releases_reservation_without_raising(caplog):
    def boom(**kwargs):
        raise RuntimeError("claude down secret=anthropic_api_key customer=cara@example.com")

    with caplog.at_level(logging.WARNING):
        with (
            _patch_db(),
            patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed) as reserve,
            patch.object(categorize, "call_claude_messages_sync", side_effect=boom),
            patch.object(categorize, "record_ai_usage") as record,
            patch.object(categorize, "release_ai_token_reservation") as release,
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
        patch.object(categorize, "reserve_ai_tokens", side_effect=capture_reserve),
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude),
        patch.object(categorize, "record_ai_usage"),
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
            estimated_tokens=400,
            operation="widget.categorize_conversation",
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
        patch.object(categorize, "reserve_ai_tokens", side_effect=_unavailable) as reserve,
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(categorize, "record_ai_usage") as record,
        patch.object(categorize, "release_ai_token_reservation") as release,
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
            patch.object(categorize, "get_service_supabase", return_value=db({})),
            patch.object(categorize, "reserve_ai_tokens") as reserve,
            patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
            patch.object(categorize, "record_ai_usage") as record,
            patch.object(categorize, "release_ai_token_reservation") as release,
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
                    "phone=+15555550100 tag=Kitchen Remodel"
                )
            return db({}).table(name)

    with caplog.at_level(logging.WARNING):
        with (
            patch.object(categorize, "get_service_supabase", return_value=BoomDb()),
            patch.object(categorize, "reserve_ai_tokens") as reserve,
            patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
            patch.object(categorize, "record_ai_usage") as record,
            patch.object(categorize, "release_ai_token_reservation") as release,
        ):
            result = _run()
    assert result is None
    assert "tenant load failed" in caplog.text
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    _assert_no_secrets(caplog.text)


def test_tag_definition_failure_does_not_look_like_budget_failure(caplog):
    """A tag-definition miss must not emit the budget fail-closed warning."""

    class TagBoomDb:
        def __init__(self):
            self._inner = _fixture()

        def table(self, name):
            if name == "tenant_tag_definitions":
                raise RuntimeError("tag defs down")
            return self._inner.table(name)

    with caplog.at_level(logging.WARNING):
        with (
            patch.object(categorize, "get_service_supabase", return_value=TagBoomDb()),
            patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
            patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude),
            patch.object(categorize, "record_ai_usage"),
        ):
            _run()
    assert "failing closed before provider" not in caplog.text
    assert "budget tenant unavailable" not in caplog.text


def test_supabase_client_error_fails_closed_before_provider(caplog):
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(
                categorize,
                "get_service_supabase",
                side_effect=RuntimeError(
                    "supabase down secret=anthropic_api_key customer=cara@example.com"
                ),
            ),
            patch.object(categorize, "reserve_ai_tokens") as reserve,
            patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
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
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(categorize, "call_claude_messages_sync", side_effect=capture_claude),
        patch.object(categorize, "record_ai_usage"),
    ):
        _run()
    meta = seen[0]["metadata"]
    assert set(meta) == {"tenant_id", "session_id", "tag_count"}
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["session_id"] == _SESSION_ID
    assert isinstance(meta["tag_count"], int)
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
            operation="widget.categorize_conversation",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )
    assert recorded is None
    release.assert_called_once_with(reservation)


def test_categorize_path_releases_when_record_rpc_fails():
    reservation = _allowed()

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with (
        _patch_db(),
        patch.object(categorize, "reserve_ai_tokens", return_value=reservation),
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude) as provider,
        patch.object(categorize, "record_ai_usage", side_effect=fail_record),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        result = _run()
    assert result is None
    provider.assert_called_once()
    release.assert_called_once_with(reservation)


def test_tag_persist_failure_does_not_release_after_record():
    """Category persist is independent of usage accounting; Claude already ran."""
    with (
        _patch_db(),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude),
        patch.object(categorize, "record_ai_usage") as record,
        patch.object(categorize, "release_ai_token_reservation") as release,
        patch.object(
            categorize,
            "tenant_update",
            side_effect=RuntimeError("persist down cara@example.com Kitchen Remodel"),
        ),
    ):
        result = _run()
    assert result is None
    record.assert_called_once()
    release.assert_not_called()


def test_provider_and_budget_logs_do_not_leak_secrets(caplog):
    def boom(**kwargs):
        raise RuntimeError("provider boom cara@example.com anthropic_api_key +15555550100")

    with caplog.at_level(logging.WARNING):
        with (
            _patch_db(),
            patch.object(categorize, "reserve_ai_tokens", side_effect=_allowed),
            patch.object(categorize, "call_claude_messages_sync", side_effect=boom),
            patch.object(categorize, "record_ai_usage"),
            patch.object(categorize, "release_ai_token_reservation"),
        ):
            _run()
        with (
            _patch_db(),
            patch.object(categorize, "reserve_ai_tokens", side_effect=_blocked),
            patch.object(categorize, "call_claude_messages_sync", side_effect=_ok_claude),
        ):
            _run()
    _assert_no_secrets(caplog.text)
    assert "RuntimeError" not in caplog.text
    assert "provider boom" not in caplog.text


def test_blocked_categorization_does_not_raise_into_visitor_effects():
    """Background categorization must not turn a successful widget reply into a failure."""
    bg = BackgroundTasks()
    prior = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "need a quote"},
    ]
    has_contact = widget_chat_effects.schedule_post_response_effects(
        bg,
        tenant=_tenant(id=_TENANT_ID),
        widget=_widget(),
        req=_req(message="Please send it", session_id=_SESSION_ID),
        conversation_id="conv-p-categorize",
        messages=prior,
        assistant_text="I will follow up.",
        saved_rows=[{"id": "row-1", "role": "user"}],
    )
    assert has_contact is False
    categorize_tasks = [
        task for task in bg.tasks if task.func is categorize._categorize_conversation
    ]
    assert len(categorize_tasks) == 1

    provider = MagicMock(side_effect=_ok_claude)
    with (
        _patch_db(),
        patch.object(categorize, "reserve_ai_tokens", side_effect=_blocked),
        patch.object(categorize, "call_claude_messages_sync", side_effect=provider),
    ):
        categorize_tasks[0].func(*categorize_tasks[0].args, **categorize_tasks[0].kwargs)
    provider.assert_not_called()
