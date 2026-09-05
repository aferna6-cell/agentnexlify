"""Enforceable AI budget for calls.generate_summary.

Contract:
- Claude spend uses reserve_ai_tokens → call_claude_messages →
  record_ai_usage (release on provider error or record failure).
  llm_runtime does not record.
- Hard cap and missing/unloadable tenant policy block before the provider.
  The background task returns; it must not raise into an already-completed
  call or transcription webhook.
- Purchased usage packs are honored because the tenant row passed to reserve
  includes id.
- After a valid tenant is loaded, a transient reserve RPC outage keeps the
  shared widget-chat contract: allowed=True, reason=guard_unavailable;
  provider may run; record is invoked and persist is skipped.
- Live-AI finalize and /voice/transcription-complete can both target the
  same calls.id. A compare-and-swap on calls.summary means two delivery
  paths create at most one provider/accounting/persisted summary.
- Genuinely separate call ids still reserve and record independently.
- New logs/errors are tenant id + call id + counts only. No transcript,
  customer PII, credentials, provider exception text, or summary payload.

Run: pytest backend/tests/test_voice_call_summary_usage_guard.py -q
"""

import logging
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.background import BackgroundTasks

from backend.main import app
from backend.routers import calls_webhooks
from backend.routers.automations import verify_twilio_request
from backend.services.ai_usage_guard import AIUsageReservation, record_ai_usage
from backend.services.voice_call_summary import (
    SUMMARY_CLAIM,
    SUMMARY_OPERATION,
    _finalize_ai_call,
    _generate_call_summary,
    _summary_max_tokens,
)
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase import db, run

_TENANT_ID = "t-voice-summary-budget"
_CALL_ID = "call-summary-001"
_CALL_SID = "CA-summary-001"
_SESSION_ID = _CALL_ID
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
    "business_name": "Summary Plumbing",
}
_TRANSCRIPT = (
    "[caller]: Hi, this is Cara Diaz at cara@example.com +15555550100\n"
    "[assistant]: Thanks for calling. What can we help with?"
)
_SUMMARY_JSON = (
    '{"summary": "Caller asked about a kitchen remodel quote.", '
    '"action_items": ["Send quote"], '
    '"sentiment": "positive", '
    '"follow_up": "Email pricing sheet"}'
)


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 800),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 800),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 800),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="guard_unavailable",
    )


def _claude_result(text=_SUMMARY_JSON):
    result = MagicMock()
    result.text = text
    result.input_tokens = 120
    result.output_tokens = 40
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    result.duration_ms = 18
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
    assert "email pricing" not in blob
    assert "send quote" not in blob


def _call_row(**overrides):
    row = {
        "id": _CALL_ID,
        "tenant_id": _TENANT_ID,
        "lead_id": "lead-summary-1",
        "twilio_call_sid": _CALL_SID,
        "status": "in-progress",
        "summary": "AI conversation completed. Summary generating...",
        "caller_phone": "+15555550100",
        "transcript": [],
    }
    row.update(overrides)
    return row


class _StoreTable:
    def __init__(self, store, name):
        self.store = store
        self.name = name
        self._op = None
        self._payload = None
        self._filters = {}

    def select(self, _cols="*"):
        self._op = "select"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def eq(self, col, val):
        self._filters[col] = ("eq", val)
        return self

    def is_(self, col, val):
        self._filters[col] = ("is", val)
        return self

    def limit(self, _n):
        return self

    def order(self, *_a, **_k):
        return self

    def _match(self, row):
        for col, (kind, val) in self._filters.items():
            cur = row.get(col)
            if kind == "is" and val == "null" and cur is not None:
                return False
            if kind == "eq" and cur != val:
                return False
        return True

    def execute(self):
        if self.name == "tenants":
            tid = self._filters.get("id", (None, None))[1]
            if self.store.tenant and (tid is None or self.store.tenant.get("id") == tid):
                return MagicMock(data=[dict(self.store.tenant)])
            return MagicMock(data=[])
        if self.name == "calls":
            rows = [dict(c) for c in self.store.calls.values() if self._match(c)]
            if self._op == "update":
                updated = []
                for row in rows:
                    row.update(self._payload)
                    self.store.calls[row["id"]].update(self._payload)
                    self.store.updates.append(dict(self._payload, id=row["id"]))
                    updated.append(dict(self.store.calls[row["id"]]))
                return MagicMock(data=updated)
            return MagicMock(data=rows)
        if self.name == "chat_messages":
            return MagicMock(data=list(self.store.chat_messages))
        if self.name == "action_items" and self._op == "insert":
            self.store.action_items.append(self._payload)
            return MagicMock(data=[self._payload])
        return MagicMock(data=[])


