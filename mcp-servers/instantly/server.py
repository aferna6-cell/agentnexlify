"""
Instantly.ai MCP server — send cold-email campaigns via the Instantly v2 API.

Wraps https://api.instantly.ai/api/v2. Auth is a Bearer API key read from the
INSTANTLY_API_KEY env var (create one in Instantly → Settings → Integrations →
API keys). No secret is stored in this repo.

Tool surface (one tool per real task):
    list_sending_accounts   — which inboxes are connected/warmed
    list_campaigns          — see existing campaigns + their status
    get_campaign            — one campaign's full config
    create_campaign         — build a campaign (schedule + email sequence)
    add_lead_to_campaign    — add a prospect to a campaign
    activate_campaign       — start sending (real emails go out)
    pause_campaign          — stop sending
    get_campaign_analytics  — sent / opens / replies / bounces
    list_emails             — sent + received messages (read replies)

Run standalone for a smoke test:
    INSTANTLY_API_KEY=... uv run python server.py
"""

import os

import httpx
from fastmcp import FastMCP

mcp = FastMCP("instantly")

API_BASE = "https://api.instantly.ai/api/v2"
_TIMEOUT = 30.0

# Instantly day index in campaign_schedule.days — 0=Mon … 6=Sun (per API docs
# "Business Hours" example). Default: weekdays on, weekend off.
_WEEKDAYS = {"0": True, "1": True, "2": True, "3": True, "4": True, "5": False, "6": False}


