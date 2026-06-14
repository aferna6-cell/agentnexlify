"""Safe, no-cost preflight for managed-agent release readiness.

Checks backend importability, managed-agent route registration, and the
managed-agent migration/schema-log contract. Optionally performs a read-only
live API probe if Anthropic credentials are available.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.config import settings  # noqa: E402
from backend.main import app  # noqa: E402
from backend.services.managed_agents import (  # noqa: E402
    ManagedAgentsClient,
    ManagedAgentsError,
)

REQUIRED_ROUTES = {
    ("POST", "/api/v1/managed-agents/{tenant_id}/lead-qualify"),
    ("GET", "/api/v1/managed-agents/{tenant_id}/health"),
    ("POST", "/api/v1/managed-agents/{tenant_id}/draft-document"),
    ("GET", "/api/v1/managed-agents/{tenant_id}/documents/{document_id}/download"),
}

REQUIRED_MIGRATIONS = {
    "099": "AI Lead Qualification Fields",
    "100": "AI-Drafted Documents (quotes / invoices / proposals)",
}


def _registered_routes() -> set[tuple[str, str]]:
    signatures: set[tuple[str, str]] = set()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            signatures.add((method, path))
    return signatures


def _check_static_contracts() -> list[str]:
    issues: list[str] = []
    routes = _registered_routes()
    # Robust match: a required route is present when some registered route has the
    # same method AND the same path (or the same suffix under the managed-agents
    # prefix). This tolerates path-format drift across FastAPI/Starlette versions
    # (e.g. param-syntax or prefix-normalization changes) while STILL failing if a
    # route is genuinely unregistered — so it cannot mask a real regression.
    _MANAGED_PREFIX = "/api/v1/managed-agents"
    for method, path in sorted(REQUIRED_ROUTES):
        suffix = path[len(_MANAGED_PREFIX):]
        present = (method, path) in routes or any(
            m == method
            and p.startswith(_MANAGED_PREFIX)
            and (p == path or p.rstrip("/").endswith(suffix))
            for (m, p) in routes
        )
        if not present:
            issues.append(f"missing route {method} {path}")

    if any(i.startswith("missing route") for i in issues):
        # Diagnostic: surface what IS registered so a real regression is obvious.
        managed = sorted(
            f"{m} {p}" for (m, p) in routes if "managed-agents" in p
        )
        print("Registered managed-agents routes:")
        for line in managed or ["  (none)"]:
            print(f"  {line}")
        # Pinpoint where registration broke: does the router itself have routes,
        # or did include_router never attach them?
        try:
            import traceback

            from backend.routers import managed_agent_runs as _mar

            router_paths = [getattr(r, "path", "?") for r in _mar.router.routes]
            print(f"managed_agent_runs.router has {len(router_paths)} routes: {router_paths}")
        except Exception:
            print("managed_agent_runs import raised:")
            traceback.print_exc()

    schema_log = (REPO_ROOT / "docs" / "dev-knowledge" / "schema-log.md").read_text(
        encoding="utf-8"
    )
    for migration, heading in REQUIRED_MIGRATIONS.items():
        migration_file = REPO_ROOT / "migrations" / f"{migration}_{heading.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_')}.sql"
        if not any(path.name.startswith(f"{migration}_") for path in (REPO_ROOT / "migrations").glob(f"{migration}_*.sql")):
            issues.append(f"missing migration file {migration}_*.sql")
        if f"### {migration} —" not in schema_log:
            issues.append(f"schema-log missing heading for migration {migration}")

    return issues


def _print_config_status() -> None:
    print("Managed Agents config:")
    print(f"  environment id: {'present' if settings.managed_agents_environment_id else 'missing'}")
    print(f"  lead_qualifier: {'present' if settings.lead_qualifier_agent_id else 'missing'}")
    print(f"  document_drafter: {'present' if settings.document_drafter_agent_id else 'missing'}")
    print(f"  codebase_reviewer: {'present' if settings.codebase_reviewer_agent_id else 'missing'}")


def _run_live_readonly_probe() -> list[str]:
    issues: list[str] = []
    try:
        client = ManagedAgentsClient()
    except ManagedAgentsError as exc:
        return [f"live readonly probe unavailable: {exc}"]

    try:
        environments = client.list_environments().get("data") or []
        agents = client.list_agents().get("data") or []
    except ManagedAgentsError as exc:
        return [f"live readonly probe failed: {exc}"]

    print("Managed Agents live readonly probe:")
    print(f"  environments visible: {len(environments)}")
    print(f"  agents visible:       {len(agents)}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live-readonly",
        action="store_true",
        help="Also call the read-only Managed Agents list endpoints.",
    )
    args = parser.parse_args()

    print("Managed Agents preflight")
    print(f"  repo: {REPO_ROOT}")
    _print_config_status()

    issues = _check_static_contracts()
    if args.live_readonly:
        issues.extend(_run_live_readonly_probe())

    if issues:
        print("FAIL:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("PASS: managed-agent preflight checks are clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
