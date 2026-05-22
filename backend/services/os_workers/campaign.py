"""Agent OS worker: campaign — AI-drafted marketing campaign copy.

The orchestrator routes here when a small-business owner wants a marketing
campaign, promotion, announcement, or seasonal offer drafted.  This worker
calls Claude to produce a reviewable campaign draft (email and/or social copy)
that the owner can review then publish.  No database queries are made and no
messages are sent — draft-only; the only DB side effect is ctx.step() calls
(which persist thought progress via the base WorkerContext).
"""

import logging

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Route here when the owner wants to create a marketing campaign, promotion, "
    "announcement, or seasonal offer — any request to draft promotional copy, an "
    "email blast, or a social-media post for a sale, event, or special offer. "
    "Produces a reviewable campaign draft the owner can edit then publish."
)

_SYSTEM_PROMPT = (
    "You are a professional marketing copywriter helping a small-business owner "
    "draft a marketing campaign. Based on the owner's request, write a campaign "
    "draft that includes:\n"
    "- A subject line or headline (bold, first line)\n"
    "- The main promotional body with a clear call to action\n"
    "- A short social-post variant (1–3 sentences) when it adds value\n\n"
    "Write the full draft in markdown. Do not add a preamble such as "
    "'Here is your draft' or 'I've written'. Output only the campaign body "
    "so the owner can paste it directly into their email or social tools."
)


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Campaign Draft"

    ctx.step(
        "Planning the campaign",
        f"Drafting campaign copy for: {ctx.user_message[:120]}",
    )

    body: str
    try:
        result = await call_claude_messages(
            operation="os_worker_campaign",
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ctx.user_message}],
            metadata={"client_id": ctx.client_id},
        )
        body = result.text.strip()
        ctx.step("Draft prepared", "Campaign draft ready for owner review.")
    except Exception:
        logger.warning(
            "campaign worker: Claude call failed for client_id=%s run_id=%s",
            ctx.client_id,
            ctx.run_id,
            exc_info=True,
        )
        body = (
            f"# {title}\n\n"
            f"Campaign draft prepared in response to:\n\n> {ctx.user_message}\n\n"
            "Review and edit the campaign copy in the side panel, then approve or reject."
        )
        ctx.step("Draft prepared (fallback)", "Deterministic fallback draft ready.")

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Campaign draft ready: “{title}”. "
            "Review it in the side panel, then approve or reject."
        ),
    )


SPEC = WorkerSpec(name="campaign", description=_DESCRIPTION, run=_run)
