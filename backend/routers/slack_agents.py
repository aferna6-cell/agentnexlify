"""Slack Events API endpoint for the internal agent team bots.

One endpoint serves every agent app on the roster — the request
signature identifies which app (and therefore which agent persona) the
event belongs to. See ``backend/services/slack_agent_team.py`` for the
security posture and ``docs/slack-agent-team.md`` for workspace setup.

Order is load-bearing — the signature is verified against the RAW body
BEFORE any payload field is parsed or branched on. Slack retries
deliveries that don't get a 2xx within 3 seconds, so event handling
(thread fetch + Claude call + postMessage) runs in ``BackgroundTasks``
and the webhook returns immediately.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from backend.services import slack_agent_team

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/slack", tags=["slack-agents"])


@router.post("/events")
async def slack_events(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Receive a Slack Events API delivery for any roster agent app.

    Flow:
      1. Load the roster → 403 when SLACK_AGENT_TEAM is not configured.
      2. Verify the v0 signature against the raw body; the matching
         signing secret resolves which agent app sent this → 401 on
         mismatch.
      3. ``url_verification`` → echo the challenge (Slack app setup).
      4. ``event_callback`` → skip retries and non-human events, then
         enqueue the mention handler on BackgroundTasks → 200.
    """
    team = slack_agent_team.load_team()
    if not team:
        logger.warning("slack events webhook hit without SLACK_AGENT_TEAM configured")
        raise HTTPException(status_code=403, detail="Slack agent team not configured")

    raw_body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    app = slack_agent_team.resolve_app(team, timestamp, raw_body, signature)
    if app is None:
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    try:
        payload = await request.json()
    except Exception as exc:
        logger.warning("slack_events: JSON parse failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    payload_type = payload.get("type")

    if payload_type == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    if payload_type != "event_callback":
        return {"status": "ignored"}

    # Slack retries when the first delivery is slow — processing is
    # fire-and-forget with no dedupe store, so a retry would double-post
    # the same reply. Acknowledge and drop.
    if request.headers.get("X-Slack-Retry-Num"):
        return {"status": "ignored_retry"}

    event = payload.get("event") or {}
    if not slack_agent_team.should_handle_event(event):
        return {"status": "ignored"}

    background_tasks.add_task(
        slack_agent_team.handle_event,
        app=app,
        team=team,
        event=event,
        bot_user_id=_authorized_bot_user_id(payload),
    )
    return {"status": "accepted", "agent": app.agent}


def _authorized_bot_user_id(payload: dict[str, Any]) -> str:
    """Bot user id from the event envelope, for self-mention stripping.

    ``authorizations`` carries the app's own bot user when Slack routes
    the event; absent or malformed just means mention stripping falls
    back to the leading-token heuristic.
    """
    authorizations = payload.get("authorizations")
    if not isinstance(authorizations, list):
        return ""
    for auth in authorizations:
        if isinstance(auth, dict) and auth.get("is_bot") and auth.get("user_id"):
            return str(auth["user_id"])
    return ""
