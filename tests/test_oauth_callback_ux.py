"""OAuth callback landing path, Google redirect URI, and access-log redaction.

Lives under tests/ so the existing ``pytest tests`` CI invocation runs it
without a workflow change.
"""

import io
import json
import logging
from urllib.parse import urlparse

import pytest
from fastapi import HTTPException
from uvicorn.logging import AccessFormatter

from backend.oauth_access_log import install_oauth_callback_log_redaction, sentry_before_send
from backend.routers import integrations as integrations_router
from backend.services import google_calendar

_PUBLIC_REDIRECT = "https://app.agentnexlify.com/api/v1/integrations/google/callback"
_RAILWAY_REDIRECT = (
    "https://agentnexlify-production.up.railway.app/api/v1/integrations/google/callback"
)
_FRONTEND = "https://app.agentnexlify.com"
_PROVIDERS = (
    ("google_callback", "google", "google_calendar"),
    ("m365_callback", "m365", "m365_calendar"),
    ("hubspot_callback", "hubspot", "hubspot"),
)


class _FakeGoogleCreds:
    token = "access-tok"
    refresh_token = "refresh-tok"
    expiry = None


def _location(response) -> str:
    assert response.status_code in (302, 303, 307, 308)
    return response.headers["location"]


def _stub_success(monkeypatch):
    monkeypatch.setattr(
        integrations_router, "exchange_code", lambda code, redirect_uri: _FakeGoogleCreds()
    )
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
    monkeypatch.setattr(integrations_router, "_fetch_m365_profile", lambda access_token: {})
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


def test_build_redirect_uri_uses_public_override(monkeypatch):
    monkeypatch.setattr(google_calendar.settings, "google_public_redirect_uri", _PUBLIC_REDIRECT)
    monkeypatch.setattr(google_calendar.settings, "google_redirect_uri", _RAILWAY_REDIRECT)

    assert google_calendar.build_redirect_uri() == _PUBLIC_REDIRECT


def test_build_redirect_uri_falls_back_when_public_override_unset(monkeypatch):
    monkeypatch.setattr(google_calendar.settings, "google_public_redirect_uri", "  ")
    monkeypatch.setattr(google_calendar.settings, "google_redirect_uri", _RAILWAY_REDIRECT)

    assert google_calendar.build_redirect_uri() == _RAILWAY_REDIRECT


