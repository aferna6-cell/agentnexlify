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
        )
    )
