"""SMS rate limiting — in-memory daily tracking per tenant."""

from datetime import datetime, timezone

# In-memory daily SMS tracking per tenant (reset at midnight UTC)
_daily_sms: dict[str, int] = {}
_last_reset_date: str = ""

# Plans with unlimited SMS
_UNLIMITED_PLANS = {"growth", "operations", "enterprise"}
FREE_DAILY_LIMIT = 50


def _maybe_reset() -> None:
    global _last_reset_date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today != _last_reset_date:
        _daily_sms.clear()
        _last_reset_date = today


def check_sms_rate_limit(tenant_id: str, plan: str) -> bool:
    """Return True if tenant is within daily SMS limit."""
    _maybe_reset()
    if plan in _UNLIMITED_PLANS:
        return True
    return _daily_sms.get(tenant_id, 0) < FREE_DAILY_LIMIT


def increment_sms_count(tenant_id: str) -> None:
    _maybe_reset()
    _daily_sms[tenant_id] = _daily_sms.get(tenant_id, 0) + 1


def get_sms_usage(tenant_id: str) -> int:
    _maybe_reset()
    return _daily_sms.get(tenant_id, 0)
