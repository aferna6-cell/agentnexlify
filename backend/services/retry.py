"""Retry utility for transient external service failures (Anthropic, Resend, Twilio)."""

import asyncio
import logging

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 529}  # 529 = Anthropic overloaded


async def with_retry(fn, max_retries: int = 2, backoff_base: float = 1.0, label: str = ""):
    """Call fn() with exponential backoff retries on transient errors.

    Retries on: 5xx status codes, 529 (Anthropic overloaded), timeouts, connection errors.
    Raises immediately on: 4xx errors, non-transient exceptions.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            status = getattr(getattr(e, "response", None), "status_code", getattr(e, "status_code", 0))
            err_str = str(e).lower()
            is_timeout = "timeout" in err_str or "timed out" in err_str
            is_connection = "connection" in err_str or "connect" in err_str
            is_retryable = status in RETRYABLE_STATUS_CODES or is_timeout or is_connection

            if not is_retryable or attempt == max_retries:
                raise

            wait = backoff_base * (2 ** attempt)
            logger.warning(
                "Retry %d/%d for %s after %.1fs (error: %s)",
                attempt + 1, max_retries, label or "call", wait, str(e)[:200],
            )
            await asyncio.sleep(wait)

    raise last_error