class _SummaryStore:
    def __init__(self, tenant=None, calls=None, chat_messages=None):
        self.tenant = dict(tenant) if tenant else None
        self.calls = {c["id"]: dict(c) for c in (calls or [])}
        self.chat_messages = list(chat_messages or [])
        self.action_items = []
        self.updates = []

    def table(self, name):
        return _StoreTable(self, name)


def _store(**call_overrides):
    return _SummaryStore(tenant=_TENANT, calls=[_call_row(**call_overrides)])


def _run_summary(store=None, **kwargs):
    return run(
        _generate_call_summary(
            kwargs.get("call_id", _CALL_ID),
            kwargs.get("tenant_id", _TENANT_ID),
            kwargs.get("lead_id", "lead-summary-1"),
            kwargs.get("transcript_text", _TRANSCRIPT),
        )
    )


# --- reserve / record / release ---------------------------------------------


def test_empty_transcript_skips_reserve_and_provider():
    provider = AsyncMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=_store(),
        ),
        patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
    ):
        result = _run_summary(transcript_text="   \n")
    assert result is None
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()


def test_hard_cap_blocks_before_provider():
    provider = AsyncMock(side_effect=_ok_claude)
    store = _store()
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_blocked,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_call_summary.release_ai_token_reservation"
        ) as release,
    ):
        result = _run_summary()
    assert result is None
    reserve.assert_called_once()
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()
    assert reserve.call_args.kwargs["tenant"]["id"] == _TENANT_ID
    assert reserve.call_args.kwargs["operation"] == SUMMARY_OPERATION
    assert reserve.call_args.kwargs["session_id"] == _SESSION_ID
    assert reserve.call_args.kwargs["estimated_tokens"] >= _summary_max_tokens()
    assert store.calls[_CALL_ID]["summary"] == SUMMARY_CLAIM


def test_success_records_usage_once():
    store = _store()
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_call_summary.release_ai_token_reservation"
        ) as release,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        result = _run_summary()
    assert result is None
    reserve.assert_called_once()
    provider.assert_awaited_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == SUMMARY_OPERATION
    assert recorded["session_id"] == _SESSION_ID
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 120
    assert recorded["result"].output_tokens == 40
    assert provider.call_args.kwargs["max_tokens"] == _summary_max_tokens()
    assert provider.call_args.kwargs["operation"] == SUMMARY_OPERATION
    assert store.calls[_CALL_ID]["summary"] == "Caller asked about a kitchen remodel quote."


def test_provider_error_releases_reservation_without_raising(caplog):
    def boom(**kwargs):
        raise RuntimeError(
            "claude down secret=anthropic_api_key customer=cara@example.com"
        )

    with caplog.at_level(logging.WARNING):
        with (
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=_store(),
            ),
            patch(
                "backend.services.voice_call_summary.reserve_ai_tokens",
                side_effect=_allowed,
            ) as reserve,
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=boom,
            ),
            patch("backend.services.voice_call_summary.record_ai_usage") as record,
            patch(
                "backend.services.voice_call_summary.release_ai_token_reservation"
            ) as release,
        ):
            result = _run_summary()
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
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=_store(),
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=capture_reserve,
        ),
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage"),
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
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
            tenant={"id": _TENANT_ID, "plan": "agent_os"},
            estimated_tokens=800,
            operation=SUMMARY_OPERATION,
            session_id=_SESSION_ID,
        )
        _run_summary()

    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["tenant"]["plan"] == "agent_os"
    assert reservation.allowed is True
    assert rpc_limit["hard"] == 6_000_000


def test_guard_unavailable_allows_call_without_persisting():
    """Valid tenant loaded, reserve RPC down: shared widget-chat fail-open."""
    store = _store()
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_unavailable,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_call_summary.release_ai_token_reservation"
        ) as release,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        result = _run_summary()
    assert result is None
    reserve.assert_called_once()
    provider.assert_awaited_once()
    record.assert_called_once()
    assert record.call_args.kwargs["reservation"].reason == "guard_unavailable"
    assert record.call_args.kwargs["reservation"].allowed is True
    release.assert_not_called()
    assert store.calls[_CALL_ID]["summary"] == "Caller asked about a kitchen remodel quote."


