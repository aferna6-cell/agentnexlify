"""Twilio phone-number webhook auto-sync.

Keeps every IncomingPhoneNumber on the Twilio account pointed at this
backend's voice + SMS webhooks, so nobody has to configure numbers in the
Twilio console by hand. Runs from the automation loop (30-min tier) and is
idempotent: numbers already pointing at the right URLs are left untouched.

Desired wiring per number:
  - VoiceUrl        -> POST {api_url}/api/v1/calls/voice/incoming
  - StatusCallback  -> POST {api_url}/api/v1/calls/voice/call-status
  - SmsUrl          -> POST {api_url}/api/v1/os/inbound/sms

Opt out with TWILIO_WEBHOOK_SYNC_ENABLED=false (e.g. while pointing a
number at ngrok for local webhook debugging).
"""

import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

_TWILIO_API = "https://api.twilio.com/2010-04-01"


def desired_webhooks() -> dict[str, str]:
    """Twilio update payload mapping every number to this backend."""
    base = (settings.api_url or "").rstrip("/")
    return {
        "VoiceUrl": f"{base}/api/v1/calls/voice/incoming",
        "VoiceMethod": "POST",
        "StatusCallback": f"{base}/api/v1/calls/voice/call-status",
        "StatusCallbackMethod": "POST",
        "SmsUrl": f"{base}/api/v1/os/inbound/sms",
        "SmsMethod": "POST",
    }


def _number_drifted(number: dict, desired: dict[str, str]) -> bool:
    """True when any webhook field differs from the desired wiring."""
    current = {
        "VoiceUrl": number.get("voice_url") or "",
        "VoiceMethod": (number.get("voice_method") or "").upper(),
        "StatusCallback": number.get("status_callback") or "",
        "StatusCallbackMethod": (number.get("status_callback_method") or "").upper(),
        "SmsUrl": number.get("sms_url") or "",
        "SmsMethod": (number.get("sms_method") or "").upper(),
    }
    return any(current[key] != desired[key] for key in desired)


async def sync_twilio_number_webhooks() -> dict:
    """Point every Twilio number at this backend's webhooks. Idempotent.

    Returns a summary dict: {"checked": n, "updated": n, "failed": n} or
    {"skipped": reason} when sync cannot or should not run.
    """
    if not getattr(settings, "twilio_webhook_sync_enabled", True):
        return {"skipped": "disabled"}
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return {"skipped": "twilio_unconfigured"}
    if not (settings.api_url or "").startswith("https://"):
        # Twilio requires HTTPS webhooks; never write a localhost URL to prod numbers.
        return {"skipped": "api_url_not_https"}

    auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    desired = desired_webhooks()
    checked = updated = failed = 0

    url = (
        f"{_TWILIO_API}/Accounts/{settings.twilio_account_sid}"
        f"/IncomingPhoneNumbers.json?PageSize=100"
    )
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                resp = await client.get(url, auth=auth)
                resp.raise_for_status()
                page = resp.json()

                for number in page.get("incoming_phone_numbers", []):
                    checked += 1
                    if not _number_drifted(number, desired):
                        continue
                    try:
                        update = await client.post(
                            f"{_TWILIO_API}/Accounts/{settings.twilio_account_sid}"
                            f"/IncomingPhoneNumbers/{number['sid']}.json",
                            data=desired,
                            auth=auth,
                        )
                        update.raise_for_status()
                        updated += 1
                        logger.info(
                            "Twilio webhook sync: updated %s (%s)",
                            number.get("phone_number"),
                            number["sid"],
                        )
                    except Exception:
                        failed += 1
                        logger.warning(
                            "Twilio webhook sync: failed to update %s",
                            number.get("sid"),
                            exc_info=True,
                        )

                next_page = page.get("next_page_uri")
                url = f"https://api.twilio.com{next_page}" if next_page else None
    except Exception:
        logger.warning("Twilio webhook sync: account listing failed", exc_info=True)
        return {"checked": checked, "updated": updated, "failed": failed, "error": "list_failed"}

    if updated or failed:
        logger.info(
            "Twilio webhook sync: checked=%d updated=%d failed=%d", checked, updated, failed
        )
    return {"checked": checked, "updated": updated, "failed": failed}
