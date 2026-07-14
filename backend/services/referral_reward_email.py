"""Referral reward email — tell the referrer their $20 credit landed.

Called synchronously from referral_reward._grant_sync AFTER the Stripe
balance credit succeeds and the reward row is marked granted. Best-effort:
the credit is already granted, so a mail failure only logs — it never
un-grants, never raises into the webhook path (GH #413 checklist item:
"tenant notification email sent when referral converts").

Do NOT add 'from __future__ import annotations' — project rule.
"""

import logging

logger = logging.getLogger(__name__)


def _body_html(referrer_name: str, referred_name: str, amount_cents: int) -> str:
    amount = f"${amount_cents / 100:.2f}"
    referred = referred_name or "A business you referred"
    return f"""
<div style="font-family:sans-serif;max-width:540px;margin:0 auto">
  <h2 style="margin-bottom:4px">You earned {amount} in credit</h2>
  <p><strong>{referred}</strong> signed up through your referral link and just
  paid their first invoice — so your {amount} referral credit is live.</p>
  <p>No action needed: the credit is already on your account and will be
  applied automatically to your next AgentNexLiFy bill.</p>
  <p>You can see your referral stats (and grab your link to share again) on
  your dashboard's Referral page.</p>
  <p style="color:#666;font-size:13px;margin-top:24px">Thanks for spreading
  the word — every business you refer earns you another {amount}.</p>
</div>
"""


def notify_reward_granted_sync(
    *,
    recipient: str,
    referrer_name: str,
    referred_name: str,
    amount_cents: int,
) -> bool:
    """Send the reward-granted email. Sync (grant flow runs in a thread).

    Returns True when Resend accepted the send; False on any skip/failure.
    Never raises."""
    try:
        import resend

        from backend.config import settings
        from backend.services.platform_mailer import FROM_ADDRESS

        if not recipient:
            return False
        if not settings.resend_api_key:
            logger.info(
                "referral_reward_email: resend_api_key not configured — skipping"
            )
            return False

        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": FROM_ADDRESS,
                "to": [recipient],
                "subject": f"You earned ${amount_cents / 100:.0f} — thanks for the referral",
                "html": _body_html(referrer_name, referred_name, amount_cents),
            }
        )
        logger.info(
            "referral_reward_email: sent reward email to referrer (%s)",
            referrer_name or "unnamed",
        )
        return True
    except Exception:
        logger.warning(
            "referral_reward_email: send failed — credit is granted regardless",
            exc_info=True,
        )
        return False
