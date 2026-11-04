"""Optional Sentry init. Stays off unless SENTRY_DSN is set, and scrubs PII."""

import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\-\s().]{7,}\d)")
_SECRET_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-widget-key",
    "x-auth-token",
}
_USER_FIELDS = ("email", "ip_address", "username", "name")


def _redact_text(value: str) -> str:
    value = _EMAIL.sub("[redacted-email]", value)
    return _PHONE.sub("[redacted-phone]", value)


def _scrub_strings(value):
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_scrub_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_strings(item) for key, item in value.items()}
    return value


def scrub_sentry_event(event, _hint):
    """Drop secrets and redact emails/phones before an event leaves the process."""
    if not isinstance(event, dict):
        return event

    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            cleaned = {}
            for key, value in headers.items():
                if str(key).lower() in _SECRET_HEADERS:
                    cleaned[key] = "[redacted]"
                elif isinstance(value, str):
                    cleaned[key] = _redact_text(value)
                else:
                    cleaned[key] = value
            request["headers"] = cleaned
        request.pop("cookies", None)
        request.pop("data", None)
        if isinstance(request.get("query_string"), str):
            request["query_string"] = _redact_text(request["query_string"])

    user = event.get("user")
    if isinstance(user, dict):
        for key in _USER_FIELDS:
            if key in user:
                user[key] = "[redacted]"

    if isinstance(event.get("message"), str):
        event["message"] = _redact_text(event["message"])

    exception = event.get("exception")
    if isinstance(exception, dict):
        event["exception"] = _scrub_strings(exception)

    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = _scrub_strings(extra)

    return event


def init_sentry(dsn: str) -> bool:
    """Initialize Sentry only when a DSN is configured. Returns whether it did."""
    cleaned = (dsn or "").strip()
    if not cleaned:
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=cleaned,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=scrub_sentry_event,
    )
    return True
