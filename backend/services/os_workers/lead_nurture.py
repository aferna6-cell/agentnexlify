"""Agent OS worker: lead_nurture — AI-backed lead follow-up draft.

Turns a small-business owner's request into an approval-gated draft follow-up
message (or short sequence) to re-engage a prospect who has not converted.
Grounds the draft in real lead data via ``ctx.tools`` — stale leads + tenant
profile, read-only, tenant-scoped.
"""

import json
import logging
import re

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

logger = logging.getLogger(__name__)

# Channel routing — owner request picks which Group B handler fires on approve.
# Email is the default: it's the workflow this worker's prompt was tuned for
# and the safest channel (no SMS opt-in regulation, less intrusive than CRM
# auto-upsert). Explicit email beats other directives so "email Jane and text
# her" still routes to email.send.
_EMAIL_RE = re.compile(r"\b(email|e-mail)\b", re.IGNORECASE)
_SMS_RE = re.compile(
    r"\b(sms|text\s+(this|the|them|him|her|that)|via\s+text|send\s+a\s+text)\b",
    re.IGNORECASE,
)
_CRM_RE = re.compile(
    r"\b(crm|log\s+(a\s+)?note|add\s+(a\s+)?note|leave\s+(a\s+)?note)\b",
    re.IGNORECASE,
)


def _choose_action_type(user_message: str) -> str:
    """Pick the Group B action handler for this follow-up draft.

    Defaults to ``email.send``. Owner directives override: explicit email wins
    over sms/crm; otherwise sms wins over crm; otherwise crm wins over the
    default.
    """
    msg = user_message or ""
    if _EMAIL_RE.search(msg):
        return "email.send"
    if _SMS_RE.search(msg):
        return "sms.send"
    if _CRM_RE.search(msg):
        return "crm.contact_upsert"
    return "email.send"


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
    "- When stale-lead data is included, prefer leads with `areas_of_interest` "
    "and `conversation_summary` set; ignore leads with status 'closed' or "
    "'unsubscribed'.\n"
    "- Output the message body in markdown.\n"
    "- Do not include a preamble or meta-commentary such as 'Here is your draft'.\n"
    "- Do not include a subject line unless the owner asked for one."
)


_LEAD_BRIEF_KEYS = (
    "id",
    "name",
    "email",
    "phone",
    "status",
    "source",
    "areas_of_interest",
    "conversation_summary",
    "updated_at",
)

_PROFILE_KEYS = (
    "business_name",
    "business_type",
    "services_offered",
    "owner_name",
)


def _lead_brief(leads: list[dict]) -> list[dict]:
    return [
        {key: lead.get(key) for key in _LEAD_BRIEF_KEYS if lead.get(key) is not None}
        for lead in leads[:10]
    ]


def _profile_brief(profile: dict) -> dict:
    return {key: profile.get(key) for key in _PROFILE_KEYS if profile.get(key)}


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Lead Follow-Up"

    ctx.step("Reviewing the lead", "Preparing a personalised follow-up draft.")

    stale: list[dict] = []
    profile: dict = {}
    if ctx.tools is not None:
        ctx.step(
            "Loading stale leads",
            "Pulling leads with no touch in the last 14 days.",
        )
        stale = await ctx.tools.stale_leads(days_since_last_touch=14, limit=10)
        ctx.step("Loading business profile", "For voice and offering context.")
        profile = await ctx.tools.tenant_profile()

    lead_brief = _lead_brief(stale)
    profile_brief = _profile_brief(profile)

    user_content_parts = [f"Owner request:\n{ctx.user_message}"]
    if profile_brief:
        user_content_parts.append(
            "Business profile:\n" + json.dumps(profile_brief, default=str)
        )
    if lead_brief:
        user_content_parts.append(
            "Stale leads (oldest touch first):\n" + json.dumps(lead_brief, default=str)
        )
    user_content = "\n\n".join(user_content_parts)

    body: str
    try:
        result = await call_claude_messages(
            operation="os_worker_lead_nurture",
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
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

    action_type = _choose_action_type(ctx.user_message)

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Your follow-up draft '{title}' is ready for review in the side panel. "
            "Edit as needed, then approve to use it."
        ),
        action_type=action_type,
    )


SPEC = WorkerSpec(name="lead_nurture", description=_DESCRIPTION, run=_run)
