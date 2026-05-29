"""The agent registry — where the three rules are enforced.

Registration runs static schema validation (:func:`agent_os.rules.validate_spec`).
Execution runs the agent and then runtime rule validation
(:func:`agent_os.rules.validate_output`) before any result is handed back. There
is no path to the owner that skips the registry, so a rule break cannot ship.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import agent_os.rules as rules
from agent_os.context import SharedContext
from agent_os.errors import RegistryError
from agent_os.result import AgentResult, OwnerAsk
from agent_os.schema import AgentSpec, Bucket

if TYPE_CHECKING:  # avoid import cycle at runtime
    from agent_os.base import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, "BaseAgent"] = {}

    # ----- registration -----
    def register(self, agent: "BaseAgent") -> "BaseAgent":
        spec = agent.spec
        rules.validate_spec(spec)  # raises SchemaViolation on bad spec
        if spec.agent_id in self._agents:
            raise RegistryError(f"duplicate agent_id: {spec.agent_id}")
        self._agents[spec.agent_id] = agent
        return agent

    # ----- lookup -----
    def get(self, agent_id: str) -> "BaseAgent":
        try:
            return self._agents[agent_id]
        except KeyError:
            raise RegistryError(f"unknown agent: {agent_id}") from None

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def all(self) -> list["BaseAgent"]:
        return list(self._agents.values())

    def specs(self) -> list[AgentSpec]:
        return [a.spec for a in self._agents.values()]

    def by_bucket(self, bucket: Bucket) -> list["BaseAgent"]:
        return [a for a in self._agents.values() if a.spec.bucket == bucket]

    def buckets(self) -> dict[Bucket, list[AgentSpec]]:
        out: dict[Bucket, list[AgentSpec]] = {}
        for agent in self._agents.values():
            out.setdefault(agent.spec.bucket, []).append(agent.spec)
        return out

    def __len__(self) -> int:
        return len(self._agents)

    def __iter__(self) -> Iterable["BaseAgent"]:
        return iter(self._agents.values())

    # ----- execution (rules enforced here) -----
    def run(self, agent_id: str, ask: OwnerAsk, context: SharedContext) -> AgentResult:
        agent = self.get(agent_id)
        result = agent.run(ask, context)
        # Defense in depth: even though BaseAgent.run validates, the registry is
        # the contractual gate. Re-validate here so no caller can bypass it.
        rules.validate_output(agent.spec, result, context.business_profile)
        return result


# Global registry. Importing agent_os.agents populates it.
REGISTRY = AgentRegistry()