def _request(method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> dict:
    """Call the Instantly v2 API and return a structured result.

    Returns {"ok": True, "data": <json>} on success, or
    {"ok": False, "error": <actionable message>, "status": <int|None>} on failure.
    Never raises — callers get a dict either way.
    """
    api_key = os.environ.get("INSTANTLY_API_KEY", "").strip()
    if not api_key:
        return {
            "ok": False,
            "status": None,
            "error": (
                "INSTANTLY_API_KEY is not set. Create an API key in Instantly "
                "(Settings → Integrations → API keys) and export it as "
                "INSTANTLY_API_KEY before starting the MCP server."
            ),
        }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    try:
        resp = httpx.request(
            method, url, headers=headers, params=params, json=json_body, timeout=_TIMEOUT
        )
    except httpx.HTTPError as exc:
        return {"ok": False, "status": None, "error": f"network error calling {url}: {exc}"}

    if resp.status_code == 401:
        return {
            "ok": False,
            "status": 401,
            "error": "401 Unauthorized — INSTANTLY_API_KEY is missing, invalid, or revoked.",
        }
    if resp.status_code >= 400:
        # Surface the API's own message so the caller can act, not just an HTTP code.
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return {"ok": False, "status": resp.status_code, "error": body}

    try:
        return {"ok": True, "data": resp.json()}
    except ValueError:
        return {"ok": True, "data": resp.text}


@mcp.tool()
def list_sending_accounts(limit: int = 100) -> dict:
    """List connected sending email accounts (inboxes) and their warmup status.

    Check this first — a campaign can only send from accounts listed here.

    Args:
        limit: Max accounts to return (1-100).
    Returns:
        {"ok": bool, "data"|"error": ...}. data.items[] each has email + status.
    """
    return _request("GET", "/accounts", params={"limit": max(1, min(limit, 100))})


@mcp.tool()
def list_campaigns(limit: int = 50, search: str | None = None) -> dict:
    """List campaigns with their id, name, and status.

    Args:
        limit: Max campaigns to return (1-100).
        search: Optional case-insensitive name filter.
    Returns:
        {"ok": bool, "data"|"error": ...}. Campaign status: 0=draft, 1=active,
        2=paused, 3=completed.
    """
    params: dict = {"limit": max(1, min(limit, 100))}
    if search:
        params["search"] = search
    return _request("GET", "/campaigns", params=params)


@mcp.tool()
def get_campaign(campaign_id: str) -> dict:
    """Get one campaign's full configuration (schedule, sequences, settings).

    Args:
        campaign_id: The campaign UUID.
    """
    return _request("GET", f"/campaigns/{campaign_id}")


@mcp.tool()
def create_campaign(
    name: str,
    email_subject: str,
    email_body: str,
    sending_accounts: list[str] | None = None,
    timezone: str = "America/New_York",
    from_time: str = "09:00",
    to_time: str = "17:00",
    daily_limit: int | None = None,
    open_tracking: bool = True,
    link_tracking: bool = False,
    stop_on_reply: bool = True,
    days: dict | None = None,
    follow_ups: list[dict] | None = None,
) -> dict:
    """Create a cold-email campaign with a schedule and a first email step.

    The campaign is created in DRAFT — nothing sends until activate_campaign.

    Args:
        name: Campaign name.
        email_subject: Subject of the first email. Instantly vars like
            {{firstName}} / {{companyName}} are interpolated at send time.
        email_body: Body of the first email (plain text or HTML).
        sending_accounts: Inbox emails to send from (from list_sending_accounts).
            Omit to create the campaign without inboxes attached (attach later in UI).
        timezone: IANA tz for the sending window (e.g. "America/New_York").
        from_time / to_time: Daily sending window, 24h "HH:MM".
        daily_limit: Max emails/day across the campaign (None = Instantly default).
        open_tracking: Track opens.
        link_tracking: Track link clicks.
        stop_on_reply: Stop sequencing a lead once they reply.
        days: Optional Instantly days map (keys "0"=Mon..."6"=Sun → bool).
            Defaults to weekdays on, weekend off.
        follow_ups: Optional extra steps, each
            {"delay": <days_after_prev:int>, "subject": str, "body": str}.
    Returns:
        {"ok": bool, "data"|"error": ...}. data.id is the new campaign UUID.
    """
    steps = [
        {
            "type": "email",
            "delay": 0,
            "variants": [{"subject": email_subject, "body": email_body}],
        }
    ]
    for step in follow_ups or []:
        steps.append(
            {
                "type": "email",
                "delay": int(step.get("delay", 2)),
                "variants": [
                    {"subject": step.get("subject", ""), "body": step.get("body", "")}
                ],
            }
        )

    payload: dict = {
        "name": name,
        "campaign_schedule": {
            "schedules": [
                {
                    "name": "Default schedule",
                    "timing": {"from": from_time, "to": to_time},
                    "days": days or dict(_WEEKDAYS),
                    "timezone": timezone,
                }
            ]
        },
        "sequences": [{"steps": steps}],
        "open_tracking": open_tracking,
        "link_tracking": link_tracking,
        "stop_on_reply": stop_on_reply,
    }
    if sending_accounts:
        payload["email_list"] = sending_accounts
    if daily_limit is not None:
        payload["daily_limit"] = daily_limit
    return _request("POST", "/campaigns", json_body=payload)


@mcp.tool()
def add_lead_to_campaign(
    campaign_id: str,
    email: str,
    first_name: str | None = None,
    last_name: str | None = None,
    company_name: str | None = None,
    phone: str | None = None,
    website: str | None = None,
    personalization: str | None = None,
    custom_variables: dict | None = None,
    skip_if_in_campaign: bool = True,
) -> dict:
    """Add a prospect to a campaign so they enter its sending sequence.

    Args:
        campaign_id: Target campaign UUID.
        email: Lead email (required when adding to a campaign).
        first_name, last_name, company_name, phone, website: Optional lead fields.
        personalization: Optional first-line / snippet used by {{personalization}}.
        custom_variables: Optional dict of extra merge vars usable in the email
            as {{key}}.
        skip_if_in_campaign: Skip if this email is already in the campaign
            (avoids duplicate sends).
    Returns:
        {"ok": bool, "data"|"error": ...}. data.id is the new lead UUID.
    """
    payload: dict = {"campaign": campaign_id, "email": email, "skip_if_in_campaign": skip_if_in_campaign}
    for key, val in (
        ("first_name", first_name),
        ("last_name", last_name),
        ("company_name", company_name),
        ("phone", phone),
        ("website", website),
        ("personalization", personalization),
        ("custom_variables", custom_variables),
    ):
        if val is not None:
            payload[key] = val
    return _request("POST", "/leads", json_body=payload)


@mcp.tool()
def activate_campaign(campaign_id: str) -> dict:
    """Activate a campaign — this STARTS sending real emails to its leads.

    Confirm the sequence, sending accounts, and lead list are correct first.

    Args:
        campaign_id: The campaign UUID to start.
    """
    return _request("POST", f"/campaigns/{campaign_id}/activate")


@mcp.tool()
def pause_campaign(campaign_id: str) -> dict:
    """Pause a campaign — stop sending. Safe to call on an active campaign.

    Args:
        campaign_id: The campaign UUID to pause.
    """
    return _request("POST", f"/campaigns/{campaign_id}/pause")


@mcp.tool()
def get_campaign_analytics(
    campaign_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Get campaign performance: sent, opens, replies, bounces, opportunities.

    Args:
        campaign_id: Optional — one campaign UUID. Omit for all campaigns.
        start_date / end_date: Optional "YYYY-MM-DD" window.
    """
    body: dict = {}
    if campaign_id:
        body["id"] = campaign_id
    if start_date:
        body["start_date"] = start_date
    if end_date:
        body["end_date"] = end_date
    return _request("POST", "/campaigns/analytics", json_body=body)


@mcp.tool()
def list_emails(campaign_id: str | None = None, limit: int = 25) -> dict:
    """List sent and received emails — use to read replies from prospects.

    Args:
        campaign_id: Optional — filter to one campaign UUID.
        limit: Max emails to return (1-100).
    """
    params: dict = {"limit": max(1, min(limit, 100))}
    if campaign_id:
        params["campaign_id"] = campaign_id
    return _request("GET", "/emails", params=params)


if __name__ == "__main__":
    mcp.run()
