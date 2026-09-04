"""Enforceable AI budget for live-AI voice respond (calls.voice_respond).

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages → record_ai_usage
  (release on provider error or record failure). llm_runtime does not record.
- Hard cap blocks before the provider. Twilio still gets HTTP 200 TwiML with
  a paused spoken line and goodbye (more Gather rounds cannot unblock a cap).
- Purchased usage packs are honored because the tenant row passed to reserve
  includes id.
- Tenant/policy cannot be loaded (missing row or lookup exception): fail
  closed before the provider. Spoken fallback, not a 5xx and not unmetered
  Claude. No invented free-plan cap.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Signed /voice/respond is not a paid-Claude bypass of incoming: voicemail-mode
  tenants fail closed before reserve/provider. Voice minutes are not rechecked
  on each Gather (start-of-call gate only).
- Repeated Gather rounds reserve and record independently.

Run: pytest backend/tests/test_voice_respond_usage_guard.py -q
"""

import logging
import os
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.main import app
from backend.routers import calls_webhooks as voice
from backend.routers.automations import verify_twilio_request
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase import db, run

_TENANT_ID = "t-voice-budget"
_CALL_SID = "CA-budget-001"
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}
_PHONE_TENANT = {
    "id": _TENANT_ID,
    "business_name": "Test Plumbing",
    "business_type": "plumber",
    "plan": "agent_os",
    "voice_ai_enabled": True,
}
_VOICEMAIL_TENANT = {
    "id": _TENANT_ID,
    "business_name": "Test Plumbing",
    "business_type": "plumber",
    "plan": "chatbot",
    "voice_ai_enabled": False,
}


def _fixture():
    return db({"tenants": [_TENANT]})


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


def _claude_result(text="We are open nine to five."):
    result = MagicMock()
    result.text = text
    result.input_tokens = 80
    result.output_tokens = 30
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    result.duration_ms = 12
    return result


async def _ok_claude(**kwargs):
    return _claude_result()


def _assert_no_secrets(text: str) -> None:
    blob = text.lower()
    assert "cara@example.com" not in blob
    assert "cara diaz" not in blob
    assert "sk-ant" not in blob
    assert "anthropic_api_key" not in blob
    assert "anx_" not in blob
    assert "+15555550100" not in blob


def _call(**kwargs):
    return voice._call_voice_claude_with_budget(
        db=kwargs.get("db", _fixture()),
        tenant_id=kwargs.get("tenant_id", _TENANT_ID),
        call_sid=kwargs.get("call_sid", _CALL_SID),
        system=kwargs.get("system", "You are a phone assistant."),
        messages=kwargs.get("messages", [{"role": "user", "content": "hours?"}]),
        model=kwargs.get("model", "claude-sonnet-4-6"),
        max_tokens=kwargs.get("max_tokens", 160),
        round_num=kwargs.get("round_num", 1),
        faq_chars=kwargs.get("faq_chars", 0),
    )


# --- reserve / record / release ---------------------------------------------


def test_hard_cap_blocks_before_provider():
    provider = MagicMock(side_effect=_ok_claude)
    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_blocked) as reserve,
        patch.object(voice, "call_claude_messages", side_effect=provider),
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "release_ai_token_reservation") as release,
    ):
        with pytest.raises(voice.VoiceBudgetExceeded):
            run(_call())
    reserve.assert_called_once()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["operation"] == "calls.voice_respond"
    assert reserve.call_args.kwargs["session_id"] == _CALL_SID


def test_repeated_gather_rounds_reserve_and_record_independently():
    """Each Gather round is its own reserve/record; one result is not double-counted."""
    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "release_ai_token_reservation") as release,
    ):
        first = run(_call(round_num=1, call_sid="CA-round-1"))
        second = run(_call(round_num=2, call_sid="CA-round-2"))
    assert first.text.startswith("We are open")
    assert second.text.startswith("We are open")
    assert reserve.call_count == 2
    assert provider.call_count == 2
    assert record.call_count == 2
    release.assert_not_called()
    sessions = [c.kwargs["session_id"] for c in reserve.call_args_list]
    assert sessions == ["CA-round-1", "CA-round-2"]
    recorded_sessions = [c.kwargs["session_id"] for c in record.call_args_list]
    assert recorded_sessions == ["CA-round-1", "CA-round-2"]


def test_success_records_usage_once():
    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "release_ai_token_reservation") as release,
    ):
        out = run(_call())
    assert out.text.startswith("We are open")
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == "calls.voice_respond"
    assert recorded["session_id"] == _CALL_SID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 80
    assert recorded["result"].output_tokens == 30


