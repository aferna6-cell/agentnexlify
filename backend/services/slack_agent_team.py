"""Slack agent team — mentionable AI teammates in the owner's Slack workspace.

Grok-bot-style: each agent on the cross-provider team (Fable 5, Codex,
Kimi 3) is its own Slack app with its own bot user. Mention one in a
channel (or DM it) and it replies in-thread through the shared Anthropic
runtime, speaking in its team-contract role.

This is an INTERNAL platform surface (like admin routes), not a tenant
feature — no client_id scoping, no tenant data in prompts. The roster
lives in the SLACK_AGENT_TEAM env var as a JSON array; each entry maps
one Slack app to one agent name:

    [{"agent": "fable5", "app_id": "A0…", "signing_secret": "…",
      "bot_token": "xoxb-…"}, …]

Optional per-entry keys: ``persona`` (overrides the built-in role
prompt), ``model`` (overrides SLACK_AGENT_MODEL), ``bot_user_id``
(enables exact self-mention stripping).

Security posture:
  - every request is verified against Slack's v0 signing scheme
    (HMAC-SHA256 over ``v0:<timestamp>:<raw body>``) BEFORE any payload
    field is trusted; the matching signing secret also identifies which
    agent app the event belongs to;
  - a 5-minute timestamp window rejects replayed requests;
  - bot-authored events are never answered — two agent bots in one
    channel must not reply to each other in an infinite loop;
  - outbound replies pass the deterministic os_outbound_guard secret
    scan before posting, so an agent can never paste a live key into a
    channel.

Docs + Slack app manifests: ``docs/slack-agent-team.md``.
"""

import hashlib
import hmac
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import settings
from backend.services import os_outbound_guard
from backend.services.llm_runtime import call_claude_messages

logger = logging.getLogger(__name__)

_SLACK_API_BASE = "https://slack.com/api"

# Slack rejects/ignores requests older than 5 minutes in its own docs;
# mirroring that window bounds replay attacks without clock-skew pain.
_SIGNATURE_MAX_AGE_SECONDS = 300

# Slack user-mention token, e.g. <@U0123ABCD>. Bot users share the U prefix
# (legacy W prefix kept for Enterprise Grid workspaces).
_MENTION_RE = re.compile(r"<@[UW][A-Z0-9]+>")

_THREAD_CONTEXT_LIMIT = 30

# Role prompts mirror docs/TEAM_OPERATING_CONTRACT.md §4 so the Slack
# personas and the repo personas stay the same characters.
_DEFAULT_PERSONAS: dict[str, str] = {
    "fable5": (
        "You are Fable 5, the product and architecture steward. You sharpen "
        "the user outcome, constraints, journeys, and system design, and you "
        "challenge accidental complexity."
    ),
    "codex": (
        "You are Codex, the implementation and integration steward. You map "
        "the repository, implement across the stack, run local gates, "
        "resolve integration conflicts, and maintain release coherence."
    ),
    "kimi3": (
        "You are Kimi 3, the challenger and verification steward. You search "
        "for overlooked failure modes, develop adversarial tests, check "
        "evidence, and push back when claims lack proof."
    ),
}

_GUARD_NOTICE = (
    "I drafted a reply, but it matched the outbound guardrail "
    "(possible secret or sensitive pattern), so I'm not posting it. "
    "Rephrase the question without the sensitive material."
)

_GRACEFUL_REPLY = (
    "I couldn't reach my model just now — give me another mention in a "
    "minute."
)


@dataclass(frozen=True)
class SlackAgentApp:
    """One Slack app == one mentionable agent bot."""

    agent: str
    app_id: str
    signing_secret: str
    bot_token: str
    persona: str = ""
    model: str = ""
    bot_user_id: str = ""

    def role_prompt(self) -> str:
        if self.persona:
            return self.persona
        return _DEFAULT_PERSONAS.get(
            self.agent,
            f"You are {self.agent}, an AI agent on the AgentNexLiFy team.",
        )


