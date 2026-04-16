"""HTTP client for the agent-service Node.js layer.

The agent-service wraps @anthropic-ai/claude-agent-sdk and exposes:
  POST /agents/<name>/run  ->  {"is_error": bool, "result": str|null, ...}

This module is the Python side of that interface. All functions are
synchronous (blocking httpx) — callers must use run_in_threadpool or
BackgroundTasks.

Graceful degradation: all functions return None when AGENT_SERVICE_URL
is not configured, so callers can fall back to the managed-agents path
without any extra branching.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_AGENT_SERVICE_URL: str = os.getenv("AGENT_SERVICE_URL", "").rstrip("/")

# Inner timeout passed to the Node service (it aborts the query at this point).
# Outer HTTP timeout is 2 s longer so the node process has time to return the
# error response before the httpx socket closes.
_DEFAULT_AGENT_TIMEOUT_S: float = 25.0


def is_configured() -> bool:
    """Return True when AGENT_SERVICE_URL is set and non-empty."""
    return bool(_AGENT_SERVICE_URL)


def run_agent_sync(
    agent_name: str,
    prompt: str,
    *,
    timeout: float = _DEFAULT_AGENT_TIMEOUT_S,
) -> dict[str, Any] | None:
    """Call agent-service synchronously. Returns None when not configured.

    On success returns the raw JSON dict from agent-service:
      {"is_error": false, "result": "<text>", "cost_usd": 0.001, "turns": 2}

    On agent-level error (timeout inside node, max_turns, etc.):
      {"is_error": true, "error": "<subtype>", "cost_usd": 0.0, "turns": 1}

    Returns None on HTTP error, connection failure, or unconfigured URL.
    Callers should fall back to managed-agents path when None is returned.

    Must be called from a threadpool — this is blocking.
    """
    if not _AGENT_SERVICE_URL:
        return None

    endpoint = f"{_AGENT_SERVICE_URL}/agents/{agent_name}/run"
    try:
        resp = httpx.post(
            endpoint,
            json={"prompt": prompt, "timeout_ms": int(timeout * 1000)},
            # Outer HTTP timeout is agent timeout + buffer for response encoding.
            timeout=timeout + 2.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        logger.warning(
            "agent_sdk_client: timeout calling %s (agent=%s)", endpoint, agent_name
        )
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "agent_sdk_client: HTTP %s from %s (agent=%s): %s",
            exc.response.status_code,
            endpoint,
            agent_name,
            exc.response.text[:200],
        )
        return None
    except Exception:
        logger.warning(
            "agent_sdk_client: error calling %s (agent=%s)",
            endpoint,
            agent_name,
            exc_info=True,
        )
        return None
