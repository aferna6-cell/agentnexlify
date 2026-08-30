"""Slack agent team — thread context, model calls, and persona posting.

One Slack app, several agents. Each reply is posted with ``username`` and
``icon_emoji`` overrides so `Schema Guardian` and `Ops` show up as
distinct teammates in the channel instead of one generic bot. That needs
the ``chat:write.customize`` scope (see ``docs/slack-agent-team.md``).

Design notes worth keeping:

- **Access is workspace-scoped, not public.** Every model call spends
  Anthropic credits, so ``SLACK_TEAM_ID`` is required and events from any
  other workspace are dropped. ``SLACK_ALLOWED_USER_IDS`` narrows further.
- **Thread context is one transcript in a single user message**, not a
  reconstructed multi-turn ``messages`` array. A Slack thread has N
  speakers (human plus several agents), which does not map onto the
  two-role alternation the Messages API expects; flattening keeps the
  mapping honest and the code simple.
- **Nothing raises.** Handlers run in ``BackgroundTasks`` after the
  webhook already returned 200, so an exception has nowhere to go. Every
  failure is logged and, where the user is waiting, posted in-thread.
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

from backend.config import settings
from backend.services import slack_agent_roster as roster_mod
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)
from backend.services.slack_agent_roster import SlackAgent, SlackCommand

logger = logging.getLogger(__name__)

_SLACK_API = "https://slack.com/api"
_HTTP_TIMEOUT = 10.0

# Per-message truncation for thread context. A single pasted stack trace
# should not evict the rest of the conversation.
_HISTORY_MESSAGE_CHARS = 700
_HISTORY_TOTAL_CHARS = 6000
_QUESTION_CHARS = 4000

_FAILURE_NOTICE = (
    "I couldn't reach the model just now. Try again in a moment — if it keeps "
    "failing, check the backend logs for `llm.call.error`."
)


@dataclass(frozen=True)
class ThreadMessage:
    """One prior Slack message, normalized for prompt building."""

    speaker: str
    text: str
    is_agent: bool


def is_configured() -> bool:
    """True when the Slack agent team can actually run.

    All three are required on purpose: the signing secret authenticates
    Slack, the bot token lets us reply, and the team id bounds who can
    spend model credits. A partial configuration is treated as "off"
    rather than "open".
    """
    return bool(
        settings.slack_signing_secret
        and settings.slack_bot_token
        and settings.slack_team_id
    )


def is_allowed_user(user_id: str) -> bool:
    """Honor the optional per-user allow-list. Empty list = whole workspace."""
    raw = (settings.slack_allowed_user_ids or "").strip()
    if not raw:
        return True
    allowed = {part.strip() for part in raw.split(",") if part.strip()}
    return user_id in allowed


# ---------------------------------------------------------------------------
# Slack Web API
# ---------------------------------------------------------------------------


async def _slack_call(method: str, payload: dict) -> dict:
    """POST to a Slack Web API method. Returns the parsed body, never raises.

    Slack reports application errors as HTTP 200 with ``ok: false``, so the
    caller must check ``ok`` — an HTTP-status-only check would silently
    swallow ``invalid_auth`` and ``missing_scope``.
    """
    headers = {"Authorization": f"Bearer {settings.slack_bot_token}"}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                f"{_SLACK_API}/{method}", headers=headers, json=payload
            )
    except httpx.HTTPError as exc:
        # No exc_info: httpx exception frames can carry the bound request,
        # and the request carries the bot token in its headers.
        logger.warning(
            "slack_agent_team: %s HTTP error exc_type=%s", method, type(exc).__name__
        )
        return {"ok": False, "error": f"http_error:{type(exc).__name__}"}

    try:
        body = resp.json() if resp.content else {}
    except ValueError:
        # Non-JSON body (proxy error page). Falls through to the ok:false
        # branch below so the caller sees a failure, not a silent success.
        body = {}

    if not body.get("ok"):
        logger.warning(
            "slack_agent_team: %s failed status=%s error=%s",
            method,
            resp.status_code,
            body.get("error", "unknown"),
        )
    return body


async def post_as_agent(
    *,
    channel: str,
    text: str,
    agent: SlackAgent | None = None,
    thread_ts: str | None = None,
) -> dict:
    """Post ``text`` to ``channel``, wearing ``agent``'s name and icon."""
    payload: dict = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if agent:
        payload["username"] = agent.display_name
        payload["icon_emoji"] = agent.emoji
    return await _slack_call("chat.postMessage", payload)


async def fetch_thread(
    *, channel: str, thread_ts: str, exclude_ts: str | None = None
) -> list[ThreadMessage]:
    """Return prior messages in a thread, oldest first, newest-capped.

    ``exclude_ts`` drops the triggering message so it is not both context
    and question. Returns ``[]`` on any Slack error — losing context
    degrades the answer, but failing the whole reply is worse.
    """
    limit = resolve_int_setting("slack_agents_history_messages", 12, minimum=1)
    body = await _slack_call(
        "conversations.replies",
        {"channel": channel, "ts": thread_ts, "limit": limit + 1},
    )
    if not body.get("ok"):
        return []

    out: list[ThreadMessage] = []
    for raw in body.get("messages") or []:
        ts = raw.get("ts")
        if exclude_ts and ts == exclude_ts:
            continue
        text = roster_mod.strip_mentions(raw.get("text") or "")
        if not text:
            continue
        is_agent = bool(raw.get("bot_id"))
        speaker = raw.get("username") or ("Agent" if is_agent else "Founder")
        out.append(
            ThreadMessage(
                speaker=speaker,
                text=text[:_HISTORY_MESSAGE_CHARS],
                is_agent=is_agent,
            )
        )
    return out[-limit:]