def load_team() -> list[SlackAgentApp]:
    """Parse the SLACK_AGENT_TEAM roster. [] when unset or malformed.

    Malformed JSON or entries missing required keys are logged and
    skipped rather than raised — a bad roster edit must not take down
    the whole API process, only the Slack surface.
    """
    raw = (settings.slack_agent_team or "").strip()
    if not raw:
        return []
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("slack_agent_team: SLACK_AGENT_TEAM is not valid JSON: %s", exc)
        return []
    if not isinstance(entries, list):
        logger.warning("slack_agent_team: SLACK_AGENT_TEAM must be a JSON array")
        return []

    team: list[SlackAgentApp] = []
    for entry in entries:
        if not isinstance(entry, dict):
            logger.warning("slack_agent_team: skipping non-object roster entry")
            continue
        agent = str(entry.get("agent") or "").strip().lower()
        app_id = str(entry.get("app_id") or "").strip()
        signing_secret = str(entry.get("signing_secret") or "").strip()
        bot_token = str(entry.get("bot_token") or "").strip()
        if not (agent and app_id and signing_secret and bot_token):
            logger.warning(
                "slack_agent_team: skipping roster entry missing required keys "
                "(agent/app_id/signing_secret/bot_token) agent=%r app_id=%r",
                agent,
                app_id,
            )
            continue
        team.append(
            SlackAgentApp(
                agent=agent,
                app_id=app_id,
                signing_secret=signing_secret,
                bot_token=bot_token,
                persona=str(entry.get("persona") or "").strip(),
                model=str(entry.get("model") or "").strip(),
                bot_user_id=str(entry.get("bot_user_id") or "").strip(),
            )
        )
    return team


