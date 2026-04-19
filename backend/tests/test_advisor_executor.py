"""Unit tests for backend.services.advisor_executor.

Covers:
- advise() parses valid JSON into AdvisorBrief
- advise() handles fenced JSON output
- advise() raises on empty / invalid output
- AdvisorBrief.to_kickoff_prefix() shape
- run() falls back to pure executor when advise() raises
- run() injects brief into executor kickoff text when advise() succeeds
- enable_advisor=False skips advisor entirely
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.advisor_executor import (
    AdvisedRunResult,
    AdvisorBrief,
    AdvisorExecutorRunner,
)
from backend.services.llm_runtime import ClaudeCallResult
from backend.services.managed_agents import SessionTerminalState
from backend.services.managed_agents_registry import ManagedAgentHandle


def _handle() -> ManagedAgentHandle:
    return ManagedAgentHandle(
        agent_id="agt_test_executor",
        environment_id="env_test",
    )


def _mock_claude_result(text: str) -> ClaudeCallResult:
    return ClaudeCallResult(
        text=text,
        duration_ms=150,
        input_tokens=200,
        output_tokens=120,
        stop_reason="end_turn",
    )


def _mock_client():
    client = MagicMock()
    client.create_session.return_value = {"id": "sess_abc"}
    client.run_until_idle.return_value = SessionTerminalState(
        terminated=False,
        stop_reason_type="end_turn",
        last_event_id="evt_1",
        session_id="sess_abc",
    )
    return client


_VALID_ADVISOR_JSON = """{
  "plan": "1. Read the lead record. 2. Score intent + fit. 3. Recommend next action.",
  "constraints": ["Use client_id not tenant_id", "Return valid JSON"],
  "risks": ["Low signal on phone-only leads"],
  "success_criteria": ["intent_score 1-10 present", "recommendation in allowed enum"],
  "output_shape": "JSON with intent_score, fit_score, recommendation, reasoning",
  "advisor_escalation_rule": "If source evidence conflicts or required fields remain ambiguous, stop and request another Opus 4.7 advisor pass."
}"""


class TestAdvise:
    def test_parses_valid_json(self):
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=_mock_client(),
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result(_VALID_ADVISOR_JSON),
        ) as mock_call:
            brief = runner.advise("Qualify this lead.")

        assert "Read the lead record" in brief.plan
        assert "Use client_id not tenant_id" in brief.constraints
        assert brief.risks == ["Low signal on phone-only leads"]
        assert "Opus 4.7 advisor pass" in brief.advisor_escalation_rule
        assert brief.input_tokens == 200
        assert brief.output_tokens == 120
        call_kwargs = mock_call.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4-7"
        assert call_kwargs["temperature"] is None
        assert call_kwargs["output_config"] == {"effort": "xhigh"}

    def test_strips_markdown_fences(self):
        fenced = f"```json\n{_VALID_ADVISOR_JSON}\n```"
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=_mock_client(),
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result(fenced),
        ):
            brief = runner.advise("Task")
        assert "Read the lead record" in brief.plan

    def test_raises_on_empty_output(self):
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=_mock_client(),
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result("   "),
        ):
            with pytest.raises(ValueError, match="empty"):
                runner.advise("Task")

    def test_raises_on_invalid_json(self):
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=_mock_client(),
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result("not json at all"),
        ):
            with pytest.raises(ValueError, match="valid JSON"):
                runner.advise("Task")

    def test_raises_when_json_is_not_an_object(self):
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=_mock_client(),
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result('["not", "an", "object"]'),
        ):
            with pytest.raises(ValueError, match="not a JSON object"):
                runner.advise("Task")


class TestKickoffPrefix:
    def test_contains_all_sections(self):
        brief = AdvisorBrief(
            plan="Step 1. Step 2.",
            constraints=["no tenant_id"],
            risks=["flaky webhook"],
            success_criteria=["200 OK"],
            output_shape="JSON response",
            advisor_escalation_rule="Ask Opus again before guessing.",
        )
        text = brief.to_kickoff_prefix()
        assert "[ADVISOR BRIEF" in text
        assert "Plan:" in text
        assert "Step 1" in text
        assert "Hard constraints:" in text
        assert "no tenant_id" in text
        assert "Risks to avoid:" in text
        assert "Success criteria:" in text
        assert "Required output shape:" in text
        assert "Advisor escalation rule:" in text
        assert "Ask Opus again before guessing." in text
        assert "[END ADVISOR BRIEF]" in text

    def test_omits_empty_sections(self):
        brief = AdvisorBrief(plan="just plan")
        text = brief.to_kickoff_prefix()
        assert "Plan:" in text
        assert "Hard constraints:" not in text
        assert "Risks to avoid:" not in text


class TestRun:
    def test_happy_path_injects_brief_into_kickoff(self):
        client = _mock_client()
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=client,
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result(_VALID_ADVISOR_JSON),
        ):
            result = runner.run("Qualify lead X")

        assert result.advisor_used is True
        assert result.brief is not None
        assert result.fallback_reason is None
        assert result.terminal_state.session_id == "sess_abc"

        # Verify the executor kickoff text includes the brief prefix.
        _, kwargs = client.run_until_idle.call_args
        kickoff = kwargs["kickoff_text"]
        assert "[ADVISOR BRIEF" in kickoff
        assert "Qualify lead X" in kickoff
        assert "Read the lead record" in kickoff

    def test_advise_failure_falls_back_to_pure_executor(self):
        client = _mock_client()
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=client,
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            side_effect=RuntimeError("opus down"),
        ):
            result = runner.run("Qualify lead Y")

        assert result.advisor_used is False
        assert result.brief is None
        assert result.fallback_reason and "opus down" in result.fallback_reason
        assert result.terminal_state.session_id == "sess_abc"

        _, kwargs = client.run_until_idle.call_args
        kickoff = kwargs["kickoff_text"]
        assert "[ADVISOR BRIEF" not in kickoff
        assert "Qualify lead Y" in kickoff

    def test_enable_advisor_false_skips_advise(self):
        client = _mock_client()
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=client,
            enable_advisor=False,
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
        ) as mock_call:
            result = runner.run("Qualify lead Z")

        mock_call.assert_not_called()
        assert result.advisor_used is False
        assert result.brief is None
        assert result.fallback_reason == "advisor disabled"

    def test_executor_failure_bubbles(self):
        client = _mock_client()
        client.run_until_idle.side_effect = RuntimeError("session crashed")
        runner = AdvisorExecutorRunner(
            executor_handle=_handle(),
            managed_agents_client=client,
        )
        with patch(
            "backend.services.advisor_executor.call_claude_messages_sync",
            return_value=_mock_claude_result(_VALID_ADVISOR_JSON),
        ):
            with pytest.raises(RuntimeError, match="session crashed"):
                runner.run("Qualify lead X")
