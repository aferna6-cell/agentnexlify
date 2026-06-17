"""AI Workforce (Agent OS) is gated to the agent_os plan.

The chatbot plan's AI Front Desk runs through the widget chat endpoint, not
orchestrate, so a chatbot/free tenant must not reach the multi-agent workforce.
``_require_agent_os_plan`` raises 402 for non-agent_os tenants, passes for
agent_os tenants, and always passes demo tenants (the public sales demo runs
on orchestrate). The /orchestrate and /context routes enforce it.
"""

import asyncio

import pytest
from fastapi import BackgroundTasks, HTTPException

from backend.routers import os_orchestrate


def _run(coro):
    return asyncio.run(coro)


def _patch(monkeypatch, *, plan, demo=False):
    monkeypatch.setattr(os_orchestrate, "get_service_supabase", lambda: object())
    monkeypatch.setattr(os_orchestrate, "is_demo_tenant", lambda _cid: demo)
    monkeypatch.setattr(
        os_orchestrate.usage_meter, "tenant_plan", lambda *_a, **_k: plan
    )


# --- helper ---------------------------------------------------------------


def test_helper_passes_for_agent_os(monkeypatch):
    _patch(monkeypatch, plan="agent_os")
    # No raise.
    os_orchestrate._require_agent_os_plan(object(), "client-1")


@pytest.mark.parametrize("plan", ["chatbot", "free", "", "growth", "professional"])
def test_helper_blocks_non_agent_os(monkeypatch, plan):
    _patch(monkeypatch, plan=plan)
    with pytest.raises(HTTPException) as exc:
        os_orchestrate._require_agent_os_plan(object(), "client-1")
    assert exc.value.status_code == 402
    assert exc.value.detail["error"] == "plan_upgrade_required"


def test_helper_bypasses_for_demo_even_on_chatbot(monkeypatch):
    # A demo tenant always passes regardless of plan (public demo runs here).
    _patch(monkeypatch, plan="chatbot", demo=True)
    os_orchestrate._require_agent_os_plan(object(), "demo-client")


# --- routes ---------------------------------------------------------------


def test_context_route_blocks_chatbot(monkeypatch):
    _patch(monkeypatch, plan="chatbot")
    with pytest.raises(HTTPException) as exc:
        _run(os_orchestrate.get_context(claims={"tenant_id": "client-1"}))
    assert exc.value.status_code == 402


def test_orchestrate_route_blocks_chatbot(monkeypatch):
    _patch(monkeypatch, plan="chatbot")
    req = os_orchestrate.OrchestrateRequest(thread_id="t1", content="hi")
    with pytest.raises(HTTPException) as exc:
        _run(
            os_orchestrate.orchestrate(
                req, BackgroundTasks(), claims={"tenant_id": "client-1"}
            )
        )
    assert exc.value.status_code == 402
    assert exc.value.detail["error"] == "plan_upgrade_required"
