"""Agent OS worker: booking — appointment booking draft messages.

Turns a small-business owner's request into an approval-gated draft reply that
the owner can review and then send to a customer who wants to book, reschedule,
or cancel an appointment, or needs a booking confirmation/summary. Draft-only:
no calendar integration, no database queries beyond ``ctx.step`` progress
tracking.
"""

import logging

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

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

If the request is incomplete (missing preferred date/time or service type), include \
a polite question asking for the missing detail.

Output only the message body in markdown. Do not include a preamble, subject line, \
or any phrase like "here is your draft" — start directly with the message content.\
"""


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Booking Reply"

    ctx.step(
        "Reviewing the booking request",
        f"Preparing a draft reply for: {ctx.user_message[:120]}",
    )

    body: str
    try:
        response = await call_claude_messages(
            operation="os_worker_booking",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ctx.user_message}],
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
    )


SPEC = WorkerSpec(name="booking", description=_DESCRIPTION, run=_run)
