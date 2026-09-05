"""Enforceable AI budget for sms_agent.reply.

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages →
  record_ai_usage (release on provider error or record failure).
  llm_runtime does not record.
- Hard cap and missing/unloadable tenant policy block before the provider.
  The helper returns the existing Claude-error fallback SMS; it must not
  invent a new automated body and must not raise into the Twilio webhook.
- Compliance short-circuits (STOP/START/opt-out/rate-limit/handoff) stay
  provider-free and do not reserve.
- Purchased usage packs are honored because the reloaded tenant row
  passed to reserve includes id.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Two distinct inbound MessageSids reserve and record independently.
- Same MessageSid retry claims idempotency_keys
  (twilio:sms_agent:<MessageSid>) after silent compliance and before
  increment/reserve/provider. A duplicate returns None (webhook does not
  send). Empty MessageSid cannot be claimed.
- New logs/errors are tenant id + session id only. No SMS body, phone,
  email, credentials, provider exception text, or generated reply.

Run: pytest backend/tests/test_sms_agent_reply_usage_guard.py -q
"""

import inspect
import logging
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.routers import twilio_webhooks
from backend.services import sms_agent
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.services.sms_agent import REPLY_OPERATION, SMS_MAX_TOKENS
from backend.tests.fake_supabase import run
from backend.tests.test_sms_agent import (
    FROM_NUMBER,
    TENANT,
    TO_NUMBER,
    FakeDB,
    _base_tables,
)

_TENANT_ID = TENANT["id"]
_SESSION_ID = sms_agent.sms_session_id(FROM_NUMBER)
_BODY = "Are you open tonight? email cara@example.com +15555550100"
_REPLY = "Yes, we are open until 8."
_FALLBACK = sms_agent._CLAUDE_ERROR_FALLBACK


def _fixture(**extra):
    return FakeDB(_base_tables(**extra))


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=640_000,
        hard_limit_tokens=800_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=640_000,
        hard_limit_tokens=800_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 500),
        alert_threshold_tokens=640_000,
        hard_limit_tokens=800_000,
        reason="guard_unavailable",
    )


def _claude_result(text=_REPLY):
    result = MagicMock()
    result.text = text
    result.input_tokens = 80
    result.output_tokens = 24
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    result.duration_ms = 12
    return result


def _ok_claude(**kwargs):
    return _claude_result()


def _assert_no_secrets(text: str) -> None:
    blob = text.lower()
    assert "cara@example.com" not in blob
    assert _BODY.lower() not in blob
    assert "sk-ant" not in blob
    assert "anthropic_api_key" not in blob
    assert "anx_" not in blob
    assert "+15555550100" not in blob
    assert FROM_NUMBER.lower() not in blob
    assert _REPLY.lower() not in blob
    assert "sorry, having trouble" not in blob


async def _new_delivery(*_a, **_k):
    return True, None


async def _noop_idempotency(*_a, **_k):
    return None


def _invoke(*, db=None, body=_BODY, sid="SM-meter-1", tenant=None):
    return run(
        sms_agent.handle_inbound_sms(
            db or _fixture(),
            tenant=tenant or TENANT,
            from_number=FROM_NUMBER,
            to_number=TO_NUMBER,
            body=body,
            provider_message_id=sid,
        )
    )


