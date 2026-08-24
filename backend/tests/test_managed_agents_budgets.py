"""Tests for session budgets, multiagent rosters, and scheduled deployments.

Separate from `test_managed_agents.py` (already 1300+ lines) because these
cover distinct concerns added 2026-08-24. See `.claude/rules/user-rules.md`
Rule 12.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.services.managed_agents import ManagedAgentsClient, build_budget
from backend.services.managed_agents_deployments import (
    create_deployment,
    find_deployment_by_name,
    list_deployment_runs,
    pause_deployment,
)


def _ok_response(payload: Any) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json=payload,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/test"),
    )


def _make_client() -> ManagedAgentsClient:
    return ManagedAgentsClient(api_key="sk-test-noop")


def _mock_http(payload: Any) -> MagicMock:
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    mock.request.return_value = _ok_response(payload)
    return mock


class TestBuildBudget:
    def test_amount_is_a_whole_cents_string(self):
        """The API rejects decimal forms like "25.00", and a string avoids any
        float rounding on the way out."""
        budget = build_budget(125)
        assert budget == {
            "type": "limit",
            "max_list_cost": {"amount": "125", "currency": "USD"},
        }
        assert isinstance(budget["max_list_cost"]["amount"], str)
        assert "." not in budget["max_list_cost"]["amount"]

    @pytest.mark.parametrize("bad", [0, -1, -500])
    def test_rejects_non_positive(self, bad):
        with pytest.raises(ValueError, match="positive number of cents"):
            build_budget(bad)


class TestSessionBudget:
    def test_budget_omitted_by_default(self):
        """Interactive paths must keep working with no cap and no `budget` key
        in the body — a budget can only ever be attached at creation."""
        client = _make_client()
        mock = _mock_http({"id": "sess_1"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            client.create_session(agent_id="agent_abc", environment_id="env_abc")

        body = mock.request.call_args.kwargs["json"]
        assert "budget" not in body

    def test_budget_attached_when_requested(self):
        client = _make_client()
        mock = _mock_http({"id": "sess_1"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            client.create_session(
                agent_id="agent_abc", environment_id="env_abc", budget_cents=500
            )

        body = mock.request.call_args.kwargs["json"]
        assert body["budget"]["max_list_cost"] == {"amount": "500", "currency": "USD"}

    def test_invalid_budget_raises_before_any_http_call(self):
        """A bad cap must fail loudly at the call site rather than creating an
        uncapped session."""
        client = _make_client()
        mock = _mock_http({"id": "sess_1"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            with pytest.raises(ValueError):
                client.create_session(
                    agent_id="agent_abc", environment_id="env_abc", budget_cents=-1
                )
        mock.request.assert_not_called()


class TestMultiagentRoster:
    def test_multiagent_omitted_by_default(self):
        client = _make_client()
        mock = _mock_http({"id": "agent_abc"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            client.create_agent(name="Bot", model="claude-opus-4-8")

        assert "multiagent" not in mock.request.call_args.kwargs["json"]

    def test_advisor_roster_passed_through(self):
        client = _make_client()
        roster = {
            "type": "coordinator",
            "agents": [{"type": "advisor", "model": "claude-opus-4-8"}],
        }
        mock = _mock_http({"id": "agent_abc"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            client.create_agent(
                name="Drafter", model="claude-sonnet-5", multiagent=roster
            )

        assert mock.request.call_args.kwargs["json"]["multiagent"] == roster

    def test_model_object_form_carries_effort(self):
        """The object form is the only way to set effort; a plain string can't."""
        client = _make_client()
        mock = _mock_http({"id": "agent_abc"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            client.create_agent(
                name="Bot", model={"id": "claude-opus-4-8", "effort": "high"}
            )

        body = mock.request.call_args.kwargs["json"]
        assert body["model"] == {"id": "claude-opus-4-8", "effort": "high"}


class TestDeployments:
    def test_create_sends_cron_schedule_and_beta_param(self):
        client = _make_client()
        mock = _mock_http(
            {"id": "depl_1", "schedule": {"upcoming_runs_at": ["2026-09-01T12:00:00Z"]}}
        )
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            create_deployment(
                client,
                name="Weekly digest",
                agent_id="agent_abc",
                environment_id="env_abc",
                cron_expression="0 12 * * 1",
                timezone="America/New_York",
                kickoff_text="Run the weekly digest.",
                budget_cents=300,
            )

        kwargs = mock.request.call_args.kwargs
        body = kwargs["json"]
        assert body["schedule"] == {
            "type": "cron",
            "expression": "0 12 * * 1",
            "timezone": "America/New_York",
        }
        assert body["agent"] == "agent_abc"
        assert body["initial_events"][0]["type"] == "user.message"
        # Budget bounds EACH run, not cumulative spend across runs.
        assert body["budget"]["max_list_cost"]["amount"] == "300"
        # Deployment endpoints need ?beta=true on top of the beta header.
        assert kwargs["params"]["beta"] == "true"

    def test_budget_omitted_when_not_given(self):
        client = _make_client()
        mock = _mock_http({"id": "depl_1", "schedule": {}})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            create_deployment(
                client,
                name="No budget",
                agent_id="agent_abc",
                environment_id="env_abc",
                cron_expression="0 12 * * 1",
                timezone="UTC",
                kickoff_text="go",
            )

        assert "budget" not in mock.request.call_args.kwargs["json"]

    def test_find_by_name_skips_archived(self):
        """An archived deployment keeps its name; matching it would make
        provisioning try to update a terminal resource."""
        client = _make_client()
        mock = _mock_http(
            {
                "data": [
                    {"id": "depl_old", "name": "Weekly digest", "archived_at": "2026-01-01"},
                    {"id": "depl_new", "name": "Weekly digest", "archived_at": None},
                ]
            }
        )
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            found = find_deployment_by_name(client, "Weekly digest")

        assert found is not None
        assert found["id"] == "depl_new"

    def test_find_by_name_returns_none_when_absent(self):
        client = _make_client()
        mock = _mock_http({"data": []})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            assert find_deployment_by_name(client, "nope") is None

    def test_list_runs_can_filter_to_errors(self):
        """Failed firings never produce a session, so this is the only place a
        rate-limited or auto-paused deployment shows up."""
        client = _make_client()
        mock = _mock_http({"data": [{"id": "drun_1", "error": {"type": "boom"}}]})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            runs = list_deployment_runs(client, "depl_1", has_error=True)

        params = mock.request.call_args.kwargs["params"]
        assert params["deployment_id"] == "depl_1"
        assert params["has_error"] == "true"
        assert len(runs) == 1

    def test_pause_hits_the_pause_endpoint(self):
        client = _make_client()
        mock = _mock_http({"id": "depl_1", "status": "paused"})
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock):
            pause_deployment(client, "depl_1")

        args = mock.request.call_args.args
        assert args[0] == "POST"
        assert args[1].endswith("/v1/deployments/depl_1/pause")
