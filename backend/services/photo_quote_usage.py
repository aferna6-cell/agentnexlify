"""Photo-quote metered billing — 500/mo cap + $0.15 overage (#39).

Pro tier includes 500 photo quotes/month; beyond that each quote is $0.15,
reported to Stripe as a metered usage event. Resolved decision #6 in
``specs/photo-quote_spec.md``.

- Usage is counted per calendar month in ``tenant_quote_usage``
  (``(client_id, period_start)`` PK, migration 108) — a new ``period_start`` row
  is created the first time a tenant quotes in a new month (monthly rollover).
- Once the month's count passes 500, ``overage_count`` increments and a Stripe
  metered usage event is reported with idempotency key
  ``{client_id}:{quote_request_id}`` so a retried request never double-charges.
- Fail-open on billing: if the metered price isn't configured or the Stripe call
  fails, usage is still counted locally and the visitor is never blocked — the
  overage is reconciled from ``tenant_quote_usage`` if reporting lagged.

``client_id`` (not ``tenant_id``) per schema-discipline. Stripe reporting is an
injected callable so the counting logic is unit-tested without Stripe.
"""

import logging
from datetime import datetime, timezone
from typing import Callable

from backend.services.plan_catalog import PREMIUM_PLANS

logger = logging.getLogger(__name__)

FREE_MONTHLY_QUOTA = 500
OVERAGE_PRICE_USD = 0.15


def is_billing_eligible(plan: str | None) -> bool:
    """True when the tenant's plan includes photo-quote (Pro/premium tier).

    A non-eligible tenant should get HTTP 402 from the endpoint rather than a
    quote — photo-quote is a premium feature (canonical ``PREMIUM_PLANS``).
    """
    return (plan or "") in PREMIUM_PLANS


def _period_start(now: datetime) -> str:
    """First-of-month date string (the ``tenant_quote_usage`` period key)."""
    return now.strftime("%Y-%m-01")


def _report_overage_to_stripe(
    client_id: str,
    quote_request_id: str | None,
    *,
    stripe_reporter: Callable[..., None] | None,
) -> None:
    """Best-effort metered-usage report. Never raises."""
    from backend.config import settings

    price_id = settings.stripe_photo_quote_metered_price_id
    if not price_id:
        return  # metering not configured — count locally only
    idem = f"{client_id}:{quote_request_id or 'na'}"
    try:
        if stripe_reporter is not None:
            stripe_reporter(client_id=client_id, price_id=price_id, idempotency_key=idem)
        else:  # pragma: no cover - real Stripe path, exercised in integration
            import stripe

            stripe.billing.MeterEvent.create(
                event_name="photo_quote_overage",
                payload={"stripe_customer_id": client_id, "value": "1"},
                identifier=idem,
            )
    except Exception:
        logger.warning(
            "photo_quote_usage: Stripe overage report failed for %s (counted locally)",
            client_id,
        )


def get_usage_summary(
    client_id: str,
    *,
    db=None,
    now: datetime | None = None,
) -> dict:
    """Current-month usage for the dashboard meter.

    Returns ``{quote_count, overage_count, cap, overage_charge}`` — the count
    against the 500/mo cap and the dollar value of any overage. Fail-open: a read
    error returns zeros rather than 500ing the dashboard.
    """
    now = now or datetime.now(timezone.utc)
    period = _period_start(now)
    if db is None:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()
    quote_count = 0
    overage_count = 0
    try:
        res = (
            db.table("tenant_quote_usage")
            .select("quote_count, overage_count")
            .eq("client_id", client_id)
            .eq("period_start", period)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        quote_count = int(row.get("quote_count") or 0)
        overage_count = int(row.get("overage_count") or 0)
    except Exception:
        logger.warning("photo_quote_usage: summary read failed for %s", client_id)
    return {
        "quote_count": quote_count,
        "overage_count": overage_count,
        "cap": FREE_MONTHLY_QUOTA,
        "overage_charge": round(overage_count * OVERAGE_PRICE_USD, 2),
    }


def increment_usage(
    client_id: str,
    *,
    quote_request_id: str | None = None,
    db=None,
    now: datetime | None = None,
    stripe_reporter: Callable[..., None] | None = None,
) -> tuple[int, int]:
    """Count one photo quote for this month; report + return overage.

    Returns ``(quote_count, overage_count)`` AFTER this increment. The upsert on
    ``(client_id, period_start)`` is atomic per the table PK; call exactly once
    per persisted ``quote_requests`` row (the row is the idempotency anchor) —
    the Stripe idempotency key additionally dedupes the charge on any retry.
    """
    now = now or datetime.now(timezone.utc)
    period = _period_start(now)
    if db is None:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()

    quote_count = 0
    overage_count = 0
    try:
        existing = (
            db.table("tenant_quote_usage")
            .select("quote_count, overage_count")
            .eq("client_id", client_id)
            .eq("period_start", period)
            .limit(1)
            .execute()
        )
        row = (existing.data or [{}])[0]
        quote_count = int(row.get("quote_count") or 0)
        overage_count = int(row.get("overage_count") or 0)
    except Exception:
        logger.warning("photo_quote_usage: usage read failed for %s", client_id)

    quote_count += 1
    is_overage = quote_count > FREE_MONTHLY_QUOTA
    if is_overage:
        overage_count += 1

    try:
        db.table("tenant_quote_usage").upsert(
            {
                "client_id": client_id,
                "period_start": period,
                "quote_count": quote_count,
                "overage_count": overage_count,
                "updated_at": now.isoformat(),
            },
            on_conflict="client_id,period_start",
        ).execute()
    except Exception:
        logger.warning("photo_quote_usage: usage upsert failed for %s", client_id)

    if is_overage:
        _report_overage_to_stripe(
            client_id, quote_request_id, stripe_reporter=stripe_reporter
        )

    return quote_count, overage_count
