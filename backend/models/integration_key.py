"""Pydantic models for the integration key vault (onboarding-v2, GH #131).

These map to FastAPI request/response bodies, so PEP 563 deferred annotations
must stay off (they break Pydantic body resolution -> 422s).
"""

from pydantic import BaseModel, Field


class SaveIntegrationKeyRequest(BaseModel):
    """Owner submits a third-party API key for encryption at rest."""

    provider: str = Field(..., min_length=1, description="e.g. stripe, twilio, resend")
    plaintext: str = Field(..., min_length=1, description="Raw API key; never stored in the clear")
    metadata: dict = Field(default_factory=dict, description="Auxiliary non-secret fields")


class MaskedKeyResponse(BaseModel):
    """Safe-to-display result after save/mask. Never carries the plaintext key."""

    provider: str
    masked: str = Field(..., description="e.g. apikey__••••1234")
    enc_key_version: int = 1