def test_missing_tenant_row_fails_closed_before_provider(caplog):
    store = _SummaryStore(tenant=None, calls=[_call_row()])
    with caplog.at_level(logging.WARNING):
        with (
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=store,
            ),
            patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=_ok_claude,
            ) as provider,
            patch("backend.services.voice_call_summary.record_ai_usage") as record,
            patch(
                "backend.services.voice_call_summary.release_ai_token_reservation"
            ) as release,
        ):
            result = _run_summary()
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
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=BoomDb(),
            ),
            patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=_ok_claude,
            ) as provider,
            patch("backend.services.voice_call_summary.record_ai_usage") as record,
            patch(
                "backend.services.voice_call_summary.release_ai_token_reservation"
            ) as release,
        ):
            result = _run_summary()
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
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                side_effect=RuntimeError(
                    "supabase down secret=anthropic_api_key customer=cara@example.com"
                ),
            ),
            patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=_ok_claude,
            ) as provider,
        ):
            result = _run_summary()
    assert result is None
    assert "tenant load failed" in caplog.text
    reserve.assert_not_called()
    provider.assert_not_called()
    _assert_no_secrets(caplog.text)


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
            operation=SUMMARY_OPERATION,
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )
    assert recorded is None
    release.assert_called_once_with(reservation)


def test_summary_path_releases_when_record_rpc_fails():
    reservation = _allowed()
    store = _store()

    def fail_record(**kwargs):
        return record_ai_usage(**kwargs)

    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            return_value=reservation,
        ),
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
        patch(
            "backend.services.voice_call_summary.record_ai_usage",
            side_effect=fail_record,
        ),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.release_ai_token_reservation") as release,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        mock_supa.return_value.rpc.side_effect = RuntimeError("record rpc down")
        result = _run_summary()
    assert result is None
    provider.assert_awaited_once()
    release.assert_called_once_with(reservation)


def test_parse_failure_records_and_does_not_raise(caplog):
    store = _store()
    with caplog.at_level(logging.WARNING):
        with (
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=store,
            ),
            patch(
                "backend.services.voice_call_summary.reserve_ai_tokens",
                side_effect=_allowed,
            ),
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                return_value=_claude_result("not json at all {{{"),
            ),
            patch("backend.services.voice_call_summary.record_ai_usage") as record,
            patch(
                "backend.services.voice_call_summary.release_ai_token_reservation"
            ) as release,
            patch(
                "backend.services.voice_recovery.create_missed_call_followup",
                new_callable=AsyncMock,
            ),
            patch(
                "backend.services.os_inbound_bridge.bridge_voice",
                new_callable=AsyncMock,
            ),
            patch("backend.services.voice_call_summary.log_activity"),
        ):
            result = _run_summary()
    assert result is None
    record.assert_called_once()
    release.assert_not_called()
    assert "parse skipped" in caplog.text or "no JSON" in caplog.text
    _assert_no_secrets(caplog.text)


def test_provider_and_budget_logs_do_not_leak_secrets(caplog):
    def boom(**kwargs):
        raise RuntimeError(
            "provider boom cara@example.com anthropic_api_key +15555550100"
        )

    with caplog.at_level(logging.WARNING):
        with (
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=_store(),
            ),
            patch(
                "backend.services.voice_call_summary.reserve_ai_tokens",
                side_effect=_allowed,
            ),
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=boom,
            ),
            patch("backend.services.voice_call_summary.record_ai_usage"),
            patch("backend.services.voice_call_summary.release_ai_token_reservation"),
        ):
            _run_summary()
        with (
            patch(
                "backend.services.voice_call_summary.get_service_supabase",
                return_value=_store(),
            ),
            patch(
                "backend.services.voice_call_summary.reserve_ai_tokens",
                side_effect=_blocked,
            ),
            patch(
                "backend.services.voice_call_summary.call_claude_messages",
                new_callable=AsyncMock,
                side_effect=_ok_claude,
            ),
        ):
            _run_summary()
    _assert_no_secrets(caplog.text)
    assert "RuntimeError" not in caplog.text
    assert "provider boom" not in caplog.text


