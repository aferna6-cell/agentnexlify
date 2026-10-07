"""Post-billable accounting: a failed record RPC must not release spend.

A provider result is already billable. If ``record_ai_token_usage`` fails,
the reservation stays held and is marked accounting debt. A successful RPC
with an unreadable payload, or a later activity-log failure, must not raise
into a caller that would release. Pre-billable paths still release exactly
once through ``release_ai_token_reservation``.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from backend.services.ai_usage_guard import (
    AIUsageAccountingDebt,
    AIUsageRecord,
    AIUsageReservation,
    record_ai_usage,
    release_ai_token_reservation,
)
from backend.services.llm_runtime import ClaudeCallResult

_TENANT_ID = "tenant-accounting-debt"
_SESSION_ID = "sess-accounting-debt"
_SECRET = "sk-ant-secret prompt body"


def _reservation(**overrides) -> AIUsageReservation:
    payload = {
        "allowed": True,
        "tenant_id": _TENANT_ID,
        "period_month": "2026-10-01",
        "estimated_tokens": 640,
        "alert_threshold_tokens": 800_000,
        "hard_limit_tokens": 1_000_000,
        "reason": "",
    }
    payload.update(overrides)
    return AIUsageReservation(**payload)


def _result() -> ClaudeCallResult:
    return ClaudeCallResult(
        text='["keyword"]',
        duration_ms=12,
        input_tokens=11,
        output_tokens=7,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def test_record_rpc_failure_retains_observable_debt_without_release(caplog):
    """Mutation: release-after-record-failure must fail this test."""
    calls: list[str] = []

    def rpc(name, _payload):
        calls.append(name)
        raise RuntimeError(_SECRET)

    with (
        caplog.at_level(logging.WARNING),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert not isinstance(recorded, AIUsageRecord)
    assert recorded.reason == "record_rpc_failed"
    assert recorded.alert_triggered is False
    assert recorded.tenant_id == _TENANT_ID
    assert recorded.session_id == _SESSION_ID
    assert recorded.operation == "seo.generate_keywords"
    assert recorded.estimated_tokens == 640
    assert recorded.model == "claude-sonnet-4-6"
    assert not (recorded and recorded.alert_triggered)
    assert "accounting_debt" in caplog.text
    assert "record_rpc_failed" in caplog.text
    assert _TENANT_ID in caplog.text
    assert _SECRET not in caplog.text
    assert "Traceback" not in caplog.text
    assert _SECRET not in repr(recorded)


def test_record_rpc_success_returns_usage_and_does_not_release():
    calls: list[tuple[str, int, int]] = []

    def rpc(name, payload):
        calls.append((name, payload["p_input_tokens"], payload["p_output_tokens"]))
        response = MagicMock()
        response.execute.return_value.data = {
            "total_tokens": 18,
            "alert_triggered": False,
            "hard_limit_reached": False,
        }
        return response

    with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )

    assert calls == [("record_ai_token_usage", 11, 7)]
    assert isinstance(recorded, AIUsageRecord)
    assert recorded.total_tokens == 18
    assert recorded.alert_triggered is False


def test_unheld_reservations_do_not_record_or_release():
    calls: list[str] = []

    def rpc(name, _payload):
        calls.append(name)
        raise AssertionError(name)

    with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
        mock_supa.return_value.rpc.side_effect = rpc
        denied = record_ai_usage(
            reservation=_reservation(allowed=False, reason="hard_limit"),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )
        unavailable = record_ai_usage(
            reservation=_reservation(allowed=True, reason="guard_unavailable"),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )

    assert denied is None
    assert unavailable is None
    assert calls == []


def test_pre_billable_release_fires_exactly_once_for_a_held_reservation():
    calls: list[tuple[str, str, int]] = []

    def rpc(name, payload):
        calls.append((name, payload["p_tenant_id"], payload["p_reserved_tokens"]))
        return MagicMock()

    reservation = _reservation()
    with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
        mock_supa.return_value.rpc.side_effect = rpc
        release_ai_token_reservation(reservation)

    assert calls == [
        ("release_ai_token_reservation", _TENANT_ID, reservation.estimated_tokens)
    ]


def test_release_skips_denied_and_guard_unavailable_reservations():
    calls: list[str] = []

    def rpc(name, _payload):
        calls.append(name)
        return MagicMock()

    with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
        mock_supa.return_value.rpc.side_effect = rpc
        release_ai_token_reservation(_reservation(allowed=False, reason="hard_limit"))
        release_ai_token_reservation(
            _reservation(allowed=True, reason="guard_unavailable")
        )

    assert calls == []


def _record_response(data: dict):
    calls: list[str] = []

    def rpc(name, _payload):
        calls.append(name)
        if name != "record_ai_token_usage":
            return MagicMock()
        response = MagicMock()
        response.execute.return_value.data = data
        return response

    return calls, rpc


def test_malformed_record_payload_is_unproved_debt_without_release(caplog):
    """Successful RPC + total_tokens='malformed' must not raise or release."""
    calls, rpc = _record_response(
        {
            "total_tokens": "malformed",
            "alert_triggered": False,
            "hard_limit_reached": False,
        }
    )
    with (
        caplog.at_level(logging.WARNING),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert not isinstance(recorded, AIUsageRecord)
    assert recorded.reason == "record_response_unproved"
    assert "total_tokens" not in recorded.__dataclass_fields__
    assert recorded.alert_triggered is False
    assert not (recorded and recorded.alert_triggered)
    assert "record_response_unproved" in caplog.text
    assert "record_rpc_failed" not in caplog.text
    assert "malformed" not in caplog.text
    assert "invalid literal" not in caplog.text
    assert "Traceback" not in caplog.text


def test_activity_log_failure_returns_proved_record_without_release(caplog):
    calls, rpc = _record_response(
        {"total_tokens": 18, "alert_triggered": True, "hard_limit_reached": False}
    )

    def explode(**_kwargs):
        raise RuntimeError(_SECRET)

    with (
        caplog.at_level(logging.WARNING),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=explode),
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_SESSION_ID,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    assert isinstance(recorded, AIUsageRecord)
    assert recorded.total_tokens == 18
    assert recorded.alert_triggered is True
    assert "accounting_observability_failed" in caplog.text
    assert "record_response_unproved" not in caplog.text
    assert "record_rpc_failed" not in caplog.text
    assert _SECRET not in caplog.text
    assert "Traceback" not in caplog.text


async def _run_metered_graph_node(*, provider, rpc, activity=None):
    from backend.graph.adapters.llm import agent_node
    from backend.graph.nodes import NodeContext

    node = agent_node(
        operation="seo.generate_keywords",
        model="claude-sonnet-4-6",
        prompt="hi",
    )
    context = NodeContext(
        state={},
        node="keywords",
        superstep=0,
        run_id=_SESSION_ID,
        tenant_id=_TENANT_ID,
    )
    with (
        patch(
            "backend.graph.adapters.llm._load_budget_tenant",
            return_value={"id": _TENANT_ID, "plan": "chatbot"},
        ),
        patch("backend.graph.adapters.llm.reserve_ai_tokens", return_value=_reservation()),
        patch("backend.graph.adapters.llm.call_claude_messages", side_effect=provider),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=activity),
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        return await node(context)


async def test_graph_adapter_does_not_release_after_malformed_record_payload(caplog):
    """Falsifier: graph catch must not turn a post-record ValueError into release."""
    calls, rpc = _record_response(
        {
            "total_tokens": "malformed",
            "alert_triggered": False,
            "hard_limit_reached": False,
        }
    )

    async def provider(**_kwargs):
        return _result()

    with caplog.at_level(logging.WARNING):
        result = await _run_metered_graph_node(provider=provider, rpc=rpc)

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'
    assert "record_response_unproved" in caplog.text
    assert "malformed" not in caplog.text
    assert "invalid literal" not in caplog.text


async def test_graph_adapter_does_not_release_when_activity_log_fails(caplog):
    calls, rpc = _record_response(
        {"total_tokens": 18, "alert_triggered": True, "hard_limit_reached": False}
    )

    async def provider(**_kwargs):
        return _result()

    def explode(**_kwargs):
        raise RuntimeError(_SECRET)

    with caplog.at_level(logging.WARNING):
        result = await _run_metered_graph_node(
            provider=provider,
            rpc=rpc,
            activity=explode,
        )

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'
    assert "accounting_observability_failed" in caplog.text
    assert _SECRET not in caplog.text


async def test_graph_provider_failure_releases_exactly_once():
    calls: list[str] = []

    def rpc(name, _payload):
        calls.append(name)
        return MagicMock()

    async def provider(**_kwargs):
        raise RuntimeError("provider down")

    with pytest.raises(RuntimeError, match="provider down"):
        await _run_metered_graph_node(provider=provider, rpc=rpc)

    assert calls == ["release_ai_token_reservation"]
