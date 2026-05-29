"""The agent schema (library spec §2).

Every agent in the library conforms to :class:`AgentSpec`. The registry
(:mod:`agent_os.registry`) enforces this schema at registration time so a
malformed agent can never ship.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Bucket(str, Enum):
    """Functional bucket. A maintenance/prioritization construct for the team;
    owners never see buckets directly (orchestrator can list them on request)."""

    customer_service = "customer_service"
    sales = "sales"
    marketing = "marketing"
    scheduling_ops = "scheduling_ops"
    finance = "finance"
    reputation = "reputation"
    reporting = "reporting"
    system = "system"


class Status(str, Enum):
    existing = "existing"
    new = "new"
    workaround = "workaround"
    stub = "stub"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Channel(str, Enum):
    """Output channel. Drives the formatting rules enforced in
    :mod:`agent_os.channels`."""

    sms = "sms"
    email = "email"
    sequence = "sequence"
    report = "report"
    post = "post"
    widget_reply = "widget_reply"
    internal = "internal"


class TriggerType(str, Enum):
    manual = "manual"
    scheduled = "scheduled"
    event_based = "event_based"


# Channels whose output is read by a customer (not just the owner). Bracketed
# placeholders are never acceptable here, and back-channel/internal content must
# never leak into these drafts.
CUSTOMER_FACING_CHANNELS = frozenset(
    {Channel.sms, Channel.email, Channel.post, Channel.widget_reply}
)

# Channels that may contain markdown. Everything not in this set must be plain
# text (no markdown, no asterisks, no headers).
MARKDOWN_CHANNELS = frozenset(
    {Channel.email, Channel.report, Channel.sequence, Channel.internal}
)


@dataclass(frozen=True)
class InputField:
    """A single typed input the agent consumes."""

    name: str
    type: str  # string | number | date | array | object
    required: bool
    description: str
    # Where the orchestrator sources this field from.
    source: str = "owner"  # owner | shared_context


@dataclass(frozen=True)
class SendCaps:
    per_day: int | None = None
    per_month: int | None = None


@dataclass(frozen=True)
class PermissionScope:
    """Permission posture for an agent. Defaults to drafts-only (v1)."""

    default: str = "drafts_only"
    # Hardcoded approval can never be turned off, even after Phase 4 auto-send
    # ships (complaints, quotes, payment escalation).
    require_owner_approval: bool = True
    hardcoded_approval: bool = False
    send_caps: SendCaps = field(default_factory=SendCaps)
    recipient_filter: str = (
        "any"  # any | existing_customers_only | custom_list | completed_service_only
    )
    notes: str = ""


@dataclass(frozen=True)
class Example:
    owner_ask: str
    expected_route: str
    expected_output_excerpt: str


@dataclass(frozen=True)
class AgentSpec:
    """The full, validated specification for one worker agent (library §2)."""

    agent_id: str
    display_name: str
    bucket: Bucket
    status: Status
    build_priority: Priority
    purpose: str
    routes_here_when: tuple[str, ...]
    channel: Channel
    inputs: tuple[InputField, ...]
    shared_context_reads: tuple[str, ...]
    tool_dependencies: tuple[str, ...]
    permission_scope: PermissionScope
    triggers_supported: tuple[TriggerType, ...]
    title_format: str
    body_format: str
    # Names of trace steps the agent SHOULD honestly show. These are declared
    # intent; the runtime trace must still reflect what actually loaded.
    reasoning_trace_steps: tuple[str, ...]
    example_interactions: tuple[Example, ...]
    # Orchestrator routing hints (keyword sets). Not part of the published
    # schema but stored alongside it so routing stays declarative.
    routing_keywords: tuple[str, ...] = ()
    secondary_channels: tuple[Channel, ...] = ()

    # ----- convenience -----
    @property
    def can_use_markdown(self) -> bool:
        return self.channel in MARKDOWN_CHANNELS

    @property
    def is_customer_facing(self) -> bool:
        return self.channel in CUSTOMER_FACING_CHANNELS