def test_metered_call_metadata_is_ids_and_counts_only():
    seen = []

    async def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=_store(),
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ),
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            side_effect=capture_claude,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage"),
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        _run_summary()
    meta = seen[0]["metadata"]
    assert set(meta) == {"tenant_id", "call_id", "transcript_chars"}
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["call_id"] == _CALL_ID
    assert meta["transcript_chars"] == len(_TRANSCRIPT)
    _assert_no_secrets(str(meta))


# --- dual-trigger claim ------------------------------------------------------


def test_both_triggers_same_call_one_provider_and_record():
    store = _store()
    provider = AsyncMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_call_summary.release_ai_token_reservation"
        ) as release,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        _run_summary()
        _run_summary()
    assert provider.await_count == 1
    assert reserve.call_count == 1
    assert record.call_count == 1
    release.assert_not_called()
    persisted = [
        u for u in store.updates if u.get("summary", "").startswith("Caller asked")
    ]
    assert len(persisted) == 1
    assert store.calls[_CALL_ID]["summary"] == "Caller asked about a kitchen remodel quote."


def test_separate_calls_account_independently():
    store = _SummaryStore(
        tenant=_TENANT,
        calls=[
            _call_row(id="call-a", twilio_call_sid="CA-a"),
            _call_row(id="call-b", twilio_call_sid="CA-b"),
        ],
    )
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_call_summary.release_ai_token_reservation"
        ) as release,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        _run_summary(call_id="call-a")
        _run_summary(call_id="call-b")
    assert provider.await_count == 2
    assert reserve.call_count == 2
    assert record.call_count == 2
    release.assert_not_called()
    sessions = [c.kwargs["session_id"] for c in reserve.call_args_list]
    assert sessions == ["call-a", "call-b"]
    recorded_sessions = [c.kwargs["session_id"] for c in record.call_args_list]
    assert recorded_sessions == ["call-a", "call-b"]


def test_existing_real_summary_skips_provider():
    store = _store(summary="Caller already summarized.")
    provider = AsyncMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
    ):
        result = _run_summary()
    assert result is None
    reserve.assert_not_called()
    provider.assert_not_called()
    record.assert_not_called()
    assert store.calls[_CALL_ID]["summary"] == "Caller already summarized."


def test_in_flight_claim_skips_second_provider():
    store = _store(summary=SUMMARY_CLAIM)
    provider = AsyncMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch("backend.services.voice_call_summary.reserve_ai_tokens") as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
    ):
        _run_summary()
    reserve.assert_not_called()
    provider.assert_not_called()


def test_finalize_only_summarizes_once():
    store = _SummaryStore(
        tenant=_TENANT,
        calls=[_call_row(summary="AI conversation in progress.")],
        chat_messages=[
            {"role": "assistant", "content": "Thanks for calling"},
            {"role": "user", "content": "Need a plumber"},
        ],
    )
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        run(_finalize_ai_call(store, _TENANT_ID, _CALL_SID, 45))
    provider.assert_awaited_once()
    reserve.assert_called_once()
    record.assert_called_once()
    assert store.calls[_CALL_ID]["status"] == "completed"
    assert store.calls[_CALL_ID]["summary"] == "Caller asked about a kitchen remodel quote."


def test_finalize_skips_generate_when_summary_already_persisted():
    store = _SummaryStore(
        tenant=_TENANT,
        calls=[_call_row(summary="Already done.")],
        chat_messages=[{"role": "user", "content": "hi"}],
    )
    with patch(
        "backend.services.voice_call_summary._generate_call_summary",
        new_callable=AsyncMock,
    ) as generate:
        run(_finalize_ai_call(store, _TENANT_ID, _CALL_SID, 12))
    generate.assert_not_awaited()
    assert store.calls[_CALL_ID]["status"] == "completed"
    assert store.calls[_CALL_ID]["summary"] == "Already done."


def _form(**fields) -> bytes:
    return urllib.parse.urlencode(fields).encode()


def _client() -> SyncASGITestClient:
    return SyncASGITestClient(app)


@pytest.fixture
def _bypass_twilio_sig():
    app.dependency_overrides[verify_twilio_request] = lambda: None
    yield
    app.dependency_overrides.pop(verify_twilio_request, None)


