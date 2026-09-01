#!/usr/bin/env python3
"""Import Railway `variables --json` output into gitignored .env.staging.

Never prints secret values.

Usage (on a machine with Railway CLI):
  railway link -p cheerful-freedom -e staging -s agentnexlify
  railway variables --json > /tmp/railway-staging.json
  python3 scripts/m8_import_railway_vars_json.py /tmp/railway-staging.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.staging"

DEFAULTS = {
    "M8_SMOKE_API_BASE": "https://agentnexlify-staging.up.railway.app",
    "M8_SMOKE_ALLOW_EXTERNAL_SEND": "1",
    "M8_SMOKE_CLIENT_ID": "3ddd9072-ad9f-4214-970d-11386d8c1b4a",
    "SEND_EMAIL_ENABLED": "1",
    "CALENDAR_ACTIONS_ENABLED": "1",
}


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
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/m8_import_railway_vars_json.py <railway-variables.json>")
        return 2
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"STOP: file not found: {src}")
        return 2
    raw = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        print("STOP: expected JSON object from railway variables --json")
        return 2

    merged = _load_env_file(ENV_PATH)
    merged.update({str(k): str(v) for k, v in raw.items() if v is not None})
    for k, v in DEFAULTS.items():
        merged.setdefault(k, v)
    ENV_PATH.write_text("\n".join(f"{k}={merged[k]}" for k in sorted(merged)) + "\n")
    ENV_PATH.chmod(0o600)
    print(f"OK: imported {len(raw)} Railway vars into .env.staging ({len(merged)} total keys)")
    need = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "M8_SMOKE_LOGIN_PASSWORD",
        "M8_SMOKE_GMAIL_RECIPIENT",
        "M8_SMOKE_EXTERNAL_ATTENDEE",
    ]
    missing = [k for k in need if not merged.get(k)]
    if missing:
        print(f"WARN: still missing: {', '.join(missing)}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
