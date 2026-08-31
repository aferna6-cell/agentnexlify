#!/usr/bin/env python3
"""Wire staging service_role into gitignored .env.staging (never print secrets).

Reads STAGING_SUPABASE_SERVICE_ROLE_KEY from the environment (Cursor secret or
shell export). Validates JWT role=service_role and ref matches SUPABASE_URL host.
Updates SUPABASE_SERVICE_KEY and SUPABASE_SERVICE_ROLE_KEY in .env.staging only.

Does NOT commit secrets. Does NOT write to artifacts. Railway vars must be set
separately via dashboard or Railway MCP set-variables by an operator with the
same validated key.

Usage (after owner pastes secret into agent env):
  export STAGING_SUPABASE_SERVICE_ROLE_KEY='eyJ...'
  python3 scripts/m8_wire_staging_service_key.py
  set -a && source .env.staging && set +a
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.staging"


def _jwt_claims(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    pad = "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(parts[1] + pad))
    except Exception:
        return {}


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
    if "•" in raw or raw.startswith("sb_secret_•"):
        print("STOP: value looks like a masked UI paste (bullet characters)")
        return 2
    if not raw.startswith("eyJ"):
        print("STOP: expected Legacy JWT service_role (starts with eyJ)")
        return 2

    claims = _jwt_claims(raw)
    role = claims.get("role")
    ref = claims.get("ref")
    if role != "service_role":
        print(f"STOP: JWT role is {role!r}, expected service_role")
        return 2

    env_existing = _load_env_file(ENV_PATH)
    supabase_url = (
        os.environ.get("SUPABASE_URL") or env_existing.get("SUPABASE_URL") or ""
    ).strip()
    host = urlparse(supabase_url).netloc.split(".")[0] if supabase_url else ""
    if ref and host and ref != host:
        print(f"STOP: JWT ref {ref!r} does not match SUPABASE_URL host {host!r}")
        return 2

    anon = (
        os.environ.get("SUPABASE_KEY")
        or env_existing.get("SUPABASE_KEY")
        or ""
    ).strip()
    if anon:
        anon_claims = _jwt_claims(anon)
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
    print("OK: updated .env.staging SUPABASE_SERVICE_KEY/SUPABASE_SERVICE_ROLE_KEY")
    print(f"    jwt_role={role} jwt_ref={ref} len={len(raw)}")
    print("Next: set Railway staging SUPABASE_SERVICE_KEY to the same JWT (not in chat)")
    print("      then redeploy agentnexlify and run M8_SMOKE_SUITES=isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