@contextmanager
def _patches(*, reserve=_allowed, provider=None, record=None, release=None, claim=_new_delivery):
    with ExitStack() as stack:
        stack.enter_context(
            patch.object(sms_agent.sms_compliance, "is_suppressed", return_value=False)
        )
        stack.enter_context(
            patch.object(
                sms_agent.sms_rate_limiter, "check_sms_rate_limit", return_value=True
            )
        )
        increment = stack.enter_context(
            patch.object(sms_agent.sms_rate_limiter, "increment_sms_count")
        )
        stack.enter_context(
            patch.object(sms_agent, "_query_kb_articles", new=AsyncMock(return_value=[]))
        )
        stack.enter_context(patch.object(sms_agent, "_load_chat_history", return_value=[]))
        stack.enter_context(
            patch.object(sms_agent, "_compact_messages_for_llm", return_value=[])
        )
        stack.enter_context(patch.object(sms_agent, "_save_chat_messages"))
        claim_mock = stack.enter_context(
            patch.object(sms_agent, "check_and_record", new=AsyncMock(side_effect=claim))
        )
        stack.enter_context(
            patch.object(
                sms_agent, "record_response", new=AsyncMock(side_effect=_noop_idempotency)
            )
        )
        stack.enter_context(
            patch.object(
                sms_agent, "delete_key", new=AsyncMock(side_effect=_noop_idempotency)
            )
        )
        reserve_mock = stack.enter_context(
            patch.object(sms_agent, "reserve_ai_tokens", side_effect=reserve)
        )
        provider_mock = stack.enter_context(
            patch.object(
                sms_agent,
                "call_claude_messages",
                new=provider or AsyncMock(side_effect=_ok_claude),
            )
        )
        record_mock = stack.enter_context(
            patch.object(sms_agent, "record_ai_usage", side_effect=record or MagicMock())
        )
        release_mock = stack.enter_context(
            patch.object(
                sms_agent,
                "release_ai_token_reservation",
                side_effect=release or MagicMock(),
            )
        )
        yield SimpleNamespace(
            increment=increment,
            claim=claim_mock,
            reserve=reserve_mock,
            provider=provider_mock,
            record=record_mock,
            release=release_mock,
        )


# --- compliance short-circuits ----------------------------------------------


def test_stop_keyword_skips_claim_reserve_and_provider():
    with (
        patch.object(sms_agent.sms_compliance, "record_opt_out") as opt_out,
        patch.object(sms_agent, "check_and_record", new=AsyncMock()) as claim,
        patch.object(sms_agent, "reserve_ai_tokens") as reserve,
        patch.object(sms_agent, "call_claude_messages", new=AsyncMock()) as provider,
        patch.object(sms_agent.sms_rate_limiter, "increment_sms_count") as increment,
    ):
        result = _invoke(body="STOP", sid="SM-stop")
    assert result is None
    opt_out.assert_called_once()
    claim.assert_not_awaited()
    reserve.assert_not_called()
    provider.assert_not_awaited()
    increment.assert_not_called()


def test_start_keyword_skips_provider():
    with (
        patch.object(sms_agent.sms_compliance, "record_opt_in") as opt_in,
        patch.object(sms_agent, "check_and_record", new=AsyncMock()) as claim,
        patch.object(sms_agent, "reserve_ai_tokens") as reserve,
        patch.object(sms_agent, "call_claude_messages", new=AsyncMock()) as provider,
    ):
        result = _invoke(body="START", sid="SM-start")
    assert result is None
    opt_in.assert_called_once()
    claim.assert_not_awaited()
    reserve.assert_not_called()
    provider.assert_not_awaited()


def test_suppressed_recipient_skips_provider():
    with (
        patch.object(sms_agent.sms_compliance, "is_suppressed", return_value=True),
        patch.object(sms_agent, "check_and_record", new=AsyncMock()) as claim,
        patch.object(sms_agent, "reserve_ai_tokens") as reserve,
        patch.object(sms_agent, "call_claude_messages", new=AsyncMock()) as provider,
    ):
        result = _invoke(sid="SM-suppressed")
    assert result is None
    claim.assert_not_awaited()
    reserve.assert_not_called()
    provider.assert_not_awaited()


def test_rate_limit_skips_provider():
    with (
        patch.object(sms_agent.sms_compliance, "is_suppressed", return_value=False),
        patch.object(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", return_value=False
        ),
        patch.object(sms_agent, "check_and_record", new=AsyncMock()) as claim,
        patch.object(sms_agent, "reserve_ai_tokens") as reserve,
        patch.object(sms_agent, "call_claude_messages", new=AsyncMock()) as provider,
        patch.object(sms_agent.sms_rate_limiter, "increment_sms_count") as increment,
    ):
        result = _invoke(sid="SM-limited")
    assert result is None
    claim.assert_not_awaited()
    reserve.assert_not_called()
    provider.assert_not_awaited()
    increment.assert_not_called()


def test_handoff_lockout_skips_provider():
    db = FakeDB(
        _base_tables(
            conversations={"select_data": [{"id": "conv-1", "tags": ["handoff"]}]}
        )
    )
    with (
        patch.object(sms_agent.sms_compliance, "is_suppressed", return_value=False),
        patch.object(
            sms_agent.sms_rate_limiter, "check_sms_rate_limit", return_value=True
        ),
        patch.object(sms_agent, "_save_chat_messages"),
        patch.object(sms_agent, "check_and_record", new=AsyncMock()) as claim,
        patch.object(sms_agent, "reserve_ai_tokens") as reserve,
        patch.object(sms_agent, "call_claude_messages", new=AsyncMock()) as provider,
        patch.object(sms_agent.sms_rate_limiter, "increment_sms_count") as increment,
    ):
        result = _invoke(db=db, sid="SM-handoff")
    assert result is None
    claim.assert_not_awaited()
    reserve.assert_not_called()
    provider.assert_not_awaited()
    increment.assert_not_called()


