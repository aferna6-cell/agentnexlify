#!/usr/bin/env python3
"""One-shot backfill: encrypt existing plaintext integration secrets (GH #131/#266).

Reads every ``integrations`` row that has a plaintext ``access_token`` or
``refresh_token`` without the corresponding ``*_enc`` ciphertext yet, encrypts
the plaintext with the current key version, and writes the ciphertext columns.
The plaintext columns are left intact — a separate sunset migration drops them
after this backfill is verified (user-rules Rule 8: no half-migrations).

Idempotent: rows whose ciphertext columns are already populated are skipped,
so re-runs are safe.

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
        .select(
            "id, tenant_id, provider, metadata, "
            "access_token, access_token_enc, refresh_token, refresh_token_enc"
        )
        .execute()
    )
    rows = res.data or []

    token_columns = (
        ("access_token", "access_token_enc"),
        ("refresh_token", "refresh_token_enc"),
    )

    scanned = 0
    encrypted = 0
    skipped = 0
    failed = 0

    for row in rows:
        scanned += 1
        update: dict = {}
        row_failed = False
        for plain_col, enc_col in token_columns:
            if row.get(enc_col) is not None:
                continue
            plaintext = row.get(plain_col)
            if not plaintext:
                continue
            try:
                update[enc_col] = _to_bytea(encrypt_key(plaintext, DEFAULT_KEY_VERSION))
            except IntegrationKeyVaultError:
                logger.exception(
                    "encrypt %s failed for integration id=%s", enc_col, row.get("id")
                )
                row_failed = True

        if row_failed:
            failed += 1
            continue
        if not update:
            skipped += 1
            continue
        if dry_run:
            logger.info(
                "[dry-run] would encrypt %s id=%s tenant=%s provider=%s",
                ",".join(update.keys()),
                row.get("id"),
                row.get("tenant_id"),
                row.get("provider"),
            )
            encrypted += 1
            continue
        meta = dict(row.get("metadata") or {})
        meta["enc_key_version"] = DEFAULT_KEY_VERSION
        update["metadata"] = meta
        db.table("integrations").update(update).eq("id", row["id"]).execute()
        encrypted += 1
        logger.info(
            "encrypted %s id=%s tenant=%s provider=%s",
            ",".join(k for k in update if k != "metadata"),
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
