"""Agent OS — v1 worker agent library.

A self-contained implementation of the AgentNexLiFy Agent OS: an orchestrator
that routes a small-business owner's natural-language asks to one of 18
specialist worker agents, each of which drafts channel-appropriate output
grounded in the owner's real business profile.

Three rules are enforced at the architectural level (see ``registry`` and
``rules``):

1. Honest reasoning traces — no "loaded" step for data that did not load.
2. No bracketed placeholders for fields that exist in the business profile.
3. Every agent declares its channel and respects channel formatting.

See ``README.md`` for how to run the demo.
"""

from agent_os.schema import (
    AgentSpec,
    Bucket,
    Channel,
    InputField,
    PermissionScope,
    Priority,
    Status,
    TriggerType,
)
from agent_os.context import SharedContext
from agent_os.profile import BusinessProfile, KBEntry
from agent_os.result import AgentResult, OwnerAsk
from agent_os.registry import REGISTRY, AgentRegistry
from agent_os.orchestrator import Orchestrator, RoutingDecision

# Importing the agents package registers all 18 worker agents into REGISTRY.
# Each register() call runs static schema + rule validation, so this import is
# also the architectural CI gate: a rule-violating agent fails the import.
import agent_os.agents  # noqa: E402,F401

__all__ = [
    "AgentSpec",
    "Bucket",
    "Channel",
    "InputField",
    "PermissionScope",
    "Priority",
    "Status",
    "TriggerType",
    "SharedContext",
    "BusinessProfile",
    "KBEntry",
    "AgentResult",
    "OwnerAsk",
    "REGISTRY",
    "AgentRegistry",
    "Orchestrator",
    "RoutingDecision",
]

__version__ = "1.0.0"
