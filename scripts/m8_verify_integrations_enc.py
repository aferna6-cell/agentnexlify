#!/usr/bin/env python3
"""Verify INTEGRATIONS_ENC_KEY is set and encrypt_oauth_tokens round-trips.

Run before connecting real Google OAuth in staging (issue #536). Does not
apply migration 176 — only proves the vault is live.

Usage:
  source .env.staging  # or export INTEGRATIONS_ENC_KEY=...
  python3 scripts/m8_verify_integrations_enc.py
"""

from __future__ import annotations

import os
import sys

# Repo root on path for backend imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services import integration_key_vault as vault


def main() -> int:
    key = (os.environ.get("INTEGRATIONS_ENC_KEY") or "").strip()
    if not key:
        print("FAIL: INTEGRATIONS_ENC_KEY unset — generate per ops/docs/runbook-integrations-enc-key.md")
        return 1

    if not vault.encryption_configured():
        print("FAIL: vault.encryption_configured() is false despite env var present")
        return 1

    sample = {
        "access_token": "ya29.smoke-test-access",
        "refresh_token": "1//smoke-test-refresh",
    }
    encrypted = vault.encrypt_oauth_tokens(dict(sample))
    if "access_token_enc" not in encrypted or "refresh_token_enc" not in encrypted:
        print("FAIL: encrypt_oauth_tokens did not add ciphertext columns")
        return 1

    row = {
        **sample,
        **encrypted,
        "metadata": {"enc_key_version": 1},
    }
    decrypted = vault.decrypt_integration_row(row)
    if not decrypted:
        print("FAIL: decrypt_integration_row returned None")
        return 1
    if decrypted.get("access_token") != sample["access_token"]:
        print("FAIL: access_token round-trip mismatch")
        return 1
    if decrypted.get("refresh_token") != sample["refresh_token"]:
        print("FAIL: refresh_token round-trip mismatch")
        return 1

    print("PASS: INTEGRATIONS_ENC_KEY configured; OAuth token encrypt/decrypt round-trip OK")
    print("Next: set same key on Railway staging, connect OAuth, confirm access_token_enc populated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
