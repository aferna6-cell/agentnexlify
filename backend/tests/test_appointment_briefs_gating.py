"""Guard-stack + enforceable AI budget for appointment briefs (GH #643 / #791).

Contract:
- Router Depends: block_demo_role + require_agent_os_access (chatbot/free 402).
- Claude spend uses reserve_ai_tokens → call_claude_messages → record_ai_usage
  (release on provider error). llm_runtime does not record usage.
- Hard cap blocks before the provider. Purchased usage packs are honored
  because the tenant row passed to reserve includes id.
- Tenant/guard unavailable is explicit fail-open on this surface only
  (matches reserve_ai_tokens.reason == "guard_unavailable"); no invented
  free-plan cap.

Run: pytest backend/tests/test_appointment_briefs_gating.py --noconftest -v
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.routers import appointment_briefs as ab
from backend.services import appointment_brief
from backend.services.ai_usage_guard import AIUsageReservation
from backend.services.appointment_brief import AppointmentBudgetExceeded
from backend.tests.fake_supabase import db, run

_TENANT_ID = "t-budget"
_APPT_ID = "a1"
_APPT = {
    "id": _APPT_ID,
    "customer_name": "Cara Diaz",
    "customer_email": "cara@example.com",
    "customer_phone": None,
    "start_time": "2026-08-06T15:00:00Z",
    "end_time": "2026-08-06T16:00:00Z",
    "status": "confirmed",
    "notes": None,
    "lead_id": None,
}
_TENANT = {
    "id": _TENANT_ID,
    "plan": "agent_os",
    "ai_monthly_token_alert_threshold": None,
    "ai_monthly_token_hard_limit": None,
}


def _fixture():
    return db({"appointments": [_APPT], "tenants": [_TENANT]})


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 900),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=kwargs.get("reason", ""),
    )


def _blocked(**kwargs):
    return AIUsageReservation(
        allowed=False,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 900),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="hard_limit",
    )


def _unavailable(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id=_TENANT_ID,
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 900),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason="guard_unavailable",
    )


def _claude_result(text="## Who they are\nCara."):
    result = MagicMock()
    result.text = text
    result.input_tokens = 120
    result.output_tokens = 40
    result.cache_creation_input_tokens = 0
    result.cache_read_input_tokens = 0
    return result


async def _ok_claude(**kwargs):
    return _claude_result()


# --- router plan / demo gates ------------------------------------------------


def test_router_dependencies_include_demo_block_and_plan_gate():
    from backend.dependencies import block_demo_role
    from backend.services.agent_os_gate import require_agent_os_access

    deps = [d.dependency for d in ab.router.dependencies]
    assert block_demo_role in deps
    assert require_agent_os_access in deps


def test_agent_os_plan_set_excludes_chatbot_and_free():
    from backend.services.agent_os_gate import AGENT_OS_PLANS

    assert "chatbot" not in AGENT_OS_PLANS
    assert "free" not in AGENT_OS_PLANS
    assert "agent_os" in AGENT_OS_PLANS


def test_router_has_no_inert_status_fail_open_wrapper():
    assert not hasattr(ab, "_check_ai_budget")
    assert not hasattr(ab, "get_ai_usage_status")


def test_router_maps_budget_exceeded_to_429():
    async def blocked(*_a, **_k):
        raise AppointmentBudgetExceeded(
            "Monthly AI usage limit reached — add a usage pack or wait for the next cycle"
        )

    with patch.object(ab, "get_service_supabase", return_value=db({})):
        with patch.object(ab.appointment_brief, "generate_brief", blocked):
            with pytest.raises(HTTPException) as exc:
                run(ab.get_appointment_brief(_TENANT_ID, _APPT_ID, {"tenant_id": _TENANT_ID}))
        assert exc.value.status_code == 429
        with patch.object(ab.appointment_brief, "draft_followup", blocked):
            with pytest.raises(HTTPException) as exc:
                run(ab.get_followup_draft(_TENANT_ID, _APPT_ID, {"tenant_id": _TENANT_ID}))
        assert exc.value.status_code == 429


# --- reserve / record / release ---------------------------------------------


def test_hard_cap_blocks_before_provider():
    provider = MagicMock(side_effect=_ok_claude)
    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=_blocked) as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=provider),
        patch.object(appointment_brief, "record_ai_usage") as record,
        patch.object(appointment_brief, "release_ai_token_reservation") as release,
    ):
        with pytest.raises(AppointmentBudgetExceeded):
            run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
        with pytest.raises(AppointmentBudgetExceeded):
            run(appointment_brief.draft_followup(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    assert reserve.call_count == 2
    provider.assert_not_called()
    record.assert_not_called()
    release.assert_not_called()


def test_under_limit_call_is_permitted_and_recorded():
    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(appointment_brief, "record_ai_usage") as record,
        patch.object(appointment_brief, "release_ai_token_reservation") as release,
    ):
        out = run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    assert out["brief"].startswith("## Who they are")
    reserve.assert_called_once()
    provider.assert_called_once()
    record.assert_called_once()
    release.assert_not_called()
    recorded = record.call_args.kwargs
    assert recorded["operation"] == "appointments.brief"
    assert recorded["reservation"].allowed is True
    assert recorded["result"].input_tokens == 120
    assert recorded["result"].output_tokens == 40


def test_followup_draft_records_successful_usage():
    async def followup_claude(**kwargs):
        return _claude_result("Subject: Thanks\n\nSee you soon.")

    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(appointment_brief, "call_claude_messages", side_effect=followup_claude),
        patch.object(appointment_brief, "record_ai_usage") as record,
    ):
        out = run(appointment_brief.draft_followup(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    assert out["subject"] == "Thanks"
    assert record.call_args.kwargs["operation"] == "appointments.followup_draft"


def test_purchased_usage_pack_is_honored_on_reserve():
    """Tenant id must reach reserve so resolve_ai_usage_policy can add packs."""
    captured = {}

    def capture_reserve(*, tenant, estimated_tokens, operation, session_id):
        captured["tenant"] = tenant
        captured["estimated_tokens"] = estimated_tokens
        captured["operation"] = operation
        return _allowed(estimated_tokens=estimated_tokens)

    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=capture_reserve),
        patch.object(appointment_brief, "call_claude_messages", side_effect=_ok_claude),
        patch.object(appointment_brief, "record_ai_usage"),
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
            estimated_tokens=900,
            operation="appointments.brief",
            session_id=_APPT_ID,
        )
        run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))

    assert captured["tenant"]["id"] == _TENANT_ID
    assert captured["tenant"]["plan"] == "agent_os"
    assert reservation.allowed is True
    # agent_os baseline 5M + 1M pack
    assert rpc_limit["hard"] == 6_000_000


def test_provider_error_releases_reservation():
    async def boom(**kwargs):
        raise RuntimeError("claude down")

    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=_allowed) as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=boom),
        patch.object(appointment_brief, "record_ai_usage") as record,
        patch.object(appointment_brief, "release_ai_token_reservation") as release,
    ):
        with pytest.raises(RuntimeError, match="claude down"):
            run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    reserve.assert_called_once()
    record.assert_not_called()
    release.assert_called_once()
    assert release.call_args.args[0].allowed is True
    assert release.call_args.args[0].reason != "guard_unavailable"


def test_guard_unavailable_allows_call_without_recording():
    """Shared reserve fail-open: reason=guard_unavailable. Do not invent a cap."""
    with (
        patch.object(
            appointment_brief, "reserve_ai_tokens", side_effect=_unavailable
        ) as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(appointment_brief, "record_ai_usage") as record,
        patch.object(appointment_brief, "release_ai_token_reservation") as release,
    ):
        out = run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    assert out["has_history"] is False
    reserve.assert_called_once()
    provider.assert_called_once()
    # record_ai_usage itself no-ops on guard_unavailable; we still invoke it
    # so the shared helper owns that contract.
    record.assert_called_once()
    assert record.call_args.kwargs["reservation"].reason == "guard_unavailable"
    release.assert_not_called()


def test_missing_tenant_row_skips_reservation_and_does_not_invent_free_cap():
    fixture = db({"appointments": [_APPT]})  # no tenants row
    with (
        patch.object(appointment_brief, "reserve_ai_tokens") as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(appointment_brief, "record_ai_usage") as record,
        patch.object(appointment_brief, "release_ai_token_reservation") as release,
    ):
        out = run(appointment_brief.generate_brief(fixture, _TENANT_ID, _APPT_ID, "Acme"))
    assert out["brief"]
    reserve.assert_not_called()
    provider.assert_called_once()
    record.assert_not_called()
    release.assert_not_called()


def test_metered_call_metadata_is_ids_only():
    seen = []

    async def capture_claude(**kwargs):
        seen.append(kwargs)
        return _claude_result()

    with (
        patch.object(appointment_brief, "reserve_ai_tokens", side_effect=_allowed),
        patch.object(appointment_brief, "call_claude_messages", side_effect=capture_claude),
        patch.object(appointment_brief, "record_ai_usage"),
    ):
        run(appointment_brief.generate_brief(_fixture(), _TENANT_ID, _APPT_ID, "Acme"))
    meta = seen[0]["metadata"]
    assert set(meta) == {"tenant_id", "appointment_id"}
    assert meta["tenant_id"] == _TENANT_ID
    assert meta["appointment_id"] == _APPT_ID


def test_tenant_lookup_error_skips_reservation():
    class BoomDb:
        def table(self, name):
            if name == "tenants":
                raise RuntimeError("db down")
            return db({"appointments": [_APPT]}).table(name)

    with (
        patch.object(appointment_brief, "reserve_ai_tokens") as reserve,
        patch.object(appointment_brief, "call_claude_messages", side_effect=_ok_claude) as provider,
        patch.object(appointment_brief, "record_ai_usage") as record,
    ):
        out = run(appointment_brief.generate_brief(BoomDb(), _TENANT_ID, _APPT_ID, "Acme"))
    assert out["brief"]
    reserve.assert_not_called()
    provider.assert_called_once()
    record.assert_not_called()