def test_disabled_tenant_webhook_never_reaches_agent():
    src = inspect.getsource(twilio_webhooks.handle_inbound_sms)
    assert src.count("await sms_agent.handle_inbound_sms") == 1
    assert "sms_agent_enabled" in src
    assert src.index("sms_agent_enabled") < src.index("await sms_agent.handle_inbound_sms")


# --- reserve / record / release ---------------------------------------------


def test_hard_cap_blocks_before_provider_and_uses_existing_fallback():
    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(reserve=_blocked, provider=provider):
        result = _invoke()
    assert result == _FALLBACK
    provider.assert_not_awaited()


def test_missing_tenant_row_fails_closed_before_provider(caplog):
    db = FakeDB(_base_tables(tenants={"select_data": []}))
    provider = AsyncMock(side_effect=_ok_claude)
    with caplog.at_level(logging.WARNING):
        with _patches(provider=provider):
            result = _invoke(db=db)
    assert result == _FALLBACK
    assert "failing closed before provider" in caplog.text
    provider.assert_not_awaited()
    _assert_no_secrets(caplog.text)


def test_tenant_lookup_error_fails_closed_before_provider(caplog):
    db = FakeDB(_base_tables(tenants={"raise_select": True}))
    provider = AsyncMock(side_effect=_ok_claude)
    with caplog.at_level(logging.WARNING):
        with _patches(provider=provider):
            result = _invoke(db=db)
    assert result == _FALLBACK
    assert "tenant load failed" in caplog.text
    provider.assert_not_awaited()
    _assert_no_secrets(caplog.text)


def test_success_records_usage_once():
    record = MagicMock()
    release = MagicMock()
    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(provider=provider, record=record, release=release):
        result = _invoke()
    assert result == _REPLY
    provider.assert_awaited_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == REPLY_OPERATION
    assert recorded["session_id"] == _SESSION_ID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 80
    assert provider.call_args.kwargs["max_tokens"] == SMS_MAX_TOKENS
    assert provider.call_args.kwargs["operation"] == REPLY_OPERATION


def test_provider_error_releases_reservation_and_uses_existing_fallback(caplog):
    def boom(**kwargs):
        raise RuntimeError(
            "claude down secret=anthropic_api_key customer=cara@example.com "
            f"phone={FROM_NUMBER} body={_BODY} reply={_REPLY}"
        )

    release = MagicMock()
    record = MagicMock()
    with caplog.at_level(logging.WARNING):
        with _patches(
            provider=AsyncMock(side_effect=boom),
            record=record,
            release=release,
        ):
            result = _invoke()
    assert result == _FALLBACK
    assert "provider error" in caplog.text
    _assert_no_secrets(caplog.text)
    record.assert_not_called()
    release.assert_called_once()
    assert release.call_args.args[0].allowed is True
    assert release.call_args.args[0].reason != "guard_unavailable"


def test_guard_unavailable_allows_call_without_persisting():
    record = MagicMock()
    release = MagicMock()
    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(
        reserve=_unavailable, provider=provider, record=record, release=release
    ):
        result = _invoke()
    assert result == _REPLY
    provider.assert_awaited_once()
    record.assert_called_once()
    assert record.call_args.kwargs["reservation"].reason == "guard_unavailable"
    assert record.call_args.kwargs["reservation"].allowed is True
    release.assert_not_called()


