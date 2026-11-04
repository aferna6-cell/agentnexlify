"""Strip OAuth callback query strings before they reach access logs.

Google, Microsoft, and HubSpot send the browser to
``/integrations/{provider}/callback`` with a one-time ``code`` and the signed
``state``. Uvicorn's access log records the raw request target, so those
values have to be removed before a log line is formatted.
"""

import logging
import re
import traceback
from urllib.parse import urlparse

_CALLBACK_WITH_QUERY = re.compile(
    r"(/integrations/(?:google|m365|hubspot)/callback)\?[^\s\"']*"
)
# Authorization codes and signed state values are long. Leave short tokens
# such as "code=404" alone.
_OAUTH_PARAM = re.compile(
    r"(?:(?<=^)|(?<=[?&\s\"']))(?:code|state)=[^&\s\"']{8,}",
    re.IGNORECASE,
)
# Source lines and messages can contain the marker without a long value,
# for example code={code}. Do not match encode= or statement=.
_PARAM_MARKER = re.compile(r"(?<![A-Za-z0-9_])(?:code|state)=", re.IGNORECASE)
_CALLBACK_FUNCTIONS = frozenset(
    {"google_callback", "m365_callback", "hubspot_callback"}
)
_MIN_SECRET_LEN = 8

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
    """Drop callback queries and long ``code=`` / ``state=`` values."""
    text = _CALLBACK_WITH_QUERY.sub(r"\1", text)
    text = _OAUTH_PARAM.sub("", text)
    return _PARAM_MARKER.sub("", text)


def _pii_scrubbers():
    """PR #977's scrubber, when that module is on the tree.

    Importing it keeps this hook from replacing ``scrub_sentry_event``.
    Both run: OAuth redaction first, then the PII scrubber.
    """
    try:
        from backend.services.sentry_scrub import (
            scrub_sentry_breadcrumb,
            scrub_sentry_event,
        )
    except ImportError:
        return None, None
    return scrub_sentry_event, scrub_sentry_breadcrumb


def _request_path(url) -> str:
    if isinstance(url, (bytes, bytearray)):
        url = url.decode("latin-1", "replace")
    if not isinstance(url, str) or not url:
        return ""
    return urlparse(url).path or url.split("?", 1)[0]


def _iter_stack_frames(event):
    for container_key in ("exception", "threads"):
        container = event.get(container_key)
        if not isinstance(container, dict):
            continue
        for value in container.get("values") or []:
            if not isinstance(value, dict):
                continue
            stack = value.get("stacktrace") or {}
            for frame in stack.get("frames") or []:
                if isinstance(frame, dict):
                    yield frame


def _is_callback_event(event) -> bool:
    request = event.get("request")
    if isinstance(request, dict) and is_oauth_callback_path(_request_path(request.get("url"))):
        return True
    for frame in _iter_stack_frames(event):
        if frame.get("function") in _CALLBACK_FUNCTIONS:
            return True
    return False


def _frame_secret_values(event) -> list[str]:
    found = []
    for frame in _iter_stack_frames(event):
        variables = frame.get("vars")
        if not isinstance(variables, dict):
            continue
        for name, value in variables.items():
            if name not in {"code", "state"} or not isinstance(value, str):
                continue
            if len(value) >= _MIN_SECRET_LEN:
                found.append(value)
    return found


def _drop_frame_vars(event) -> None:
    for frame in _iter_stack_frames(event):
        frame.pop("vars", None)


