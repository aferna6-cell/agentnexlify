#!/usr/bin/env python3
"""Step 3 gate: verify staging credentials after Railway redeploy.

Requires M8_SMOKE_* and SUPABASE_* from sourced .env.staging.
Never prints secrets. Exit 0 only if all checks pass.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request


def _jwt_role(token: str) -> str | None:
    if not token.startswith("eyJ"):
        return None
    parts = token.split(".")
    if len(parts) < 2:
        return None
    pad = "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(parts[1] + pad)).get("role")
    except Exception:
        return None


def _get(url: str, headers: dict) -> tuple[int, object]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw[:200]
        return int(exc.code), body


def _post_json(url: str, payload: dict) -> tuple[int, object]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw[:200]
        return int(exc.code), body


def main() -> int:
    base = (os.environ.get("M8_SMOKE_API_BASE") or "").rstrip("/")
    sb_url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    anon = (os.environ.get("SUPABASE_KEY") or "").strip()
    service = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("STAGING_SUPABASE_SERVICE_ROLE_KEY")
        or ""
    ).strip()
    client_id = (os.environ.get("M8_SMOKE_CLIENT_ID") or "").strip()
    email = (os.environ.get("M8_SMOKE_LOGIN_EMAIL") or "").strip()
    password = (os.environ.get("M8_SMOKE_LOGIN_PASSWORD") or "").strip()

    fails: list[str] = []

    if not base:
        fails.append("M8_SMOKE_API_BASE unset")
    if _jwt_role(service) != "service_role":
        fails.append("local service key role is not service_role")
    if _jwt_role(anon) != "anon":
        fails.append("SUPABASE_KEY is not anon JWT")

    if base:
        code, body = _get(f"{base}/health", {"Accept": "application/json"})
        if code != 200 or not isinstance(body, dict) or body.get("status") != "ok":
            fails.append(f"/health failed http={code}")
        else:
            print("PASS /health ok")

    if sb_url and anon:
        code, body = _get(
            f"{sb_url}/rest/v1/tenant_kb_chunks?select=id&limit=3",
            {"apikey": anon, "Authorization": f"Bearer {anon}", "Accept": "application/json"},
        )
        if code == 200 and isinstance(body, list) and len(body) == 0:
            print("PASS anon tenant_kb_chunks []")
        else:
            fails.append(f"anon chunks expected [] got http={code} n={len(body) if isinstance(body,list) else body}")

    if sb_url and service and client_id:
        code, body = _get(
            f"{sb_url}/rest/v1/tenant_kb_chunks?select=id&client_id=eq.{client_id}&status=eq.active&limit=5",
            {
                "apikey": service,
                "Authorization": f"Bearer {service}",
                "Accept": "application/json",
            },
        )
        if code == 200 and isinstance(body, list) and len(body) > 0:
            print(f"PASS service_role smoke chunks n={len(body)}")
        else:
            fails.append(
                f"service_role smoke chunks expected >0 got http={code} n={len(body) if isinstance(body,list) else body}"
            )

    if base and email and password:
        code, body = _post_json(
            f"{base}/api/v1/auth/login", {"email": email, "password": password}
        )
        if code == 200 and isinstance(body, dict) and body.get("token"):
            print("PASS smoke login 200")
        else:
            fails.append(f"smoke login failed http={code} (Railway SUPABASE_SERVICE_KEY likely still anon)")

    if fails:
        print("FAIL step-3 verification:")
        for f in fails:
            print(f"  - {f}")
        return 1

    print("OK step-3 verification complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
