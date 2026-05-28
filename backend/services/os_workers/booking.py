"""Agent OS worker: booking — appointment booking draft messages.

Turns a small-business owner's request into an approval-gated draft reply that
the owner can review and then send to a customer who wants to book, reschedule,
or cancel an appointment, or needs a booking confirmation/summary. Grounds the
draft in real tenant data (business hours, services, recent widget chats) via
``ctx.tools`` — read-only, tenant-scoped.
"""

import json
import logging

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec
from backend.services.os_workers.profile import (
    PLACEHOLDER_INSTRUCTION,
    format_business_profile_block,
    profile_trace_step,
)

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Handles appointment-related requests: booking, rescheduling, cancellation, "
    "or confirmation messages. Route here when a customer wants to book or change "
    "an appointment, or when the owner needs a booking message drafted for review."
)

_SYSTEM_PROMPT = """\
You are a professional assistant helping a small-business owner draft appointment \
messages. Write a clear, polite message the owner can review and then send to the \
customer. The message should handle the customer's request — booking a new \
appointment, rescheduling or cancelling an existing one, or providing a booking \
confirmation or summary.

Use the business profile (hours, services, business name) supplied in the user \
message to make the draft specific and accurate. If recent customer chats are \
included, reference them only when directly relevant.

If the request is incomplete (missing preferred date/time or service type), include \
a polite question asking for the missing detail.

Output only the message body in markdown. Do not include a preamble, subject line, \
or any phrase like "here is your draft" — start directly with the message content.

""" + PLACEHOLDER_INSTRUCTION


_PROFILE_KEYS = (
    "business_name",
    "business_type",
    "timezone",
    "business_hours",
    "services_offered",
    "owner_name",
)


def _profile_brief(profile: dict) -> dict:
    return {key: profile.get(key) for key in _PROFILE_KEYS if profile.get(key)}


def _conversations_brief(convos: list[dict]) -> list[dict]:
    brief: list[dict] = []
    for row in convos[:5]:
        brief.append(
            {
                "session_id": row.get("session_id"),
                "customer_name": row.get("customer_name"),
                "needs_handoff": row.get("needs_handoff"),
                "updated_at": row.get("updated_at"),
            }
        )
    return brief


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Booking Reply"

    ctx.step(
        "Reviewing the booking request",
        f"Preparing a draft reply for: {ctx.user_message[:120]}",
    )

    profile: dict = {}
    recent_convos: list[dict] = []
    if ctx.tools is not None:
        profile = await ctx.tools.tenant_profile()
        trace_label, trace_detail = profile_trace_step(profile)
        ctx.step(trace_label, trace_detail)
        ctx.step("Loading recent chats", "Last 7 days of widget conversations.")
        recent_convos = await ctx.tools.recent_widget_conversations(days=7, limit=5)

    profile_block = format_business_profile_block(profile)
    profile_brief = _profile_brief(profile)
    convo_brief = _conversations_brief(recent_convos)

    user_content_parts: list[str] = []
    if profile_block:
        user_content_parts.append(profile_block)
    user_content_parts.append(f"Owner request:\n{ctx.user_message}")
    if profile_brief:
        user_content_parts.append(
            "Business profile:\n" + json.dumps(profile_brief, default=str)
        )
    if convo_brief:
        user_content_parts.append(
            "Recent widget conversations (most recent first):\n"
            + json.dumps(convo_brief, default=str)
        )
    user_content = "\n\n".join(user_content_parts)

    body: str
    try:
        response = await call_claude_messages(
            operation="os_worker_booking",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            metadata={"client_id": ctx.client_id},
        )
        body = response.text.strip()
        ctx.step("Draft prepared", "Booking reply ready for owner review.")
    except Exception:
        logger.warning(
            "os_worker_booking: Claude call failed for client_id=%s run_id=%s — using fallback",
            ctx.client_id,
            ctx.run_id,
            exc_info=True,
        )
        body = (
            f"# {title}\n\n"
            f"Draft prepared in response to:\n\n> {ctx.user_message}\n\n"
            "Review and edit this message in the side panel, "
            "then approve or reject it before sending."
        )
        ctx.step(
            "Draft prepared (fallback)",
            "Claude unavailable — deterministic draft used.",
        )

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f'Booking draft ready: "{title}". '
            "Review it in the side panel, then approve or reject."
        ),
        action_type="calendar.event.create",
    )


SPEC = WorkerSpec(name="booking", description=_DESCRIPTION, run=_run)
