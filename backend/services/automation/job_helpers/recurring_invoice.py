"""Pure helpers for process_recurring_invoices.

Invoice math, date arithmetic, and dict construction.
DB calls (number generation) take db as parameter.
"""

from datetime import date, datetime, timezone
from typing import Any

from dateutil.relativedelta import relativedelta

__all__ = [
    "compute_invoice_totals",
    "compute_next_invoice_dates",
    "generate_invoice_number",
    "build_new_invoice_payload",
]

_INTERVAL_MAP = {
    "weekly": relativedelta(weeks=1),
    "biweekly": relativedelta(weeks=2),
    "monthly": relativedelta(months=1),
    "quarterly": relativedelta(months=3),
}


def compute_invoice_totals(
    items: list, tax_rate: float
) -> tuple[float, float, float]:
    """Return (subtotal, tax_amount, total) rounded to 2 decimals."""
    subtotal = sum(
        float(i.get("quantity", 1)) * float(i.get("unit_price", 0)) for i in items
    )
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    return subtotal, tax_amount, total


def compute_next_invoice_dates(
    interval: str, today: date, original_next_date_str: str
) -> tuple[relativedelta, str, date]:
    """Return (delta, due_date_iso, next_invoice_date) given recurrence interval."""
    delta = _INTERVAL_MAP.get(interval, relativedelta(months=1))
    due_date = (today + delta).isoformat()
    next_date = date.fromisoformat(original_next_date_str) + delta
    return delta, due_date, next_date


def generate_invoice_number(db: Any, tenant_id: str, now_dt: datetime) -> str:
    """Generate INV-YYYYMMDD-NNNN for a tenant based on its invoice count."""
    prefix = f"INV-{now_dt.astimezone(timezone.utc).strftime('%Y%m%d')}"
    count_result = (
        db.table("invoices")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    seq = (count_result.count or 0) + 1
    return f"{prefix}-{seq:04d}"


def build_new_invoice_payload(
    *,
    tenant_id: str,
    parent: dict,
    invoice_number: str,
    items: list,
    subtotal: float,
    tax_rate: float,
    tax_amount: float,
    total: float,
    due_date: str,
) -> dict:
    """Build the dict inserted into the invoices table for a new recurring child."""
    return {
        "tenant_id": tenant_id,
        "lead_id": parent.get("lead_id"),
        "parent_invoice_id": parent["id"],
        "invoice_number": invoice_number,
        "items_json": items,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "notes": parent.get("notes"),
        "status": "draft",
        "due_date": due_date,
        "is_recurring": False,
    }
