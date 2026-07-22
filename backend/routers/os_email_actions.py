"""Public confirm + apply pages for signed deliverable email actions.

Token-authed (HMAC, see services/os_email_actions.py) - deliberately NOT
behind the JWT dependency or the plan gate: the owner clicks straight from
their inbox. GET renders a confirmation page (mail scanners prefetch links,
so the GET never mutates); the explicit POST applies the action.
"""

import html
import logging

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from backend.models.database import get_service_supabase
from backend.services.os_email_actions import (
    apply_action,
    load_pending_title,
    verify_action_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os", tags=["agent-os"])

_DASHBOARD_URL = "https://app.agentnexlify.com/dashboard/agent-os"


def _page(title: str, body_html: str) -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title></head>"
        "<body style=\"background:#0f172a;color:#f1f5f9;font-family:sans-serif;"
        "display:flex;justify-content:center;padding:48px 16px;\">"
        "<div style=\"max-width:480px;width:100%;background:#1e293b;"
        "border:1px solid #334155;border-radius:12px;padding:28px;\">"
        + body_html
        + f"<p style='margin-top:24px;font-size:13px;'><a href='{_DASHBOARD_URL}' "
        "style='color:#818cf8;'>Open your dashboard</a></p>"
        "</div></body></html>"
    )


def _invalid() -> HTMLResponse:
    return _page(
        "Link expired",
        "<h2 style='margin:0 0 8px;'>This link is no longer valid</h2>"
        "<p style='color:#94a3b8;'>It may have expired (links last 7 days). "
        "You can still review the draft from your dashboard.</p>",
    )


def _state_page(state: str, title: str | None, action: str) -> HTMLResponse:
    safe_title = html.escape(title or "this draft")
    if state == "not_found":
        return _invalid()
    if state.startswith("already:"):
        status = html.escape(state.split(":", 1)[1] or "handled")
        return _page(
            "Already handled",
            f"<h2 style='margin:0 0 8px;'>Already {status}</h2>"
            f"<p style='color:#94a3b8;'>“{safe_title}” was already "
            f"{status} - nothing more to do.</p>",
        )
    verb = "approved" if action == "approve" else "rejected"
    extra = (
        "Your AI staff will send it now."
        if action == "approve"
        else "It will not be sent."
    )
    return _page(
        f"Draft {verb}",
        f"<h2 style='margin:0 0 8px;'>Draft {verb}</h2>"
        f"<p style='color:#94a3b8;'>“{safe_title}” has been {verb}. "
        f"{extra}</p>",
    )


@router.get("/deliverables/email-action", response_class=HTMLResponse)
async def email_action_confirm(token: str = Query(min_length=16)):
    """Confirmation page - shows the draft and an explicit action button."""
    payload = verify_action_token(token)
    if payload is None:
        return _invalid()
    db = get_service_supabase()
    try:
        state, title = load_pending_title(db, payload)
    except Exception:
        logger.warning("email_action: load failed", exc_info=True)
        return _invalid()

    # Funnel meter (round 8): a valid-token GET means the owner opened the
    # link (scanner prefetches also land here - treat as upper bound).
    # Distinguishes "rollup never opened" from "opened, didn't decide".
    try:
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=payload["c"],
            activity_type="email_action_viewed",
            description=f"One-click {payload['a']} page viewed",
            metadata={"run_id": payload["r"], "action": payload["a"], "state": state},
        )
    except Exception:
        logger.warning("email_action: view log failed", exc_info=True)

    if state != "pending":
        return _state_page(state, title, payload["a"])

    action = payload["a"]
    verb = "Approve" if action == "approve" else "Reject"
    color = "#6366f1" if action == "approve" else "#b91c1c"
    safe_title = html.escape(title or "this draft")
    return _page(
        f"{verb} draft",
        f"<h2 style='margin:0 0 8px;'>{verb} this draft?</h2>"
        f"<p style='color:#94a3b8;'>“{safe_title}”</p>"
        + (
            "<p style='color:#94a3b8;font-size:13px;'>Approving may send it "
            "to its recipient right away.</p>"
            if action == "approve"
            else ""
        )
        + f"<form method='post' action='?token={html.escape(token)}' "
        "style='margin-top:16px;'>"
        f"<button type='submit' style=\"background:{color};color:#fff;"
        "border:none;border-radius:8px;padding:10px 24px;font-size:15px;"
        f"font-weight:600;cursor:pointer;\">{verb}</button></form>",
    )


@router.post("/deliverables/email-action", response_class=HTMLResponse)
async def email_action_apply(token: str = Query(min_length=16)):
    """Apply the action after the explicit confirmation click."""
    payload = verify_action_token(token)
    if payload is None:
        return _invalid()
    db = get_service_supabase()
    try:
        state, title = await apply_action(db, payload)
    except Exception:
        logger.warning("email_action: apply failed", exc_info=True)
        return _invalid()
    if state == "done":
        return _state_page("done", title, payload["a"])
    return _state_page(state, title, payload["a"])
