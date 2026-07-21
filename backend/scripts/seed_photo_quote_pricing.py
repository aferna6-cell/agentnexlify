"""Seed platform-default photo-quote pricing rules for the 6 verticals (#43).

Upserts one ``tenant_pricing_rules`` row per (eligible tenant, vertical) from
the platform-curated defaults in ``backend/data/photo_quote_defaults/*.json``.
Tenants override these in the dashboard (future issue) or keep the defaults.

Idempotent: uses upsert on the table's ``(client_id, industry)`` unique
constraint (migration 108), so re-running refreshes the default rules without
creating duplicates and without clobbering a tenant-set ``min_confidence_threshold``
(that column is left untouched on update).

Eligibility: the spec targets Pro-tier tenants with ``photo_quote_enabled =
true``. That flag column is a prerequisite migration that is NOT yet in the
schema (see README). Until it lands, ``--require-flag`` is off by default and
the script falls back to selecting paid-plan tenants; pass ``--require-flag``
once the column exists to honor the spec exactly.

Usage:
    python3 backend/scripts/seed_photo_quote_pricing.py --dry-run
    python3 backend/scripts/seed_photo_quote_pricing.py
    python3 backend/scripts/seed_photo_quote_pricing.py --require-flag
"""

import argparse
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("seed_photo_quote_pricing")

DEFAULTS_DIR = Path(__file__).resolve().parent.parent / "data" / "photo_quote_defaults"
VERTICALS = ("plumbing", "roofing", "hvac", "auto_body", "landscaping", "pest")

# Paid plans that carry the photo-quote add-on when the enablement flag is absent.
_PAID_PLANS = ("agent_os", "chatbot", "growth", "autopilot", "professional", "enterprise")


def load_defaults() -> dict:
    """Load and validate the six per-vertical default files.

    Returns ``{industry: rules_jsonb}``. Raises if a file is missing/invalid so
    a bad data drop fails loudly instead of seeding partial pricing.
    """
    out: dict[str, dict] = {}
    for industry in VERTICALS:
        path = DEFAULTS_DIR / f"{industry}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        damage = doc.get("damage_types")
        if not isinstance(damage, dict) or len(damage) < 6:
            raise ValueError(f"{path}: expected >=6 damage_types, got {len(damage or {})}")
        out[industry] = doc
    return out


def _eligible_tenants(db, *, require_flag: bool) -> list[dict]:
    """Return tenants that should receive default pricing rules.

    With ``require_flag`` the query honors the spec (``photo_quote_enabled =
    true``). Without it (the current default, since that column is not yet in
    the schema) it falls back to paid-plan tenants.
    """
    query = db.table("tenants").select("id, plan")
    if require_flag:
        query = query.eq("photo_quote_enabled", True)
    else:
        query = query.in_("plan", list(_PAID_PLANS))
    return query.execute().data or []


def seed(*, dry_run: bool = False, require_flag: bool = False, db=None) -> dict:
    """Upsert default pricing rules for every eligible tenant × vertical.

    Returns ``{tenants, rows_upserted, skipped, dry_run}``. Never raises on a
    per-tenant DB error — logs and continues so one bad tenant cannot abort the
    whole seed.
    """
    defaults = load_defaults()

    if db is None:
        from backend.models.database import get_service_supabase

        db = get_service_supabase()

    try:
        tenants = _eligible_tenants(db, require_flag=require_flag)
    except Exception:
        logger.exception("seed_photo_quote_pricing: tenant query failed")
        return {"tenants": 0, "rows_upserted": 0, "skipped": 0, "dry_run": dry_run}

    rows_upserted = 0
    skipped = 0
    for tenant in tenants:
        tid = tenant.get("id")
        if not tid:
            continue
        for industry, doc in defaults.items():
            row = {
                "client_id": tid,
                "industry": industry,
                "rules_jsonb": doc,
            }
            if dry_run:
                skipped += 1
                continue
            try:
                (
                    db.table("tenant_pricing_rules")
                    .upsert(row, on_conflict="client_id,industry")
                    .execute()
                )
                rows_upserted += 1
            except Exception:
                skipped += 1
                logger.warning(
                    "seed_photo_quote_pricing: upsert failed for one (tenant, vertical)"
                )

    summary = {
        "tenants": len(tenants),
        "rows_upserted": rows_upserted,
        "skipped": skipped,
        "dry_run": dry_run,
    }
    logger.info("seed_photo_quote_pricing: %s", summary)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Seed default photo-quote pricing rules")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    parser.add_argument(
        "--require-flag",
        action="store_true",
        help="select only tenants with photo_quote_enabled=true (needs the flag column)",
    )
    args = parser.parse_args()
    result = seed(dry_run=args.dry_run, require_flag=args.require_flag)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
