import logging
import os

from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)

# Deterministic dev-only fallback — production MUST set API_SECRET_KEY env var.
# Using a random default causes each Uvicorn worker to generate a different key,
# making JWTs non-portable across workers.
_DEV_FALLBACK_SECRET = "INSECURE-DEV-ONLY-CHANGE-ME-IN-PRODUCTION"
_WEAK_SECRET_MIN_LEN = 32


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    widget_chat_model: str = "claude-sonnet-4-6"
    widget_chat_max_tokens: int = 320
    voice_chat_model: str = "claude-sonnet-4-6"
    voice_chat_max_tokens: int = 160
    widget_prompt_faq_limit: int = 6
    widget_prompt_corrections_limit: int = 8
    widget_prompt_website_chars: int = 2500
    widget_prompt_knowledge_chars: int = 3500
    widget_prompt_flow_chars: int = 1500
    widget_prompt_history_messages: int = 8
    widget_prompt_history_chars: int = 2200
    widget_prompt_message_chars: int = 420
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_growth_monthly: str = ""
    stripe_price_professional_monthly: str = ""
    stripe_price_autopilot_monthly: str = ""
    stripe_price_enterprise_monthly: str = ""
    stripe_price_marketing_addon_monthly: str = ""
    frontend_url: str = "http://localhost:5173"
    api_url: str = "https://agentnexlify-production.up.railway.app"
    cors_allowed_origins: str = ""

    resend_api_key: str = ""
    sentry_dsn: str = ""

    # Inbound email webhooks (Agent OS connectors — Phase 4).
    # Postmark: HMAC-SHA256 over raw body using this secret, sent as
    # X-Postmark-Webhook-Hmac. Mailgun: HMAC-SHA256 over timestamp+token
    # using the signing key configured in the Mailgun control panel.
    postmark_webhook_secret: str = ""
    mailgun_signing_key: str = ""

    widget_allowed_origins: str = "*"
    # Production MUST set API_SECRET_KEY env var. The dev fallback is deterministic
    # so all workers share the same key, but it is NOT secure for production use.
    api_secret_key: str = _DEV_FALLBACK_SECRET
    # Optional dedicated JWT signing key. Falls back to API secret when unset.
    jwt_secret_key: str = ""
    # Optional dedicated admin API secret for /api/v1/admin routes.
    # Falls back to API secret when unset for backward compatibility.
    admin_api_secret_key: str = ""
    # Transitional switch for old unsubscribe links that only sign lead_id.
    # New links are tenant-bound and this should stay disabled in production.
    allow_legacy_unsubscribe_signatures: bool = False
    # Transitional switch for old appointment links signed only with appointment_id.
    # Keep disabled in production; old tokens are bearer credentials with no expiry.
    allow_legacy_reschedule_tokens: bool = False
    billing_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # Microsoft 365 / Azure AD OAuth — calendar + mail send scopes.
    # `m365_tenant_id` is the Azure AD tenant ("common" for multi-tenant +
    # personal accounts, "organizations" for work/school only, or a specific
    # tenant GUID for single-tenant). Defaults to "common" so any M365 user
    # can connect.
    m365_client_id: str = ""
    m365_client_secret: str = ""
    m365_redirect_uri: str = ""
    m365_tenant_id: str = "common"

    # HubSpot OAuth — CRM write-back for contact upserts via Group B actions.
    # Scopes are space-separated: `crm.objects.contacts.read
    # crm.objects.contacts.write oauth`. The redirect URI must match the
    # value registered in the HubSpot app config exactly.
    hubspot_client_id: str = ""
    hubspot_client_secret: str = ""
    hubspot_redirect_uri: str = ""

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    voyage_api_key: str = ""
    openrouter_api_key: str = ""

    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_verify_token: str = ""

    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    # Claude Managed Agents — populated by scripts/managed_agents/provision.py.
    # Load via BaseSettings from .env AND from .env.managed_agents (see model_config).
    managed_agents_environment_id: str = ""
    lead_qualifier_agent_id: str = ""
    document_drafter_agent_id: str = ""
    codebase_reviewer_agent_id: str = ""
    support_agent_id: str = ""
    structured_extractor_agent_id: str = ""
    deep_researcher_agent_id: str = ""
    field_monitor_agent_id: str = ""
    data_analyst_agent_id: str = ""

    model_config = {
        "env_file": (".env", ".env.managed_agents"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()


def is_production() -> bool:
    """Return True when the process is running in a production deployment."""
    candidates = (
        os.environ.get("ENV"),
        os.environ.get("APP_ENV"),
        os.environ.get("ENVIRONMENT"),
        os.environ.get("RAILWAY_ENVIRONMENT"),
        os.environ.get("VERCEL_ENV"),
    )
    return any(
        (value or "").strip().lower() in {"prod", "production"} for value in candidates
    )


def _is_weak_secret(value: str | None) -> bool:
    value = (value or "").strip()
    return (
        not value or value == _DEV_FALLBACK_SECRET or len(value) < _WEAK_SECRET_MIN_LEN
    )


def _production_secret_failures(
    api_secret_key: str,
    jwt_secret_key: str,
    admin_api_secret_key: str,
) -> list[str]:
    """Return the production secret env vars that are missing or weak."""
    failures: list[str] = []
    if _is_weak_secret(api_secret_key):
        failures.append("API_SECRET_KEY")
    if jwt_secret_key and _is_weak_secret(jwt_secret_key):
        failures.append("JWT_SECRET_KEY")
    if admin_api_secret_key and _is_weak_secret(admin_api_secret_key):
        failures.append("ADMIN_API_SECRET_KEY")
    return failures


def _enforce_production_secrets() -> None:
    if not is_production():
        return

    failures = _production_secret_failures(
        settings.api_secret_key,
        settings.jwt_secret_key,
        settings.admin_api_secret_key,
    )

    if failures:
        raise RuntimeError(
            "Refusing to start production with missing or weak secrets: "
            + ", ".join(failures)
        )


_enforce_production_secrets()

if settings.api_secret_key == _DEV_FALLBACK_SECRET:
    _config_logger.warning(
        "API_SECRET_KEY is not set — using insecure dev-only fallback. "
        "Set the API_SECRET_KEY environment variable before deploying to production!"
    )

if not settings.jwt_secret_key:
    _config_logger.warning(
        "JWT_SECRET_KEY is not set — falling back to API_SECRET_KEY. "
        "Set JWT_SECRET_KEY to isolate JWT signing from other secrets."
    )

if not settings.admin_api_secret_key:
    _config_logger.warning(
        "ADMIN_API_SECRET_KEY is not set — falling back to API_SECRET_KEY. "
        "Set ADMIN_API_SECRET_KEY to isolate admin access."
    )
