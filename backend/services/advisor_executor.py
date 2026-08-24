"""Advisor-Executor runtime pattern for Claude Managed Agents.

Claude Platform launched the advisor pattern (2026-04-10): pair Opus as an
advisor with Sonnet or Haiku as an executor. Near-Opus quality at ~1.3x pure
Sonnet cost instead of 5x pure Opus. AgentNexLiFy uses Opus 4.7 for the
advisor pass and keeps Sonnet/Haiku executor agents on cheaper models unless
they need the advisor boost.

This module implements the pattern for product-runtime tenant agents. The
dev-time equivalent lives in `.claude/agents/opus-advisor.md` and
`.claude/agents/sonnet-executor.md`.

Flow (one `run()` call):

    1. advise() — single direct Messages API call to Opus. Returns a
       structured brief (plan, constraints, risks, success_criteria) as JSON.
       Cheap: ~300-500 output tokens. Uses `call_claude_messages_sync` from
       llm_runtime for consistent logging/timing.
    2. execute() — creates a new Managed Agent session on the executor handle,
       injects the brief into the kickoff user message, drains the event
       stream via ManagedAgentsClient.run_until_idle().

Why not use Managed Agents for the advisor pass?
- No tools / MCP / skills needed during planning — pure reasoning
- Avoids double environment overhead
- Lets us swap the advisor model independently (Opus → smaller model later)
  without touching the executor agent config

Why keep Managed Agents for the executor pass?
- Sessions, events, resources, files, and vault_ids are already wired
- Avoids duplicating session management
- Executor agents benefit from tool access that the advisor doesn't need

Opt-in per call site: existing direct `lead_qualifier()` calls keep working.
New code that wants the advisor boost uses `advised_lead_qualifier()` from
the registry.

Failure semantics:
- Advisor call fails → fall back to pure executor pass (log warning, continue)
- Executor call fails → bubble the error (no silent swallow)
- Never let advisor failures block user-facing runs
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from backend.services.llm_runtime import call_claude_messages_sync
from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    SessionTerminalState,
    get_default_client,
)
from backend.services.managed_agents_registry import ManagedAgentHandle

logger = logging.getLogger(__name__)


DEFAULT_ADVISOR_MODEL = "claude-opus-4-8"
# 1200, not 800: the Opus 4.7+ tokenizer maps the same text to up to 1.35x the
# token count of 4.6, so the original 800 budget became ~600 effective and
# truncated briefs. See .claude/rules/advisor-consult.md "Cost model".
DEFAULT_ADVISOR_MAX_TOKENS = 1200
DEFAULT_ADVISOR_TEMPERATURE: float | None = None
DEFAULT_ADVISOR_OUTPUT_CONFIG = {"effort": "xhigh"}

_ADVISOR_SYSTEM_PROMPT = """You are the Planning Advisor in the Advisor-Executor pattern.

Your role is planning. Produce a short written brief that a Sonnet or Haiku
executor agent will follow to perform the work.

Output STRICT JSON matching this shape (no prose outside the JSON — the
downstream parser requires pure JSON):

{
  "plan": "<ordered, numbered steps the executor must follow>",
  "constraints": ["<hard rule 1>", "<hard rule 2>"],
  "risks": ["<what could go wrong>"],
  "success_criteria": ["<observable signal the task succeeded>"],
  "output_shape": "<what the executor's final response should contain>",
  "advisor_escalation_rule": "<when the executor must stop and ask for another advisor pass>"
}

Rules:
- Be specific. Steps should reference concrete fields, values, or actions.
- Keep total output under 500 tokens (cost guard).
- List the 2-5 most important gotchas in `constraints`.
- If the task is ambiguous, pick the most likely interpretation and flag
  the ambiguity in `risks` with the assumption you made.
- If Sonnet or Haiku would need to guess, instruct it to stop and request
  another Opus 4.7 advisor pass instead of improvising.