def test_transcription_complete_only_queues_summary(_bypass_twilio_sig):
    call_row = _call_row(
        summary="Voicemail recorded. Transcription pending.",
        status="completed",
        transcript=[],
    )
    store = _SummaryStore(tenant=_TENANT, calls=[call_row])
    with (
        patch.object(calls_webhooks, "get_service_supabase", return_value=store),
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        resp = _client().post(
            "/api/v1/calls/voice/transcription-complete",
            content=_form(
                TranscriptionText="I need a quote for a water heater.",
                TranscriptionSid="TR1",
                RecordingSid="RE1",
                CallSid=_CALL_SID,
                TranscriptionStatus="completed",
            ),
        )
    assert resp.status_code == 200 and resp.text == "OK"
    assert add_task.call_count == 1
    assert add_task.call_args.args[1] is calls_webhooks._generate_call_summary
    kwargs = add_task.call_args.kwargs
    assert kwargs["call_id"] == _CALL_ID
    assert kwargs["tenant_id"] == _TENANT_ID
    assert "water heater" in kwargs["transcript_text"]
    assert store.calls[_CALL_ID]["summary"] == (
        "Transcription received. AI summary generating..."
    )


def test_transcription_complete_skips_queue_when_summary_persisted(
    _bypass_twilio_sig,
):
    store = _SummaryStore(
        tenant=_TENANT,
        calls=[
            _call_row(
                summary="Caller asked about a kitchen remodel quote.",
                status="completed",
                transcript=[{"timestamp": 0, "speaker": "assistant", "text": "Hi"}],
            )
        ],
    )
    with (
        patch.object(calls_webhooks, "get_service_supabase", return_value=store),
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        resp = _client().post(
            "/api/v1/calls/voice/transcription-complete",
            content=_form(
                TranscriptionText="Please send the quote.",
                CallSid=_CALL_SID,
                TranscriptionStatus="completed",
            ),
        )
    assert resp.status_code == 200
    add_task.assert_not_called()
    assert store.calls[_CALL_ID]["summary"] == (
        "Caller asked about a kitchen remodel quote."
    )
    texts = [e["text"] for e in store.calls[_CALL_ID]["transcript"]]
    assert "Please send the quote." in texts


def test_finalize_then_transcription_same_call_one_provider(_bypass_twilio_sig):
    store = _SummaryStore(
        tenant=_TENANT,
        calls=[_call_row(summary="AI conversation in progress.")],
        chat_messages=[
            {"role": "assistant", "content": "Thanks for calling"},
            {"role": "user", "content": "Need a plumber"},
        ],
    )
    provider = AsyncMock(side_effect=_ok_claude)
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ) as reserve,
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=provider,
        ),
        patch("backend.services.voice_call_summary.record_ai_usage") as record,
        patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new_callable=AsyncMock,
        ),
        patch(
            "backend.services.os_inbound_bridge.bridge_voice",
            new_callable=AsyncMock,
        ),
        patch("backend.services.voice_call_summary.log_activity"),
    ):
        run(_finalize_ai_call(store, _TENANT_ID, _CALL_SID, 30))
        with (
            patch.object(calls_webhooks, "get_service_supabase", return_value=store),
            patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
        ):
            resp = _client().post(
                "/api/v1/calls/voice/transcription-complete",
                content=_form(
                    TranscriptionText="Please send the quote.",
                    CallSid=_CALL_SID,
                    TranscriptionStatus="completed",
                ),
            )
    assert resp.status_code == 200
    add_task.assert_not_called()
    assert provider.await_count == 1
    assert reserve.call_count == 1
    assert record.call_count == 1


def test_blocked_summary_does_not_raise_into_transcription_webhook(
    _bypass_twilio_sig,
):
    store = _store(summary="Transcription received. AI summary generating...")
    with (
        patch.object(calls_webhooks, "get_service_supabase", return_value=store),
        patch.object(BackgroundTasks, "add_task", autospec=True) as add_task,
    ):
        resp = _client().post(
            "/api/v1/calls/voice/transcription-complete",
            content=_form(
                TranscriptionText="Need a plumber tomorrow",
                CallSid=_CALL_SID,
                TranscriptionStatus="completed",
            ),
        )
    assert resp.status_code == 200
    fn = add_task.call_args.args[1]
    kwargs = add_task.call_args.kwargs
    with (
        patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=store,
        ),
        patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_blocked,
        ),
        patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=_ok_claude,
        ) as provider,
    ):
        run(fn(**kwargs))
    provider.assert_not_called()
