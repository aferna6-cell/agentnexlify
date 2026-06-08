"""Agent OS worker: research — web-grounded topic research + outreach draft.

The orchestrator routes here when a small-business owner wants the agent to
research a topic on the web (a competitor, a trend, a prospect's company, a
local market question) and then draft outreach off the findings. Uses
Anthropic's server-side ``web_search`` tool (runs on Anthropic infra with the
platform's existing API key — no external search credentials) and grounds the
outreach draft in the tenant's business profile via ``ctx.tools``.

Output is one approval-gated markdown deliverable with two sections: a research
summary and a ready-to-review outreach draft. ``action_type`` defaults to
``email.send`` so approval fires the email connector; the owner can route to
SMS or CRM by saying so.
"""

import json
import logging
import re

from backend.services.llm_runtime import call_claude_messages
from backend.services.os_workers.base import WorkerContext, WorkerResult, WorkerSpec

logger = logging.getLogger(__name__)

# Anthropic server-side web search. The `_20260209` version auto-enables
# dynamic filtering and needs no beta header. Runs on Anthropic's
# infrastructure using the platform's existing API key.
_WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

# Web research + a drafted outreach message needs more room than a single
# follow-up note, and the server-side search loop can run for a while.
_MAX_TOKENS = 2500
_TIMEOUT_SECONDS = 120.0

# Channel routing — mirrors lead_nurture. Email is the default outreach
# channel: safest (no SMS opt-in regulation), least intrusive. Explicit email
# wins over sms/crm so "research X and email them" routes to email.send.
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
    """Pick the Group B action handler for the outreach draft.

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
    "Researches a topic on the web — a competitor, an industry trend, a "
    "prospect's company, a local market question — then drafts outreach off the "
    "findings. Route here when the owner wants current information looked up "
    "online and turned into a message, brief, or talking points. Has live web "
    "access; prefer this over other workers whenever the request needs facts "
    "the business does not already hold."
)

_SYSTEM_PROMPT = (
    "You are a research assistant for a small-business owner. Use the web_search "
    "tool to gather current, accurate information on the topic in the owner's "
    "request, then turn it into something the owner can act on.\n\n"
    "Produce exactly two markdown sections:\n"
    "## Research summary\n"
    "The key findings as tight bullets — the facts that matter for the owner's "
    "goal. Add a source name or URL inline next to any specific claim (a number, "
    "date, name, or quote) so the owner can verify it.\n"
    "## Outreach draft\n"
    "A ready-to-send message built on those findings and tailored to the "
    "business profile supplied below. Keep it warm and specific; give a clear, "
    "low-pressure next step.\n\n"
    "Ground specific claims in search results. When a fact is not found, say so "
    "in the summary and leave a bracketed placeholder in the draft for the owner "
    "to fill in. Output only the two sections in markdown — open directly with "
    "the `## Research summary` heading."
)


_PROFILE_KEYS = (
    "business_name",
    "business_type",
    "services_offered",
    "owner_name",
)


def _profile_brief(profile: dict) -> dict:
    return {key: profile.get(key) for key in _PROFILE_KEYS if profile.get(key)}


async def _run(ctx: WorkerContext) -> WorkerResult:
    title = ctx.deliverable_title or "Research Brief"

    ctx.step(
        "Scoping the research",
        f"Preparing to research: {ctx.user_message[:120]}",
    )

    profile: dict = {}
    if ctx.tools is not None:
        ctx.step("Loading business profile", "For tailoring the outreach draft.")
        profile = await ctx.tools.tenant_profile()

    profile_brief = _profile_brief(profile)

    user_content_parts = [f"Owner request:\n{ctx.user_message}"]
    if profile_brief:
        user_content_parts.append(
            "Business profile:\n" + json.dumps(profile_brief, default=str)
        )
    user_content = "\n\n".join(user_content_parts)

    body: str
    try:
        ctx.step("Searching the web", "Gathering current information on the topic.")
        result = await call_claude_messages(
            operation="os_worker_research",
            model="claude-sonnet-4-6",
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            tools=[_WEB_SEARCH_TOOL],
            timeout=_TIMEOUT_SECONDS,
            metadata={"client_id": ctx.client_id},
        )
        body = result.text.strip()
        ctx.step(
            "Draft prepared", "Research summary + outreach draft ready for review."
        )
    except Exception:
        logger.warning(
            "research worker: Claude call failed for client_id=%s run_id=%s — "
            "using deterministic fallback",
            ctx.client_id,
            ctx.run_id,
            exc_info=True,
        )
        body = (
            f"# {title}\n\n"
            "Web research was unavailable, so this is a placeholder to edit.\n\n"
            f"Research request:\n\n> {ctx.user_message}\n\n"
            "## Research summary\n\n"
            "_Add findings here, or re-run when web access is restored._\n\n"
            "## Outreach draft\n\n"
            "_Draft the outreach message here, then approve or reject._"
        )
        ctx.step(
            "Draft prepared (fallback)",
            "Research draft ready — web access unavailable, edit before sending.",
        )

    action_type = _choose_action_type(ctx.user_message)

    return WorkerResult(
        deliverable={"title": title, "format": "markdown", "body": body},
        summary=(
            f"Your research brief '{title}' — summary plus an outreach draft — is "
            "ready for review in the side panel. Edit as needed, then approve to send."
        ),
        action_type=action_type,
    )


SPEC = WorkerSpec(name="research", description=_DESCRIPTION, run=_run)
