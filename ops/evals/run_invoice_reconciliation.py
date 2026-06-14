"""Invoice reconciliation eval runner.

Usage:
    python ops/evals/run_invoice_reconciliation.py
    python ops/evals/run_invoice_reconciliation.py --tenant-id <uuid>

Prints a per-tenant JSON summary to stdout.
Exits 1 if any internal consistency mismatch is found.

No writes are made — read-only audit.
Stripe cross-check is skipped gracefully when STRIPE_SECRET_KEY is absent
(safe to run in CI without secrets).
"""

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _format_row(r: dict) -> str:
    """Return a single human-readable summary line for one tenant result."""
    tid = r.get("tenant_id", "unknown")[:14]
    err = r.get("error")
    if err:
        return f"  {tid:<16} ERROR: {err}"

    counts = r.get("counts", {})
    internal = r.get("internal", {})
    stripe = r.get("stripe_check", "skipped")

    paid = counts.get("paid", 0)
    overdue = counts.get("overdue", 0)
    sent = counts.get("sent", 0)
    total = r.get("total_invoices", 0)

    evidence_issues = len(internal.get("paid_missing_evidence", []))
    overdue_issues = len(internal.get("overdue_not_past_due", []))
    neg_total = len(internal.get("negative_total", []))
    orphan = len(internal.get("orphaned_tenant", []))
    stripe_mm = len(r.get("stripe_mismatches", []))

    issues = []
    if evidence_issues:
        issues.append(f"paid_no_evidence={evidence_issues}")
    if overdue_issues:
        issues.append(f"overdue_not_past={overdue_issues}")
    if neg_total:
        issues.append(f"neg_total={neg_total}")
    if orphan:
        issues.append(f"orphan={orphan}")
    if stripe_mm:
        issues.append(f"stripe_mm={stripe_mm}")

    issue_str = " | ".join(issues) if issues else "clean"
    flag = " <<MISMATCH>>" if r.get("any_mismatch") else ""

    return (
        f"  {tid:<16} total={total:<5} paid={paid:<4} overdue={overdue:<4} "
        f"sent={sent:<4} stripe={stripe:<8} {issue_str}{flag}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoice reconciliation eval")
    parser.add_argument(
        "--tenant-id",
        metavar="UUID",
        help="Reconcile a single tenant instead of all.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Dump full JSON results to stdout instead of table.",
    )
    args = parser.parse_args()

    from backend.models.database import get_service_supabase
    from backend.services.invoice_reconciliation import (
        reconcile_all_invoices,
        reconcile_invoices_for_tenant,
    )

    db = get_service_supabase()

    if args.tenant_id:
        results = [reconcile_invoices_for_tenant(db, args.tenant_id)]
    else:
        results = reconcile_all_invoices(db)

    if args.as_json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print("\nInvoice reconciliation")
        print(
            f"{'tenant_id':<18} {'total':<7} {'paid':<6} {'overdue':<8} "
            f"{'sent':<6} {'stripe':<10} issues"
        )
        print("-" * 90)

        mismatch_count = 0
        for r in results:
            print(_format_row(r))
            if r.get("any_mismatch"):
                mismatch_count += 1

        print("-" * 90)
        print(
            f"  Total: {len(results)} tenant(s) — "
            f"{mismatch_count} with mismatches\n"
        )

    mismatch_count = sum(1 for r in results if r.get("any_mismatch"))
    if mismatch_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