- Describe changes in prose. The executor writes the code.
- Valid JSON only. No markdown fences. No commentary. (Parser invariant.)
"""


@dataclass
class AdvisorBrief:
    """Structured output from the advisor pass."""

    plan: str
    constraints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    output_shape: str = ""
    advisor_escalation_rule: str = ""
    raw_text: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_kickoff_prefix(self) -> str:
        """Format the brief as a kickoff-message prefix the executor reads."""
        lines = ["[ADVISOR BRIEF — follow these instructions]", ""]
        lines.append("Plan:")
        lines.append(self.plan.strip())
        if self.constraints:
            lines.append("")
            lines.append("Hard constraints:")
            for c in self.constraints:
                lines.append(f"- {c}")
        if self.risks:
            lines.append("")
            lines.append("Risks to avoid:")
            for r in self.risks:
                lines.append(f"- {r}")
        if self.success_criteria:
            lines.append("")
            lines.append("Success criteria:")
            for s in self.success_criteria:
                lines.append(f"- {s}")
        if self.output_shape:
            lines.append("")
            lines.append("Required output shape:")
            lines.append(self.output_shape.strip())
        if self.advisor_escalation_rule:
            lines.append("")
            lines.append("Advisor escalation rule:")
            lines.append(self.advisor_escalation_rule.strip())
        lines.append("")
        lines.append("[END ADVISOR BRIEF]")
        return "\n".join(lines)


@dataclass
class AdvisedRunResult:
    """Summary of a full advised run (advise + execute)."""

    terminal_state: SessionTerminalState
    brief: AdvisorBrief | None
    advisor_used: bool
    fallback_reason: str | None = None


class AdvisorExecutorRunner:
    """Two-pass runner: Opus advises, executor Managed Agent executes.

    Typical usage:

        runner = AdvisorExecutorRunner(executor_handle=lead_qualifier())
        result = runner.run(
            task_prompt="Qualify this inbound lead: ...",
            session_title="lead-qual-2026-04-10",
        )
        # result.terminal_state.session_id → used to pull events + final
        # agent output via ManagedAgentsClient.list_events(...)
    """

    def __init__(
        self,
        executor_handle: ManagedAgentHandle,
        *,
        advisor_model: str = DEFAULT_ADVISOR_MODEL,
        advisor_max_tokens: int = DEFAULT_ADVISOR_MAX_TOKENS,
        advisor_temperature: float | None = DEFAULT_ADVISOR_TEMPERATURE,
        advisor_output_config: dict[str, Any] | None = None,
        managed_agents_client: ManagedAgentsClient | None = None,
        enable_advisor: bool = True,
    ):
        self.executor_handle = executor_handle
        self.advisor_model = advisor_model
        self.advisor_max_tokens = advisor_max_tokens
        self.advisor_temperature = advisor_temperature
        self.advisor_output_config = dict(
            advisor_output_config or DEFAULT_ADVISOR_OUTPUT_CONFIG
        )
        self._client = managed_agents_client or get_default_client()
        self.enable_advisor = enable_advisor

    # ------------------------------------------------------------------
    # advise pass — direct Messages API, not Managed Agents
    # ------------------------------------------------------------------

    def advise(self, task_prompt: str, *, context: str | None = None) -> AdvisorBrief:
        """Single Messages API call to Opus. Returns parsed AdvisorBrief.

        Raises ManagedAgentsError-like exception on transport failure, or
        ValueError on unparseable JSON output.
        """
        user_content = task_prompt.strip()
        if context:
            user_content = f"{user_content}\n\n---\nAdditional context:\n{context.strip()}"

        result = call_claude_messages_sync(
            operation="advisor_executor.advise",
            model=self.advisor_model,
            max_tokens=self.advisor_max_tokens,
            temperature=self.advisor_temperature,
            output_config=self.advisor_output_config,
            system=_ADVISOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            metadata={
                "pattern": "advisor_executor",
                "pass": "advise",
                "executor_agent_id": self.executor_handle.agent_id,
            },
        )

        raw = result.text.strip()
        if not raw:
            raise ValueError("Advisor returned empty output")

        # Strip accidental fences (advisor is told not to use them, but
        # some Opus versions add them anyway).
        if raw.startswith("```"):
            raw = raw.strip("`")
            # After stripping backticks, drop an optional "json" hint line.
            lines = raw.split("\n", 1)
            if len(lines) == 2 and lines[0].strip().lower() in {"json", ""}:
                raw = lines[1]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Advisor output was not valid JSON: {exc} — raw: {raw[:400]}",
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(f"Advisor output was not a JSON object: {type(data).__name__}")

        return AdvisorBrief(
            plan=str(data.get("plan", "")).strip(),
            constraints=[str(x) for x in (data.get("constraints") or [])],
            risks=[str(x) for x in (data.get("risks") or [])],
            success_criteria=[str(x) for x in (data.get("success_criteria") or [])],
            output_shape=str(data.get("output_shape", "")).strip(),
            advisor_escalation_rule=str(data.get("advisor_escalation_rule", "")).strip(),
            raw_text=raw,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    # ------------------------------------------------------------------
    # execute pass — Managed Agent session
    # ------------------------------------------------------------------

    def execute(
        self,
        task_prompt: str,
        *,
        brief: AdvisorBrief | None,
        session_title: str | None = None,
        resources: list[dict[str, Any]] | None = None,
        vault_ids: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> SessionTerminalState:
        """Create a Managed Agent session and drain to idle.

        If `brief` is provided, its contents are injected into the kickoff
        user message as a prefix. If None, runs the executor with the raw
        task prompt (pure-executor fallback path).
        """
        session = self._client.create_session(
            agent_id=self.executor_handle.agent_id,
            environment_id=self.executor_handle.environment_id,
            title=session_title,
            resources=resources,
            vault_ids=vault_ids,
            metadata=metadata,
        )
        session_id = session.get("id")
        if not isinstance(session_id, str):
            raise ManagedAgentsError(
                f"create_session returned no id — got {session!r}",
            )

        kickoff = task_prompt.strip()
        if brief is not None:
            kickoff = f"{brief.to_kickoff_prefix()}\n\nTask:\n{kickoff}"

        return self._client.run_until_idle(session_id, kickoff_text=kickoff)

    # ------------------------------------------------------------------
    # full two-pass run
    # ------------------------------------------------------------------

    def run(
        self,
        task_prompt: str,
        *,
        context: str | None = None,
        session_title: str | None = None,
        resources: list[dict[str, Any]] | None = None,
        vault_ids: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> AdvisedRunResult:
        """Run the full advisor → executor pipe for a single task.

        Advisor failures fall back to pure executor. Executor failures
        bubble up.
        """
        brief: AdvisorBrief | None = None
        fallback_reason: str | None = None

        if self.enable_advisor:
            try:
                brief = self.advise(task_prompt, context=context)
                logger.info(
                    "advisor_executor: advise pass ok (input=%s output=%s)",
                    brief.input_tokens,
                    brief.output_tokens,
                )
            except Exception as exc:  # noqa: BLE001 — intentional fallback
                fallback_reason = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "advisor_executor: advise pass failed, falling back to pure executor: %s",
                    fallback_reason,
                )
                brief = None
        else:
            fallback_reason = "advisor disabled"

        terminal = self.execute(
            task_prompt,
            brief=brief,
            session_title=session_title,
            resources=resources,
            vault_ids=vault_ids,
            metadata=metadata,
        )

        return AdvisedRunResult(
            terminal_state=terminal,
            brief=brief,
            advisor_used=(brief is not None),
            fallback_reason=fallback_reason,
        )
