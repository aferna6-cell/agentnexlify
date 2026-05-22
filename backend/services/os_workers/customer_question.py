"""Agent OS worker: customer_question — AI-drafted answer to a customer question.

The orchestrator routes here when a small-business owner needs a written reply
to a question a customer has asked about the business (hours, services, pricing,
policies, etc.). This worker calls Claude to produce a clear, friendly answer
draft that the owner can review and then send.  No database queries are made;
the only side effect is ctx.step() calls (which persist thought progress).
"""

import logging

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Route here when a customer has asked a question that the business owner "
    "needs a written answer for — questions about hours, services, pricing, "
    "policies, products, or anything the business would reply to in writing. "
    "Produces a reviewable draft answer ready to copy-and-send."
)

_SYSTEM_PROMPT = (
    "You are a professional business communication assistant helping a small-business "
    "owner draft a reply to a customer question. Write a clear, friendly, and accurate "
    "answer that the owner can review and then send directly to the customer. "
    "Output only the answer body in markdown — no preamble such as 'Here is your draft', "
    "no sign-off, no subject line. If the question cannot be answered from the context "
    "provided, write a polite placeholder that the owner can fill in with real details."
)


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Customer Answer"

    ctx.step(
        "Analyzing the question",
        f"Preparing a draft answer for: {ctx.user_message[:120]}",
    )

    body: str
    try:
        result = await call_claude_messages(
            operation="os_worker_customer_question",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ctx.user_message}],
            metadata={"client_id": ctx.client_id},
        )
        body = result.text.strip()
        ctx.step("Draft prepared", "Claude draft ready for owner review.")
    except Exception:
        logger.warning(
            "customer_question worker: Claude call failed for client_id=%s run_id=%s",
            ctx.client_id,
            ctx.run_id,
            exc_info=True,
        )
        body = (
            f"# {title}\n\n"
            f"Draft answer prepared in response to:\n\n> {ctx.user_message}\n\n"
            "Review and edit the answer in the side panel, then approve or reject."
        )
        ctx.step("Draft prepared (fallback)", "Deterministic fallback draft ready.")

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Answer draft ready: “{title}”. "
            "Review it in the side panel, then approve or reject."
        ),
    )


SPEC = WorkerSpec(name="customer_question", description=_DESCRIPTION, run=_run)
