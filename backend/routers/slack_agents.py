"""Slack Events API endpoint for the internal agent team.

One public endpoint, ``POST /api/v1/slack/events``, backing a Slack app
whose bot answers ``@mention``s in channels and plain messages in DMs as
a roster of personas (``backend/services/slack_agent_roster.py``).

This is an operator surface, not a tenant feature: there is no tenant JWT,
no ``client_id``, and it touches no tenant data. What stands in for auth:

  1. Slack request-signature verification over the RAW body
     (``slack_verify``) — done before anything in the payload is read.
  2. ``SLACK_TEAM_ID`` allow-list — events from any other workspace are
     dropped, because every accepted event spends Anthropic credits.
  3. Optional ``SLACK_ALLOWED_USER_IDS`` allow-list for single-operator
     workspaces with guests.

Slack retries any event it does not see acked within 3 seconds, so the
model work runs in ``BackgroundTasks`` and ``event_id`` is recorded in the
shared idempotency store to make a retry a no-op.

Setup: ``docs/slack-agent-team.md``. App manifest:
``ops/slack/agent-team-manifest.json``.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services import idempotency, slack_agent_team
from backend.services.slack_verify import verify_slack_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/slack", tags=["slack-agents"])

# Event types we act on. `app_mention` covers channels; `message` is only
# honored for DMs (`channel_type == "im"`) so the bot never reads channel
# traffic it was not addressed in.
_MENTION_EVENT = "app_mention"
_MESSAGE_EVENT = "message"


@router.post("/events")
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Receive one Slack Events API delivery.

    Order is load-bearing: verify the signature against the raw body
    BEFORE parsing or branching on any payload field, so a forged payload
    cannot influence which workspace or user we believe sent it.
    """
    if not slack_agent_team.is_configured():
        # 503 rather than 404: the route exists, the app is not set up.
        # Surfaces as a clear failure in Slack's event-delivery log
        # instead of a silent drop.
        raise HTTPException(status_code=503, detail="Slack agent team not configured")

    raw_body = await request.body()
    if not verify_slack_signature(
        raw_body=raw_body,
        timestamp=request.headers.get("X-Slack-Request-Timestamp", ""),
        signature=request.headers.get("X-Slack-Signature", ""),
        signing_secret=settings.slack_signing_secret,
    ):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    payload_type = payload.get("type")

    # Slack posts this once when the Request URL is saved in the app config.
    if payload_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    if payload_type != "event_callback":
        return {"ok": True, "ignored": payload_type or "unknown"}

    if payload.get("team_id") != settings.slack_team_id:
        logger.warning(
            "slack_events: rejected event from team_id=%s", payload.get("team_id")
        )
        raise HTTPException(status_code=403, detail="Workspace not allowed")

    event = payload.get("event") or {}
    reason = _skip_reason(event)
    if reason:
        return {"ok": True, "skipped": reason}

    event_id = payload.get("event_id") or ""
    if event_id:
        is_new, _cached = await idempotency.check_and_record(
            get_service_supabase(), "slack", event_id
        )
        if not is_new:
            return {"ok": True, "skipped": "duplicate"}

    background_tasks.add_task(
        _handle_safe,
        channel=event.get("channel", ""),
        text=event.get("text", ""),
        thread_ts=event.get("thread_ts"),
        message_ts=event.get("ts", ""),
    )
    return {"ok": True}


def _skip_reason(event: dict[str, Any]) -> str | None:
    """Why this event needs no reply, or None when it should be handled.

    Dropping our own posts is what stops an infinite loop: the bot's reply
    is itself a `message` event in the same channel.
    """
    event_type = event.get("type")
    if event_type not in (_MENTION_EVENT, _MESSAGE_EVENT):
        return f"event_type:{event_type}"

    # `bot_id`/`bot_profile` are what Slack sets on app-authored messages.
    # (`api_app_id` lives on the wrapper, not the event, so it is not a
    # bot signal here — an `app_id` inside the event is.)
    if event.get("bot_id") or event.get("bot_profile") or event.get("app_id"):
        return "bot_message"
    if event.get("subtype"):
        # Joins, edits, deletions, file shares, channel topic changes.
        return f"subtype:{event['subtype']}"

    if event_type == _MESSAGE_EVENT and event.get("channel_type") != "im":
        # A non-DM plain message means the bot was not addressed.
        return "not_a_dm"

    if not event.get("channel") or not event.get("ts"):
        return "missing_channel_or_ts"
    if not (event.get("text") or "").strip():
        return "empty_text"

    user_id = event.get("user") or ""
    if not slack_agent_team.is_allowed_user(user_id):
        logger.warning("slack_events: user %s not in SLACK_ALLOWED_USER_IDS", user_id)
        return "user_not_allowed"

    return None


async def _handle_safe(
    *,
    channel: str,
    text: str,
    thread_ts: str | None,
    message_ts: str,
) -> None:
    """BackgroundTasks wrapper: never let handler errors escape the task.

    The webhook already returned 200. Raising here would only produce an
    unhandled-exception log with no retry path, and the person in Slack
    would be left waiting on a reply that never comes — so post the
    failure in-thread as well as logging it.
    """
    try:
        await slack_agent_team.handle_message(
            channel=channel,
            text=text,
            thread_ts=thread_ts,
            message_ts=message_ts,
        )
    except Exception:
        logger.exception("slack_agent_team.handle_message failed channel=%s", channel)
        try:
            await slack_agent_team.post_as_agent(
                channel=channel,
                text="Something broke on my side handling that. It's in the backend logs.",
                thread_ts=thread_ts or message_ts,
            )
        except Exception:
            logger.exception("slack_agent_team: failure notice post failed")
