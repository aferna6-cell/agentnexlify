from pydantic import BaseModel


class CreateCheckoutRequest(BaseModel):
    tenant_id: str
    plan: str  # growth|professional|enterprise
    promo_code: str | None = None
    source: str | None = None  # "wizard" or null


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str
