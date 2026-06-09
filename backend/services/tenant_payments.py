"""Tenant-owned payment routing (Item 5 — Stripe Connect, launch-safe scaffold).

Today every tenant invoice payment link is created on the *platform* Stripe
account. This module is the single seam that lets a tenant route their own
invoice payments to a connected Stripe account (Stripe Connect *Standard*) once
the gated onboarding flow is built and the feature flag is enabled.

Design (reversible, low-liability):
  - We store ONLY the connected account id (``acct_xxx``) on ``tenants`` — never
    a secret key. No key-vault, no PCI-adjacent secret storage.
  - ``stripe_account=acct_xxx`` is passed per Stripe API call so charges land in
    the owner's account. Zero application fee by default (pass-through, not a
    marketplace cut).
  - Disconnect = clear the column = automatic fallback to the platform account.

Safety:
  - Gated by ``settings.tenant_payments_byok_enabled`` (default ``False``).
  - With the flag OFF (prod default) this ALWAYS returns ``None`` so callers use
    the platform account exactly as before — behavior is byte-identical to the
    pre-Item-5 path.
  - The DB read is resilient: if migration 135 has not been applied (columns
    absent) it returns ``None`` instead of raising, so code is safe to ship
    before/with the migration.
"""

import logging
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


def tenant_payments_enabled() -> bool:
    """True when the bring-your-own-Stripe flag is on. Off by default in prod."""
    return bool(getattr(settings, "tenant_payments_byok_enabled", False))


def resolve_invoice_stripe_account(db: Any, tenant_id: str) -> str | None:
    """Return the tenant's connected Stripe account id, or ``None``.

    ``None`` means "use the platform account" — the current, default behavior.
    Only returns an account id when ALL of these hold:
      - the feature flag is enabled,
      - the tenant has an ``active`` Connect status,
      - a non-empty ``stripe_connect_account_id`` is stored.

    Any failure (flag off, columns missing, no row, error) resolves to ``None``
    so invoice creation never breaks on this lookup.
    """
    if not tenant_payments_enabled():
        return None
    if not tenant_id:
        return None
    try:
        res = (
            db.table("tenants")
            .select("stripe_connect_account_id, stripe_connect_status")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 — columns may not exist pre-135
        logger.info(
            "tenant_payments: Connect columns unavailable for tenant %s (%s); "
            "using platform account",
            tenant_id,
            exc,
        )
        return None

    row = res.data[0] if res.data else {}
    status = (row.get("stripe_connect_status") or "").strip().lower()
    account_id = (row.get("stripe_connect_account_id") or "").strip()
    if status == "active" and account_id:
        return account_id
    return None
