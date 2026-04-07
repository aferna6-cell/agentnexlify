
from supabase import create_client, Client

from backend.config import is_production, settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        if is_production() and not settings.supabase_service_key:
            raise RuntimeError("SUPABASE_SERVICE_KEY is required in production")
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client
