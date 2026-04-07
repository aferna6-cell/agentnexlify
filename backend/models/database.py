
from supabase import create_client, Client

from backend.config import is_production, settings
from backend.services.tenant_scope import TenantScopedClient, tenant_client

_service_client: Client | None = None
_public_client: Client | None = None


def get_service_supabase() -> Client:
    """Return the privileged Supabase service-role client.

    Use this for internal jobs/admin operations only. Request-path tenant data
    should use ``get_tenant_supabase`` or the helpers in ``tenant_scope``.
    """
    global _service_client
    if _service_client is None:
        if is_production() and not settings.supabase_service_key:
            raise RuntimeError("SUPABASE_SERVICE_KEY is required in production")
        _service_client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _service_client


def get_public_supabase() -> Client:
    """Return a non-service Supabase client for public/anon flows."""
    global _public_client
    if _public_client is None:
        if is_production() and not settings.supabase_key:
            raise RuntimeError("SUPABASE_KEY is required for the public Supabase client in production")
        _public_client = create_client(settings.supabase_url, settings.supabase_key or settings.supabase_service_key)
    return _public_client


def get_tenant_supabase(tenant_id: str) -> TenantScopedClient:
    """Return a tenant-scoped facade over the service client."""
    return tenant_client(get_service_supabase(), tenant_id)


def get_supabase() -> Client:
    """Backward-compatible service-role client.

    New tenant request-path code should prefer ``get_tenant_supabase``.
    """
    return get_service_supabase()