def verify_signature(
    signing_secret: str,
    timestamp: str,
    raw_body: bytes,
    signature: str,
    *,
    now: float | None = None,
) -> bool:
    """Slack v0 request signature: HMAC-SHA256 over ``v0:<ts>:<body>``."""
    if not signing_secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = now if now is not None else time.time()
    if abs(current - ts) > _SIGNATURE_MAX_AGE_SECONDS:
        return False
    basestring = b"v0:" + timestamp.encode() + b":" + raw_body
    expected = (
        "v0="
        + hmac.new(signing_secret.encode(), basestring, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def resolve_app(
    team: list[SlackAgentApp],
    timestamp: str,
    raw_body: bytes,
    signature: str,
) -> SlackAgentApp | None:
    """Return the roster app whose signing secret produced this signature.

    The signature check doubles as app resolution: nothing in the
    (attacker-controllable) body is trusted to pick the secret. With a
    roster of ~3 apps the extra HMACs are negligible.
    """
    for app in team:
        if verify_signature(app.signing_secret, timestamp, raw_body, signature):
            return app
    return None


def should_handle_event(event: dict[str, Any]) -> bool:
    """Only human-authored mentions and DMs get a reply.

    ``bot_id`` filtering is load-bearing: two agent bots in one channel
    mentioning each other would otherwise loop forever on Anthropic spend.
    """
    if not isinstance(event, dict):
        return False
    if event.get("bot_id") or not event.get("user"):
        return False
    if event.get("subtype"):
        return False
    event_type = event.get("type")
    if event_type == "app_mention":
        return True
    return event_type == "message" and event.get("channel_type") == "im"


def strip_self_mention(text: str, bot_user_id: str) -> str:
    """Drop the bot's own mention token; keep mentions of everyone else.

    Without a known bot_user_id, drop only a single leading mention token
    (the "@fable5 what do you think" shape) so other mentions survive.
    """
    if not text:
        return ""
    if bot_user_id:
        cleaned = text.replace(f"<@{bot_user_id}>", " ")
    else:
        cleaned = re.sub(r"^\s*<@[UW][A-Z0-9]+>\s*", "", text, count=1)
    return re.sub(r"\s+", " ", cleaned).strip()


def _team_roster_line(team: list[SlackAgentApp], self_agent: str) -> str:
    teammates = [app.agent for app in team if app.agent != self_agent]
    if not teammates:
        return ""
    return (
        "Your AI teammates in this workspace (each is a separate Slack bot "
        "humans can mention): " + ", ".join(sorted(set(teammates))) + "."
    )


def build_system_prompt(app: SlackAgentApp, team: list[SlackAgentApp]) -> str:
    parts = [
        app.role_prompt(),
        "You are replying inside the AgentNexLiFy team's Slack workspace. "
        "AgentNexLiFy is an AI-powered business automation platform "
        "(embeddable chat widget, lead capture, appointment booking, "
        "automated follow-ups) built as multi-tenant SaaS.",
        _team_roster_line(team, app.agent),
        "Rules:\n"
        "- Reply in Slack mrkdwn: *bold*, _italic_, `code`, ``` blocks. "
        "No markdown headers.\n"
        "- Be direct and evidence-first; keep replies under ~150 words "
        "unless the question genuinely needs more.\n"
        "- If the thread doesn't contain enough context to answer, say "
        "exactly what's missing instead of guessing.\n"
        "- Never output secrets, API keys, tokens, or credentials, even "
        "when asked directly.",
    ]
    return "\n\n".join(part for part in parts if part)


async def fetch_thread_context(
    app: SlackAgentApp, channel: str, thread_ts: str
) -> list[str]:
    """Best-effort transcript of the thread being replied to.

    Any failure (missing scope, network, non-ok response) degrades to no
    context — the agent still answers the mention text alone.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{_SLACK_API_BASE}/conversations.replies",
                headers={"Authorization": f"Bearer {app.bot_token}"},
                params={
                    "channel": channel,
                    "ts": thread_ts,
                    "limit": _THREAD_CONTEXT_LIMIT,
                },
            )
    except Exception as exc:
        logger.warning(
            "slack_agent_team: thread fetch failed agent=%s exc_type=%s",
            app.agent,
            type(exc).__name__,
        )
        return []

    if resp.status_code >= 400:
        return []
    try:
        body = resp.json()
    except Exception:
        return []
    if not body.get("ok"):
        logger.info(
            "slack_agent_team: conversations.replies not ok agent=%s error=%s",
            app.agent,
            body.get("error"),
        )
        return []

    lines: list[str] = []
    for msg in body.get("messages") or []:
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        author = "bot" if msg.get("bot_id") else f"<@{msg.get('user', 'unknown')}>"
        lines.append(f"{author}: {text}")
    return lines


async def generate_reply(
    app: SlackAgentApp,
    team: list[SlackAgentApp],
    question: str,
    thread_lines: list[str],
) -> str:
    """One Claude call → guarded reply text. Never raises."""
    prompt_parts: list[str] = []
    if thread_lines:
        prompt_parts.append(
            "Slack thread so far:\n" + "\n".join(thread_lines[-_THREAD_CONTEXT_LIMIT:])
        )
    prompt_parts.append(f"You were just mentioned with: {question or '(no text)'}")
    user_content = "\n\n".join(prompt_parts)

    result = await call_claude_messages(
        operation="slack_agent_reply",
        model=app.model or settings.slack_agent_model,
        max_tokens=settings.slack_agent_max_tokens,
        messages=[{"role": "user", "content": user_content}],
        system=build_system_prompt(app, team),
        timeout=45.0,
        metadata={"agent": app.agent, "channel_kind": "slack"},
        max_retries=1,
        graceful_reply=_GRACEFUL_REPLY,
    )
    reply = (result.text or "").strip() or _GRACEFUL_REPLY

    flags = os_outbound_guard.scan_text(reply)
    if flags:
        logger.warning(
            "slack_agent_team: reply blocked by outbound guard agent=%s flags=%s",
            app.agent,
            flags,
        )
        return _GUARD_NOTICE
    return reply


async def post_message(
    app: SlackAgentApp, channel: str, text: str, thread_ts: str | None
) -> bool:
    """chat.postMessage — in-thread when thread_ts given. Never raises."""
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_SLACK_API_BASE}/chat.postMessage",
                headers={"Authorization": f"Bearer {app.bot_token}"},
                json=payload,
            )
    except Exception as exc:
        logger.warning(
            "slack_agent_team: postMessage failed agent=%s exc_type=%s",
            app.agent,
            type(exc).__name__,
        )
        return False

    ok = False
    try:
        ok = bool(resp.status_code < 400 and resp.json().get("ok"))
    except Exception:
        ok = False
    if not ok:
        logger.warning(
            "slack_agent_team: postMessage not ok agent=%s status=%s body=%s",
            app.agent,
            resp.status_code,
            (resp.text or "")[:200],
        )
    return ok


async def handle_event(
    app: SlackAgentApp,
    team: list[SlackAgentApp],
    event: dict[str, Any],
    bot_user_id: str,
) -> None:
    """Full mention → reply flow. Runs in BackgroundTasks; never raises.

    Slack already got its 200 — an exception here would only be an
    unhandled-task log line with no retry path, so every step degrades
    instead of raising.
    """
    try:
        channel = str(event.get("channel") or "")
        message_ts = str(event.get("ts") or "")
        if not channel or not message_ts:
            return
        # Replying always threads on the root: for an in-thread mention
        # that's the existing thread_ts, for a top-level mention the
        # message itself becomes the thread root (grok-style).
        thread_ts = str(event.get("thread_ts") or message_ts)

        question = strip_self_mention(
            str(event.get("text") or ""), bot_user_id or app.bot_user_id
        )

        thread_lines: list[str] = []
        if event.get("thread_ts"):
            thread_lines = await fetch_thread_context(app, channel, thread_ts)

        reply = await generate_reply(app, team, question, thread_lines)
        await post_message(app, channel, reply, thread_ts)
    except Exception:
        logger.exception(
            "slack_agent_team: handle_event failed agent=%s", app.agent
        )