def test_provider_error_releases_reservation():
    async def boom(**kwargs):
        raise RuntimeError("claude down")

    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(voice, "call_claude_messages", side_effect=boom),
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "release_ai_token_reservation") as release,
    ):
        with pytest.raises(RuntimeError, match="claude down"):
            run(_call())
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
        patch.object(voice, "reserve_ai_tokens", side_effect=capture_reserve),
        patch.object(voice, "call_claude_messages", side_effect=_ok_claude),
        patch.object(voice, "record_ai_usage"),
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
            operation="calls.voice_respond",
            session_id=_CALL_SID,
        )
        run(_call())

    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["tenant"]["plan"] == "agent_os"
    assert reservation.allowed is True
    # agent_os baseline 5M + 1M pack
    assert rpc_limit["hard"] == 6_000_000


def test_guard_unavailable_allows_call_without_persisting():
    """Valid tenant loaded, reserve RPC down: shared widget-chat fail-open."""
    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_unavailable) as reserve,
        patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "release_ai_token_reservation") as release,
    ):
        out = run(_call())
    assert out.text.startswith("We are open")
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    assert record.call_args.kwargs["reservation"].reason == "guard_unavailable"
    assert record.call_args.kwargs["reservation"].allowed is True
    release.assert_not_called()


def test_missing_tenant_row_fails_closed_before_provider(caplog):
    fixture = db({})  # no tenants row
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(voice, "reserve_ai_tokens") as reserve,
            patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
            patch.object(voice, "record_ai_usage") as record,
            patch.object(voice, "release_ai_token_reservation") as release,
        ):
            with pytest.raises(voice.VoiceBudgetGuardUnavailable) as exc:
                run(_call(db=fixture))
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    _assert_no_secrets(str(exc.value))
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
            patch.object(voice, "reserve_ai_tokens") as reserve,
            patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
            patch.object(voice, "record_ai_usage") as record,
            patch.object(voice, "release_ai_token_reservation") as release,
        ):
            with pytest.raises(voice.VoiceBudgetGuardUnavailable) as exc:
                run(_call(db=BoomDb()))
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    _assert_no_secrets(str(exc.value))
    _assert_no_secrets(caplog.text)


def test_metered_call_metadata_is_ids_and_counts_only():
    seen = []

    async def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with (
        patch.object(voice, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(voice, "call_claude_messages", side_effect=capture_claude),
        patch.object(voice, "record_ai_usage"),
    ):
        run(_call())
    meta = seen[0]["metadata"]
    assert set(meta) == {
        "tenant_id",
        "call_sid",
        "round",
        "history_count",
        "faq_chars",
    }
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["call_sid"] == _CALL_SID
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
            operation="calls.voice_respond",
            session_id=_CALL_SID,
            model="claude-sonnet-4-6",
        )
    assert recorded is None
    release.assert_called_once_with(reservation)


def test_voice_path_releases_when_record_rpc_fails():
    reservation = _allowed()

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with (
        patch.object(voice, "reserve_ai_tokens", return_value=reservation),
        patch.object(voice, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(voice, "record_ai_usage", side_effect=fail_record),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        out = run(_call())
    assert out.text.startswith("We are open")
    provider.assert_called_once()
    release.assert_called_once_with(reservation)


# --- Twilio HTTP semantics ---------------------------------------------------


_ENDPOINT = "/api/v1/calls/voice/respond"
_CALLER = "+15555550100"
_CALLED = "+15555550200"


def _post(client, speech="what are your hours", round_num=1):
    body = urllib.parse.urlencode(
        {
            "SpeechResult": speech,
            "CallSid": _CALL_SID,
            "From": _CALLER,
            "To": _CALLED,
        }
    )
    return client.post(
        f"{_ENDPOINT}?round={round_num}",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.fixture()
def respond_client(mock_supabase):
    def _chain(rows):
        result = MagicMock()
        result.data = rows
        chain = MagicMock()
        for method in ("select", "eq", "order", "limit", "insert", "update", "gte", "lt"):
            getattr(chain, method).return_value = chain
        chain.execute.return_value = result
        return chain

    tables = {
        "chat_messages": _chain([]),
        "tenants": _chain([_TENANT]),
        "faq_entries": _chain([]),
        "widget_configs": _chain([]),
    }
    mock_supabase.table.side_effect = lambda name: tables.get(name, _chain([]))
    client = SyncASGITestClient(app)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture(autouse=True)
def _bypass_twilio_signature():
    app.dependency_overrides[verify_twilio_request] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(verify_twilio_request, None)


def test_hard_cap_returns_200_twiml_goodbye_without_provider(respond_client):
    provider = AsyncMock(return_value=_claude_result())
    with (
        patch.object(voice, "_find_tenant_by_phone", return_value=_PHONE_TENANT),
        patch.object(voice, "reserve_ai_tokens", side_effect=_blocked),
        patch.object(voice, "call_claude_messages", new=provider),
        patch.object(voice, "record_ai_usage") as record,
        patch.object(voice, "_finalize_ai_call", new=AsyncMock()),
        patch("backend.services.voice_booking.booking_prompt_context", return_value=None),
        patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ),
        patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]),
    ):
        resp = _post(respond_client)
    assert resp.status_code == 200
    assert "application/xml" in resp.headers.get("content-type", "")
    assert "<Gather" not in resp.text
    assert "temporarily paused" in resp.text
    provider.assert_not_called()
    record.assert_not_called()
    _assert_no_secrets(resp.text)


