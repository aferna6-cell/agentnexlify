"""URL + JWT secret helpers for the client portal flow.

Re-exported through ``backend.routers.client_portal`` for backward
compatibility with tests that patch ``client_portal.settings`` and call
``client_portal._portal_base_url``.
"""

from urllib.parse import urlparse

from backend.config import settings

_PUBLIC_PORTAL_FRONTEND_URL = "https://app.agentnexlify.com"
_PUBLIC_API_BASE_URL = "https://agentnexlify-production.up.railway.app"
_STALE_FRONTEND_HOSTS = {"agentnexlify.com"}
_STALE_FRONTEND_HOST_SUFFIXES = (".vercel.app",)

__all__ = [
    "_PUBLIC_PORTAL_FRONTEND_URL",
    "_PUBLIC_API_BASE_URL",
    "_STALE_FRONTEND_HOSTS",
    "_STALE_FRONTEND_HOST_SUFFIXES",
    "_portal_base_url",
    "_api_base_url",
    "_jwt_secret",
]


def _portal_base_url() -> str:
    frontend_url = getattr(settings, "frontend_url", "")
    if not isinstance(frontend_url, str):
        frontend_url = ""
    frontend_url = frontend_url.rstrip("/")
    parsed = urlparse(frontend_url)
    hostname = parsed.hostname or ""
    is_local = hostname in {"localhost", "127.0.0.1", "::1"}
    is_stale_alias = (
        hostname in _STALE_FRONTEND_HOSTS
        or any(hostname.endswith(suffix) for suffix in _STALE_FRONTEND_HOST_SUFFIXES)
    )
    if parsed.scheme in {"http", "https"} and hostname and not is_local and not is_stale_alias:
        return f"{frontend_url}/client"
    return f"{_PUBLIC_PORTAL_FRONTEND_URL}/client"


def _api_base_url() -> str:
    api_url = getattr(settings, "api_url", "")
    if isinstance(api_url, str) and api_url.strip():
        return api_url
    return _PUBLIC_API_BASE_URL


def _jwt_secret() -> str:
    jwt_secret = getattr(settings, "jwt_secret_key", "")
    if isinstance(jwt_secret, str) and jwt_secret:
        return jwt_secret
    api_secret = getattr(settings, "api_secret_key", "")
    return api_secret if isinstance(api_secret, str) else ""
