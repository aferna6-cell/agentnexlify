"""Thin CLI wrapper around backend.services.demo_seed.ensure_demo_tenant.

Creates (or verifies) the plumbing demo tenant for local/staging use.
Re-running is idempotent — existing rows are left untouched.

SAFETY NOTE:
  This script retains a production-URL guard (aborts if SUPABASE_URL
  points at the production database). The service it delegates to
  (backend.services.demo_seed) has NO such guard because it is designed
  to run in production for the public live-demo sandbox — its safety
  guarantee comes from the is_demo flag check, not a URL comparison.
  That asymmetry is intentional.

Usage (from project root, venv active):
    python scripts/demos/seed_plumbing_demo.py

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in environment or .env file.
"""

import logging
import sys
from pathlib import Path

# ── project root on path ─────────────────────────────────────────────────────
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── PROD GUARD ────────────────────────────────────────────────────────────────
PROD_URL = "https://pxserpybmajixqrmzaly.supabase.co"


def main() -> None:
    try:
        from backend.config import settings
        from backend.models.database import get_supabase
        from backend.services.demo_seed import ensure_demo_tenant
    except ImportError as exc:
        logger.error(
            "Import failed: %s — run from project root with venv active", exc
        )
        sys.exit(1)

    # --- PROD GUARD (script-only; the service itself has no such guard) ---
    supabase_url = (settings.supabase_url or "").rstrip("/")
    if supabase_url == PROD_URL.rstrip("/"):
        logger.error(
            "ABORT: SUPABASE_URL points at the production database (%s). "
            "This script must only run against a LOCAL or STAGING Supabase instance. "
            "Set SUPABASE_URL to your local URL (e.g. http://localhost:54321) and re-run.",
            supabase_url,
        )
        sys.exit(1)

    if not supabase_url or not settings.supabase_service_key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    logger.info(
        "Targeting Supabase at: %s (NOT production — safe to proceed)", supabase_url
    )

    db = get_supabase()
    tenant_id = ensure_demo_tenant(db)

    if tenant_id:
        logger.info("=" * 60)
        logger.info("DEMO SEED COMPLETE — Plumbing Vertical")
        logger.info("  tenant_id : %s", tenant_id)
        logger.info("  Supabase  : %s", supabase_url)
        logger.info("=" * 60)
    else:
        logger.error("DEMO SEED FAILED — ensure_demo_tenant returned None")
        sys.exit(1)


if __name__ == "__main__":
    main()
