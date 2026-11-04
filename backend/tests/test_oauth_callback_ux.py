"""OAuth callback landing path, Google redirect URI, and access-log redaction."""

import io
import logging

import pytest
from fastapi import HTTPException
from uvicorn.logging import AccessFormatter

from backend.oauth_access_log import install_oauth_callback_log_redaction
from backend.routers import integrations as integrations_router
from backend.services import google_calendar


class _FakeGoogleCreds:
    token = "access-tok"
    refresh_token = "refresh-tok"
    expiry = None


def _location(response) -> str:
    assert response.status_code in (302, 303, 307, 308)
    return response.headers["location"]


def test_build_redirect_uri_uses_public_override(monkeypatch):
    monkeypatch.setattr(
        google_calendar.settings,
        "google_public_redirect_uri",
        "https://app.agentnexlify.com/api/v1/integrations/google/callback",
    )
    monkeypatch.setattr(
        google_calendar.settings,
        "google_redirect_uri",
        "https://agentnexlify-production.up.railway.app/api/v1/integrations/google/callback",
    )

    assert (
        google_calendar.build_redirect_uri()
        == "https://app.agentnexlify.com/api/v1/integrations/google/callback"
    )


def test_build_redirect_uri_falls_back_when_public_override_unset(monkeypatch):
    monkeypatch.setattr(google_calendar.settings, "google_public_redirect_uri", "  ")
    monkeypatch.setattr(
        google_calendar.settings,
        "google_redirect_uri",
        "https://agentnexlify-production.up.railway.app/api/v1/integrations/google/callback",
    )

    assert (
        google_calendar.build_redirect_uri()
        == "https://agentnexlify-production.up.railway.app/api/v1/integrations/google/callback"
    )


@pytest.mark.asyncio
async def test_google_auth_sends_built_redirect_uri(monkeypatch):
    seen = {}

    monkeypatch.setattr(integrations_router.settings, "google_client_id", "gid")
    monkeypatch.setattr(integrations_router.settings, "google_client_secret", "gsecret")
    monkeypatch.setattr(
        integrations_router,
        "build_redirect_uri",
        lambda: "https://app.agentnexlify.com/api/v1/integrations/google/callback",
    )

    def _auth_url(redirect_uri, state):
        seen["redirect_uri"] = redirect_uri
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    monkeypatch.setattr(integrations_router, "get_auth_url", _auth_url)

    result = await integrations_router.google_auth(
        claims={"tenant_id": "tenant-1"}, os_thread_id=None
    )

    assert seen["redirect_uri"] == (
        "https://app.agentnexlify.com/api/v1/integrations/google/callback"
    )
    assert "auth_url" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_name", "provider_param"),
    [
        ("google_callback", "google"),
        ("m365_callback", "m365"),
        ("hubspot_callback", "hubspot"),
    ],
)
async def test_oauth_callback_lands_on_dashboard_integrations(
    monkeypatch, callback_name, provider_param
):
    monkeypatch.setattr(
        integrations_router.settings, "frontend_url", "https://app.agentnexlify.com"
    )
    monkeypatch.setattr(
        integrations_router,
        "build_redirect_uri",
        lambda: "https://app.agentnexlify.com/api/v1/integrations/google/callback",
    )
    seen = {}

    def _google_exchange(code, redirect_uri):
        seen["redirect_uri"] = redirect_uri
        return _FakeGoogleCreds()

    monkeypatch.setattr(integrations_router, "exchange_code", _google_exchange)
    monkeypatch.setattr(integrations_router, "save_integration", lambda **kwargs: None)
    monkeypatch.setattr(
        integrations_router.m365_calendar,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        integrations_router, "_fetch_m365_profile", lambda access_token: {}
    )
    monkeypatch.setattr(
        integrations_router.m365_calendar, "save_integration", lambda **kwargs: None
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant,
        "exchange_code",
        lambda code, redirect_uri: {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 1800,
        },
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant, "fetch_profile", lambda access_token: {}
    )
    monkeypatch.setattr(
        integrations_router.hubspot_tenant, "save_integration", lambda **kwargs: None
    )

    state = integrations_router._encode_state("tenant-9")
    callback = getattr(integrations_router, callback_name)
    location = _location(await callback(code="auth-code", state=state))

    assert location == (
        f"https://app.agentnexlify.com/dashboard/integrations?{provider_param}=connected"
    )
    assert "#integrations" not in location
    if callback_name == "google_callback":
        assert seen["redirect_uri"] == (
            "https://app.agentnexlify.com/api/v1/integrations/google/callback"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_name", "provider_param"),
    [
        ("google_callback", "google"),
        ("m365_callback", "m365"),
        ("hubspot_callback", "hubspot"),
    ],
)
async def test_oauth_callback_error_lands_on_dashboard_integrations(
    monkeypatch, callback_name, provider_param
):
    monkeypatch.setattr(
        integrations_router.settings, "frontend_url", "https://app.agentnexlify.com"
    )
    state = integrations_router._encode_state("tenant-9")
    callback = getattr(integrations_router, callback_name)
    location = _location(
        await callback(code=None, state=state, error="access_denied")
    )

    assert location == (
        f"https://app.agentnexlify.com/dashboard/integrations?{provider_param}=error"
    )


