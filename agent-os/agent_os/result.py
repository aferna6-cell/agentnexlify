"""Owner ask and agent result value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_os.schema import Channel
from agent_os.trace import ReasoningTrace


@dataclass
class OwnerAsk:
    """A natural-language request from the owner, plus any params the
    orchestrator extracted from it."""

    text: str
    params: dict[str, Any] = field(default_factory=dict)
    # Channel the owner explicitly requested ("text me" -> sms), if any.
    requested_channel: Channel | None = None

    def param(self, name: str, default: Any = None) -> Any:
        return self.params.get(name, default)


@dataclass
class AgentResult:
    """What an agent produces.

    ``body`` is the customer-/owner-facing draft. ``orchestrator_messages`` are
    back-channel notes to the owner (gaps, heads-ups) that must never appear in
    ``body``. ``requires_approval`` and ``flagged`` drive the Approve/Reject UI.
    A result with ``has_draft=False`` renders no draft and no Approve button
    (the honest credit-out / no-content path).
    """

    agent_id: str
    channel: Channel
    title: str
    body: str
    trace: ReasoningTrace
    metadata: dict[str, Any] = field(default_factory=dict)
    orchestrator_messages: list[str] = field(default_factory=list)
    requires_approval: bool = True
    flagged: bool = False  # e.g. complaints surface red in the task list
    has_draft: bool = True

    def add_orchestrator_message(self, msg: str) -> None:
        self.orchestrator_messages.append(msg)

    @classmethod
    def no_draft(
        cls,
        agent_id: str,
        channel: Channel,
        reason: str,
        trace: ReasoningTrace,
    ) -> "AgentResult":
        """Construct a result that surfaces a reason in chat and shows no
        draft (used for the LLM-unavailable path)."""

        return cls(
            agent_id=agent_id,
            channel=channel,
            title="",
            body="",
            trace=trace,
            orchestrator_messages=[reason],
            requires_approval=False,
            has_draft=False,
        )