def test_purchased_usage_pack_is_honored_on_reserve():
    captured = {}

    def capture_reserve(*, tenant, estimated_tokens, operation, session_id):
        captured["tenant"] = tenant
        captured["estimated_tokens"] = estimated_tokens
        captured["operation"] = operation
        return _allowed(estimated_tokens=estimated_tokens)

    with _patches(reserve=capture_reserve):
        with (
            patch(
                "backend.services.ai_usage_guard._sum_usage_packs",
                return_value=1_000_000,
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
                tenant={"id": _TENANT_ID, "plan": "chatbot"},
                estimated_tokens=500,
                operation=REPLY_OPERATION,
                session_id=_SESSION_ID,
            )
            _invoke()

    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["tenant"]["plan"] == "chatbot"
    assert reservation.allowed is True
    # chatbot baseline 800k + 1M pack
    assert rpc_limit["hard"] == 1_800_000


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
            operation=REPLY_OPERATION,
            session_id=_SESSION_ID,
            model="claude-sonnet-5",
        )
    assert recorded is None
    release.assert_called_once_with(reservation)


def test_path_releases_when_record_rpc_fails_and_keeps_reply():
    reservation = _allowed()

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with _patches(reserve=lambda **_k: reservation, record=fail_record):
        with (
            patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
            patch(
                "backend.services.ai_usage_guard.release_ai_token_reservation"
            ) as release,
        ):
            mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
            result = _invoke()
    assert result == _REPLY
    release.assert_called_once_with(reservation)


def test_two_distinct_inbound_messages_account_independently():
    record = MagicMock()
    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(provider=provider, record=record):
        first = _invoke(sid="SM-one", body="Need a quote")
        second = _invoke(sid="SM-two", body="What time do you open")
    assert first == _REPLY
    assert second == _REPLY
    assert provider.await_count == 2
    assert record.call_count == 2


def test_same_messagesid_retry_skips_provider_and_send():
    seen: list[str] = []

    async def claim(_db, _provider, event_id):
        if event_id in seen:
            return False, {"response_body": {"status": "processed"}}
        seen.append(event_id)
        return True, None

    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(provider=provider, claim=claim) as hooks:
        first = _invoke(sid="SM-retry")
        second = _invoke(sid="SM-retry")
    assert first == _REPLY
    assert second is None
    assert provider.await_count == 1
    assert hooks.increment.call_count == 1
    assert seen == ["sms_agent:SM-retry"]


def test_empty_messagesid_does_not_claim():
    claim = AsyncMock(side_effect=_new_delivery)
    provider = AsyncMock(side_effect=_ok_claude)
    with _patches(provider=provider, claim=claim) as hooks:
        result = _invoke(sid="  ")
    assert result == _REPLY
    hooks.claim.assert_not_awaited()
    provider.assert_awaited_once()


def test_metered_call_metadata_is_ids_only():
    seen = []

    async def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with _patches(provider=AsyncMock(side_effect=capture_claude)):
        _invoke()
    meta = seen[0]["metadata"]
    assert set(meta) == {"tenant_id", "session_id", "channel"}
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["session_id"] == _SESSION_ID
    _assert_no_secrets(str(meta))


def test_provider_and_budget_logs_do_not_leak_secrets(caplog):
    def boom(**kwargs):
        raise RuntimeError(
            f"provider boom cara@example.com anthropic_api_key {FROM_NUMBER} {_BODY}"
        )

    with caplog.at_level(logging.WARNING):
        with _patches(provider=AsyncMock(side_effect=boom)):
            _invoke()
        with _patches(reserve=_blocked):
            _invoke()
    _assert_no_secrets(caplog.text)
    assert "RuntimeError" not in caplog.text
    assert "provider boom" not in caplog.text


def test_single_external_call_site_and_os_inbound_does_not_call_reply():
    webhook_src = inspect.getsource(twilio_webhooks.handle_inbound_sms)
    assert webhook_src.count("await sms_agent.handle_inbound_sms") == 1
    from backend.routers import os_inbound

    assert "sms_agent" not in inspect.getsource(os_inbound)
    agent_src = inspect.getsource(sms_agent.handle_inbound_sms)
    assert agent_src.count("call_claude_messages") == 1
    assert "REPLY_OPERATION" in agent_src


def test_reserve_uses_reloaded_tenant_id_and_estimate():
    captured = {}

    def capture_reserve(*, tenant, estimated_tokens, operation, session_id):
        captured.update(
            {
                "tenant": tenant,
                "estimated_tokens": estimated_tokens,
                "operation": operation,
                "session_id": session_id,
            }
        )
        return _allowed(estimated_tokens=estimated_tokens)

    with _patches(reserve=capture_reserve):
        _invoke()
    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["operation"] == REPLY_OPERATION
    assert captured["session_id"] == _SESSION_ID
    assert captured["estimated_tokens"] >= SMS_MAX_TOKENS
