"""Strip OAuth callback query strings before they reach access logs.

Google, Microsoft, and HubSpot send the browser to
``/integrations/{provider}/callback`` with a one-time ``code`` and the signed
``state``. Uvicorn's access log records the raw request target, so those
values have to be removed before a log line is formatted.
"""

import logging
import re

_CALLBACK_WITH_QUERY = re.compile(
    r"(/integrations/(?:google|m365|hubspot)/callback)\?[^\s\"']*"
)

_ACCESS_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def is_oauth_callback_path(path: str) -> bool:
    path_only = path.split("?", 1)[0]
    return path_only.endswith(
        (
            "/integrations/google/callback",
            "/integrations/m365/callback",
            "/integrations/hubspot/callback",
        )
    )


def redact_oauth_callback_secrets(text: str) -> str:
    """Drop the query string on Google, M365, and HubSpot callback URLs."""
    return _CALLBACK_WITH_QUERY.sub(r"\1", text)


def logged_http_target(path: str, query: str) -> str:
    """Path written to request logs. Callback queries are never included."""
    if not is_oauth_callback_path(path):
        return path
    raw = f"{path}?{query}" if query else path
    return redact_oauth_callback_secrets(raw)


def _redact_value(value):
    if isinstance(value, str):
        return redact_oauth_callback_secrets(value)
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    return value


class OAuthCallbackQueryRedactionFilter(logging.Filter):
    """Remove callback query strings from uvicorn access lines and app logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_oauth_callback_secrets(record.msg)
        if record.args:
            record.args = _redact_value(record.args)
        for key, value in list(record.__dict__.items()):
            if key in {"msg", "args", "exc_info", "exc_text", "stack_info"}:
                continue
            if isinstance(value, str) and "integrations/" in value:
                setattr(record, key, redact_oauth_callback_secrets(value))
        return True


def install_oauth_callback_log_redaction(*handlers: logging.Handler) -> None:
    """Attach the redaction filter to access loggers and the given handlers.

    Logger filters do not run for records propagated from a child logger, so
    the JSON handler on the root logger needs the filter too.
    """
    filt = OAuthCallbackQueryRedactionFilter()
    targets: list[logging.Logger] = [logging.getLogger(name) for name in _ACCESS_LOGGERS]
    targets.append(logging.getLogger())
    seen_handlers: set[int] = set()
    for logger in targets:
        if not any(isinstance(existing, OAuthCallbackQueryRedactionFilter) for existing in logger.filters):
            logger.addFilter(filt)
        for handler in logger.handlers:
            seen_handlers.add(id(handler))
            if not any(
                isinstance(existing, OAuthCallbackQueryRedactionFilter)
                for existing in handler.filters
            ):
                handler.addFilter(filt)
    for handler in handlers:
        if id(handler) in seen_handlers:
            continue
        if not any(
            isinstance(existing, OAuthCallbackQueryRedactionFilter)
            for existing in handler.filters
        ):
            handler.addFilter(filt)
