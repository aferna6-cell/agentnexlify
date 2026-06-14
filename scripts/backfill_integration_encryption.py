#!/usr/bin/env python3
"""One-shot backfill: encrypt existing plaintext integration secrets (GH #131).

Reads every ``integrations`` row that has a plaintext ``access_token`` but no
``access_token_enc`` yet, encrypts the plaintext with the current key version,
and writes ``access_token_enc``. The plaintext column is left intact — a
separate sunset migration drops it after this backfill is verified
(user-rules Rule 8: no half-migrations).

Idempotent: rows that already have ``access_token_enc`` are skipped, so re-runs
are safe.

Usage:
    INTEGRATIONS_ENC_KEY=<fernet-key> python scripts/backfill_integration_encryption.py [--dry-run]
"""

import argparse
import logging
import sys

from backend.models.database import get_service_supabase
from backend.services.integration_key_vault import (
    DEFAULT_KEY_VERSION,
    IntegrationKeyVaultError,
    _to_bytea,
    encrypt_key,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("backfill_integration_encryption")


def run(dry_run: bool = False) -> dict:
    db = get_service_supabase()
    res = (
        db.table("integrations")
        .select("id, tenant_id, provider, access_token, access_token_enc")
        .execute()
    )
    rows = res.data or []

    scanned = 0
    encrypted = 0
    skipped = 0
    failed = 0

    for row in rows:
        scanned += 1
        if row.get("access_token_enc") is not None:
            skipped += 1
            continue
        plaintext = row.get("access_token")
        if not plaintext:
            skipped += 1
            continue
        try:
            token = encrypt_key(plaintext, DEFAULT_KEY_VERSION)
        except IntegrationKeyVaultError:
            logger.exception("encrypt failed for integration id=%s", row.get("id"))
            failed += 1
            continue
        if dry_run:
            logger.info(
                "[dry-run] would encrypt id=%s tenant=%s provider=%s",
                row.get("id"),
                row.get("tenant_id"),
                row.get("provider"),
            )
            encrypted += 1
            continue
        meta = dict(row.get("metadata") or {})
        meta["enc_key_version"] = DEFAULT_KEY_VERSION
        db.table("integrations").update(
            {"access_token_enc": _to_bytea(token), "metadata": meta}
        ).eq("id", row["id"]).execute()
        encrypted += 1
        logger.info(
            "encrypted id=%s tenant=%s provider=%s",
            row.get("id"),
            row.get("tenant_id"),
            row.get("provider"),
        )

    summary = {
        "scanned": scanned,
        "encrypted": encrypted,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run,
    }
    logger.info("backfill complete: %s", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    args = parser.parse_args()
    summary = run(dry_run=args.dry_run)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
