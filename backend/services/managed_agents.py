"""Claude Managed Agents client for AgentNexLiFy.

Thin wrapper around the Anthropic Managed Agents REST API. We talk to the
API over raw HTTP via httpx rather than the anthropic SDK.

NOTE (2026-08-24): the original reason given here was that the pinned SDK
was 0.42.0 and predated the `client.beta.agents` bindings. That is no longer
true. VERIFIED against `anthropic` 0.125.0 (inside the current
`backend/requirements.txt` pin of `>=0.95.0,<1`): `client.beta.agents`,
`.sessions`, `.deployments`, `.vaults`, and `.memory_stores` all exist.

The wrapper is kept because it is working, tested
(`backend/tests/test_managed_agents.py`), and decoupled from the SDK's beta
surface — NOT because the SDK is incapable. Swapping to the SDK is a viable
cleanup whenever someone wants it; callers would not change.

API reference:
- Overview: https://platform.claude.com/docs/en/managed-agents/overview
- Endpoints: POST /v1/agents, /v1/sessions, /v1/environments (+ events, files)

Required headers (handled automatically):
- x-api-key: $ANTHROPIC_API_KEY
- anthropic-version: 2023-06-01
- anthropic-beta: managed-agents-2026-04-01

Mandatory flow:
    1. Create an Environment ONCE (reusable).
    2. Create an Agent ONCE (persisted + versioned). Store the agent_id.
    3. For every run: Create a Session (references agent + environment),
       then stream events and send user messages until the session is
       terminated or idle with a terminal stop_reason.

Do NOT call create_agent() in the request path — agents are setup-time
resources. See scripts/managed_agents/provision.py for the one-time bootstrap.
"""

import json
import logging
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
MANAGED_AGENTS_BETA = "managed-agents-2026-04-01"
FILES_BETA = "files-api-2025-04-14"
SKILLS_BETA = "skills-2025-10-02"

_DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=30.0)
# Streaming reads can be arbitrarily long — disable the read timeout.
_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=None, write=60.0, pool=30.0)

_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504, 529})

# $5. Well above a normal qualification / draft / extraction run, so it only
# bites on a genuine runaway loop. See default_session_budget_cents().
DEFAULT_SESSION_BUDGET_CENTS = 500


def default_session_budget_cents() -> int | None:
    """Central hard spend cap (US cents) for non-interactive product sessions.

    One knob, not a number copied across call sites
    (`.claude/rules/task-budgets.md`: "never hardcode budgets in dozens of
    places"). Override with MANAGED_AGENTS_SESSION_BUDGET_CENTS; set it to 0
    to disable the cap entirely.

    Apply this to every agent session a customer is not sitting and waiting
    on — background tasks, threadpool work, HTTP-triggered batch runs. Leave
    interactive paths (widget chat) uncapped: there, a truncated answer is
    worse than the marginal spend.
    """
    raw = os.environ.get("MANAGED_AGENTS_SESSION_BUDGET_CENTS", "").strip()
    if not raw:
        return DEFAULT_SESSION_BUDGET_CENTS
    try:
        return int(raw) or None
    except ValueError:
        logger.warning(
            "managed_agents: MANAGED_AGENTS_SESSION_BUDGET_CENTS=%r is not an "
            "integer; using the %d-cent default.",
            raw,
            DEFAULT_SESSION_BUDGET_CENTS,
        )
        return DEFAULT_SESSION_BUDGET_CENTS


def build_budget(cents: int) -> dict[str, Any]:
    """Build a session `budget` object capping spend at `cents` US cents.

    This is a HARD cap enforced by the platform, and is a different thing from
    the Messages API `task_budget` (advisory, token-denominated, the model
    paces itself against it). See .claude/rules/task-budgets.md.

    Semantics worth knowing before you pick a number:
      - The cap is checked BETWEEN model requests, not mid-request, so the
        in-flight request finishes. A session capped at 50 can settle at 53.
        Size the cap with that one-request margin in mind.
      - Reaching the cap makes the session go idle with
        stop_reason.type == "budget_reached". It is NOT terminated; history
        and sandbox survive. Raising the budget resumes it automatically.
      - Removing a budget is ONE-WAY. A session created without one can never
        be given one, and one whose budget was removed can never get it back.
        Change the budget instead of removing it.
      - Multiagent sessions share ONE budget across every thread, advisor
        consultations included.

    `amount` is sent as a string of whole cents on purpose — the API rejects
    decimal forms like "25.00", and a string avoids any float rounding.
    """
    if cents <= 0:
        raise ValueError(f"budget must be a positive number of cents, got {cents!r}")
    return {
        "type": "limit",
        "max_list_cost": {"amount": str(int(cents)), "currency": "USD"},
    }