@pytest.mark.asyncio
async def test_oauth_callback_error_stays_http_without_frontend(monkeypatch):
    monkeypatch.setattr(integrations_router.settings, "frontend_url", "")
    state = integrations_router._encode_state("tenant-9")

    with pytest.raises(HTTPException) as exc_info:
        await integrations_router.google_callback(
            code=None, state=state, error="access_denied"
        )

    assert exc_info.value.status_code == 400


def _log_blob(records) -> str:
    parts = []
    for record in records:
        parts.append(record.getMessage())
        path = getattr(record, "path", None)
        if isinstance(path, str):
            parts.append(path)
        if record.args:
            parts.append(repr(record.args))
    return "\n".join(parts)


@pytest.mark.asyncio
async def test_oauth_callback_secrets_never_appear_in_log_output(caplog):
    from backend.main import RequestContextMiddleware

    install_oauth_callback_log_redaction()
    code = "super-secret-oauth-code"
    state = "super-secret-oauth-state"
    providers = ("google", "m365", "hubspot")

    async def _downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 302, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(message):
        return None

    middleware = RequestContextMiddleware(_downstream)
    access_logger = logging.getLogger("uvicorn.access")
    access_stream = io.StringIO()
    access_handler = logging.StreamHandler(access_stream)
    access_handler.setFormatter(
        AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s')
    )
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)

    try:
        with caplog.at_level(logging.INFO):
            for provider in providers:
                path = f"/api/v1/integrations/{provider}/callback"
                query = f"code={code}&state={state}"
                scope = {
                    "type": "http",
                    "http_version": "1.1",
                    "method": "GET",
                    "scheme": "https",
                    "path": path,
                    "raw_path": path.encode(),
                    "query_string": query.encode(),
                    "headers": [],
                    "client": ("127.0.0.1", 1234),
                    "server": ("test", 443),
                }
                await middleware(scope, _receive, _send)
                access_logger.info(
                    '%s - "%s %s HTTP/%s" %d',
                    "127.0.0.1:1234",
                    "GET",
                    f"{path}?{query}",
                    "1.1",
                    302,
                )
                access_logger.info(
                    '%s - "%s %s HTTP/%s" %d',
                    "127.0.0.1:1234",
                    "GET",
                    f"https://agentnexlify-production.up.railway.app{path}?{query}",
                    "1.1",
                    302,
                )
    finally:
        access_logger.removeHandler(access_handler)

    blob = _log_blob(caplog.records) + "\n" + access_stream.getvalue()
    assert code not in blob
    assert state not in blob
    assert "code=" not in blob
    assert "state=" not in blob
    for provider in providers:
        assert f"/integrations/{provider}/callback" in blob
