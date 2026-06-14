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

# Optional shared secret. When set, it is sent as the X-Agent-Token header on
# every call and agent-service rejects requests without a matching value. This
# is defense-in-depth on top of Railway private networking: even if the service
# ever gets a public domain, it is not an open credit-burn endpoint. Unset =
# no header sent (dev parity / local runs), matching agent-service's open mode.
_AGENT_SERVICE_TOKEN: str = os.getenv("AGENT_SERVICE_TOKEN", "")


def _auth_headers() -> dict[str, str]:
    """Return the X-Agent-Token header when a shared secret is configured."""
    if _AGENT_SERVICE_TOKEN:
        return {"X-Agent-Token": _AGENT_SERVICE_TOKEN}
    return {}

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
            headers=_auth_headers(),
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


# Orchestration runs the vendored Agent OS engine, which may call Sonnet for a
# draft — give it more headroom than a single agent-service /agents/:name/run.
_DEFAULT_ORCHESTRATE_TIMEOUT_S: float = 90.0


def orchestrate_sync(
    account_id: str,
    ask: str,
    context: dict[str, Any],
    *,
    force_agent_id: str | None = None,
    timeout: float = _DEFAULT_ORCHESTRATE_TIMEOUT_S,
) -> dict[str, Any] | None:
    """Call agent-service POST /orchestrate. Returns None when not configured.

    agent-service is pure compute: it runs the engine over the SharedContext we
    pass and returns ``{"result": HandleResult, "record": RunRecordBundle}`` for
    the caller to persist. Returns None on unconfigured URL, HTTP error, or
    timeout so callers can surface a clear "engine unavailable" state.

    Must be called from a threadpool — this is blocking.
    """
    if not _AGENT_SERVICE_URL:
        return None

    endpoint = f"{_AGENT_SERVICE_URL}/orchestrate"
    body: dict[str, Any] = {"accountId": account_id, "ask": ask, "context": context}
    if force_agent_id:
        body["forceAgentId"] = force_agent_id
    try:
        resp = httpx.post(endpoint, json=body, headers=_auth_headers(), timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        logger.warning("agent_sdk_client: timeout calling %s", endpoint)
        return None
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "agent_sdk_client: HTTP %s from %s: %s",
            exc.response.status_code,
            endpoint,
            exc.response.text[:200],
        )
        return None
    except Exception:
        logger.warning("agent_sdk_client: error calling %s", endpoint, exc_info=True)
        return None
