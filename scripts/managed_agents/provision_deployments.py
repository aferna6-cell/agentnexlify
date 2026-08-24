"""Provision scheduled deployments from the `deployments:` block of
`config/managed_agents.yaml`.

A deployment runs a provisioned agent on a cron schedule on Anthropic's
infrastructure — no GitHub Actions runner, a hard per-run spend cap, a run
history, and webhooks. Several of our recurring agent jobs currently burn
runner minutes to make an API call to an agent that executes remotely anyway.

    python -m scripts.managed_agents.provision_deployments --dry-run
    python -m scripts.managed_agents.provision_deployments
    python -m scripts.managed_agents.provision_deployments --list

Idempotent, the same way `provision.py` is: deployments are matched by `name`,
created if absent, updated in place if present.

## Which jobs can actually migrate

A deployment's session runs in Anthropic's sandbox. It CANNOT push to git.
So a workflow qualifies only if it does not persist output into this repo.

    Qualifies:      agent produces a result consumed via webhook, API, or the
                    session's own outputs.
    Does NOT yet:   `field-monitor-weekly.yml` — the runner's second job is
                    `git commit` + `git push` of the digest into
                    `knowledge-base/raw/` for the kb-compile pipeline. Moving
                    the schedule without first solving output persistence
                    would silently stop the digest from ever landing.

Two viable designs for the ones that write back, neither implemented yet:
  1. Deployment fires on schedule; a webhook consumer in the backend receives
     the completion event, pulls the session output, and writes it.
  2. Deployment fires on schedule; a much smaller `repository_dispatch`
     workflow wakes only to collect and commit (still a runner, but seconds
     instead of a full dependency install plus the agent's whole runtime).

Until one exists, keep those crons and rely on the per-session spend cap in
`scripts/managed_agents/_smoke_common.py`.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml  # noqa: E402

from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
)
from backend.services.managed_agents_deployments import (  # noqa: E402
    create_deployment,
    find_deployment_by_name,
    list_deployments,
    update_deployment,
)

CONFIG_PATH = _REPO_ROOT / "config" / "managed_agents.yaml"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("provision_deployments")


def _load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"config file not found: {CONFIG_PATH}")
    with CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def _resolve_agent_id(slug: str, agents_cfg: dict[str, Any]) -> str:
    """Deployments reference an agent by ID, which `provision.py` writes into
    `.env.managed_agents`. Read it from the environment the same way the
    backend does."""
    import os

    agent_cfg = agents_cfg.get(slug) or {}
    env_var = agent_cfg.get("env_var") or f"{slug.upper()}_AGENT_ID"
    agent_id = os.environ.get(env_var, "").strip()
    if not agent_id:
        raise SystemExit(
            f"{env_var} is not set — deployment for agent '{slug}' cannot be "
            f"created. Run `python -m scripts.managed_agents.provision` first "
            f"and source .env.managed_agents."
        )
    return agent_id


def _environment_id() -> str:
    import os

    env_id = os.environ.get("MANAGED_AGENTS_ENVIRONMENT_ID", "").strip()
    if not env_id:
        raise SystemExit(
            "MANAGED_AGENTS_ENVIRONMENT_ID is not set. Run "
            "`python -m scripts.managed_agents.provision` first."
        )
    return env_id


def _provision_one(
    client: ManagedAgentsClient | None,
    slug: str,
    cfg: dict[str, Any],
    agents_cfg: dict[str, Any],
    *,
    dry_run: bool,
) -> None:
    """`client` is None only when dry_run is True — the dry-run branch returns
    before any network call, so we never construct a client we won't use."""
    name = cfg.get("name") or f"AgentNexLiFy {slug}"
    schedule = cfg.get("schedule") or {}
    cron = schedule.get("cron")
    tz = schedule.get("timezone")
    if not cron or not tz:
        raise SystemExit(
            f"deployment '{slug}' needs schedule.cron and schedule.timezone"
        )

    if dry_run:
        logger.info(
            "[dry-run] would ensure deployment %s (agent=%s cron=%r tz=%s budget=%s)",
            name,
            cfg.get("agent"),
            cron,
            tz,
            cfg.get("budget_cents"),
        )
        return

    agent_id = _resolve_agent_id(cfg["agent"], agents_cfg)
    existing = find_deployment_by_name(client, name)

    if existing:
        update_deployment(
            client,
            existing["id"],
            schedule={"type": "cron", "expression": cron, "timezone": tz},
        )
        logger.info("updated deployment %s (%s)", existing["id"], name)
        return

    create_deployment(
        client,
        name=name,
        agent_id=agent_id,
        environment_id=_environment_id(),
        cron_expression=cron,
        timezone=tz,
        kickoff_text=cfg["kickoff"],
        budget_cents=cfg.get("budget_cents"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision Managed Agents scheduled deployments."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned actions, change nothing."
    )
    parser.add_argument(
        "--list", action="store_true", help="List existing deployments and exit."
    )
    args = parser.parse_args()

    cfg = _load_config()
    deployments_cfg = cfg.get("deployments") or {}
    agents_cfg = cfg.get("agents") or {}

    if args.list:
        try:
            client = ManagedAgentsClient()
            for dep in list_deployments(client):
                sched = dep.get("schedule") or {}
                logger.info(
                    "%s  %s  cron=%r tz=%s status=%s paused=%s",
                    dep.get("id"),
                    dep.get("name"),
                    sched.get("expression"),
                    sched.get("timezone"),
                    dep.get("status"),
                    dep.get("paused_reason"),
                )
        except ManagedAgentsError as exc:
            logger.error("list failed: %s", exc)
            return 1
        return 0

    if not deployments_cfg:
        logger.info(
            "No `deployments:` block in %s — nothing to provision. See this "
            "module's docstring for which jobs qualify.",
            CONFIG_PATH.relative_to(_REPO_ROOT),
        )
        return 0

    client = None if args.dry_run else ManagedAgentsClient()
    for slug, dep_cfg in deployments_cfg.items():
        try:
            _provision_one(client, slug, dep_cfg, agents_cfg, dry_run=args.dry_run)
        except ManagedAgentsError as exc:
            logger.error("deployment '%s' failed: %s", slug, exc)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
