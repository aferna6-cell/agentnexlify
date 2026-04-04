
import logging
import os

from pydantic_settings import BaseSettings

_config_logger = logging.getLogger(__name__)

# Deterministic dev-only fallback — production MUST set API_SECRET_KEY env var.
# Using a random default causes each Uvicorn worker to generate a different key,
# making JWTs non-portable across workers.
_DEV_FALLBACK_SECRET = "INSECURE-DEV-ONLY-CHANGE-ME-IN-PRODUCTION"


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
    frontend_url: str = "http://localhost:5173"
    api_url: str = "https://agentnexlify-production.up.railway.app"

    resend_api_key: str = ""

    widget_allowed_origins: str = "*"
    # Production MUST set API_SECRET_KEY env var. The dev fallback is deterministic
    # so all workers share the same key, but it is NOT secure for production use.
    api_secret_key: str = _DEV_FALLBACK_SECRET
    sentry_dsn: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()

if settings.api_secret_key == _DEV_FALLBACK_SECRET:
    _config_logger.warning(
        "API_SECRET_KEY is not set — using insecure dev-only fallback. "
        "Set the API_SECRET_KEY environment variable before deploying to production!"
    )
