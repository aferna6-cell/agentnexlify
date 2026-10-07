"""Post-billable accounting: a failed record RPC must not release spend.

A provider result is already billable. If ``record_ai_token_usage`` fails,
the reservation stays held and is marked accounting debt. A successful RPC
with an unreadable payload, or a later activity-log failure, must not raise
into a caller that would release. Pre-billable paths still release exactly
once through ``release_ai_token_reservation``.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.ai_usage_guard import (
    AIUsageAccountingDebt,
    AIUsageRecord,
    AIUsageReservation,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.llm_runtime import ClaudeCallResult

_TENANT_ID = "tenant-accounting-debt"
_SESSION_ID = "sess-accounting-debt"
_SECRET = "sentinel-token prompt body"


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


def _record_response(data):
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


_PROVED_FLAGS = {"alert_triggered": False, "hard_limit_reached": False}
_UNPROVED_PAYLOADS = [
    pytest.param(
        {"alert_triggered": False, "hard_limit_reached": False},
        "",
        id="missing-total",
    ),
    pytest.param({}, "", id="empty-dict"),
    pytest.param([], "", id="empty-list"),
    pytest.param("not-a-record", "not-a-record", id="string-payload"),
    pytest.param({**_PROVED_FLAGS, "total_tokens": True}, "", id="bool-total"),
    pytest.param({**_PROVED_FLAGS, "total_tokens": 1.5}, "1.5", id="float-total"),
    pytest.param({**_PROVED_FLAGS, "total_tokens": -3}, "-3", id="negative-total"),
    pytest.param(
        {"total_tokens": 18, "hard_limit_reached": False},
        "",
        id="missing-alert-flag",
    ),
    pytest.param(
        {"total_tokens": 18, "alert_triggered": "false", "hard_limit_reached": False},
        "false",
        id="string-alert-flag",
    ),
    pytest.param(
        {"total_tokens": 18, "alert_triggered": 1, "hard_limit_reached": False},
        "",
        id="int-alert-flag",
    ),
    pytest.param(
        {"total_tokens": 18, "alert_triggered": False},
        "",
        id="missing-hard-flag",
    ),
    pytest.param(
        {"total_tokens": 18, "alert_triggered": False, "hard_limit_reached": 0},
        "",
        id="int-hard-flag",
    ),
    pytest.param(
        {**_PROVED_FLAGS, "total_tokens": "18"},
        "18",
        id="decimal-string-total",
    ),
    pytest.param(
        [
            {**_PROVED_FLAGS, "total_tokens": 1},
            {**_PROVED_FLAGS, "total_tokens": 2},
        ],
        "",
        id="multirow",
    ),
]


def _assert_unproved(recorded, caplog, banned: str) -> None:
    assert isinstance(recorded, AIUsageAccountingDebt)
    assert not isinstance(recorded, AIUsageRecord)
    assert recorded.reason == "record_response_unproved"
    assert "total_tokens" not in recorded.__dataclass_fields__
    assert recorded.alert_triggered is False
    assert "record_response_unproved" in caplog.text
    assert "record_rpc_failed" not in caplog.text
    assert "Traceback" not in caplog.text
    if banned:
        assert banned not in caplog.text


@pytest.mark.parametrize(("payload", "banned"), _UNPROVED_PAYLOADS)
def test_unproved_record_payloads_do_not_invent_a_total_or_release(payload, banned, caplog):
    calls, rpc = _record_response(payload)
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
    _assert_unproved(recorded, caplog, banned)


def test_record_data_access_failure_is_unproved_debt_without_release(caplog):
    calls: list[str] = []

    class _RaisingExecute:
        def execute(self):
            return self

        @property
        def data(self):
            raise RuntimeError(_SECRET)

    def rpc(name, _payload):
        calls.append(name)
        if name != "record_ai_token_usage":
            return MagicMock()
        return _RaisingExecute()

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
    _assert_unproved(recorded, caplog, _SECRET)


def test_singleton_list_and_zero_total_are_proved_records():
    proved_cases = [
        [{"total_tokens": 18, "alert_triggered": False, "hard_limit_reached": True}],
        {"total_tokens": 0, "alert_triggered": False, "hard_limit_reached": False},
    ]
    seen = []
    for payload in proved_cases:
        calls, rpc = _record_response(payload)
        with patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa:
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
        seen.append((recorded.total_tokens, recorded.hard_limit_reached))
    assert seen == [(18, True), (0, False)]


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


async def _run_metered_graph_node(*, provider, rpc, activity=None, session_id=_SESSION_ID):
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
        run_id=session_id,
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


@pytest.mark.parametrize(("payload", "banned"), _UNPROVED_PAYLOADS)
async def test_graph_adapter_records_without_release_for_unproved_payloads(
    payload, banned, caplog
):
    calls, rpc = _record_response(payload)

    async def provider(**_kwargs):
        return _result()

    with caplog.at_level(logging.WARNING):
        result = await _run_metered_graph_node(provider=provider, rpc=rpc)

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'
    assert "record_response_unproved" in caplog.text
    assert "Traceback" not in caplog.text
    if banned:
        assert banned not in caplog.text


async def test_graph_adapter_records_without_release_when_data_access_fails(caplog):
    calls: list[str] = []

    class _RaisingExecute:
        def execute(self):
            return self

        @property
        def data(self):
            raise RuntimeError(_SECRET)

    def rpc(name, _payload):
        calls.append(name)
        if name != "record_ai_token_usage":
            return MagicMock()
        return _RaisingExecute()

    async def provider(**_kwargs):
        return _result()

    with caplog.at_level(logging.WARNING):
        result = await _run_metered_graph_node(provider=provider, rpc=rpc)

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'
    assert "record_response_unproved" in caplog.text
    assert _SECRET not in caplog.text
    assert "Traceback" not in caplog.text


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


_FORGED_SESSION = "visitor@example.com\nINJECTED authorization=Bearer sentinel-token"
_LOG_MODES = ("rpc_failed", "unproved", "activity")


def _accounting_log_text(caplog) -> str:
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "backend.services.ai_usage_guard"
    )


def _forged_session_absent(caplog) -> None:
    text = _accounting_log_text(caplog)
    assert "visitor@example.com" not in text
    assert "INJECTED" not in text
    assert "Bearer" not in text
    assert "sentinel-token" not in text
    assert all("\n" not in record.getMessage() for record in caplog.records if record.name == "backend.services.ai_usage_guard")


def _rpc_for_mode(mode: str):
    calls: list[str] = []

    def rpc(name, _payload=None, **_kwargs):
        calls.append(name)
        if name != "record_ai_token_usage":
            response = MagicMock()
            response.execute.return_value.data = True
            return response
        if mode == "rpc_failed":
            raise RuntimeError("record rpc down")
        response = MagicMock()
        if mode == "activity":
            response.execute.return_value.data = {
                "total_tokens": 18,
                "alert_triggered": True,
                "hard_limit_reached": False,
            }
        else:
            response.execute.return_value.data = {}
        return response

    return calls, rpc


def _activity_for_mode(mode: str):
    if mode != "activity":
        return None

    def explode(**_kwargs):
        raise RuntimeError("activity down")

    return explode


@pytest.mark.parametrize("mode", _LOG_MODES)
def test_logger_failure_still_returns_accounting_outcome(mode, caplog):
    calls, rpc = _rpc_for_mode(mode)
    with (
        caplog.at_level(logging.WARNING),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=_activity_for_mode(mode)),
        patch("backend.services.ai_usage_guard.logger.warning", side_effect=RuntimeError("log down")),
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_FORGED_SESSION,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    if mode == "activity":
        assert isinstance(recorded, AIUsageRecord)
        assert recorded.total_tokens == 18
        assert recorded.alert_triggered is True
    else:
        assert isinstance(recorded, AIUsageAccountingDebt)
        assert recorded.reason == (
            "record_rpc_failed" if mode == "rpc_failed" else "record_response_unproved"
        )
        assert recorded.session_id == _FORGED_SESSION
        assert "total_tokens" not in recorded.__dataclass_fields__
    _forged_session_absent(caplog)


@pytest.mark.parametrize("mode", _LOG_MODES)
def test_accounting_diagnostics_omit_forged_session_id(mode, caplog):
    calls, rpc = _rpc_for_mode(mode)
    with (
        caplog.at_level(logging.WARNING),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=_activity_for_mode(mode)),
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_FORGED_SESSION,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    text = _accounting_log_text(caplog)
    if mode == "activity":
        assert isinstance(recorded, AIUsageRecord)
        assert "accounting_observability_failed" in text
    elif mode == "rpc_failed":
        assert recorded.reason == "record_rpc_failed"
        assert "accounting_debt" in text
        assert "record_rpc_failed" in text
    else:
        assert recorded.reason == "record_response_unproved"
        assert "record_response_unproved" in text
    _forged_session_absent(caplog)


@pytest.mark.parametrize("mode", _LOG_MODES)
async def test_graph_logger_failure_does_not_release(mode):
    calls, rpc = _rpc_for_mode(mode)

    async def provider(**_kwargs):
        return _result()

    with patch("backend.services.ai_usage_guard.logger.warning", side_effect=RuntimeError("log down")):
        result = await _run_metered_graph_node(
            provider=provider,
            rpc=rpc,
            activity=_activity_for_mode(mode),
            session_id=_FORGED_SESSION,
        )

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'


@pytest.mark.parametrize("mode", _LOG_MODES)
def test_widget_logger_failure_does_not_release(mode, client, mock_supabase, caplog):
    from backend.tests.test_widget_chat_pipeline import _Chain, _patch_llm, _post_chat, _result, _seed

    suffix = {"rpc_failed": "1", "unproved": "2", "activity": "3"}[mode]
    tenant_id = f"p9270000-0000-4000-8000-00000000000{suffix}"
    api_key = f"anx_acct_log_{mode}"
    _seed(mock_supabase, tenant_id=tenant_id, api_key=api_key)
    calls, rpc = _rpc_for_mode(mode)

    def routed(name, params=None, **kwargs):
        if name == "reserve_ai_token_budget":
            calls.append(name)
            return _Chain(_result(True))
        return rpc(name, params, **kwargs)

    mock_supabase.rpc.side_effect = routed
    llm_patch, kb_patch, _llm = _patch_llm("Still here.")

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        caplog.at_level(logging.WARNING),
        llm_patch,
        kb_patch,
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
        patch("backend.services.ai_usage_guard.log_activity", side_effect=_activity_for_mode(mode)),
        patch("backend.services.ai_usage_guard.logger.warning", side_effect=RuntimeError("log down")),
    ):
        response = _post_chat(
            client,
            api_key,
            "How fast can you fix a pipeline?",
            _FORGED_SESSION,
        )

    assert response.status_code == 200
    assert response.json()["response"] == "Still here."
    assert calls.count("record_ai_token_usage") == 1
    assert calls.count("release_ai_token_reservation") == 0
    _forged_session_absent(caplog)


def test_widget_provider_failure_releases_exactly_once(client, mock_supabase):
    from backend.tests.test_widget_chat_pipeline import _Chain, _post_chat, _result, _seed

    _seed(
        mock_supabase,
        tenant_id="p9270000-0000-4000-8000-000000000004",
        api_key="anx_acct_provider_down",
    )
    calls: list[str] = []

    def routed(name, params=None, **_kwargs):
        calls.append(name)
        if name == "reserve_ai_token_budget":
            return _Chain(_result(True))
        raise AssertionError(name)

    mock_supabase.rpc.side_effect = routed

    async def provider(**_kwargs):
        raise RuntimeError("provider down")

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        patch("backend.routers.widget_chat.call_claude_messages", side_effect=provider),
        patch("backend.routers.widget_chat._query_kb_articles", new=AsyncMock(return_value=[])),
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
    ):
        response = _post_chat(
            client,
            "anx_acct_provider_down",
            "How fast can you fix a pipeline?",
            "sess-provider-down",
        )

    assert response.status_code == 200
    assert "having trouble" in response.json()["response"]
    assert calls.count("record_ai_token_usage") == 0
    assert calls.count("release_ai_token_reservation") == 1


_THRESHOLD_METADATA_KEYS = {
    "operation",
    "model",
    "total_tokens",
    "alert_threshold_tokens",
    "hard_limit_tokens",
    "alert_triggered",
    "hard_limit_reached",
}


def _capture_activity():
    seen: list[dict] = []

    def capture(**kwargs):
        seen.append(kwargs)

    return seen, capture


def _assert_sentinel_absent(payload) -> None:
    rendered = repr(payload)
    assert "visitor@example.com" not in rendered
    assert "INJECTED" not in rendered
    assert "Bearer" not in rendered
    assert "\n" not in rendered


def test_threshold_activity_omits_raw_session_id():
    calls, rpc = _rpc_for_mode("activity")
    seen, capture = _capture_activity()
    with (
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=capture),
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        recorded = record_ai_usage(
            reservation=_reservation(),
            result=_result(),
            operation="seo.generate_keywords",
            session_id=_FORGED_SESSION,
            model="claude-sonnet-4-6",
        )

    assert calls == ["record_ai_token_usage"]
    assert isinstance(recorded, AIUsageRecord)
    assert recorded.total_tokens == 18
    assert len(seen) == 1
    assert seen[0]["activity_type"] == "ai_usage_threshold"
    assert seen[0]["tenant_id"] == _TENANT_ID
    assert seen[0]["description"] == "AI monthly usage crossed a guardrail threshold"
    assert seen[0]["metadata"] == {
        "operation": "seo.generate_keywords",
        "model": "claude-sonnet-4-6",
        "total_tokens": 18,
        "alert_threshold_tokens": 800_000,
        "hard_limit_tokens": 1_000_000,
        "alert_triggered": True,
        "hard_limit_reached": False,
    }
    assert set(seen[0]["metadata"]) == _THRESHOLD_METADATA_KEYS
    _assert_sentinel_absent(seen)


async def test_graph_threshold_activity_omits_raw_session_id():
    calls, rpc = _rpc_for_mode("activity")
    seen, capture = _capture_activity()

    async def provider(**_kwargs):
        return _result()

    result = await _run_metered_graph_node(
        provider=provider,
        rpc=rpc,
        activity=capture,
        session_id=_FORGED_SESSION,
    )

    assert calls == ["record_ai_token_usage"]
    assert result.updates["reply"] == '["keyword"]'
    assert len(seen) == 1
    assert seen[0]["activity_type"] == "ai_usage_threshold"
    assert seen[0]["metadata"]["operation"] == "seo.generate_keywords"
    assert seen[0]["metadata"]["model"] == "claude-sonnet-4-6"
    assert seen[0]["metadata"]["total_tokens"] == 18
    assert seen[0]["metadata"]["alert_triggered"] is True
    assert seen[0]["metadata"]["hard_limit_reached"] is False
    assert set(seen[0]["metadata"]) == _THRESHOLD_METADATA_KEYS
    _assert_sentinel_absent(seen)


def test_widget_threshold_activity_omits_raw_session_id(client, mock_supabase):
    from backend.tests.test_widget_chat_pipeline import _Chain, _patch_llm, _post_chat, _result, _seed

    _seed(
        mock_supabase,
        tenant_id="p9270000-0000-4000-8000-000000000005",
        api_key="anx_acct_threshold",
    )
    calls, rpc = _rpc_for_mode("activity")

    def routed(name, params=None, **kwargs):
        if name == "reserve_ai_token_budget":
            calls.append(name)
            return _Chain(_result(True))
        return rpc(name, params, **kwargs)

    mock_supabase.rpc.side_effect = routed
    seen, capture = _capture_activity()
    llm_patch, kb_patch, _llm = _patch_llm("Still here.")

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        llm_patch,
        kb_patch,
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
        patch("backend.services.ai_usage_guard.log_activity", side_effect=capture),
    ):
        response = _post_chat(
            client,
            "anx_acct_threshold",
            "How fast can you fix a pipeline?",
            _FORGED_SESSION,
        )

    assert response.status_code == 200
    assert response.json()["response"] == "Still here."
    assert calls.count("record_ai_token_usage") == 1
    assert calls.count("release_ai_token_reservation") == 0
    assert len(seen) == 1
    assert seen[0]["activity_type"] == "ai_usage_threshold"
    assert seen[0]["metadata"]["operation"] == "widget_chat.reply"
    assert seen[0]["metadata"]["total_tokens"] == 18
    assert seen[0]["metadata"]["alert_triggered"] is True
    assert isinstance(seen[0]["metadata"]["model"], str)
    assert set(seen[0]["metadata"]) == _THRESHOLD_METADATA_KEYS
    _assert_sentinel_absent(seen)


def test_blocked_reservation_activity_omits_raw_session_id():
    seen, capture = _capture_activity()
    with (
        patch("backend.services.ai_usage_guard._sum_usage_packs", return_value=0),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
        patch("backend.services.ai_usage_guard.log_activity", side_effect=capture),
    ):
        mock_supa.return_value.rpc.return_value.execute.return_value.data = False
        reservation = reserve_ai_tokens(
            tenant={"id": _TENANT_ID, "plan": "chatbot"},
            estimated_tokens=700,
            operation="seo.generate_keywords",
            session_id=_FORGED_SESSION,
        )

    assert reservation.allowed is False
    assert reservation.reason == "hard_limit"
    assert len(seen) == 1
    assert seen[0]["activity_type"] == "ai_usage_blocked"
    assert seen[0]["tenant_id"] == _TENANT_ID
    assert seen[0]["description"] == "AI reply blocked by monthly usage guardrail"
    assert seen[0]["metadata"] == {
        "operation": "seo.generate_keywords",
        "estimated_tokens": 700,
        "hard_limit_tokens": 800_000,
    }
    _assert_sentinel_absent(seen)
