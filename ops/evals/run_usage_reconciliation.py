"""Manual usage-reconciliation runner.

Usage:
    python ops/evals/run_usage_reconciliation.py
    python ops/evals/run_usage_reconciliation.py --tenant-id <uuid>

Prints a table of per-tenant usage vs. plan caps for the current billing cycle.
Highlights rows where any counter exceeds its cap.

No writes are made — read-only audit.
"""

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _format_row(r: dict) -> str:
    tid = r.get("tenant_id", "unknown")[:12]
    plan = r.get("plan", "?")[:12]
    err = r.get("error")
    if err:
        return f"  {tid:<14} {plan:<12} ERROR: {err}"

    conv = r.get("conversations", {})
    runs = r.get("agent_runs", {})
    ai = r.get("ai_tokens", {})

    conv_str = (
        f"{conv.get('used')}/{conv.get('cap') or 'unlim'}"
        f" ({conv.get('drift_pct') or 0:.1f}%)" if conv.get("cap") else
        f"{conv.get('used')}/unlim"
    )
    runs_str = f"{runs.get('used')}/{runs.get('cap')} ({runs.get('drift_pct', 0):.1f}%)"
    ai_str = f"{ai.get('used')}/{ai.get('hard_limit')} ({ai.get('drift_pct', 0):.1f}%)"
    flag = " <<OVER>>" if r.get("any_over_cap") else ""

    return (
        f"  {tid:<14} {plan:<12} conv={conv_str:<22} "
        f"runs={runs_str:<22} ai={ai_str}{flag}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Billing usage reconciliation")
    parser.add_argument(
        "--tenant-id",
        metavar="UUID",
        help="Reconcile a single tenant instead of all.",
    )
    args = parser.parse_args()

    from backend.models.database import get_service_supabase
    from backend.services.billing_reconciliation import reconcile_all, reconcile_tenant_usage

    db = get_service_supabase()

    if args.tenant_id:
        results = [reconcile_tenant_usage(db, args.tenant_id)]
    else:
        results = reconcile_all(db)

    period = results[0].get("period_month", "?") if results else "?"
    print(f"\nBilling reconciliation — period: {period}")
    print(f"{'tenant_id':<16} {'plan':<12} {'conversations':<24} {'agent_runs':<24} ai_tokens")
    print("-" * 100)

    over_cap_count = 0
    for r in results:
        print(_format_row(r))
        if r.get("any_over_cap"):
            over_cap_count += 1

    print("-" * 100)
    print(f"  Total: {len(results)} tenant(s) — {over_cap_count} over cap\n")

    if over_cap_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
