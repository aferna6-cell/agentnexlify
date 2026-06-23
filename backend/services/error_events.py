"""Platform-level error event logger.

Inserts one row into the ``error_events`` table as a best-effort local
fallback when Sentry is not configured (or as a secondary sink when it is).

Rules enforced here:
- NEVER raises into the request path.  Every exception is caught, logged,
  and swallowed so callers stay unaffected.
- No ``from __future__ import annotations`` (critical rule for FastAPI files).
- Uses get_service_supabase() — the privileged client for internal platform
  ops.  The error_events table has no tenant scope (platform-level).
"""

import logging
import traceback
from typing import Any

logger = logging.getLogger(__name__)


def record_error_event(
    *,
    message: str,
    level: str = "error",
    source: str = "api",
    path: str | None = None,
    status_code: int | None = None,
    exc: BaseException | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Insert one error row into ``error_events``.  Best-effort; never raises.

    Args:
        message: Short human-readable description of the error.
        level:   Severity label ("error", "critical", "warning").
        source:  Originating component ("api", "automation", etc.).
        path:    HTTP path that triggered the error, if applicable.
        status_code: HTTP status code returned to the caller.
        exc:     Exception instance; stack trace extracted automatically.
        context: Optional freeform dict stored as JSONB for extra metadata.
    """
    try:
        from backend.models.database import get_service_supabase

        stack: str | None = None
        if exc is not None:
            try:
                stack = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
            except Exception as fmt_err:
                logger.warning("error_events: could not format traceback: %s", fmt_err)

        row: dict[str, Any] = {
            "level": level,
            "source": source,
            "message": message,
            "path": path,
            "status_code": status_code,
            "stack": stack,
            "context": context,
        }

        get_service_supabase().table("error_events").insert(row).execute()
    except Exception as insert_err:
        # Log but NEVER re-raise — the request path must not be affected.
        logger.warning(
            "error_events: failed to insert row (swallowed): %s", insert_err
        )
