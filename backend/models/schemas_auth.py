from pydantic import BaseModel, field_validator


class SignupRequest(BaseModel):
    business_name: str
    owner_name: str
    email: str
    industry: str = "other"
    city: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v


class SignupResponse(BaseModel):
    client_id: str
    widget_api_key: str
    embed_code: str


class WidgetConfigUpdate(BaseModel):
    bot_name: str | None = None
    brand_color: str | None = None
    greeting_message: str | None = None
    position: str | None = None


class RegisterRequest(BaseModel):
    business_name: str
    owner_name: str
    email: str
    password: str
    industry: str = "other"
    city: str = ""
    phone: str | None = None
    website_url: str | None = None

    @field_validator("email")
    @classmethod
    def validate_register_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("Invalid email address")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Password must be at least 10 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    @field_validator("website_url")
    @classmethod
    def validate_website_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        import re
        if not re.match(r"^https?://", v, re.IGNORECASE):
            v = f"https://{v}"
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v, re.IGNORECASE):
            raise ValueError("Invalid website URL")
        return v


class RegisterResponse(BaseModel):
    tenant_id: str
    api_key: str
    token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    tenant_id: str
    token: str
    business_name: str
    plan: str


class GoogleRegisterRequest(BaseModel):
    setup_token: str
    business_name: str
    industry: str = "other"
    city: str = ""
    phone: str | None = None
    website_url: str | None = None

    @field_validator("website_url")
    @classmethod
    def validate_google_website_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        import re
        if not re.match(r"^https?://", v, re.IGNORECASE):
            v = f"https://{v}"
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v, re.IGNORECASE):
            raise ValueError("Invalid website URL")
        return v


class MeResponse(BaseModel):
    tenant_id: str
    email: str
    business_name: str
    plan: str
    city: str | None = None
    owner_name: str | None = None
    business_type: str | None = None
    marketing_addon_active: bool = False
    marketing_addon_grandfathered: bool = False


class WidgetConfigDetail(BaseModel):
    bot_name: str = ""
    primary_color: str = "#00BFFF"
    greeting_message: str = "Hi! How can I help you today?"
    position: str = "bottom-right"
    branding: dict | None = None
    is_online: bool = True
    offline_message: str | None = None
    teaser_message: str | None = None
    teaser_delay_seconds: int = 3
    teaser_enabled: bool = True
    enable_ai_fallback: bool = False
    enable_structured_lead_parser: bool = False
