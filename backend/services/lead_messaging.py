"""Outbound-message bookkeeping for lead follow-ups.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. After the router awaits the external send
(email or SMS), this module owns the activity-log entry + the
new-to-contacted auto-promotion. The async I/O itself stays in the
router because both senders are async and the helper here is sync.
"""

import logging
from typing import Any

from backend.services.activity import log_activity
from backend.services.lead_contact import auto_promote_new_to_contacted

logger = logging.getLogger(__name__)


def record_followup_sent(
    db: Any,
    tenant_id: str,
    lead_id: str,
    *,
    lead: dict,
    channel: str,
    subject: str | None = None,
) -> None:
    """Log a follow-up `email_sent` / `sms_sent` event and promote new->contacted.

    `channel` must be either ``"email"`` or ``"sms"``. The activity_type and
    description text differ by channel; the auto-promotion is identical.
    """
    if channel == "email":
        recipient = lead.get("name") or lead.get("email") or lead_id
        description = f"Follow-up email sent to {recipient}"
        if subject:
            description = f"{description}: {subject}"
        activity_type = "email_sent"
    elif channel == "sms":
        recipient = lead.get("name") or lead.get("phone") or lead_id
        description = f"Follow-up SMS sent to {recipient}"
        activity_type = "sms_sent"
    else:
        raise ValueError(f"unknown channel: {channel!r}")

    log_activity(
        tenant_id=tenant_id,
        activity_type=activity_type,
        description=description,
        lead_id=lead_id,
    )
    auto_promote_new_to_contacted(db, tenant_id, lead_id)