def last_agent_in_thread(history: list[ThreadMessage]) -> str | None:
    """Key of the agent that spoke last, for thread continuation.

    Mirrors how people use a thread: once `Ops` is answering, a follow-up
    without a named agent should stay with `Ops` rather than be re-routed
    on the follow-up's wording ("and the second one?" routes nowhere).
    """
    for message in reversed(history):
        if not message.is_agent:
            continue
        agent = roster_mod.resolve_label(message.speaker)
        if agent:
            return agent.key
    return None


# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------


def build_prompt(question: str, history: list[ThreadMessage]) -> str:
    """Flatten thread context plus the question into one user turn."""
    question = (question or "").strip()[:_QUESTION_CHARS]
    if not history:
        return question

    lines: list[str] = []
    total = 0
    for message in reversed(history):
        line = f"{message.speaker}: {message.text}"
        total += len(line)
        if total > _HISTORY_TOTAL_CHARS:
            break
        lines.append(line)
    lines.reverse()

    return (
        "Earlier in this Slack thread:\n"
        + "\n".join(lines)
        + f"\n\nThe founder now asks:\n{question}"
    )


async def answer(
    *,
    agent: SlackAgent,
    question: str,
    history: list[ThreadMessage],
) -> str:
    """Ask one agent for its reply. Returns a user-facing failure line on error."""
    result = await call_claude_messages(
        operation=f"slack_agent.{agent.key}",
        model=resolve_string_setting("slack_agents_model", "claude-sonnet-5"),
        max_tokens=resolve_int_setting("slack_agents_max_tokens", 700, minimum=64),
        system=agent.system_prompt(),
        messages=[{"role": "user", "content": build_prompt(question, history)}],
        temperature=0.3,
        timeout=45.0,
        max_retries=1,
        cache_system=True,
        graceful_reply=_FAILURE_NOTICE,
        metadata={"agent": agent.key},
    )
    return (result.text or "").strip() or _FAILURE_NOTICE


async def synthesize(
    *,
    question: str,
    answers: list[tuple[SlackAgent, str]],
) -> str:
    """Chief-of-staff synthesis of a `team:` fan-out."""
    chief = roster_mod.get_agent(roster_mod.DEFAULT_AGENT_KEY)
    if chief is None or not answers:
        return ""

    transcript = "\n\n".join(
        f"{agent.display_name}: {text}" for agent, text in answers
    )
    prompt = (
        f"The founder asked the team:\n{question}\n\n"
        f"Your teammates answered:\n\n{transcript}\n\n"
        "Write the decision. Start with the single recommended action, then "
        "note any real disagreement between teammates and which side you take. "
        "Do not summarize each answer in turn and do not repeat their detail."
    )
    result = await call_claude_messages(
        operation="slack_agent.synthesis",
        model=resolve_string_setting("slack_agents_model", "claude-sonnet-5"),
        max_tokens=resolve_int_setting("slack_agents_max_tokens", 700, minimum=64),
        system=chief.system_prompt(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=45.0,
        cache_system=True,
        graceful_reply="",
        metadata={"agent": "synthesis"},
    )
    return (result.text or "").strip()


# ---------------------------------------------------------------------------
# Event handling
# ---------------------------------------------------------------------------


async def handle_message(
    *,
    channel: str,
    text: str,
    thread_ts: str | None,
    message_ts: str,
) -> None:
    """Full round-trip for one inbound Slack message.

    Replies always thread: on ``thread_ts`` when the message was already in
    a thread, otherwise off ``message_ts`` so the answer starts a thread
    instead of flooding the channel.
    """
    reply_ts = thread_ts or message_ts
    command = roster_mod.parse_command(text)

    if command.kind == "help":
        await post_as_agent(
            channel=channel,
            text=roster_mod.help_text(),
            agent=roster_mod.get_agent(roster_mod.DEFAULT_AGENT_KEY),
            thread_ts=reply_ts,
        )
        return

    history = (
        await fetch_thread(channel=channel, thread_ts=thread_ts, exclude_ts=message_ts)
        if thread_ts
        else []
    )

    if command.kind == "team":
        await _handle_team(
            channel=channel,
            reply_ts=reply_ts,
            command=command,
            history=history,
        )
        return

    agent_key = command.agent_keys[0]
    if not command.explicit:
        agent_key = last_agent_in_thread(history) or agent_key

    agent = roster_mod.get_agent(agent_key)
    if agent is None:
        logger.error("slack_agent_team: unknown agent key %r", agent_key)
        return

    reply = await answer(agent=agent, question=command.question, history=history)
    await post_as_agent(
        channel=channel, text=reply, agent=agent, thread_ts=reply_ts
    )


async def _handle_team(
    *,
    channel: str,
    reply_ts: str,
    command: SlackCommand,
    history: list[ThreadMessage],
) -> None:
    """Fan out to several agents in parallel, then post the chief's call."""
    agents = [
        a for a in (roster_mod.get_agent(k) for k in command.agent_keys) if a
    ]
    if not agents:
        return

    replies = await asyncio.gather(
        *(
            answer(agent=agent, question=command.question, history=history)
            for agent in agents
        )
    )

    answered: list[tuple[SlackAgent, str]] = []
    for agent, reply in zip(agents, replies):
        await post_as_agent(
            channel=channel, text=reply, agent=agent, thread_ts=reply_ts
        )
        if reply != _FAILURE_NOTICE:
            answered.append((agent, reply))

    if len(answered) < 2:
        # One surviving answer needs no synthesis — the chief would just
        # restate it under a different name.
        return

    verdict = await synthesize(question=command.question, answers=answered)
    if verdict:
        await post_as_agent(
            channel=channel,
            text=verdict,
            agent=roster_mod.get_agent(roster_mod.DEFAULT_AGENT_KEY),
            thread_ts=reply_ts,
        )
