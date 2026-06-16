"""Owner alert notifications - fires on key platform events.

Kept separate from platform_mailer.py (generic send) so alert-specific
formatting and error handling are co-located with the business logic.
Never raises.
"""

import html
import logging

from backend.services.platform_mailer import send_platform_email

logger = logging.getLogger(__name__)


async def notify_new_paid_signup(
    *,
    plan: str,
    amount_total: int,
    tenant_id: str,
    customer_email: str | None = None,
) -> None:
    """Email the platform owner when a new paying tenant activates.

    Args:
        plan: Plan name (e.g. "chatbot", "agent_os").
        amount_total: Raw Stripe amount_total in cents (0 if unknown).
        tenant_id: Tenant UUID string.
        customer_email: Stripe customer email if available.
    """
    try:
        amount_dollars = amount_total / 100 if amount_total else 0
        # Escape every interpolated value: customer_email (and plan) originate
        # from the Stripe session and are attacker-influenceable, so they must
        # not be injected into the email HTML raw.
        plan_safe = html.escape(str(plan))
        tenant_safe = html.escape(str(tenant_id))
        email_safe = html.escape(customer_email or "unknown")
        subject = f"New paid signup: {plan}"
        body_html = (
            "<h2>New paid signup</h2>"
            "<table>"
            f"<tr><td><strong>Plan</strong></td><td>{plan_safe}</td></tr>"
            f"<tr><td><strong>Amount</strong></td><td>${amount_dollars:.2f}</td></tr>"
            f"<tr><td><strong>Tenant ID</strong></td><td>{tenant_safe}</td></tr>"
            f"<tr><td><strong>Customer email</strong></td><td>{email_safe}</td></tr>"
            "</table>"
        )
        await send_platform_email(subject=subject, body_html=body_html)
    except Exception as exc:
        logger.warning(
            "owner_alerts.notify_new_paid_signup: send failed (tenant=%s, plan=%s)",
            tenant_id,
            plan,
            exc_info=exc,
        )
