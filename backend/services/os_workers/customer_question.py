"""Agent OS worker: customer_question — AI-drafted answer to a customer question.

The orchestrator routes here when a small-business owner needs a written reply
to a question a customer has asked about the business (hours, services, pricing,
policies, etc.). Grounds the answer in the tenant's widget knowledge base +
business profile + orchestrator memory via ``ctx.tools`` — read-only, tenant-
scoped. No outbound side effects beyond ``ctx.step`` progress.
"""

import json
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
    "You are a professional business communication assistant helping a "
    "small-business owner draft a reply to a customer question. Write a clear, "
    "friendly, and accurate answer that the owner can review and then send "
    "directly to the customer.\n\n"
    "Ground every factual claim (hours, services, pricing, policies) in the "
    "Knowledge base or Business profile supplied below. If the answer is not "
    "covered there, write a polite placeholder the owner can fill in — never "
    "invent specifics.\n\n"
    "Output only the answer body in markdown — no preamble such as 'Here is "
    "your draft', no sign-off, no subject line."
)


_PROFILE_KEYS = (
    "business_name",
    "business_type",
    "timezone",
    "business_hours",
    "services_offered",
    "owner_name",
)

_KB_CHAR_BUDGET = 6000
_MEMORY_HITS = 4


def _profile_brief(profile: dict) -> dict:
    return {key: profile.get(key) for key in _PROFILE_KEYS if profile.get(key)}


def _truncate(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    return text[:budget] + "\n…[truncated]"


def _memory_brief(hits: list[dict]) -> list[dict]:
    brief: list[dict] = []
    for hit in hits[:_MEMORY_HITS]:
        brief.append(
            {
                "summary": hit.get("summary"),
                "content": hit.get("content"),
                "kind": hit.get("kind"),
            }
        )
    return brief


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Customer Answer"

    ctx.step(
        "Analyzing the question",
        f"Preparing a draft answer for: {ctx.user_message[:120]}",
    )

    kb_text = ""
    profile: dict = {}
    memory_hits: list[dict] = []
    if ctx.tools is not None:
        ctx.step("Loading knowledge base", "Widget KB + business profile.")
        profile = await ctx.tools.tenant_profile()
        kb_text = str(profile.get("knowledge_base") or "")
        ctx.step("Searching memory", "Durable facts relevant to the question.")
        memory_hits = await ctx.tools.search_memory(
            ctx.user_message, match_count=_MEMORY_HITS
        )

    profile_brief = _profile_brief(profile)
    memory_brief = _memory_brief(memory_hits)
    kb_trimmed = _truncate(kb_text, _KB_CHAR_BUDGET) if kb_text else ""

    user_content_parts = [f"Customer question / owner request:\n{ctx.user_message}"]
    if profile_brief:
        user_content_parts.append(
            "Business profile:\n" + json.dumps(profile_brief, default=str)
        )
    if kb_trimmed:
        user_content_parts.append("Knowledge base:\n" + kb_trimmed)
    if memory_brief:
        user_content_parts.append(
            "Relevant memory:\n" + json.dumps(memory_brief, default=str)
        )
    user_content = "\n\n".join(user_content_parts)

    body: str
    try:
        result = await call_claude_messages(
            operation="os_worker_customer_question",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
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
