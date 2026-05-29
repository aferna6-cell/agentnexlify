"""Exceptions raised by the registry and rule enforcement layer."""

from __future__ import annotations


class AgentOSError(Exception):
    """Base class for all Agent OS errors."""


class SchemaViolation(AgentOSError):
    """An :class:`~agent_os.schema.AgentSpec` failed static schema validation."""


class RegistryError(AgentOSError):
    """A problem registering or looking up an agent."""


class OutputRuleViolation(AgentOSError):
    """An agent's output violated one of the three enforced rules.

    ``rule`` is a stable machine code so CI can report which invariant broke:

    - ``honest_trace`` — a trace step claimed a successful load of empty data.
    - ``placeholder`` — output contained a bracketed placeholder.
    - ``channel_format`` — output broke its channel's formatting rules.
    - ``empty_draft`` — a draft was emitted with no body and no honest reason.
    """

    def __init__(self, rule: str, message: str, agent_id: str | None = None):
        self.rule = rule
        self.agent_id = agent_id
        prefix = f"[{agent_id}] " if agent_id else ""
        super().__init__(f"{prefix}{rule}: {message}")
