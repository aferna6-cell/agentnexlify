"""Typed accessors for provisioned Claude Managed Agent IDs.

The backend reads agent IDs from environment variables at startup (populated
by `scripts/managed_agents/provision.py`). This module exposes a small,
strict surface so callers do not have to reach into `settings` directly, and
so missing configuration fails loudly with an actionable error instead of a
cryptic 400 from the API later.
"""

from dataclasses import dataclass

from backend.config import settings


class ManagedAgentNotConfigured(RuntimeError):
    """Raised when a backend call tries to use an agent that hasn't been
    provisioned yet. Points the operator at the provision script so the fix
    is obvious.
    """

    def __init__(self, env_var: str, *, hint: str | None = None):
        base = (
            f"Managed Agent not configured: set {env_var} in .env or "
            f".env.managed_agents (run `python -m scripts.managed_agents.provision` "
            f"to create it)."
        )
        super().__init__(f"{base} {hint}" if hint else base)
        self.env_var = env_var


@dataclass(frozen=True)
class ManagedAgentHandle:
    """A resolved agent ID plus the environment it must run in."""

    agent_id: str
    environment_id: str


def _require(value: str, env_var: str) -> str:
    if not value:
        raise ManagedAgentNotConfigured(env_var)
    return value


def get_environment_id() -> str:
    return _require(
        settings.managed_agents_environment_id, "MANAGED_AGENTS_ENVIRONMENT_ID",
    )


def _handle(agent_id: str, env_var: str) -> ManagedAgentHandle:
    return ManagedAgentHandle(
        agent_id=_require(agent_id, env_var),
        environment_id=get_environment_id(),
    )


def lead_qualifier() -> ManagedAgentHandle:
    return _handle(settings.lead_qualifier_agent_id, "LEAD_QUALIFIER_AGENT_ID")


def document_drafter() -> ManagedAgentHandle:
    return _handle(settings.document_drafter_agent_id, "DOCUMENT_DRAFTER_AGENT_ID")


def codebase_reviewer() -> ManagedAgentHandle:
    return _handle(
        settings.codebase_reviewer_agent_id, "CODEBASE_REVIEWER_AGENT_ID",
    )


def support_agent() -> ManagedAgentHandle:
    return _handle(settings.support_agent_id, "SUPPORT_AGENT_ID")


def structured_extractor() -> ManagedAgentHandle:
    return _handle(
        settings.structured_extractor_agent_id, "STRUCTURED_EXTRACTOR_AGENT_ID",
    )


def deep_researcher() -> ManagedAgentHandle:
    return _handle(settings.deep_researcher_agent_id, "DEEP_RESEARCHER_AGENT_ID")


def field_monitor() -> ManagedAgentHandle:
    return _handle(settings.field_monitor_agent_id, "FIELD_MONITOR_AGENT_ID")


def data_analyst() -> ManagedAgentHandle:
    return _handle(settings.data_analyst_agent_id, "DATA_ANALYST_AGENT_ID")


def is_any_configured() -> bool:
    """Return True if at least one agent is provisioned. Useful for health
    checks and admin UIs.
    """
    return bool(
        settings.managed_agents_environment_id
        and (
            settings.lead_qualifier_agent_id
            or settings.document_drafter_agent_id
            or settings.codebase_reviewer_agent_id
            or settings.support_agent_id
            or settings.structured_extractor_agent_id
            or settings.deep_researcher_agent_id
            or settings.field_monitor_agent_id
            or settings.data_analyst_agent_id
        )
    )


# ----------------------------------------------------------------------
# Advisor-Executor helpers (2026-04-10)
#
# These wrap the existing agent handles in an AdvisorExecutorRunner so the
# caller gets an Opus-advised, Sonnet-executed run with a single call.
# Opt-in per call site — existing direct handle callers keep working.
# ----------------------------------------------------------------------


def advised_lead_qualifier(
    *, advisor_model: str = "claude-opus-4-6", enable_advisor: bool = True,
):
    """Return an AdvisorExecutorRunner bound to the lead_qualifier agent.

    Imported lazily to keep the registry module free of heavy imports
    for callers that only need plain handles.
    """
    from backend.services.advisor_executor import AdvisorExecutorRunner

    return AdvisorExecutorRunner(
        executor_handle=lead_qualifier(),
        advisor_model=advisor_model,
        enable_advisor=enable_advisor,
    )


def advised_document_drafter(
    *, advisor_model: str = "claude-opus-4-6", enable_advisor: bool = True,
):
    """Return an AdvisorExecutorRunner bound to the document_drafter agent."""
    from backend.services.advisor_executor import AdvisorExecutorRunner

    return AdvisorExecutorRunner(
        executor_handle=document_drafter(),
        advisor_model=advisor_model,
        enable_advisor=enable_advisor,
    )


def advised_codebase_reviewer(
    *, advisor_model: str = "claude-opus-4-6", enable_advisor: bool = True,
):
    """Return an AdvisorExecutorRunner bound to the codebase_reviewer agent."""
    from backend.services.advisor_executor import AdvisorExecutorRunner

    return AdvisorExecutorRunner(
        executor_handle=codebase_reviewer(),
        advisor_model=advisor_model,
        enable_advisor=enable_advisor,
    )
