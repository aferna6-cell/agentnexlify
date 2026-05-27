"""Agent OS worker: generalist — general-purpose written drafts.

The orchestrator's catch-all worker. Produces a markdown draft for any general
business task that yields reviewable text: documents, summaries, plans,
outreach copy. Deterministic so it always works as the fallback even when the
LLM is unavailable — the Claude-backed specialists (customer_question, booking,
lead_nurture, campaign) handle their own domains.
"""

from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

_DESCRIPTION = (
    "General business tasks that produce a written draft: documents, "
    "summaries, plans, outreach copy, or any answer that needs drafting work. "
    "The catch-all worker — route here when no specialist fits but the request "
    "still yields a reviewable text draft."
)


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Draft"
    ctx.step("Draft prepared", "Deliverable ready for review.")
    body = (
        f"# {title}\n\n"
        f"Draft prepared in response to:\n\n> {ctx.user_message}\n\n"
        "Review and edit it in the side panel, then approve or reject."
    )
    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Draft ready: {title}. "
            "Review it in the side panel, then approve or reject."
        ),
    )


SPEC = WorkerSpec(name="generalist", description=_DESCRIPTION, run=_run)