@pytest.mark.asyncio
async def test_public_redirect_uri_is_sent_on_consent_and_token_exchange(monkeypatch):
    """Consent URL and token exchange must use the same redirect_uri."""
    seen = {}
    monkeypatch.setattr(integrations_router.settings, "google_client_id", "gid")
    monkeypatch.setattr(integrations_router.settings, "google_client_secret", "gsecret")
    monkeypatch.setattr(integrations_router.settings, "google_public_redirect_uri", _PUBLIC_REDIRECT)
    monkeypatch.setattr(integrations_router.settings, "google_redirect_uri", _RAILWAY_REDIRECT)
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)
    monkeypatch.setattr(integrations_router, "save_integration", lambda **kwargs: None)

    def _auth_url(redirect_uri, state):
        seen["consent"] = redirect_uri
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    def _exchange(code, redirect_uri):
        seen["exchange"] = redirect_uri
        return _FakeGoogleCreds()

    monkeypatch.setattr(integrations_router, "get_auth_url", _auth_url)
    monkeypatch.setattr(integrations_router, "exchange_code", _exchange)

    await integrations_router.google_auth(claims={"tenant_id": "tenant-1"}, os_thread_id=None)
    state = integrations_router._encode_state("tenant-1")
    await integrations_router.google_callback(code="auth-code", state=state)

    assert seen["consent"] == _PUBLIC_REDIRECT
    assert seen["exchange"] == seen["consent"]
    assert _RAILWAY_REDIRECT not in (seen["consent"], seen["exchange"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_name", "provider_param", "_provider_key"),
    _PROVIDERS,
)
async def test_oauth_callback_lands_on_dashboard_integrations(
    monkeypatch, callback_name, provider_param, _provider_key
):
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)
    _stub_success(monkeypatch)

    state = integrations_router._encode_state("tenant-9")
    callback = getattr(integrations_router, callback_name)
    location = _location(await callback(code="auth-code", state=state))

    assert location == (
        f"{_FRONTEND}/dashboard/integrations?{provider_param}=connected"
    )
    parsed = urlparse(location)
    assert parsed.hostname == "app.agentnexlify.com"
    assert "#integrations" not in location


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_name", "provider_param", "_provider_key"),
    _PROVIDERS,
)
async def test_oauth_callback_error_lands_on_dashboard_integrations(
    monkeypatch, callback_name, provider_param, _provider_key
):
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)
    state = integrations_router._encode_state("tenant-9")
    callback = getattr(integrations_router, callback_name)
    location = _location(await callback(code=None, state=state, error="access_denied"))

    assert location == f"{_FRONTEND}/dashboard/integrations?{provider_param}=error"
    assert urlparse(location).hostname == "app.agentnexlify.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "return_to,thread_id",
    [
        ("https://evil.example/phish", None),
        ("//evil.example", None),
        ("/\\evil.example", None),
        ("/@evil.example", None),
        ("/%2f%2fevil.example", None),
        (None, "https://evil.example"),
        (None, "th\r\nLocation: https://evil.example"),
        (None, "//evil.example"),
    ],
)
async def test_callback_redirect_cannot_leave_frontend_origin(
    monkeypatch, return_to, thread_id
):
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)
    _stub_success(monkeypatch)
    state = integrations_router._encode_state(
        "tenant-9", os_thread_id=thread_id, return_to=return_to
    )
    response = await integrations_router.google_callback(code="auth-code", state=state)
    location = _location(response)
    parsed = urlparse(location)

    assert parsed.scheme == "https"
    assert parsed.hostname == "app.agentnexlify.com"
    assert parsed.port is None
    assert "evil.example" not in location
    assert location.startswith(f"{_FRONTEND}/dashboard/")


@pytest.mark.asyncio
async def test_callback_thread_redirect_stays_on_frontend_origin(monkeypatch):
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)
    _stub_success(monkeypatch)
    state = integrations_router._encode_state("tenant-9", os_thread_id="th-42")
    location = _location(
        await integrations_router.google_callback(code="auth-code", state=state)
    )
    parsed = urlparse(location)
    assert parsed.hostname == "app.agentnexlify.com"
    assert parsed.path == "/dashboard/agent-os"
    assert "thread=th-42" in location


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
        if record.exc_text:
            parts.append(record.exc_text)
        path = getattr(record, "path", None)
        if isinstance(path, str):
            parts.append(path)
        if record.args:
            parts.append(repr(record.args))
    return "\n".join(parts)


