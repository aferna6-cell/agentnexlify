"""Lead contact helpers — email + SMS follow-up support.

Extracted from `backend/routers/leads.py` to keep the router under the 600-line
god-class threshold. Handlers still own the actual network awaits
(`send_email`, `send_sms`); this module owns DB lookups, HTML rendering, and
the new→contacted auto-promote.
"""

import html as html_mod
import logging
from typing import Any

from backend.services.tenant_scope import tenant_select, tenant_update

logger = logging.getLogger(__name__)


def fetch_lead_with_channel(
    db: Any, tenant_id: str, lead_id: str, channel: str
) -> dict:
    """Fetch a lead and verify it has a usable value for `channel`.

    `channel` is "email" or "phone". Returns the lead row dict.

    Raises:
        ValueError: if `channel` is unknown.
        LookupError("not_found"): lead does not exist for tenant.
        LookupError("no_channel"): lead exists but the channel value is empty.
    """
    if channel == "email":
        cols = "id, email, name"
    elif channel == "phone":
        cols = "id, phone, name"
    else:
        raise ValueError(f"unknown channel: {channel}")

    result = (
        tenant_select(db, "leads", tenant_id, cols)
        .eq("id", lead_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise LookupError("not_found")

    lead = result.data[0]
    if not lead.get(channel):
        raise LookupError("no_channel")
    return lead


def fetch_business_name(
    db: Any, tenant_id: str, *, default: str = "Our Team"
) -> str:
    """Return the tenant business name or `default` when the tenant row is missing."""
    result = (
        db.table("tenants")
        .select("business_name")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    return result.data[0]["business_name"] if result.data else default


def build_followup_email_html(message: str, business_name: str) -> str:
    """Render a plain-text follow-up message as safe HTML with a signature line."""
    safe_message = html_mod.escape(message).replace("\n", "<br>")
    return (
        f"<p>{safe_message}</p>"
        f"<p style='margin-top:16px;color:#666;font-size:0.9em;'>"
        f"— {html_mod.escape(business_name)}</p>"
    )


def auto_promote_new_to_contacted(db: Any, tenant_id: str, lead_id: str) -> None:
    """Promote a lead from `new` to `contacted` after first outbound touch.

    Swallows exceptions — auto-promote is a best-effort side-effect; the
    primary send already succeeded by the time we get here.
    """
    try:
        current = (
            tenant_select(db, "leads", tenant_id, "status")
            .eq("id", lead_id)
            .limit(1)
            .execute()
        )
        if current.data and current.data[0].get("status") == "new":
            tenant_update(
                db, "leads", tenant_id, {"status": "contacted"}
            ).eq("id", lead_id).execute()
    except Exception:
        logger.warning(
            "Failed to auto-update lead status to contacted", exc_info=True
        )
