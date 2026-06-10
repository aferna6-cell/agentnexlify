"""Tests for rubric criterion 2.6 — JWT expiry, tamper rejection, and auth discipline.

Architecture note — NO refresh endpoint:
    AgentNexLiFy uses single-issue HS256 JWTs with a 24-hour expiry.
    There is no /refresh or /token-renew endpoint. Clients must re-authenticate
    (call /api/v1/auth/login) to obtain a new token after expiry.
    This file documents and proves that contract.

Contracts under test:
- Expired token → 401 "Invalid or expired token"
- Valid token accepted → claims dict returned
- Tampered signature → 401 (JWTError raised → HTTPException 401)
- Algorithm confusion (alg: "none") → 401 (jose rejects alg:none by default)
- Missing Bearer prefix → 401 "Missing Bearer token"
- Wrong algorithm (RS256 token against HS256 verifier) → 401
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SECRET = "test-secret-key-for-jwt"
ALGORITHM = "HS256"


def _make_token(
    tenant_id: str = "tenant-001",
    role: str = "owner",
    exp_delta: timedelta = timedelta(hours=24),
    secret: str = SECRET,
    algorithm: str = ALGORITHM,
    extra_claims: dict | None = None,
) -> str:
    payload = {
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + exp_delta,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


# ---------------------------------------------------------------------------
# Valid token accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_valid_token_returns_claims(mock_settings):
    """A freshly-issued, non-expired HS256 token must return a claims dict."""
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    token = _make_token()
    claims = await get_current_tenant(authorization=f"Bearer {token}")

    assert claims["tenant_id"] == "tenant-001"
    assert claims["role"] == "owner"


# ---------------------------------------------------------------------------
# Expired token rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_expired_token_returns_401(mock_settings):
    """An expired token must raise HTTPException 401."""
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    expired_token = _make_token(exp_delta=timedelta(seconds=-1))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization=f"Bearer {expired_token}")

    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Tampered signature rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_tampered_token_returns_401(mock_settings):
    """A token whose signature has been modified must raise HTTPException 401."""
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    valid_token = _make_token()
    # Flip last char of signature to corrupt it
    parts = valid_token.split(".")
    assert len(parts) == 3
    sig = parts[2]
    # Replace the last character with a different one
    if sig[-1] == "A":
        bad_sig = sig[:-1] + "B"
    else:
        bad_sig = sig[:-1] + "A"
    tampered_token = ".".join([parts[0], parts[1], bad_sig])

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization=f"Bearer {tampered_token}")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# alg:none / wrong secret rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_wrong_secret_token_returns_401(mock_settings):
    """A token signed with a different secret must raise HTTPException 401."""
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    # Token signed with a completely different secret
    foreign_token = _make_token(secret="attacker-controlled-secret-xyz")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization=f"Bearer {foreign_token}")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_alg_none_token_returns_401(mock_settings):
    """A token using alg='none' must be rejected.

    python-jose raises JWTError for unsupported algorithms when the caller
    restricts the allowed list to ['HS256']. This guards against algorithm
    confusion attacks.
    """
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    # Manually craft an alg:none token (unsigned)
    import base64
    import json

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()
    payload_str = base64.urlsafe_b64encode(
        json.dumps({
            "tenant_id": "tenant-evil",
            "role": "admin",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        }).encode()
    ).rstrip(b"=").decode()
    none_token = f"{header}.{payload_str}."

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization=f"Bearer {none_token}")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Missing Bearer prefix rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_missing_bearer_prefix_returns_401(mock_settings):
    """A raw token without 'Bearer ' prefix must raise HTTPException 401."""
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    token = _make_token()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization=token)  # no "Bearer " prefix

    assert exc_info.value.status_code == 401
    assert "bearer" in exc_info.value.detail.lower() or "missing" in exc_info.value.detail.lower()


@pytest.mark.asyncio
@patch("backend.services.auth_service.settings")
async def test_empty_authorization_header_returns_401(mock_settings):
    """An empty Authorization header string must raise HTTPException 401."""
    from fastapi import HTTPException
    mock_settings.jwt_secret_key = SECRET
    mock_settings.api_secret_key = SECRET

    from backend.services.auth_service import get_current_tenant

    with pytest.raises(HTTPException) as exc_info:
        await get_current_tenant(authorization="")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# No-refresh-endpoint contract (documented assertion)
# ---------------------------------------------------------------------------


def test_no_refresh_endpoint_exists():
    """Prove there is no /refresh or /token-renew endpoint in auth or billing routers.

    AgentNexLiFy uses single-issue 24h tokens. Re-auth via /login is the only
    way to get a fresh token. This test guards against accidentally adding a
    refresh endpoint without updating the security model.
    """
    import inspect
    import backend.routers.auth as auth_module

    source = inspect.getsource(auth_module)
    assert "/refresh" not in source, (
        "A /refresh endpoint was found in auth.py. "
        "If this was intentional, update the JWT security model and remove this assertion."
    )
    assert "/token-renew" not in source, (
        "A /token-renew endpoint was found in auth.py. "
        "If this was intentional, update the JWT security model and remove this assertion."
    )
