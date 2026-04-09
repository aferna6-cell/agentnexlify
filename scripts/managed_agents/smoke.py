"""Read-only smoke test for the Claude Managed Agents integration.

Hits `list_environments` and `list_agents` against the live API to confirm
that the API key, beta header, and HTTP envelope parsing all work. Does
NOT create, update, archive, or delete anything — safe to run in any
environment (including production).

Usage:

    python -m scripts.managed_agents.smoke

Exit codes:
    0 — auth + beta headers + list endpoints all work
    1 — transport or credential failure
    2 — unexpected API response shape
"""

import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.services.managed_agents import (  # noqa: E402
    MANAGED_AGENTS_BETA,
    ManagedAgentsClient,
    ManagedAgentsError,
)

logger = logging.getLogger("managed_agents.smoke")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    try:
        client = ManagedAgentsClient()
    except ManagedAgentsError as exc:
        logger.error("client init failed: %s", exc)
        return 1

    logger.info("beta header: %s", MANAGED_AGENTS_BETA)

    try:
        envs = client.list_environments()
    except ManagedAgentsError as exc:
        logger.error("list_environments failed: %s (request_id=%s)", exc, exc.request_id)
        return 1

    if not isinstance(envs, dict):
        logger.error("list_environments returned non-dict: %r", type(envs))
        return 2

    env_count = len(envs.get("data") or [])
    logger.info("list_environments: %d environment(s) visible", env_count)

    try:
        agents = client.list_agents()
    except ManagedAgentsError as exc:
        logger.error("list_agents failed: %s (request_id=%s)", exc, exc.request_id)
        return 1

    if not isinstance(agents, dict):
        logger.error("list_agents returned non-dict: %r", type(agents))
        return 2

    agent_list = agents.get("data") or []
    logger.info("list_agents: %d agent(s) visible", len(agent_list))
    for agent in agent_list[:5]:
        logger.info(
            "  - %s (%s) model=%s",
            agent.get("name"),
            agent.get("id"),
            agent.get("model") if isinstance(agent.get("model"), str) else "(object)",
        )

    print()
    print("Managed Agents smoke check PASSED.")
    print(f"  environments: {env_count}")
    print(f"  agents:       {len(agent_list)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
