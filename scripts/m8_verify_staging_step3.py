#!/usr/bin/env python3
"""Step 3 gate: verify staging credentials after Railway redeploy.

Requires M8_SMOKE_* and SUPABASE_* from sourced .env.staging.
Never prints secrets. Exit 0 only if all checks pass.

Legacy service_role JWT: validates role claim + privileged REST reads.
Modern sb_secret_ key: validates privileged behavior functionally (no JWT decode).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m8_staging_credentials as creds


def _request_base(url: str) -> str:
    """Drop one accepted root slash after origin validation has passed."""
    if url.endswith("/") and not url.endswith("//"):
        return url[:-1]
    return url


def _is_canonical_client_id(value: str) -> bool:
    """True only for the lowercase hyphenated form produced by str(uuid.UUID)."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return str(parsed) == value


class _RejectCredentialRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse automatic redirects so credential headers are not replayed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _build_opener():
    return urllib.request.build_opener(_RejectCredentialRedirects())


def _open(req: urllib.request.Request, timeout: int) -> tuple[int, object]:
    try:
        with _build_opener().open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = raw[:200]
        return int(exc.code), body


def _get(url: str, headers: dict) -> tuple[int, object]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    return _open(req, 20)


def _post_json(url: str, payload: dict) -> tuple[int, object]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _open(req, 25)


def main() -> int:
    base = (os.environ.get("M8_SMOKE_API_BASE") or "").strip()
    sb_url = (os.environ.get("SUPABASE_URL") or "").strip()
    target_fails = creds.staging_target_errors(supabase_url=sb_url, api_base=base)
    if target_fails:
        print("FAIL step-3 verification:")
        for item in target_fails:
            print(f"  - {item}")
        return 1
    base = _request_base(base)
    sb_url = _request_base(sb_url)

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
    if not sb_url:
        fails.append("SUPABASE_URL unset")

    expected_ref = creds.project_ref_from_supabase_url(sb_url) or creds.STAGING_SUPABASE_PROJECT_REF
    validation = creds.validate_staging_server_key(service, expected_project_ref=expected_ref)
    if not validation.ok:
        fails.append(creds.local_server_credential_reason(validation))
    if not anon:
        fails.append("SUPABASE_KEY unset")
    elif creds.jwt_claims(anon).get("role") != "anon":
        fails.append("SUPABASE_KEY is not anon JWT")
    if not client_id:
        fails.append("M8_SMOKE_CLIENT_ID unset")
    elif not _is_canonical_client_id(client_id):
        fails.append("M8_SMOKE_CLIENT_ID is invalid")
    if not email:
        fails.append("M8_SMOKE_LOGIN_EMAIL unset")
    if not password:
        fails.append("M8_SMOKE_LOGIN_PASSWORD unset")
    if fails:
        print("FAIL step-3 verification:")
        for item in fails:
            print(f"  - {item}")
        return 1

    if validation.kind == creds.StagingKeyKind.LEGACY_SERVICE_ROLE:
        print(f"PASS local server credential kind={validation.kind.value} jwt_role=service_role")
    else:
        print(f"PASS local server credential kind={validation.kind.value} (functional verify below)")

    if base:
        code, body = _get(f"{base}/health", {"Accept": "application/json"})
        if code != 200 or not isinstance(body, dict) or body.get("status") != "ok":
            fails.append(f"/health failed http={code}")
        else:
            print("PASS /health ok")

    if sb_url and anon:
        code, body = _get(
            f"{sb_url}/rest/v1/tenant_kb_chunks?select=id&limit=3",
            creds.supabase_rest_headers(anon),
        )
        if code == 200 and isinstance(body, list) and len(body) == 0:
            print("PASS anon tenant_kb_chunks []")
        else:
            fails.append(
                f"anon chunks expected [] got http={code} n={len(body) if isinstance(body, list) else body}"
            )

    if sb_url and service and client_id and validation.ok:
        code, body = _get(
            f"{sb_url}/rest/v1/tenant_kb_chunks?select=id&client_id=eq.{client_id}&status=eq.active&limit=5",
            creds.supabase_rest_headers(service),
        )
        if code == 200 and isinstance(body, list) and len(body) > 0:
            print(f"PASS server credential smoke chunks n={len(body)}")
        else:
            fails.append(
                "server credential smoke chunks expected >0 got "
                f"http={code} n={len(body) if isinstance(body, list) else body}"
            )

    if base and email and password:
        code, body = _post_json(
            f"{base}/api/v1/auth/login", {"email": email, "password": password}
        )
        if code == 200 and isinstance(body, dict) and body.get("token"):
            print("PASS smoke login 200")
        else:
            fails.append(
                f"smoke login failed http={code} (Railway SUPABASE_SERVICE_KEY likely wrong/missing)"
            )

    if fails:
        print("FAIL step-3 verification:")
        for f in fails:
            print(f"  - {f}")
        return 1

    print("OK step-3 verification complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
