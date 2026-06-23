"""Admin referral overview service.

Computes per-tenant referral performance:
  - total_clicks   — rows in referral_clicks where ref_tenant_id = tenant's api_key
  - referred_signups — tenants whose referred_by_widget_key = this tenant's api_key

Data model (verified against migrations 157 and 159):
  referral_clicks.ref_tenant_id  TEXT → widget_configs.api_key of the referrer
  tenants.referred_by_widget_key TEXT → widget_configs.api_key of whoever referred them
  widget_configs.api_key         TEXT → each tenant's referral identity (ref_code)

Schema disciplines enforced:
  - widget_configs uses tenant_id (not client_id)
  - tenants uses tenant_id (primary key = id)
  - referral_clicks uses ref_tenant_id (not tenant_id)

Each metric is computed in a per-tenant try/except so one tenant's DB failure
does not break the rest of the list.  Global errors (e.g. can't load any
tenants) are surfaced by raising so the route returns 500 with context.

Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI routes.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase

logger = logging.getLogger(__name__)


def compute_referral_overview() -> dict:
    """Return per-tenant referral performance ranked by referred_signups desc.

    Returns
    -------
    dict with keys:
        tenants : list[dict]  — per-tenant rows, sorted referred_signups desc then
                                total_clicks desc.  Each row:
                                {tenant_id, business_name, ref_code,
                                 total_clicks, referred_signups}
        totals  : dict        — {total_clicks: int, total_referred_signups: int}
        computed_at : str     — UTC ISO timestamp

    Raises
    ------
    Exception  — if the initial tenant+widget_config fetch fails entirely.
                 Partial per-tenant metric failures are silently zeroed.
    """
    db = get_service_supabase()

    # Step 1: Fetch all tenants with their business names
    try:
        tenants_result = (
            db.table("tenants")
            .select("id, business_name")
            .execute()
        )
        tenant_rows = tenants_result.data or []
    except Exception:
        logger.exception("referral_overview: failed to fetch tenants")
        raise

    # Step 2: Fetch all widget_configs to get api_key per tenant
    try:
        wc_result = (
            db.table("widget_configs")
            .select("tenant_id, api_key")
            .execute()
        )
        wc_rows = wc_result.data or []
    except Exception:
        logger.exception("referral_overview: failed to fetch widget_configs")
        raise

    # Build tenant_id → api_key map
    api_key_by_tenant: dict[str, str] = {}
    for wc in wc_rows:
        tid = wc.get("tenant_id")
        ak = wc.get("api_key")
        if tid and ak:
            api_key_by_tenant[tid] = ak

    # Step 3: Fetch all referral_clicks rows (ref_tenant_id + count per api_key)
    # We fetch all and aggregate in Python to avoid N+1 queries.
    total_clicks_by_api_key: dict[str, int] = {}
    try:
        clicks_result = (
            db.table("referral_clicks")
            .select("ref_tenant_id")
            .execute()
        )
        for row in clicks_result.data or []:
            ref_tid = row.get("ref_tenant_id")
            if ref_tid:
                total_clicks_by_api_key[ref_tid] = (
                    total_clicks_by_api_key.get(ref_tid, 0) + 1
                )
    except Exception:
        logger.exception(
            "referral_overview: failed to fetch referral_clicks — "
            "total_clicks will be 0 for all tenants"
        )
        # Non-fatal: continue with zero click counts

    # Step 4: Fetch referred signups (tenants.referred_by_widget_key)
    signups_by_api_key: dict[str, int] = {}
    try:
        signups_result = (
            db.table("tenants")
            .select("referred_by_widget_key")
            .execute()
        )
        for row in signups_result.data or []:
            wk = row.get("referred_by_widget_key")
            if wk:
                signups_by_api_key[wk] = signups_by_api_key.get(wk, 0) + 1
    except Exception:
        logger.exception(
            "referral_overview: failed to fetch referred_signups — "
            "referred_signups will be 0 for all tenants"
        )
        # Non-fatal: continue with zero signup counts

    # Step 5: Build per-tenant rows
    tenant_list = []
    for tenant in tenant_rows:
        tenant_id = tenant.get("id") or ""
        business_name = tenant.get("business_name") or ""
        ref_code = api_key_by_tenant.get(tenant_id, "")

        total_clicks = total_clicks_by_api_key.get(ref_code, 0) if ref_code else 0
        referred_signups = signups_by_api_key.get(ref_code, 0) if ref_code else 0

        tenant_list.append(
            {
                "tenant_id": tenant_id,
                "business_name": business_name,
                "ref_code": ref_code,
                "total_clicks": total_clicks,
                "referred_signups": referred_signups,
            }
        )

    # Step 6: Sort — referred_signups desc, then total_clicks desc
    tenant_list.sort(
        key=lambda r: (r["referred_signups"], r["total_clicks"]),
        reverse=True,
    )

    # Step 7: Compute totals
    grand_clicks = sum(r["total_clicks"] for r in tenant_list)
    grand_signups = sum(r["referred_signups"] for r in tenant_list)

    return {
        "tenants": tenant_list,
        "totals": {
            "total_clicks": grand_clicks,
            "total_referred_signups": grand_signups,
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
