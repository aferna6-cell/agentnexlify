#!/usr/bin/env python3
"""Wire M8 live-smoke secrets into gitignored .env.staging (never print values).

Use on your laptop when Cursor Cloud Agent secrets are unavailable. Export
vars in your shell (from a password manager), then run this once:

  export GOOGLE_CLIENT_ID='...'
  export GOOGLE_CLIENT_SECRET='...'
  export M8_SMOKE_LOGIN_EMAIL='support@agentnexlify.com'
  export M8_SMOKE_LOGIN_PASSWORD='...'
  export M8_SMOKE_GMAIL_RECIPIENT='...'
  export M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST='...'
  export M8_SMOKE_EXTERNAL_ATTENDEE='...'
  python3 scripts/m8_wire_smoke_secrets.py

Then:
  bash scripts/m8_run_support_smoke.sh
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.staging"

KEYS = [
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "INTEGRATIONS_ENC_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_KEY",
    "M8_SMOKE_CLIENT_ID",
    "M8_SMOKE_LOGIN_EMAIL",
    "M8_SMOKE_LOGIN_PASSWORD",
    "M8_SMOKE_GMAIL_RECIPIENT",
    "M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST",
    "M8_SMOKE_EXTERNAL_ATTENDEE",
    "M8_SMOKE_API_BASE",
]

DEFAULTS = {
    "M8_SMOKE_CLIENT_ID": "3ddd9072-ad9f-4214-970d-11386d8c1b4a",
    "M8_SMOKE_API_BASE": "https://agentnexlify-staging.up.railway.app",
    "CALENDAR_ACTIONS_ENABLED": "1",
}

# Fail-closed: never persist send enablement. Process env must already have them.
OMIT_SEND_ENABLEMENT_KEYS = frozenset(
    {
        "SEND_EMAIL_ENABLED",
        "M8_SMOKE_ALLOW_EXTERNAL_SEND",
    }
)


def _omit_send_enablement(values: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in values.items() if k not in OMIT_SEND_ENABLEMENT_KEYS}


def merge_wired(existing: dict[str, str], pulled_env: dict[str, str]) -> dict[str, str]:
    merged = dict(existing)
    for key, val in pulled_env.items():
        if val:
            merged[key] = val
    for key, val in DEFAULTS.items():
        merged.setdefault(key, val)
    return _omit_send_enablement(merged)


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


def main() -> int:
    pulled_env = {}
    pulled = 0
    for key in KEYS:
        val = (os.environ.get(key) or "").strip()
        if val:
            pulled_env[key] = val
            pulled += 1
    merged = merge_wired(_load_env_file(ENV_PATH), pulled_env)

    if pulled == 0:
        print("STOP: no smoke secret env vars set in shell")
        print("Export GOOGLE_CLIENT_ID, M8_SMOKE_LOGIN_PASSWORD, etc., then rerun.")
        return 2

    ENV_PATH.write_text("\n".join(f"{k}={merged[k]}" for k in sorted(merged)) + "\n")
    ENV_PATH.chmod(0o600)
    print(f"OK: wired {pulled} secrets into .env.staging ({len(merged)} total keys)")

    required = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "M8_SMOKE_LOGIN_PASSWORD",
        "M8_SMOKE_GMAIL_RECIPIENT",
        "M8_SMOKE_EXTERNAL_ATTENDEE",
    ]
    missing = [k for k in required if not merged.get(k)]
    if missing:
        print(f"WARN: still missing for full proof: {', '.join(missing)}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