class ManagedAgentsError(Exception):
    """Raised for any Managed Agents API failure."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        request_id: str | None = None,
        error_type: str | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.request_id = request_id
        self.error_type = error_type


@dataclass
class SessionTerminalState:
    """Summary of how a streamed session finished."""

    terminated: bool
    stop_reason_type: str | None
    last_event_id: str | None
    session_id: str | None = None


class ManagedAgentsClient:
    """Raw-HTTP client for Claude Managed Agents (beta)."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = API_BASE_URL,
        timeout: httpx.Timeout = _DEFAULT_TIMEOUT,
    ):
        resolved_key = api_key or settings.anthropic_api_key
        if not resolved_key:
            raise ManagedAgentsError(
                "ANTHROPIC_API_KEY is not set — Managed Agents requires an API key."
            )
        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ------------------------------------------------------------------
    # internal: request / streaming helpers
    # ------------------------------------------------------------------

    def _headers(self, *, extra_beta: str | None = None) -> dict[str, str]:
        beta = MANAGED_AGENTS_BETA
        if extra_beta and extra_beta != MANAGED_AGENTS_BETA:
            beta = f"{beta},{extra_beta}"
        return {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "anthropic-beta": beta,
            "content-type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        extra_beta: str | None = None,
        retries: int = 2,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = self._headers(extra_beta=extra_beta)
        last_exc: ManagedAgentsError | None = None

        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.request(
                        method, url, headers=headers, json=json_body, params=params,
                    )
            except httpx.RequestError as exc:
                last_exc = ManagedAgentsError(f"Transport error: {exc}")
                if attempt < retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "managed_agents: %s %s transport error, retrying in %ds",
                        method, path, wait,
                    )
                    time.sleep(wait)
                    continue
                raise last_exc from exc

            if resp.status_code == 204:
                return {}

            if resp.status_code < 400:
                try:
                    return resp.json()
                except json.JSONDecodeError as exc:
                    raise ManagedAgentsError(f"Invalid JSON in response: {exc}") from exc

            # Error path — parse envelope.
            request_id = resp.headers.get("request-id") or resp.headers.get("x-request-id")
            try:
                body = resp.json()
            except json.JSONDecodeError:
                body = {}
            err = body.get("error") if isinstance(body, dict) else None
            err = err if isinstance(err, dict) else {}
            message = err.get("message") or resp.text or f"HTTP {resp.status_code}"
            error_type = err.get("type")

            last_exc = ManagedAgentsError(
                f"HTTP {resp.status_code}: {message}",
                status=resp.status_code,
                request_id=request_id,
                error_type=error_type,
            )

            if resp.status_code in _RETRYABLE_STATUSES and attempt < retries:
                retry_after = resp.headers.get("retry-after")
                wait = (
                    int(retry_after)
                    if retry_after and retry_after.isdigit()
                    else 2 ** attempt
                )
                logger.warning(
                    "managed_agents: HTTP %d on %s %s, retrying in %ds (request_id=%s)",
                    resp.status_code, method, path, wait, request_id,
                )
                time.sleep(wait)
                continue
            raise last_exc

        # Exhausted retries.
        assert last_exc is not None
        raise last_exc

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        extra_beta: str | None = None,
    ) -> dict[str, Any]:
        """Public escape hatch for endpoints implemented in sibling modules.

        Same retry/backoff/error-envelope handling as every built-in method.
        Used by `managed_agents_deployments.py` so that module doesn't have to
        reach into `_request`. Prefer a named method on this class for anything
        that becomes load-bearing.
        """
        return self._request(
            method, path, json_body=json_body, params=params, extra_beta=extra_beta
        )

    # ------------------------------------------------------------------
    # environments
    # ------------------------------------------------------------------

    def create_environment(
        self,
        *,
        name: str,
        networking: str = "unrestricted",
        description: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "name": name,
            "config": {
                "type": "cloud",
                "networking": {"type": networking},
            },
        }
        if description:
            body["description"] = description
        if metadata:
            body["metadata"] = metadata
        return self._request("POST", "/v1/environments", json_body=body)

    def list_environments(self) -> dict[str, Any]:
        return self._request("GET", "/v1/environments")

    def get_environment(self, environment_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/environments/{environment_id}")

    # ------------------------------------------------------------------
    # agents (create once, reuse forever)
    # ------------------------------------------------------------------

    def create_agent(
        self,
        *,
        name: str,
        model: str | dict[str, Any],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        skills: list[dict[str, Any]] | None = None,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        multiagent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a persistent, versioned agent.

        `model` accepts either a plain ID string (`"claude-opus-4-8"`) or the
        object form, which is the only way to set effort / speed / geo:

            model={"id": "claude-opus-4-8", "effort": "high"}

        `multiagent` declares a coordinator roster. Two useful shapes:

            # delegate to other provisioned agents
            {"type": "coordinator",
             "agents": [{"type": "agent", "id": REVIEWER_AGENT_ID}]}

            # native advisor — a stronger model this agent can consult mid-turn
            {"type": "coordinator",
             "agents": [{"type": "advisor", "model": "claude-opus-4-8"}]}

        On the advisor: at most one advisor entry per roster, and the agent's
        own model must not be more capable than the advisor's. Prefer Opus 4.8
        over Opus 5 here — Opus 5 is a redacted-result advisor, so the advice
        reaches your event stream as a `{"type": "redacted"}` placeholder
        (the agent still reads it server-side) and you lose the ability to
        read the brief in traces.
        """
        body: dict[str, Any] = {"name": name, "model": model}
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools
        if mcp_servers:
            body["mcp_servers"] = mcp_servers
        if skills:
            body["skills"] = skills
        if multiagent:
            body["multiagent"] = multiagent
        if description:
            body["description"] = description
        if metadata:
            body["metadata"] = metadata
        return self._request("POST", "/v1/agents", json_body=body)

    def update_agent(self, agent_id: str, **changes: Any) -> dict[str, Any]:
        """Update an agent — each call bumps the version and returns the
        full new agent object (including `version`). Existing sessions keep
        their pinned version; new sessions using the string shorthand pick up
        the latest version automatically.
        """
        return self._request("POST", f"/v1/agents/{agent_id}", json_body=changes)

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/agents/{agent_id}")

    def list_agents(self) -> dict[str, Any]:
        return self._request("GET", "/v1/agents")

    def archive_agent(self, agent_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/agents/{agent_id}/archive")

    # ------------------------------------------------------------------
    # sessions
    # ------------------------------------------------------------------

    def create_session(
        self,
        *,
        agent_id: str,
        environment_id: str,
        title: str | None = None,
        agent_version: int | None = None,
        resources: list[dict[str, Any]] | None = None,
        vault_ids: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        budget_cents: int | None = None,
    ) -> dict[str, Any]:
        """Start a new session. Pass `agent_version` to pin to a specific
        version for reproducibility, or omit it to use the latest.

        `budget_cents` sets a HARD platform-enforced spend ceiling on this
        session (see `build_budget`). Set it on every non-interactive session
        — anything autonomous, scheduled, or batch. Leave it off for
        user-facing interactive paths (widget chat), where correctness beats
        cost pacing. A budget can only be attached at creation time.
        """
        agent_ref: Any
        if agent_version is not None:
            agent_ref = {"type": "agent", "id": agent_id, "version": agent_version}
        else:
            agent_ref = agent_id  # string shorthand → latest version

        body: dict[str, Any] = {
            "agent": agent_ref,
            "environment_id": environment_id,
        }
        if title:
            body["title"] = title
        if resources:
            body["resources"] = resources
        if vault_ids:
            body["vault_ids"] = vault_ids
        if metadata:
            body["metadata"] = metadata
        if budget_cents is not None:
            body["budget"] = build_budget(budget_cents)
        return self._request("POST", "/v1/sessions", json_body=body)

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/sessions/{session_id}")

    def archive_session(self, session_id: str) -> dict[str, Any]:
        return self._request("POST", f"/v1/sessions/{session_id}/archive")

    def delete_session(self, session_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/sessions/{session_id}")

    # ------------------------------------------------------------------
    # events (send)
    # ------------------------------------------------------------------

    def send_user_message(self, session_id: str, text: str) -> dict[str, Any]:
        """Send a single plain-text user.message event to the session."""
        body = {
            "events": [
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": text}],
                }
            ]
        }
        return self._request(
            "POST", f"/v1/sessions/{session_id}/events", json_body=body,
        )

    def send_custom_tool_result(
        self,
        session_id: str,
        *,
        custom_tool_use_id: str,
        content: list[dict[str, Any]],
        is_error: bool = False,
    ) -> dict[str, Any]:
        body = {
            "events": [
                {
                    "type": "user.custom_tool_result",
                    "custom_tool_use_id": custom_tool_use_id,
                    "content": content,
                    "is_error": is_error,
                }
            ]
        }
        return self._request(
            "POST", f"/v1/sessions/{session_id}/events", json_body=body,
        )

    def send_tool_confirmation(
        self,
        session_id: str,
        *,
        tool_use_id: str,
        allow: bool,
        deny_message: str | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "type": "user.tool_confirmation",
            "tool_use_id": tool_use_id,
            "result": "allow" if allow else "deny",
        }
        if not allow and deny_message:
            event["deny_message"] = deny_message
        return self._request(
            "POST",
            f"/v1/sessions/{session_id}/events",
            json_body={"events": [event]},
        )

    def send_interrupt(self, session_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/sessions/{session_id}/events",
            json_body={"events": [{"type": "user.interrupt"}]},
        )

    # ------------------------------------------------------------------
    # events (receive)
    # ------------------------------------------------------------------

    def list_events(
        self,
        session_id: str,
        *,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return the first page of session events. For reconnect flows you
        want to call this BEFORE tailing stream_events() and dedupe by id.

        See docs/managed-agents.md, "Known limitations" → "No SSE reconnect /
        replay". (Earlier versions of this docstring cited an Anthropic
        workshop handout, `shared/managed-agents-client-patterns.md`, which was
        never vendored into this repo — the pattern it described is written out
        in docs/managed-agents.md instead.)
        """
        resp = self._request(
            "GET",
            f"/v1/sessions/{session_id}/events",
            params={"limit": limit},
        )
        data = resp.get("data") if isinstance(resp, dict) else None
        return data if isinstance(data, list) else []

    def stream_events(self, session_id: str) -> Iterator[dict[str, Any]]:
        """Tail the SSE event stream, yielding each event as a dict.

        The caller is responsible for the break condition. The correct gate
        (see docs/managed-agents.md, "Using an agent from code") is:

            for event in client.stream_events(session_id):
                ...
                if event["type"] == "session.status_terminated":
                    break
                if event["type"] == "session.status_idle":
                    stop = event.get("stop_reason", {}) or {}
                    if stop.get("type") != "requires_action":
                        break

        Do not break on bare `session.status_idle` — the session goes idle
        transiently while waiting for tool confirmations or custom tool
        results.
        """
        url = f"{self._base_url}/v1/sessions/{session_id}/events/stream"
        headers = self._headers()
        headers["accept"] = "text/event-stream"

        with httpx.Client(timeout=_STREAM_TIMEOUT) as client:
            with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code >= 400:
                    body = resp.read().decode("utf-8", errors="replace")
                    raise ManagedAgentsError(
                        f"Stream failed: HTTP {resp.status_code}: {body[:500]}",
                        status=resp.status_code,
                    )
                for line in resp.iter_lines():
                    if not line or line.startswith(":"):
                        # blank line or SSE comment (heartbeat) — ignore
                        continue
                    if not line.startswith("data:"):
                        # anthropic's stream uses single-line data frames;
                        # unexpected lines just get skipped
                        continue
                    raw = line[5:].lstrip()
                    if raw == "[DONE]":
                        return
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning(
                            "managed_agents: bad SSE data frame (first 200 chars): %s",
                            raw[:200],
                        )
                        continue
                    yield payload

    # ------------------------------------------------------------------
    # files (Anthropic Files API — beta: files-api-2025-04-14)
    # ------------------------------------------------------------------
    #
    # Managed Agents sessions expose the files an agent writes to
    # `/mnt/session/outputs/` through the Files API. The agent gets a
    # `file_id` when it writes, and we can retrieve the bytes via
    # `GET /v1/files/{file_id}/content` using the files-api-2025-04-14
    # beta header.
    #
    # Unlike the other endpoints on this client, the Files API is a
    # SEPARATE beta and must be opted in to by passing `extra_beta`.

    def get_file_metadata(self, file_id: str) -> dict[str, Any]:
        """Return metadata for an uploaded or session-written file."""
        return self._request(
            "GET",
            f"/v1/files/{file_id}",
            extra_beta=FILES_BETA,
        )

    def get_file_content(self, file_id: str) -> bytes:
        """Download the raw bytes of a file.

        The Files API returns a binary body — not JSON — so we bypass
        `_request` (which parses JSON) and go straight to httpx.
        """
        url = f"{self._base_url}/v1/files/{file_id}/content"
        headers = self._headers(extra_beta=FILES_BETA)
        # Accept anything — the server picks the content-type.
        headers["accept"] = "*/*"

        last_exc: ManagedAgentsError | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.get(url, headers=headers)
            except httpx.RequestError as exc:
                last_exc = ManagedAgentsError(f"Transport error: {exc}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise last_exc

            if resp.status_code == 200:
                return resp.content

            # Map the error envelope for consistent debugging.
            try:
                body = resp.json()
            except json.JSONDecodeError:
                body = {"error": {"message": resp.text[:500]}}
            error = body.get("error") if isinstance(body, dict) else None
            msg = (
                error.get("message") if isinstance(error, dict) else str(body)
            )
            err = ManagedAgentsError(
                f"HTTP {resp.status_code}: {msg}",
                status=resp.status_code,
                request_id=resp.headers.get("request-id"),
                error_type=error.get("type") if isinstance(error, dict) else None,
            )
            if resp.status_code in _RETRYABLE_STATUSES and attempt < 2:
                time.sleep(2 ** attempt)
                last_exc = err
                continue
            raise err

        if last_exc:
            raise last_exc
        raise ManagedAgentsError("get_file_content: exhausted retries")

    # ------------------------------------------------------------------
    # convenience: run until terminal
    # ------------------------------------------------------------------

    def run_until_idle(
        self,
        session_id: str,
        *,
        kickoff_text: str | None = None,
    ) -> SessionTerminalState:
        """Open the stream, optionally send a kickoff user.message, and drain
        events until the session hits a terminal state.

        Custom tool calls are NOT handled here — if the agent has custom
        tools, use stream_events() directly and implement the round-trip via
        send_custom_tool_result().
        """
        stream = self.stream_events(session_id)
        if kickoff_text is not None:
            # Stream is already opened above; it's safe to send now and the
            # stream will pick up the agent's response.
            self.send_user_message(session_id, kickoff_text)

        last_event_id: str | None = None
        for event in stream:
            event_type = event.get("type", "")
            if isinstance(event.get("id"), str):
                last_event_id = event["id"]
            if event_type == "session.status_terminated":
                return SessionTerminalState(
                    terminated=True,
                    stop_reason_type=None,
                    last_event_id=last_event_id,
                    session_id=session_id,
                )
            if event_type == "session.status_idle":
                stop_reason = event.get("stop_reason") or {}
                stop_type = stop_reason.get("type") if isinstance(stop_reason, dict) else None
                if stop_type != "requires_action":
                    return SessionTerminalState(
                        terminated=False,
                        stop_reason_type=stop_type,
                        last_event_id=last_event_id,
                        session_id=session_id,
                    )
        # Stream ended without a terminal event — treat as unterminated.
        return SessionTerminalState(
            terminated=False,
            stop_reason_type=None,
            last_event_id=last_event_id,
            session_id=session_id,
        )


def get_default_client() -> ManagedAgentsClient:
    """Construct a client using the project's ANTHROPIC_API_KEY setting."""
    return ManagedAgentsClient()
