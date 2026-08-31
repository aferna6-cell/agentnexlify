
import logging
import warnings

import httpx
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions
from supabase_auth import SyncMemoryStorage

from backend.config import is_production, settings
from backend.services.tenant_scope import TenantScopedClient, tenant_client

logger = logging.getLogger(__name__)

_service_client: Client | None = None
_public_client: Client | None = None
_get_supabase_warned: bool = False


def _create_supabase_client(supabase_url: str, supabase_key: str) -> Client:
    options = SyncClientOptions(
        storage=SyncMemoryStorage(),
        httpx_client=httpx.Client(timeout=120.0),
    )
    return create_client(supabase_url, supabase_key, options)


def get_service_supabase() -> Client:
    """Return the privileged Supabase service-role client.

    Use this for internal jobs/admin operations only. Request-path tenant data
    should use ``get_tenant_supabase`` or the helpers in ``tenant_scope``.

    ``settings.supabase_service_key`` accepts Supabase legacy ``service_role``
    JWT keys (``eyJ...``) or modern secret keys (``sb_secret_...``). Requires
    ``supabase>=2.28.0`` (pinned in backend/requirements.txt).
    """
    global _service_client
    if _service_client is None:
        if is_production() and not settings.supabase_service_key:
            raise RuntimeError("SUPABASE_SERVICE_KEY is required in production")
        _service_client = _create_supabase_client(settings.supabase_url, settings.supabase_service_key)
    return _service_client


def get_public_supabase() -> Client:
    """Return a non-service Supabase client for public/anon flows."""
    global _public_client
    if _public_client is None:
        if is_production() and not settings.supabase_key:
            raise RuntimeError("SUPABASE_KEY is required for the public Supabase client in production")
        _public_client = _create_supabase_client(
            settings.supabase_url,
            settings.supabase_key or settings.supabase_service_key,
        )
    return _public_client


def get_tenant_supabase(tenant_id: str) -> TenantScopedClient:
    """Return a tenant-scoped facade over the service client."""
    return tenant_client(get_service_supabase(), tenant_id)


def get_supabase() -> Client:
    """Backward-compatible service-role client. **Deprecated.**

    New code should call one of the explicit alternatives directly:

    - ``get_service_supabase()`` for internal admin / background jobs
    - ``get_tenant_supabase(tenant_id)`` for tenant-scoped request paths

    This wrapper is kept only so the 200+ legacy call sites keep working
    during the incremental rename. It emits a one-shot DeprecationWarning
    the first time it is invoked per worker process so drift is visible
    in CI and local dev without flooding production logs.
    """
    global _get_supabase_warned
    if not _get_supabase_warned:
        _get_supabase_warned = True
        warnings.warn(
            "backend.models.database.get_supabase() is deprecated; "
            "prefer get_service_supabase() or get_tenant_supabase(tenant_id)",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.debug(
            "get_supabase() called — this alias is deprecated, see database.py"
        )
    return get_service_supabase()