def test_voicemail_mode_signed_callback_does_not_call_provider(respond_client, caplog):
    """Signed /voice/respond must not bypass incoming's live-AI gate."""
    provider = AsyncMock(return_value=_claude_result())
    reserve = MagicMock(side_effect=_allowed)
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(voice, "_find_tenant_by_phone", return_value=_VOICEMAIL_TENANT),
            patch.object(voice, "reserve_ai_tokens", side_effect=reserve),
            patch.object(voice, "call_claude_messages", new=provider),
            patch.object(voice, "record_ai_usage") as record,
            patch.object(voice, "_finalize_ai_call", new=AsyncMock()),
        ):
            resp = _post(respond_client)
    assert resp.status_code == 200
    assert "<Gather" not in resp.text
    assert "unable to assist" in resp.text
    provider.assert_not_called()
    reserve.assert_not_called()
    record.assert_not_called()
    _assert_no_secrets(resp.text)
    _assert_no_secrets(caplog.text)
    assert "cara@example.com" not in caplog.text
    assert "SpeechResult" not in caplog.text


def test_exhausted_minutes_are_not_rechecked_on_gather(respond_client):
    """Minutes are a start-of-call gate. An in-progress Gather must not drop."""
    provider = AsyncMock(return_value=_claude_result())
    with (
        patch.object(voice, "_find_tenant_by_phone", return_value=_PHONE_TENANT),
        patch.object(voice, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(voice, "call_claude_messages", new=provider),
        patch.object(voice, "record_ai_usage"),
        patch.object(voice, "_finalize_ai_call", new=AsyncMock()),
        patch("backend.services.voice_booking.booking_prompt_context", return_value=None),
        patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ),
        patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]),
        patch(
            "backend.services.voice_usage.voice_minutes_exhausted",
            return_value=True,
        ),
    ):
        resp = _post(respond_client)
    assert resp.status_code == 200
    assert "We are open" in resp.text
    provider.assert_called_once()


def test_record_persist_failure_returns_200_with_completed_reply(respond_client):
    """Persist failure releases; the already-completed Claude reply is not a 5xx."""
    reservation = _allowed()
    provider = AsyncMock(return_value=_claude_result())

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with (
        patch.object(voice, "_find_tenant_by_phone", return_value=_PHONE_TENANT),
        patch.object(voice, "reserve_ai_tokens", return_value=reservation),
        patch.object(voice, "call_claude_messages", new=provider),
        patch.object(voice, "record_ai_usage", side_effect=fail_record),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
        patch.object(voice, "_finalize_ai_call", new=AsyncMock()),
        patch("backend.services.voice_booking.booking_prompt_context", return_value=None),
        patch(
            "backend.routers.widget_chat_helpers._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ),
        patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]),
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        resp = _post(respond_client)
    assert resp.status_code == 200
    assert "We are open" in resp.text
    assert "having a little trouble" not in resp.text
    provider.assert_called_once()
    release.assert_called_once_with(reservation)
    _assert_no_secrets(resp.text)


def test_missing_budget_tenant_returns_200_fallback_without_provider(
    respond_client, caplog
):
    provider = AsyncMock(return_value=_claude_result())
    with caplog.at_level(logging.WARNING):
        with (
            patch.object(voice, "_find_tenant_by_phone", return_value=_PHONE_TENANT),
            patch.object(voice, "_load_voice_budget_tenant", return_value=None),
            patch.object(voice, "reserve_ai_tokens") as reserve,
            patch.object(voice, "call_claude_messages", new=provider),
            patch.object(voice, "_finalize_ai_call", new=AsyncMock()),
            patch("backend.services.voice_booking.booking_prompt_context", return_value=None),
            patch(
                "backend.routers.widget_chat_helpers._query_kb_articles",
                new=AsyncMock(return_value=[]),
            ),
            patch("backend.services.os_kb_feed.vertical_guidance", return_value=[]),
        ):
            resp = _post(respond_client)
    assert resp.status_code == 200
    assert "having a little trouble" in resp.text
    reserve.assert_not_called()
    provider.assert_not_called()
    _assert_no_secrets(resp.text)
    _assert_no_secrets(caplog.text)
