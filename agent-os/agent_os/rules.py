"""The three rules the registry enforces, regardless of bucket.

These are the architectural invariants from the QA report. They are checked at
two points:

* **Static** — :func:`validate_spec` runs when an agent registers. A malformed
  spec can never ship.
* **Runtime** — :func:`validate_output` runs on every :class:`AgentResult`
  before it reaches the owner. A violating draft is rejected.

Any violation raises :class:`~agent_os.errors.OutputRuleViolation` (runtime) or
:class:`~agent_os.errors.SchemaViolation` (static), which the test suite asserts
on — so a rule break fails CI.
"""

from __future__ import annotations

from agent_os.channels import validate_channel_format
from agent_os.errors import OutputRuleViolation, SchemaViolation
from agent_os.placeholders import find_placeholders
from agent_os.profile import BusinessProfile
from agent_os.result import AgentResult
from agent_os.schema import (
    CUSTOMER_FACING_CHANNELS,
    AgentSpec,
    Channel,
    TriggerType,
)


# --------------------------------------------------------------------------- #
# Static schema validation                                                    #
# --------------------------------------------------------------------------- #
def validate_spec(spec: AgentSpec) -> None:
    """Validate an :class:`AgentSpec` against the §2 schema. Raises
    :class:`SchemaViolation` on the first problem."""

    if not spec.agent_id or not spec.agent_id.replace("_", "").isalnum():
        raise SchemaViolation(f"agent_id must be snake_case alnum: {spec.agent_id!r}")
    if not spec.display_name:
        raise SchemaViolation(f"{spec.agent_id}: display_name required")
    if not spec.purpose:
        raise SchemaViolation(f"{spec.agent_id}: purpose required")
    if not spec.routes_here_when:
        raise SchemaViolation(f"{spec.agent_id}: routes_here_when must be non-empty")
    if not isinstance(spec.channel, Channel):
        raise SchemaViolation(f"{spec.agent_id}: channel must be a Channel enum")
    # Rule 3 (declaration half): every agent declares a channel — guaranteed by
    # the type above, but we also require trace steps and at least one trigger.
    if not spec.reasoning_trace_steps:
        raise SchemaViolation(
            f"{spec.agent_id}: must declare reasoning_trace_steps (honest-trace contract)"
        )
    if TriggerType.manual not in spec.triggers_supported:
        raise SchemaViolation(
            f"{spec.agent_id}: every agent must support the manual trigger"
        )
    if not spec.example_interactions:
        raise SchemaViolation(
            f"{spec.agent_id}: at least one example_interaction required"
        )
    for ex in spec.example_interactions:
        if ex.expected_route != spec.agent_id:
            raise SchemaViolation(
                f"{spec.agent_id}: example routes to {ex.expected_route!r}, expected self"
            )


# --------------------------------------------------------------------------- #
# Runtime output validation                                                   #
# --------------------------------------------------------------------------- #
def validate_output(
    spec: AgentSpec, result: AgentResult, profile: BusinessProfile
) -> None:
    """Enforce the three rules on a produced result. Raises
    :class:`OutputRuleViolation` (with a stable ``rule`` code) on violation."""

    # A no-draft result must carry an explanation and never a stray body.
    if not result.has_draft:
        if result.body.strip():
            raise OutputRuleViolation(
                "empty_draft",
                "has_draft=False but body is non-empty",
                spec.agent_id,
            )
        if not result.orchestrator_messages:
            raise OutputRuleViolation(
                "empty_draft",
                "no draft produced and no reason surfaced to the owner",
                spec.agent_id,
            )
        return

    if not result.body.strip():
        raise OutputRuleViolation(
            "empty_draft",
            "draft has an empty body — surface 'service unavailable' instead",
            spec.agent_id,
        )

    text = f"{result.title}\n{result.body}"

    # --- Rule 1: honest reasoning trace ---
    for step in result.trace.steps:
        if (
            step.loaded
            and not (step.summary and step.summary.strip())
            and step.name.lower().endswith(
                ("profile", "base", "history", "chats", "state")
            )
        ):
            # A load-style step marked loaded must carry a real summary of what
            # loaded. (Action/decision steps use action()/note() and are fine.)
            raise OutputRuleViolation(
                "honest_trace",
                f"trace step {step.name!r} claims a load but loaded nothing",
                spec.agent_id,
            )

    # --- Rule 2: no bracketed placeholders ---
    # Customer-facing channels: no bracketed placeholders at all.
    if spec.channel in CUSTOMER_FACING_CHANNELS or spec.channel == Channel.sequence:
        found = find_placeholders(text)
        if found:
            raise OutputRuleViolation(
                "placeholder",
                "customer-facing draft contains placeholder(s): "
                + ", ".join(f.token for f in found),
                spec.agent_id,
            )
    else:
        # Owner-facing (report/internal): reject only placeholders for fields
        # that exist in the profile (the precise §2 wording).
        offenders = [
            f
            for f in find_placeholders(text)
            if f.maps_to_field and profile.has(f.maps_to_field)
        ]
        if offenders:
            raise OutputRuleViolation(
                "placeholder",
                "report contains placeholder(s) for fields present in profile: "
                + ", ".join(f.token for f in offenders),
                spec.agent_id,
            )

    # Internal back-channel content must never leak into a customer draft.
    if spec.channel in CUSTOMER_FACING_CHANNELS:
        lowered = result.body.lower()
        for leak in (
            "i need your business profile",
            "knowledge base to draft",
            "share your",
        ):
            if leak in lowered:
                raise OutputRuleViolation(
                    "placeholder",
                    "internal back-channel content leaked into a customer-facing draft",
                    spec.agent_id,
                )

    # --- Rule 3: channel formatting ---
    findings = validate_channel_format(spec.channel, result.body)
    if findings:
        raise OutputRuleViolation(
            "channel_format",
            f"{spec.channel.value} draft must be plain text; found "
            + ", ".join(f.token for f in findings),
            spec.agent_id,
        )