def _redact_tree(value, secrets: tuple[str, ...]):
    if isinstance(value, str):
        text = redact_oauth_callback_secrets(value)
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[redacted]")
        return text
    if isinstance(value, list):
        return [_redact_tree(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_tree(item, secrets) for item in value)
    if isinstance(value, dict):
        return {key: _redact_tree(item, secrets) for key, item in value.items()}
    return value


def _strip_request_query(request) -> None:
    url = request.get("url")
    if isinstance(url, (bytes, bytearray)):
        url = url.decode("latin-1", "replace")
    if isinstance(url, str):
        request["url"] = redact_oauth_callback_secrets(url)
    query = request.get("query_string")
    if isinstance(query, list):
        request["query_string"] = []
    elif query is not None:
        request["query_string"] = ""


def scrub_oauth_callback_event(event, _hint):
    """Remove OAuth callback secrets from one Sentry event.

    Does not call the PII scrubber. ``sentry_before_send`` chains that next.
    """
    if not isinstance(event, dict):
        return event
    request = event.get("request")
    callback = _is_callback_event(event)
    if isinstance(request, dict) and is_oauth_callback_path(_request_path(request.get("url"))):
        _strip_request_query(request)
        callback = True
    if not callback:
        return event

    secrets = tuple(_frame_secret_values(event))
    _drop_frame_vars(event)
    for key in ("exception", "breadcrumbs", "message", "logentry", "extra", "contexts"):
        if key in event:
            event[key] = _redact_tree(event[key], secrets)
    if isinstance(request, dict):
        event["request"] = _redact_tree(request, secrets)
        _strip_request_query(event["request"])
    return event


def sentry_before_send(event, hint):
    """OAuth callback scrub, then PR #977's ``scrub_sentry_event`` when present."""
    event = scrub_oauth_callback_event(event, hint)
    if event is None:
        return None
    nxt, _breadcrumb = _pii_scrubbers()
    if callable(nxt):
        return nxt(event, hint)
    return event


def sentry_before_breadcrumb(crumb, hint):
    """Redact callback crumbs, then PR #977's breadcrumb scrubber when present."""
    if isinstance(crumb, dict):
        crumb = _redact_tree(crumb, ())
    elif crumb is None:
        return None
    _event, nxt = _pii_scrubbers()
    if callable(nxt):
        return nxt(crumb, hint)
    return crumb


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
    """Remove callback query strings from access lines and exception text."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_oauth_callback_secrets(record.msg)
        if record.args:
            record.args = _redact_value(record.args)
        if record.exc_info and record.exc_info[0] is not None:
            _exc_type, exc_value, _exc_tb = record.exc_info
            if exc_value is not None and exc_value.args:
                try:
                    exc_value.args = tuple(
                        redact_oauth_callback_secrets(arg) if isinstance(arg, str) else arg
                        for arg in exc_value.args
                    )
                except Exception:
                    pass
            try:
                formatted = "".join(traceback.format_exception(*record.exc_info))
            except Exception:
                formatted = record.exc_text if isinstance(record.exc_text, str) else ""
            record.exc_text = redact_oauth_callback_secrets(formatted)
        elif isinstance(record.exc_text, str):
            record.exc_text = redact_oauth_callback_secrets(record.exc_text)
        if isinstance(record.stack_info, str):
            record.stack_info = redact_oauth_callback_secrets(record.stack_info)
        for key, value in list(record.__dict__.items()):
            if key in {"msg", "args", "exc_info", "exc_text", "stack_info"}:
                continue
            if isinstance(value, str) and "integrations/" in value:
                setattr(record, key, redact_oauth_callback_secrets(value))
        return True


_REDACTION_FILTER = OAuthCallbackQueryRedactionFilter()


def _install_handler_redaction() -> None:
    """Run redaction inside every handler, including ones attached later.

    Logger filters do not see records propagated from a child logger, and
    exception text is formatted by the handler. Hooking ``Handler.handle``
    covers access logs and ``logger.exception`` output.
    """
    if getattr(logging.Handler.handle, "_oauth_callback_redaction", False):
        return
    original = logging.Handler.handle

    def handle(self, record):
        _REDACTION_FILTER.filter(record)
        return original(self, record)

    handle._oauth_callback_redaction = True
    logging.Handler.handle = handle


def install_oauth_callback_log_redaction(*handlers: logging.Handler) -> None:
    """Attach the redaction filter to access loggers and the given handlers.

    Logger filters do not run for records propagated from a child logger, so
    the JSON handler on the root logger needs the filter too.
    """
    _install_handler_redaction()
    filt = _REDACTION_FILTER
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
