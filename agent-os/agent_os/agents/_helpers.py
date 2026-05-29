"""Small drafting helpers shared across agent buckets.

These keep deterministic drafts placeholder-free and channel-correct so the
package demos and tests without an API key.
"""

from __future__ import annotations

import re

from agent_os.schema import (
    AgentSpec,
    Bucket,
    Channel,
    Example,
    InputField,
    PermissionScope,
    Priority,
    Status,
    TriggerType,
)


def build_spec(
    *,
    agent_id: str,
    display_name: str,
    bucket: Bucket,
    status: Status,
    build_priority: Priority,
    purpose: str,
    routes_here_when: tuple[str, ...],
    channel: Channel,
    title_format: str,
    body_format: str,
    reasoning_trace_steps: tuple[str, ...],
    example_interactions: tuple[Example, ...],
    inputs: tuple[InputField, ...] = (),
    shared_context_reads: tuple[str, ...] = ("business_profile",),
    tool_dependencies: tuple[str, ...] = ("none",),
    permission_scope: PermissionScope | None = None,
    triggers_supported: tuple[TriggerType, ...] = (TriggerType.manual,),
    routing_keywords: tuple[str, ...] = (),
    secondary_channels: tuple[Channel, ...] = (),
) -> AgentSpec:
    """Build an :class:`AgentSpec` with sensible defaults for the boilerplate
    fields. Every agent in the library uses this so specs stay readable."""

    return AgentSpec(
        agent_id=agent_id,
        display_name=display_name,
        bucket=bucket,
        status=status,
        build_priority=build_priority,
        purpose=purpose,
        routes_here_when=routes_here_when,
        channel=channel,
        inputs=inputs,
        shared_context_reads=shared_context_reads,
        tool_dependencies=tool_dependencies,
        permission_scope=permission_scope or PermissionScope(),
        triggers_supported=triggers_supported,
        title_format=title_format,
        body_format=body_format,
        reasoning_trace_steps=reasoning_trace_steps,
        example_interactions=example_interactions,
        routing_keywords=routing_keywords,
        secondary_channels=secondary_channels,
    )


def field_input(
    name: str,
    type_: str = "string",
    *,
    required: bool = False,
    description: str = "",
    source: str = "owner",
) -> InputField:
    return InputField(
        name=name,
        type=type_,
        required=required,
        description=description,
        source=source,
    )


_STOPWORDS = {
    "do",
    "you",
    "guys",
    "i",
    "a",
    "an",
    "the",
    "is",
    "are",
    "my",
    "your",
    "we",
    "can",
    "could",
    "please",
    "help",
    "with",
    "about",
    "for",
    "to",
    "of",
    "on",
    "and",
    "have",
    "has",
    "this",
    "that",
    "it",
    "me",
    "they",
    "them",
    "draft",
    "reply",
    "response",
    "send",
    "write",
    "need",
    "want",
}


def topic_from(text: str, *, default: str = "your question") -> str:
    """Extract a short, human topic phrase from an owner/customer message."""

    words = re.findall(r"[A-Za-z][A-Za-z'-]+", text.lower())
    keep = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    if not keep:
        return default
    # Up to three significant words, in original order.
    return " ".join(keep[:3])


def sms_optout() -> str:
    return "Reply STOP to opt out."


def touch_label(index: int, offset_days: int, channel: str) -> str:
    """Relative-date touch label, e.g. 'Touch 2 — +5 days (Email)'.

    Uses relative dates (Today / +N days), never 'Day 1 / Day 5' framing
    (a QA bug for Lead Nurture).
    """

    if offset_days == 0:
        when = "Today"
    else:
        when = f"+{offset_days} days"
    return f"Touch {index} — {when} ({channel})"


def money(amount: float | int | str | None) -> str:
    """Format a dollar amount without a trailing .0 when whole."""

    if amount is None:
        return ""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    if value.is_integer():
        return f"${int(value):,}"
    return f"${value:,.2f}"
