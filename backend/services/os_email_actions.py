"""Signed one-click approve/reject links for deliverable emails (round 5).

The approval rollup email told owners drafts were waiting but only linked to
the dashboard - with 30+ drafts parked for days, the login hop was the
bottleneck in the whole workforce loop. Each draft in the email now carries
Approve / Reject links whose token is an HMAC over
(client_id, run_id, action, expiry) using the platform JWT secret - no
database token column, no login, single tenant + single run + single action
per token, 7-day expiry.

Safety: the link target renders a confirmation page first (mail scanners
prefetch GETs; the mutation only happens on the explicit POST), approval
reuses the exact queue_action_for_run path the dashboard Approve uses (the
outbound guard and idempotency rules apply unchanged), and a run that is no
longer pending reports its current state instead of double-firing.
"""

import base64
import hashlib
import hmac
import json
import logging
import time

from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

VALID_ACTIONS = ("approve", "reject")
TOKEN_TTL_SECONDS = 7 * 24 * 3600
_SIGN_CONTEXT = b"os-deliverable-email-action:"


def _secret() -> bytes:
    from backend.config import settings

    for attr in ("jwt_secret_key", "api_secret_key"):
        value = getattr(settings, attr, "")
        if isinstance(value, str) and value:
            return value.encode()
    return b""


def _sign(payload_b64: bytes) -> str:
    return hmac.new(
        _secret(), _SIGN_CONTEXT + payload_b64, hashlib.sha256
    ).hexdigest()


def make_action_token(client_id: str, run_id: str, action: str) -> str:
    """Signed token authorizing one action on one run for 7 days."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"invalid action: {action}")
    payload = {
        "c": client_id,
        "r": run_id,
        "a": action,
        "e": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )
    return f"{payload_b64.decode()}.{_sign(payload_b64)}"


def verify_action_token(token: str) -> dict | None:
    """The token's payload when the signature and expiry hold, else None."""
    if not _secret():
        logger.warning("os_email_actions: no signing secret configured")
        return None
    try:
        payload_b64_str, sig = (token or "").split(".", 1)
        payload_b64 = payload_b64_str.encode()
        if not hmac.compare_digest(sig, _sign(payload_b64)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return None
    if payload.get("a") not in VALID_ACTIONS:
        return None
    if not payload.get("c") or not payload.get("r"):
        return None
    if int(payload.get("e") or 0) < time.time():
        return None
    return payload


def load_pending_title(db, payload: dict) -> tuple[str, str | None]:
    """(state, title) for the confirm page.

    state: "pending" | "already:<status>" | "not_found".
    """
    rows = (
        tenant_table(db, "os_agent_runs", payload["c"])
        .select("id, deliverable, deliverable_status")
        .eq("id", payload["r"])
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return "not_found", None
    run = rows[0]
    deliverable = run.get("deliverable") or {}
    title = deliverable.get("title") if isinstance(deliverable, dict) else None
    if run.get("deliverable_status") != "pending_approval":
        return f"already:{run.get('deliverable_status')}", title
    return "pending", title


async def apply_action(db, payload: dict) -> tuple[str, str | None]:
    """Apply the token's action. Returns (state, title) like load_pending_title,
    with state "done" on success."""
    from datetime import datetime, timezone

    from backend.services.activity import log_activity
    from backend.services.os_action_dispatch import queue_action_for_run

    client_id, run_id, action = payload["c"], payload["r"], payload["a"]
    rows = (
        tenant_table(db, "os_agent_runs", client_id)
        .select("*")
        .eq("id", run_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return "not_found", None
    run = rows[0]
    deliverable = run.get("deliverable") or {}
    title = deliverable.get("title") if isinstance(deliverable, dict) else None
    if run.get("deliverable_status") != "pending_approval":
        return f"already:{run.get('deliverable_status')}", title

    now = datetime.now(timezone.utc).isoformat()
    if action == "approve":
        # background=None runs any action handler inline - acceptable for an
        # email click, and identical to the inbound-bridge approval path.
        action_run_id = await queue_action_for_run(db, client_id, run, None)
        fields = {"deliverable_status": "approved", "updated_at": now}
        if action_run_id:
            fields["action_run_id"] = action_run_id
    else:
        fields = {"deliverable_status": "rejected", "updated_at": now}

    tenant_table(db, "os_agent_runs", client_id).update(fields).eq(
        "id", run_id
    ).execute()
    try:
        log_activity(
            tenant_id=client_id,
            activity_type=f"email_action_{action}",
            description=f"Deliverable {action}d from email: {(title or '')[:80]}",
        )
    except Exception:
        logger.warning("os_email_actions: activity log failed", exc_info=True)
    return "done", title
