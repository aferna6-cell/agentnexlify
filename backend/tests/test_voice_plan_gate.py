"""Plan-gate tests for live AI voice answering (G3).

Contracts:
  - _ai_voice_mode returns True only when voice_ai_enabled=True AND plan in
    _AI_VOICE_PLANS (agent_os, professional, enterprise).
  - chatbot plan never gets live AI (gets voicemail mode instead).
  - free plan never gets live AI.
  - voice_ai_enabled=False always returns False regardless of plan.
  - agent_os is in _AI_VOICE_PLANS (regression guard for the 2026-06-15 repricing:
    live AI voice was gated to professional/enterprise only, which are no longer
    sold, so no current tenant could enable it until agent_os was added).

Follow-up: handle_incoming_call webhook needs a TestClient-based integration test.
It is wrapped by the slowapi rate-limit decorator, which requires a real
starlette Request (not a MagicMock), so it must be exercised through the ASGI
app rather than called directly. Tracked as a voice integration-test task.
"""

from backend.routers.calls import _ai_voice_mode, _AI_VOICE_PLANS


def test_agent_os_with_flag_enabled():
    tenant = {"plan": "agent_os", "voice_ai_enabled": True}
    assert _ai_voice_mode(tenant) is True


def test_agent_os_without_flag():
    """voice_ai_enabled=False or missing -> voicemail mode, not live AI."""
    assert _ai_voice_mode({"plan": "agent_os", "voice_ai_enabled": False}) is False
    assert _ai_voice_mode({"plan": "agent_os"}) is False


def test_chatbot_plan_never_gets_live_ai():
    """chatbot is widget/chat only — never live phone AI."""
    assert _ai_voice_mode({"plan": "chatbot", "voice_ai_enabled": True}) is False


def test_free_plan_never_gets_live_ai():
    assert _ai_voice_mode({"plan": "free", "voice_ai_enabled": True}) is False


def test_grandfathered_plans_still_work():
    """professional and enterprise are honored for existing contracts."""
    assert _ai_voice_mode({"plan": "professional", "voice_ai_enabled": True}) is True
    assert _ai_voice_mode({"plan": "enterprise", "voice_ai_enabled": True}) is True


def test_agent_os_in_allowed_set():
    """Regression guard: agent_os must be in _AI_VOICE_PLANS (2026-06-15 repricing fix)."""
    assert "agent_os" in _AI_VOICE_PLANS


def test_retired_plan_names_not_sole_members():
    """agent_os must be present; chatbot/free must not be."""
    assert "agent_os" in _AI_VOICE_PLANS
    assert "chatbot" not in _AI_VOICE_PLANS
    assert "free" not in _AI_VOICE_PLANS
