#!/usr/bin/env python3
"""Wire staging server credential into gitignored .env.staging (never print secrets).

Reads STAGING_SUPABASE_SERVICE_ROLE_KEY from the environment (Cursor secret or
shell export). Accepts either:

- legacy JWT service_role (eyJ...) with role=service_role
- modern Supabase secret key (sb_secret_...)

Updates SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_ROLE_KEY in .env.staging only.

Does NOT commit secrets. Does NOT write to artifacts. Railway vars must be set
separately via dashboard or Railway MCP set-variables by an operator with the
same validated key.

Usage (after owner pastes secret into agent env):
  export STAGING_SUPABASE_SERVICE_ROLE_KEY='sb_secret_...'   # preferred
  # or legacy: export STAGING_SUPABASE_SERVICE_ROLE_KEY='eyJ...'
  python3 scripts/m8_wire_staging_service_key.py
  set -a && source .env.staging && set +a
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m8_staging_credentials as creds

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.staging"


def _load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    existing = _load_env_file(path)
    existing.update(values)
    lines = [f"{k}={v}" for k, v in sorted(existing.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    raw = (os.environ.get("STAGING_SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not raw:
        print("STOP: STAGING_SUPABASE_SERVICE_ROLE_KEY not set in environment")
        return 2

    env_existing = _load_env_file(ENV_PATH)
    supabase_url = (
        os.environ.get("SUPABASE_URL") or env_existing.get("SUPABASE_URL") or ""
    ).strip()
    expected_ref = creds.project_ref_from_supabase_url(supabase_url) or creds.STAGING_SUPABASE_PROJECT_REF

    validation = creds.validate_staging_server_key(raw, expected_project_ref=expected_ref)
    if not validation.ok:
        print(f"STOP: {validation.error}")
        meta = creds.safe_key_metadata(raw, validation)
        print(f"    {meta}")
        return 2

    anon = (
        os.environ.get("SUPABASE_KEY")
        or env_existing.get("SUPABASE_KEY")
        or ""
    ).strip()
    if anon:
        anon_claims = creds.jwt_claims(anon)
        if anon_claims.get("role") != "anon":
            print("WARN: SUPABASE_KEY does not look like anon JWT")

    updates = {
        "SUPABASE_SERVICE_KEY": raw,
        "SUPABASE_SERVICE_ROLE_KEY": raw,
    }
    if supabase_url:
        updates["SUPABASE_URL"] = supabase_url
    if anon:
        updates["SUPABASE_KEY"] = anon

    _write_env_file(ENV_PATH, updates)
    meta = creds.safe_key_metadata(raw, validation)
    print("OK: updated .env.staging SUPABASE_SERVICE_KEY/SUPABASE_SERVICE_ROLE_KEY")
    print(f"    {meta}")
    print(
        "Next: set Railway staging SUPABASE_SERVICE_KEY to the same server credential "
        "(not in chat), keep SUPABASE_KEY=anon publishable/anon key, redeploy agentnexlify"
    )
    print("      then run: python3 scripts/m8_verify_staging_step3.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
