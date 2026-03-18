
import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    calendly_api_key: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    frontend_url: str = "http://localhost:5173"
    api_url: str = "https://agentnexlify-production.up.railway.app"

    resend_api_key: str = ""

    widget_allowed_origins: str = "*"
    api_secret_key: str = secrets.token_urlsafe(32)
    sentry_dsn: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""

    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_verify_token: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
