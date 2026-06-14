"""Invoice reconciliation — internal-consistency audit + optional Stripe cross-check.

Two-pass audit per tenant:

Pass A — Internal consistency
    1. Paid invoices must have `paid_at` populated (payment evidence field).
    2. Overdue invoices must have `due_date` actually in the past — not future-dated.
    3. Invoice totals must be non-negative.
    4. Every invoice row must reference a `tenant_id` that matches the tenant being
       checked (orphaned-tenant guard).

Pass B — Stripe cross-check (skipped gracefully when STRIPE_SECRET_KEY is absent)
    For invoices that carry a `stripe_payment_link`, extract the Stripe Payment Link
    ID and call stripe.PaymentLink.retrieve().  If the payment link is marked
    inactive and the local invoice is still `sent` or `overdue`, that is a mismatch.
    Result carries `stripe_check: "ok" | "mismatch" | "skipped" | "error"`.

Public API
----------
    reconcile_invoices_for_tenant(db, tenant_id) -> dict
    reconcile_all_invoices(db)              -> list[dict]

Each result dict has the shape defined by _to_dict().

Intended for cron/manual use via ops/evals/run_invoice_reconciliation.py.
No writes are made — read-only audit pass.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Maximum invoices loaded per tenant in one pass.
_BATCH_LIMIT = 500

# Stripe Payment Link URL pattern — capture the link ID (plink_xxx or pl_xxx or similar).
_STRIPE_LINK_RE = re.compile(
    r"https?://(?:buy\.stripe\.com|checkout\.stripe\.com)/[^/]*?([a-zA-Z0-9_]{8,})"
)


# ── result dataclass ──────────────────────────────────────────────────────────


@dataclass
class InvoiceReconciliationResult:
    tenant_id: str

    # counts
    total_invoices: int = 0
    paid_count: int = 0
    overdue_count: int = 0
    sent_count: int = 0
    draft_count: int = 0

    # internal-consistency flags
    paid_missing_evidence: list[str] = field(default_factory=list)   # invoice_ids
    overdue_not_past_due: list[str] = field(default_factory=list)    # invoice_ids
    negative_total: list[str] = field(default_factory=list)          # invoice_ids
    orphaned_tenant: list[str] = field(default_factory=list)         # invoice_ids

    # stripe cross-check
    stripe_check: str = "skipped"   # "ok" | "mismatch" | "skipped" | "error"
    stripe_mismatches: list[str] = field(default_factory=list)       # invoice_ids

    # overall
    any_mismatch: bool = False
    error: str | None = None


def _to_dict(r: InvoiceReconciliationResult) -> dict:
    return {
        "tenant_id": r.tenant_id,
        "total_invoices": r.total_invoices,
        "counts": {
            "paid": r.paid_count,
            "overdue": r.overdue_count,
            "sent": r.sent_count,
            "draft": r.draft_count,
        },
        "internal": {
            "paid_missing_evidence": r.paid_missing_evidence,
            "overdue_not_past_due": r.overdue_not_past_due,
            "negative_total": r.negative_total,
            "orphaned_tenant": r.orphaned_tenant,
        },
        "stripe_check": r.stripe_check,
        "stripe_mismatches": r.stripe_mismatches,
        "any_mismatch": r.any_mismatch,
        "error": r.error,
    }


# ── helpers ───────────────────────────────────────────────────────────────────


def _today_iso() -> str:
    return date.today().isoformat()


def _extract_stripe_link_id(url: str) -> str | None:
    """Return the Payment Link ID from a Stripe payment link URL, or None."""
    if not url:
        return None
    m = _STRIPE_LINK_RE.search(url)
    return m.group(1) if m else None


def _stripe_key() -> str | None:
    return os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("STRIPE_API_KEY")


def _check_stripe_link(link_id: str, stripe_module: Any) -> str:
    """Return 'ok', 'inactive', or 'error' for a Stripe payment link."""
    try:
        pl = stripe_module.PaymentLink.retrieve(link_id)
        return "ok" if pl.get("active", True) else "inactive"
    except Exception:
        logger.warning(
            "invoice_reconciliation: Stripe PaymentLink.retrieve(%s) failed", link_id,
            exc_info=True,
        )
        return "error"


# ── core reconciliation ───────────────────────────────────────────────────────


def reconcile_invoices_for_tenant(db, tenant_id: str) -> dict:
    """Reconcile invoice consistency for a single tenant.

    Parameters
    ----------
    db:
        Supabase client (service role).
    tenant_id:
        UUID of the tenant to audit.

    Returns
    -------
    dict with keys matching _to_dict() output.
    """
    result = InvoiceReconciliationResult(tenant_id=tenant_id)
    today = _today_iso()

    # ── load invoices ─────────────────────────────────────────────────────────
    try:
        resp = (
            db.table("invoices")
            .select("id, tenant_id, invoice_number, total, due_date, status, paid_at, stripe_payment_link")
            .eq("tenant_id", tenant_id)
            .limit(_BATCH_LIMIT)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
    except Exception:
        logger.exception(
            "reconcile_invoices_for_tenant: DB error loading invoices for tenant %s",
            tenant_id,
        )
        result.error = "db_error_invoices"
        return _to_dict(result)

    result.total_invoices = len(rows)
    if not rows:
        return _to_dict(result)

    # ── pass A: internal consistency ──────────────────────────────────────────
    stripe_candidates: list[tuple[str, str]] = []  # (invoice_id, link_id)

    for inv in rows:
        inv_id = str(inv.get("id") or "")
        status = str(inv.get("status") or "").lower()
        due_date = str(inv.get("due_date") or "")
        total = inv.get("total")
        paid_at = inv.get("paid_at")
        row_tenant = str(inv.get("tenant_id") or "")
        stripe_link = str(inv.get("stripe_payment_link") or "")

        # count by status
        if status == "paid":
            result.paid_count += 1
        elif status == "overdue":
            result.overdue_count += 1
        elif status == "sent":
            result.sent_count += 1
        elif status == "draft":
            result.draft_count += 1

        # check 1: paid invoices must have paid_at populated
        if status == "paid" and not paid_at:
            logger.warning(
                "invoice_reconciliation: invoice %s is paid but has no paid_at (tenant %s)",
                inv_id, tenant_id,
            )
            result.paid_missing_evidence.append(inv_id)

        # check 2: overdue invoices must have due_date in the past
        if status == "overdue" and due_date and due_date >= today:
            logger.warning(
                "invoice_reconciliation: invoice %s is marked overdue but due_date %s "
                "is not in the past (tenant %s)",
                inv_id, due_date, tenant_id,
            )
            result.overdue_not_past_due.append(inv_id)

        # check 3: total must be non-negative
        try:
            total_val = float(total) if total is not None else 0.0
            if total_val < 0:
                logger.warning(
                    "invoice_reconciliation: invoice %s has negative total %s (tenant %s)",
                    inv_id, total_val, tenant_id,
                )
                result.negative_total.append(inv_id)
        except (TypeError, ValueError):
            logger.warning(
                "invoice_reconciliation: invoice %s has unparseable total %r (tenant %s)",
                inv_id, total, tenant_id,
            )
            result.negative_total.append(inv_id)

        # check 4: orphaned tenant guard
        if row_tenant and row_tenant != tenant_id:
            logger.warning(
                "invoice_reconciliation: invoice %s has tenant_id %s but expected %s",
                inv_id, row_tenant, tenant_id,
            )
            result.orphaned_tenant.append(inv_id)

        # collect Stripe candidates for pass B (sent/overdue with a payment link)
        if status in ("sent", "overdue") and stripe_link:
            link_id = _extract_stripe_link_id(stripe_link)
            if link_id:
                stripe_candidates.append((inv_id, link_id))

    # ── pass B: Stripe cross-check ────────────────────────────────────────────
    stripe_key = _stripe_key()
    if not stripe_key:
        result.stripe_check = "skipped"
    elif stripe_candidates:
        try:
            stripe = __import__("stripe")  # lazy import — not a hard dep
            stripe.api_key = stripe_key
            any_stripe_error = False
            any_mismatch = False

            for inv_id, link_id in stripe_candidates:
                outcome = _check_stripe_link(link_id, stripe)
                if outcome == "inactive":
                    result.stripe_mismatches.append(inv_id)
                    any_mismatch = True
                elif outcome == "error":
                    any_stripe_error = True

            if result.stripe_mismatches:
                result.stripe_check = "mismatch"
            elif any_stripe_error:
                result.stripe_check = "error"
            else:
                result.stripe_check = "ok"
        except ImportError:
            logger.warning(
                "invoice_reconciliation: stripe library not importable; skipping Stripe check"
            )
            result.stripe_check = "skipped"
        except Exception:
            logger.exception(
                "invoice_reconciliation: unexpected error in Stripe pass for tenant %s",
                tenant_id,
            )
            result.stripe_check = "error"
    else:
        # Key present but no candidates to check
        result.stripe_check = "ok"

    # ── overall ───────────────────────────────────────────────────────────────
    result.any_mismatch = bool(
        result.paid_missing_evidence
        or result.overdue_not_past_due
        or result.negative_total
        or result.orphaned_tenant
        or result.stripe_mismatches
    )

    return _to_dict(result)


def reconcile_all_invoices(db) -> list[dict]:
    """Reconcile invoice consistency for all tenants.

    Per-tenant errors are captured in result["error"] — the loop always completes.
    Intended for cron use via ops/evals/run_invoice_reconciliation.py.
    """
    try:
        resp = db.table("tenants").select("id").execute()
        tenant_ids = [row["id"] for row in (getattr(resp, "data", None) or [])]
    except Exception:
        logger.exception("reconcile_all_invoices: failed to list tenants")
        return [{"error": "db_error_list_tenants"}]

    results = []
    for tid in tenant_ids:
        try:
            results.append(reconcile_invoices_for_tenant(db, tid))
        except Exception:
            logger.exception(
                "reconcile_all_invoices: unexpected error for tenant %s", tid
            )
            results.append({"tenant_id": tid, "error": "unexpected"})

    return results