async def _log_access(access_logger, path, query, status):
    from backend.main import RequestContextMiddleware

    async def _downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"", "more_body": False})

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(_message):
        return None

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
    await RequestContextMiddleware(_downstream)(scope, _receive, _send)
    access_logger.info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:1234",
        "GET",
        f"{path}?{query}",
        "1.1",
        status,
    )
    access_logger.info(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:1234",
        "GET",
        f"https://agentnexlify-production.up.railway.app{path}?{query}",
        "1.1",
        status,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("callback_name", "provider", "_provider_key"),
    _PROVIDERS,
)
@pytest.mark.parametrize("outcome", ["success", "error"])
async def test_callback_logs_strip_code_and_state_on_success_and_error(
    monkeypatch, caplog, callback_name, provider, _provider_key, outcome
):
    install_oauth_callback_log_redaction()
    secret_code = f"super-secret-code-{provider}-{outcome}"
    secret_state = f"super-secret-state-{provider}-{outcome}"
    path = f"/api/v1/integrations/{provider}/callback"
    query = f"code={secret_code}&state={secret_state}"
    query_form = f"{path}?{query}"
    full_url = f"https://agentnexlify-production.up.railway.app{query_form}"
    monkeypatch.setattr(integrations_router.settings, "frontend_url", _FRONTEND)

    def _exchange(code, redirect_uri):
        if outcome == "error":
            raise RuntimeError(f"token exchange failed for {query_form} and {full_url}")
        if provider == "google":
            return _FakeGoogleCreds()
        return {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}

    if provider == "google":
        monkeypatch.setattr(integrations_router, "exchange_code", _exchange)
        monkeypatch.setattr(integrations_router, "save_integration", lambda **kwargs: None)
    elif provider == "m365":
        monkeypatch.setattr(integrations_router.m365_calendar, "exchange_code", _exchange)
        monkeypatch.setattr(integrations_router, "_fetch_m365_profile", lambda access_token: {})
        monkeypatch.setattr(
            integrations_router.m365_calendar, "save_integration", lambda **kwargs: None
        )
    else:
        monkeypatch.setattr(integrations_router.hubspot_tenant, "exchange_code", _exchange)
        monkeypatch.setattr(
            integrations_router.hubspot_tenant, "fetch_profile", lambda access_token: {}
        )
        monkeypatch.setattr(
            integrations_router.hubspot_tenant, "save_integration", lambda **kwargs: None
        )

    access_logger = logging.getLogger("uvicorn.access")
    access_stream = io.StringIO()
    access_handler = logging.StreamHandler(access_stream)
    access_handler.setFormatter(
        AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s')
    )
    access_logger.addHandler(access_handler)
    access_logger.setLevel(logging.INFO)
    state = integrations_router._encode_state("tenant-9")
    callback = getattr(integrations_router, callback_name)

    try:
        with caplog.at_level(logging.INFO):
            await callback(code=secret_code, state=state)
            await _log_access(access_logger, path, query, 302 if outcome == "success" else 400)
    finally:
        access_logger.removeHandler(access_handler)

    blob = _log_blob(caplog.records) + "\n" + access_stream.getvalue()
    assert secret_code not in blob
    assert secret_state not in blob
    assert "code=" not in blob
    assert "state=" not in blob
    assert path in blob
    assert full_url.split("?", 1)[0] in blob
    if outcome == "error":
        error_text = "\n".join(
            (record.getMessage() + "\n" + (record.exc_text or ""))
            for record in caplog.records
            if record.levelno >= logging.ERROR
        )
        assert error_text
        assert secret_code not in error_text
        assert secret_state not in error_text
        assert "code=" not in error_text
        assert "state=" not in error_text
        assert path in error_text


@pytest.mark.parametrize("provider", ["google", "m365", "hubspot"])
@pytest.mark.parametrize("url_includes_query", [True, False])
def test_sentry_callback_exception_event_has_no_code_or_state(provider, url_includes_query):
    secret_code = f"super-secret-code-{provider}"
    secret_state = f"super-secret-state-{provider}"
    path = f"/api/v1/integrations/{provider}/callback"
    query = f"code={secret_code}&state={secret_state}"
    url = f"https://app.agentnexlify.com{path}"
    if url_includes_query:
        url = f"{url}?{query}"
    event = {
        "exception": {
            "values": [{"type": "RuntimeError", "value": "OAuth callback failed"}]
        },
        "request": {
            "method": "GET",
            "url": url,
            "query_string": query,
        },
    }

    sent = sentry_before_send(event, {"exc_info": (RuntimeError, RuntimeError("x"), None)})
    blob = json.dumps(sent)

    assert secret_code not in blob
    assert secret_state not in blob
    assert "code=" not in blob
    assert "state=" not in blob
    assert sent["request"]["query_string"] == ""
    assert sent["request"]["url"] == f"https://app.agentnexlify.com{path}"
    assert sent["exception"]["values"][0]["type"] == "RuntimeError"


def test_sentry_before_send_leaves_other_requests_unchanged():
    event = {
        "exception": {"values": [{"type": "RuntimeError", "value": "other"}]},
        "request": {
            "url": "https://app.agentnexlify.com/api/v1/leads?status=new",
            "query_string": "status=new",
        },
    }
    sent = sentry_before_send(event, {})
    assert sent["request"]["query_string"] == "status=new"
    assert sent["request"]["url"].endswith("?status=new")
