"""Tests for managed-agent route guardrails."""

from backend.routers.managed_agent_runs import _managed_agents_unavailable
from backend.services.managed_agents_registry import ManagedAgentNotConfigured


def test_not_configured_response_is_product_safe():
    exc = ManagedAgentNotConfigured("LEAD_QUALIFIER_AGENT_ID")

    http_exc = _managed_agents_unavailable(exc)

    assert http_exc.status_code == 503
    assert http_exc.detail["error"] == "managed_agents_unavailable"
    assert http_exc.detail["planned_update"] is True
    assert http_exc.detail["missing_config"] == "LEAD_QUALIFIER_AGENT_ID"
    assert "future update" in http_exc.detail["message"]
