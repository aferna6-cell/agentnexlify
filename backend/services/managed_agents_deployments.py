"""Scheduled deployments for Claude Managed Agents.

A *deployment* runs a provisioned agent on a recurring cron schedule, on
Anthropic's infrastructure. Each firing creates a normal session; each attempt
is recorded as a *deployment run* whether or not the session started.

Why this exists: several of our recurring agent jobs run as GitHub Actions cron
workflows that spin up an `ubuntu-latest` runner purely to make an API call to
an agent that executes on Anthropic's side anyway. A deployment does the same
work with no runner, and adds a per-run spend cap, a run history, and webhooks.
See `docs/managed-agents.md` and `.claude/rules/task-budgets.md`.

This lives in its own module rather than in `managed_agents.py` because that
file is already at the project's 600-line god-class threshold
(`.claude/rules/user-rules.md` Rule 9 / Rule 12).

Endpoints wrapped:
    POST   /v1/deployments                  create
    POST   /v1/deployments/{id}             update
    POST   /v1/deployments/{id}/pause       suspend future firings
    POST   /v1/deployments/{id}/unpause     resume (missed firings are NOT backfilled)
    POST   /v1/deployments/{id}/archive     terminal, cannot be undone
    POST   /v1/deployments/{id}/run         fire once, now, outside the schedule
    GET    /v1/deployments                  list
    GET    /v1/deployment_runs              list runs (filter by deployment / errors)

All of them require `?beta=true` in addition to the `managed-agents-2026-04-01`
beta header that `ManagedAgentsClient` already sends.
"""

import logging
from typing import Any

from backend.services.managed_agents import ManagedAgentsClient, build_budget

logger = logging.getLogger(__name__)

# Deployment endpoints require this query param on top of the beta header.
_BETA_PARAMS: dict[str, Any] = {"beta": "true"}

# Anthropic caps an organization at 1000 scheduled deployments.
MAX_DEPLOYMENTS_PER_ORG = 1000


def create_deployment(
    client: ManagedAgentsClient,
    *,
    name: str,
    agent_id: str,
    environment_id: str,
    cron_expression: str,
    timezone: str,
    kickoff_text: str,
    budget_cents: int | None = None,
    resources: list[dict[str, Any]] | None = None,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create a scheduled deployment.

    `cron_expression` is standard 5-field POSIX cron (minute hour day-of-month
    month day-of-week), evaluated against wall-clock time in `timezone` (an
    IANA identifier such as "America/New_York").

    DST caveat, straight from the API docs: wall-clock times that do not exist
    on a spring-forward day never fire, and times that occur twice on a
    fall-back day fire twice. Schedule outside the local 01:00-03:00 window, or
    use UTC, when a missed or duplicated run would matter.

    Execution is jittered by up to 15% of the inter-run interval (min 5s, max
    9 min) to spread load, so a run does not land exactly on the stated minute.

    `budget_cents` is copied onto EVERY session the deployment starts — it
    bounds each run separately, not the deployment's cumulative spend. A
    deployment with a 2000-cent cap can spend up to ~$20 per run, forever.

    The response carries `schedule.upcoming_runs_at`; log it and eyeball the
    times before trusting a new schedule.
    """
    body: dict[str, Any] = {
        "name": name,
        "agent": agent_id,
        "environment_id": environment_id,
        "initial_events": [
            {"type": "user.message", "content": [{"type": "text", "text": kickoff_text}]}
        ],
        "schedule": {
            "type": "cron",
            "expression": cron_expression,
            "timezone": timezone,
        },
    }
    if budget_cents is not None:
        body["budget"] = build_budget(budget_cents)
    if resources:
        body["resources"] = resources
    if metadata:
        body["metadata"] = metadata

    result = client.request("POST", "/v1/deployments", json_body=body, params=_BETA_PARAMS)
    schedule = result.get("schedule") or {}
    logger.info(
        "created deployment %s (%s) cron=%r tz=%s next=%s",
        result.get("id"),
        name,
        cron_expression,
        timezone,
        (schedule.get("upcoming_runs_at") or [])[:3],
    )
    return result


def update_deployment(
    client: ManagedAgentsClient, deployment_id: str, **changes: Any
) -> dict[str, Any]:
    """Patch a deployment. Only the fields you pass are changed.

    A budget change applies to runs started AFTER the update; a session already
    running keeps the cap it started with. Unlike a session budget, a
    deployment budget can be cleared with `budget=None` and set again later.
    """
    return client.request(
        "POST", f"/v1/deployments/{deployment_id}", json_body=changes, params=_BETA_PARAMS
    )


def pause_deployment(client: ManagedAgentsClient, deployment_id: str) -> dict[str, Any]:
    """Suspend future firings. Sessions from earlier runs keep executing, and
    manual `run_deployment` calls still work while paused."""
    return client.request(
        "POST", f"/v1/deployments/{deployment_id}/pause", params=_BETA_PARAMS
    )


def unpause_deployment(client: ManagedAgentsClient, deployment_id: str) -> dict[str, Any]:
    """Resume from the next scheduled occurrence. Missed firings during the
    pause are NOT backfilled."""
    return client.request(
        "POST", f"/v1/deployments/{deployment_id}/unpause", params=_BETA_PARAMS
    )


def archive_deployment(client: ManagedAgentsClient, deployment_id: str) -> dict[str, Any]:
    """Terminal. The schedule stops and the deployment can never be modified
    again. Use `pause_deployment` if you might want it back."""
    return client.request(
        "POST", f"/v1/deployments/{deployment_id}/archive", params=_BETA_PARAMS
    )


def run_deployment(client: ManagedAgentsClient, deployment_id: str) -> dict[str, Any]:
    """Fire once immediately, outside the schedule. Records a run with
    `trigger_context.type == "manual"`. Use this to prove a deployment works
    before trusting its cron."""
    return client.request(
        "POST", f"/v1/deployments/{deployment_id}/run", params=_BETA_PARAMS
    )


def list_deployments(client: ManagedAgentsClient) -> list[dict[str, Any]]:
    resp = client.request("GET", "/v1/deployments", params=_BETA_PARAMS)
    data = resp.get("data") if isinstance(resp, dict) else None
    return data if isinstance(data, list) else []


def find_deployment_by_name(
    client: ManagedAgentsClient, name: str
) -> dict[str, Any] | None:
    """Look up a deployment by its display name, so provisioning can be
    idempotent the same way `provision.py` is for agents."""
    for deployment in list_deployments(client):
        if deployment.get("name") == name and not deployment.get("archived_at"):
            return deployment
    return None


def list_deployment_runs(
    client: ManagedAgentsClient,
    deployment_id: str,
    *,
    has_error: bool | None = None,
) -> list[dict[str, Any]]:
    """List run records for a deployment, newest first.

    A run exists for every firing ATTEMPT, so this is where you see failures
    that never produced a session at all — `environment_archived_error`,
    `agent_archived_error`, `session_rate_limited_error`. Pass
    `has_error=True` to see only those.

    Note the platform's own failure semantics: a rate-limited firing is
    recorded and NOT retried until the next scheduled occurrence, and an
    archived agent/environment/vault auto-pauses the deployment. So an
    unattended deployment can be quietly paused — check
    `paused_reason` periodically rather than assuming it is still live.
    """
    params: dict[str, Any] = {**_BETA_PARAMS, "deployment_id": deployment_id}
    if has_error is not None:
        params["has_error"] = "true" if has_error else "false"
    resp = client.request("GET", "/v1/deployment_runs", params=params)
    data = resp.get("data") if isinstance(resp, dict) else None
    return data if isinstance(data, list) else []
