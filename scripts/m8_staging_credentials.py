"""Shared staging server-credential validation for M8 tooling.

Supports Supabase legacy JWT service_role keys (eyJ...) and modern secret keys
(sb_secret_...). Never log or return raw secret values from helpers here.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

STAGING_SUPABASE_PROJECT_REF = "nohanoiugcbaxtxinttp"
PRODUCTION_SUPABASE_PROJECT_REF = "pxserpybmajixqrmzaly"
STAGING_API_HOST = "agentnexlify-staging.up.railway.app"
PRODUCTION_API_HOST = "agentnexlify-production.up.railway.app"

REASON_PRODUCTION_API = "M8_SMOKE_API_BASE is production API"
REASON_PRODUCTION_SUPABASE = "SUPABASE_URL host is production project ref"
REASON_MALFORMED_API = "M8_SMOKE_API_BASE is malformed"
REASON_MALFORMED_SUPABASE = "SUPABASE_URL is malformed"
REASON_USERINFO_API = "M8_SMOKE_API_BASE contains URL userinfo"
REASON_USERINFO_SUPABASE = "SUPABASE_URL contains URL userinfo"
REASON_UNAPPROVED_API = "M8_SMOKE_API_BASE host is not an approved staging host"
REASON_UNAPPROVED_SUPABASE = "SUPABASE_URL host is not an approved staging host"
REASON_HTTPS_API = "M8_SMOKE_API_BASE must use https"
REASON_HTTPS_SUPABASE = "SUPABASE_URL must use https"

_API_TARGET = "api"
_SUPABASE_TARGET = "supabase"
_TARGET_REASONS = {
    _API_TARGET: {
        "production": REASON_PRODUCTION_API,
        "malformed": REASON_MALFORMED_API,
        "userinfo": REASON_USERINFO_API,
        "unapproved": REASON_UNAPPROVED_API,
        "https": REASON_HTTPS_API,
    },
    _SUPABASE_TARGET: {
        "production": REASON_PRODUCTION_SUPABASE,
        "malformed": REASON_MALFORMED_SUPABASE,
        "userinfo": REASON_USERINFO_SUPABASE,
        "unapproved": REASON_UNAPPROVED_SUPABASE,
        "https": REASON_HTTPS_SUPABASE,
    },
}
_TARGET_HOSTS = {
    _API_TARGET: (STAGING_API_HOST, PRODUCTION_API_HOST),
    _SUPABASE_TARGET: (
        f"{STAGING_SUPABASE_PROJECT_REF}.supabase.co",
        f"{PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co",
    ),
}

MODERN_SECRET_PREFIX = "sb_secret_"
MODERN_PUBLISHABLE_PREFIX = "sb_publishable_"
MASK_BULLET = "•"

_MIN_MODERN_SECRET_LEN = len(MODERN_SECRET_PREFIX) + 8


class StagingKeyKind(str, Enum):
    LEGACY_SERVICE_ROLE = "legacy_service_role_jwt"
    MODERN_SECRET = "modern_secret_key"
    INVALID = "invalid"


@dataclass(frozen=True)
class StagingKeyValidation:
    ok: bool
    kind: StagingKeyKind
    error: str | None = None
    jwt_role: str | None = None
    jwt_ref: str | None = None


def jwt_claims(token: str) -> dict:
    parts = (token or "").split(".")
    if len(parts) < 2:
        return {}
    pad = "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(parts[1] + pad))
    except Exception:
        return {}


def is_masked_value(raw: str) -> bool:
    text = (raw or "").strip()
    if not text:
        return False
    if MASK_BULLET in text:
        return True
    if re.search(r"[•]{2,}", text):
        return True
    return text.startswith(f"{MODERN_SECRET_PREFIX}{MASK_BULLET}")


def project_ref_from_supabase_url(supabase_url: str) -> str:
    return urlparse((supabase_url or "").strip()).netloc.split(".")[0]


def classify_staging_server_key(raw: str) -> StagingKeyKind:
    text = (raw or "").strip()
    if not text or is_masked_value(text):
        return StagingKeyKind.INVALID
    if text.startswith(MODERN_SECRET_PREFIX):
        return StagingKeyKind.MODERN_SECRET
    if text.startswith("eyJ"):
        return StagingKeyKind.LEGACY_SERVICE_ROLE
    return StagingKeyKind.INVALID


def validate_staging_server_key(
    raw: str,
    *,
    expected_project_ref: str | None = None,
) -> StagingKeyValidation:
    text = (raw or "").strip()
    if not text:
        return StagingKeyValidation(False, StagingKeyKind.INVALID, "empty credential")
    if is_masked_value(text):
        return StagingKeyValidation(
            False,
            StagingKeyKind.INVALID,
            "masked UI paste (bullet characters)",
        )
    if text.startswith(MODERN_PUBLISHABLE_PREFIX):
        return StagingKeyValidation(
            False,
            StagingKeyKind.INVALID,
            "publishable key cannot be used as server credential",
        )

    kind = classify_staging_server_key(text)
    if kind == StagingKeyKind.MODERN_SECRET:
        if len(text) < _MIN_MODERN_SECRET_LEN:
            return StagingKeyValidation(
                False,
                StagingKeyKind.INVALID,
                "modern secret key too short",
            )
        return StagingKeyValidation(True, StagingKeyKind.MODERN_SECRET)

    if kind == StagingKeyKind.LEGACY_SERVICE_ROLE:
        claims = jwt_claims(text)
        role = claims.get("role")
        ref = claims.get("ref")
        if role != "service_role":
            return StagingKeyValidation(
                False,
                StagingKeyKind.INVALID,
                f"JWT role is {role!r}, expected service_role",
                jwt_role=str(role) if role is not None else None,
                jwt_ref=str(ref) if ref is not None else None,
            )
        if expected_project_ref and ref and ref != expected_project_ref:
            return StagingKeyValidation(
                False,
                StagingKeyKind.INVALID,
                f"JWT ref {ref!r} does not match expected {expected_project_ref!r}",
                jwt_role="service_role",
                jwt_ref=str(ref),
            )
        return StagingKeyValidation(
            True,
            StagingKeyKind.LEGACY_SERVICE_ROLE,
            jwt_role="service_role",
            jwt_ref=str(ref) if ref is not None else None,
        )

    return StagingKeyValidation(
        False,
        StagingKeyKind.INVALID,
        "expected legacy service_role JWT (eyJ...) or modern secret key (sb_secret_...)",
    )


def is_trusted_server_key(raw: str, *, expected_project_ref: str | None = None) -> bool:
    return validate_staging_server_key(raw, expected_project_ref=expected_project_ref).ok


def supabase_rest_headers(api_key: str) -> dict[str, str]:
    """Headers for direct PostgREST calls.

    Legacy JWT keys use apikey + Authorization Bearer.
    Modern sb_secret_ keys must not be sent as a JWT Bearer token.
    """
    headers = {"apikey": api_key, "Accept": "application/json"}
    if (api_key or "").startswith("eyJ"):
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def safe_key_metadata(raw: str, validation: StagingKeyValidation | None = None) -> dict[str, object]:
    """Return log-safe metadata only — never secret contents."""
    v = validation or validate_staging_server_key(raw)
    meta: dict[str, object] = {
        "key_kind": v.kind.value,
        "key_len": len((raw or "").strip()),
    }
    if v.jwt_role:
        meta["jwt_role"] = v.jwt_role
    if v.jwt_ref:
        meta["jwt_ref"] = v.jwt_ref
    if v.error and not v.ok:
        meta["error"] = v.error
    return meta


def _normalized_hostname(hostname: str | None) -> str:
    return (hostname or "").rstrip(".").lower()


def _classify_staging_target(raw: str, target: str) -> str | None:
    """Return one secret-safe reason, or None when the target is approved staging.

    Empty values are unset configuration, not malformed targets. Host checks use
    the parsed hostname only, case-folded, with trailing dots removed.
    An approved staging host is accepted only over https.
    urlparse and port access raise ValueError for unmatched IPv6 brackets and
    invalid ports. Those, and any other parser exception, become the malformed
    reason so the raw URL cannot leak through a traceback.
    """
    text = (raw or "").strip()
    if not text:
        return None
    reasons = _TARGET_REASONS[target]
    staging_host, production_host = _TARGET_HOSTS[target]
    try:
        parsed = urlparse(text)
        hostname = parsed.hostname
        port = parsed.port
        username = parsed.username
        password = parsed.password
    except Exception:
        return reasons["malformed"]

    host = _normalized_hostname(hostname)
    if not host:
        return reasons["malformed"]
    if host == production_host:
        return reasons["production"]
    if host != staging_host:
        return reasons["unapproved"]
    if parsed.scheme != "https":
        return reasons["https"]
    if username is not None or password is not None:
        return reasons["userinfo"]
    if port is not None and port != 443:
        return reasons["malformed"]
    return None


def staging_target_errors(*, supabase_url: str, api_base: str) -> list[str]:
    """Fail closed unless both targets are the approved staging hosts."""
    fails: list[str] = []
    supabase_reason = _classify_staging_target(supabase_url, _SUPABASE_TARGET)
    if supabase_reason:
        fails.append(supabase_reason)
    api_reason = _classify_staging_target(api_base, _API_TARGET)
    if api_reason:
        fails.append(api_reason)
    return fails
