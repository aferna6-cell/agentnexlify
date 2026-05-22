"""Agent OS worker: lead_nurture — AI-backed lead follow-up draft.

Turns a small-business owner's request into an approval-gated draft follow-up
message (or short sequence) to re-engage a prospect who has not converted.
Produces reviewable text only — no email sending, no database reads beyond the
progress steps already handled by WorkerContext.step().
"""

import logging

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Drafts a warm, low-pressure follow-up message or short 2-3 touch follow-up "
    "sequence to re-engage a prospect who has not yet converted. Route here when "
    "the owner wants to follow up with or re-engage a lead who hasn't responded, "
    "booked, or moved forward."
)

_SYSTEM_PROMPT = (
    "You are a follow-up copywriter for a small-business owner. "
    "Write a warm, low-pressure follow-up message — or a short 2-3 touch sequence "
    "when the request implies multiple touchpoints — to re-engage a prospect who "
    "has not yet converted.\n\n"
    "Guidelines:\n"
    "- Reference the prospect's earlier interest so the message feels personal.\n"
    "- Give a clear, gentle next step (e.g. book a call, reply to this message).\n"
    "- Keep the tone helpful and conversational, never pushy or salesy.\n"
    "- For a sequence, label each touch (e.g. Touch 1 — Day 1, Touch 2 — Day 3).\n"
    "- Output the message body in markdown.\n"
    "- Do not include a preamble or meta-commentary such as 'Here is your draft'.\n"
    "- Do not include a subject line unless the owner asked for one."
)


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Lead Follow-Up"

    ctx.step("Reviewing the lead", "Preparing a personalised follow-up draft.")

    body: str
    try:
        result = await call_claude_messages(
            operation="os_worker_lead_nurture",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ctx.user_message}],
            metadata={"client_id": ctx.client_id},
        )
        body = result.text.strip()
        ctx.step("Draft prepared", "Follow-up draft is ready for review.")
    except Exception:
        logger.warning(
            "lead_nurture worker: Claude call failed for client_id=%s run_id=%s — "
            "using deterministic fallback",
            ctx.client_id,
            ctx.run_id,
            exc_info=True,
        )
        body = (
            f"# {title}\n\n"
            f"Draft prepared in response to:\n\n> {ctx.user_message}\n\n"
            "Review and personalise the message below, then approve or reject."
        )
        ctx.step(
            "Draft prepared (fallback)",
            "Follow-up draft ready — Claude unavailable, edit before sending.",
        )

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Your follow-up draft '{title}' is ready for review in the side panel. "
            "Edit as needed, then approve to use it."
        ),
    )


SPEC = WorkerSpec(name="lead_nurture", description=_DESCRIPTION, run=_run)
