#!/usr/bin/env python3
"""Pull rendered Railway staging service variables into gitignored .env.staging.

Uses the logged-in Chrome profile on this machine (Playwright persistent context)
to call Railway GraphQL with the user's existing session cookies. Never prints
secret values.

Requires: playwright, an authenticated Railway session in Chrome Profile 1.

Usage:
  python3 scripts/m8_pull_railway_staging_env.py
  set -a && source .env.staging && set +a
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env.staging"

PROJECT_ID = "22fbefe0-bd69-41c6-9896-e5f533473c60"
ENVIRONMENT_ID = "5988ed51-6691-4497-825d-14fefff5f591"
SERVICE_ID = "293f3d78-f644-470a-ba40-a6767ad2fbcd"
CHROME_PROFILE = Path.home() / ".config/google-chrome/Profile 1"

# Keys the M8 smoke runner needs locally (staging agentnexlify already has most).
PULL_KEYS = [
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
    "CALENDAR_ACTIONS_ENABLED",
]

DEFAULTS = {
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


def merge_pulled(pulled: dict[str, str]) -> dict[str, str]:
    merged = dict(pulled)
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


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    existing = _load_env_file(path)
    existing.update(values)
    existing = _omit_send_enablement(existing)
    lines = [f"{k}={existing[k]}" for k in sorted(existing)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _fetch_variables_playwright() -> dict[str, str]:
    from playwright.sync_api import sync_playwright

    query = """
    query($projectId: String!, $environmentId: String!, $serviceId: String!) {
      variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
    }
    """
    variables = {
        "projectId": PROJECT_ID,
        "environmentId": ENVIRONMENT_ID,
        "serviceId": SERVICE_ID,
    }

    with sync_playwright() as p:
        if not CHROME_PROFILE.exists():
            raise RuntimeError(f"Chrome profile not found: {CHROME_PROFILE}")
        ctx = p.chromium.launch_persistent_context(
            str(CHROME_PROFILE),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://railway.com/dashboard", wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(2000)

        result = page.evaluate(
            """async ({ query, variables }) => {
              const resp = await fetch('https://backboard.railway.com/graphql/v2', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, variables }),
              });
              const text = await resp.text();
              return { status: resp.status, text };
            }""",
            {"query": query, "variables": variables},
        )
        ctx.close()

    if result.get("status") != 200:
        raise RuntimeError(f"Railway GraphQL HTTP {result.get('status')}")
    payload = json.loads(result["text"])
    if payload.get("errors"):
        msgs = [e.get("message", str(e)) for e in payload["errors"][:3]]
        raise RuntimeError(f"Railway GraphQL errors: {'; '.join(msgs)}")
    raw = payload.get("data", {}).get("variables")
    if not isinstance(raw, dict):
        raise RuntimeError("Railway GraphQL returned no variables object")
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def main() -> int:
    try:
        all_vars = _fetch_variables_playwright()
    except Exception as exc:
        print(f"STOP: {exc}")
        print("Fallback: on a machine with Railway CLI logged in, run:")
        print("  railway link -p cheerful-freedom -e staging -s agentnexlify")
        print("  railway variables --json > /tmp/railway-staging.json")
        print("  python3 scripts/m8_import_railway_vars_json.py /tmp/railway-staging.json")
        return 2

    pulled = {k: all_vars[k] for k in PULL_KEYS if k in all_vars and all_vars[k]}
    if not pulled.get("GOOGLE_CLIENT_ID") or not pulled.get("GOOGLE_CLIENT_SECRET"):
        print("STOP: GOOGLE_CLIENT_ID/SECRET not returned from Railway staging")
        print(f"    fetched {len(all_vars)} total vars; missing Google OAuth pair")
        return 2

    # Sensible defaults for support-tenant proof when not yet on Railway.
    # Do not default or persist send enablement flags.
    pulled.setdefault(
        "M8_SMOKE_CLIENT_ID", "3ddd9072-ad9f-4214-970d-11386d8c1b4a"
    )

    pulled = merge_pulled(pulled)
    _write_env_file(ENV_PATH, pulled)
    present = sorted(pulled.keys())
    missing = [k for k in PULL_KEYS if k not in pulled]
    print(f"OK: merged {len(pulled)} vars into .env.staging")
    print(f"    present: {', '.join(present)}")
    if missing:
        print(f"    still missing (add to Railway staging Variables): {', '.join(missing)}")
        print("    Required for full calendar+gmail proof:")
        print("      M8_SMOKE_LOGIN_EMAIL, M8_SMOKE_LOGIN_PASSWORD")
        print("      M8_SMOKE_GMAIL_RECIPIENT, M8_SMOKE_GMAIL_RECIPIENT_ALLOWLIST")
        print("      M8_SMOKE_EXTERNAL_ATTENDEE")
    return 0 if not missing else 3


if __name__ == "__main__":
    raise SystemExit(main())
