"""Base class for every worker agent.

Handles the cross-cutting concerns so each agent only has to implement
:meth:`BaseAgent.build`:

* loads the business-profile substrate honestly into the trace on every run;
* offers helpers for placeholder-safe values and channel-correct drafting;
* validates its own output against the three rules before returning (the
  registry validates again as the contractual gate).
"""

from __future__ import annotations

import agent_os.rules as rules
from agent_os.context import SharedContext
from agent_os.llm import LLMProvider, default_provider
from agent_os.profile import BusinessProfile
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import AgentSpec, Channel
from agent_os.trace import ReasoningTrace


class BaseAgent:
    """Subclasses set :attr:`spec` and implement :meth:`build`."""

    spec: AgentSpec

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self.llm = llm or default_provider()

    # ----- public entry point -----
    def run(self, ask: OwnerAsk, context: SharedContext) -> AgentResult:
        trace = ReasoningTrace()
        profile = context.business_profile

        # Substrate: honestly record what loaded from the profile. This is the
        # one load every agent performs, and the QA report's #1 complaint.
        trace.record_load(
            "Business profile",
            profile.loaded_summary(),
            describe=lambda summary: summary,
        )

        result = self.build(ask, context, trace)

        # Self-validate (registry re-validates as the contractual gate).
        rules.validate_output(self.spec, result, profile)
        return result

    # ----- subclass hook -----
    def build(
        self, ask: OwnerAsk, context: SharedContext, trace: ReasoningTrace
    ) -> AgentResult:  # pragma: no cover - abstract
        raise NotImplementedError

    # ----- helpers shared by agents -----
    def draft(
        self,
        *,
        trace: ReasoningTrace,
        system: str,
        prompt: str,
        fallback: str,
        step_name: str = "Drafted reply",
        max_tokens: int = 1024,
    ) -> tuple[str, bool]:
        """Produce body text. Returns ``(text, live)``.

        Uses the LLM when available, otherwise the deterministic *fallback*.
        Records an honest trace action describing what produced the text.
        """

        resp = self.llm.complete(
            system=system,
            prompt=prompt,
            fallback=fallback,
            model="draft",
            max_tokens=max_tokens,
        )
        how = "Claude draft" if resp.live else "template draft"
        trace.action(
            step_name,
            f"{resp.text[:60].strip()}…" if len(resp.text) > 60 else resp.text,
        )
        trace.note("Draft source", how)
        return resp.text, resp.live

    def value_or_gap(
        self,
        profile: BusinessProfile,
        field_name: str,
        result_messages: list[str],
        *,
        human_label: str | None = None,
    ) -> str | None:
        """Return the real profile value, or record a gap for the orchestrator.

        Never returns a bracketed placeholder. When the field is missing we add
        an honest heads-up to *result_messages* (back-channel to the owner).
        """

        val = profile.value(field_name)
        if val is None:
            label = human_label or field_name.replace("_", " ")
            result_messages.append(
                f"Heads up — your {label} isn't in your business profile yet, "
                f"so this draft leaves it out. Add it to sharpen future drafts."
            )
        return val

    def channel_for(self, ask: OwnerAsk) -> Channel:
        """Resolve the channel for this run: owner override if it's one this
        agent supports, otherwise the spec default."""

        requested = ask.requested_channel
        if requested and (
            requested == self.spec.channel or requested in self.spec.secondary_channels
        ):
            return requested
        return self.spec.channel
