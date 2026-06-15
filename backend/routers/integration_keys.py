"""Tenant-facing API for saving, listing, deleting, and verifying third-party
integration keys (Stripe, Twilio, Resend).  GH #132.

All routes require a valid JWT via ``Depends(_get_current_tenant)``.
The tenant_id is ALWAYS taken from the JWT claims — never from the request body.

Security invariants (from vault module):
- Plaintext key values are never logged.
- Only tenant_id + provider appear in log lines.

Route prefix: /api/v1/integrations  (shares prefix with integrations.py for
Google Calendar; FastAPI merges routers at app level so there is no conflict).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.dependencies import _get_current_tenant
from backend.limiter import limiter
from backend.models.database import get_service_supabase
from backend.models.integration_key import (
    IntegrationsHealthResponse,
    MaskedKeyResponse,
    ProviderHealth,
    SaveIntegrationKeyRequest,
    SaveKeyResult,
)
from backend.services.integration_health_checker import (
    check_all_providers,
    check_provider,
)
from backend.services.integration_key_vault import (
    IntegrationKeyVaultError,
    load_integration_key,
    mask_key,
    save_integration_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

_ALLOWED_PROVIDERS = frozenset({"stripe", "twilio", "resend"})


def _overall_status(providers: list) -> str:
    """Derive the aggregate status string from a list of provider health dicts."""
    healths = [p.get("health", "red") for p in providers]
    if any(h == "red" for h in healths):
        return "not_ready"
    if any(h == "yellow" for h in healths):
        return "needs_attention"
    return "healthy"


# ---------------------------------------------------------------------------
# POST /keys — save (encrypt) a new key and inline-verify it
# ---------------------------------------------------------------------------


@router.post("/keys", response_model=SaveKeyResult, status_code=200)
async def save_key(
    body: SaveIntegrationKeyRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Encrypt and store a third-party API key, then run an inline health check."""
    tenant_id: str = claims["tenant_id"]
    provider = body.provider.lower().strip()

    if provider not in _ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(sorted(_ALLOWED_PROVIDERS))}",
        )

    try:
        result = save_integration_key(
            tenant_id=tenant_id,
            provider=provider,
            plaintext=body.plaintext,
            metadata=body.metadata or {},
        )
    except IntegrationKeyVaultError as exc:
        logger.warning(
            "key save failed tenant=%s provider=%s: %s", tenant_id, provider, exc
        )
        raise HTTPException(status_code=500, detail="Failed to save integration key") from exc
    except Exception as exc:
        logger.exception(
            "unexpected error saving key tenant=%s provider=%s", tenant_id, provider
        )
        raise HTTPException(status_code=500, detail="Internal error") from exc

    # Inline health check after save
    health_result = check_provider(tenant_id, provider)

    logger.info("key saved+verified tenant=%s provider=%s", tenant_id, provider)
    return SaveKeyResult(
        saved=True,
        verified=health_result["health"],
        masked=result["masked"],
    )


# ---------------------------------------------------------------------------
# GET /keys — list configured providers for this tenant
# ---------------------------------------------------------------------------


@router.get("/keys", response_model=list)
async def list_keys(
    claims: dict = Depends(_get_current_tenant),
):
    """List all integration providers configured for this tenant with health status."""
    tenant_id: str = claims["tenant_id"]

    try:
        db = get_service_supabase()
        res = (
            db.table("integrations")
            .select("provider, metadata")
            .eq("tenant_id", tenant_id)
            .in_("provider", list(_ALLOWED_PROVIDERS))
            .execute()
        )
        rows = res.data or []
    except Exception as exc:
        logger.exception("list_keys DB query failed tenant=%s", tenant_id)
        raise HTTPException(status_code=500, detail="Failed to list integrations") from exc

    results = []
    for row in rows:
        provider = row.get("provider", "")
        # Decrypt for masking — safe because mask_key never logs the plaintext
        masked = ""
        health_signal = "red"
        try:
            plaintext = load_integration_key(tenant_id, provider)
            if plaintext:
                masked = mask_key(plaintext)
        except IntegrationKeyVaultError as exc:
            logger.warning(
                "decrypt failed for list tenant=%s provider=%s: %s",
                tenant_id,
                provider,
                exc,
            )

        health_result = check_provider(tenant_id, provider)
        results.append(
            ProviderHealth(
                provider=provider,
                health=health_result["health"],
                detail=health_result["detail"],
                last_verified_at=health_result.get("last_verified_at"),
                masked_key=masked,
            )
        )

    return [r.model_dump() for r in results]


# ---------------------------------------------------------------------------
# DELETE /keys/{provider} — remove a provider's stored key
# ---------------------------------------------------------------------------


@router.delete("/keys/{provider}", status_code=200)
async def delete_key(
    provider: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a stored integration key.

    Stripe deletion is blocked when the tenant has an active subscription to
    prevent breaking the billing flow.
    """
    tenant_id: str = claims["tenant_id"]
    provider = provider.lower().strip()

    if provider not in _ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(sorted(_ALLOWED_PROVIDERS))}",
        )

    # Guard: refuse to delete Stripe key when tenant has an active subscription
    if provider == "stripe":
        try:
            db = get_service_supabase()
            res = (
                db.table("tenants")
                .select("stripe_subscription_id, plan_status")
                .eq("id", tenant_id)
                .limit(1)
                .execute()
            )
            tenant_rows = res.data or []
            if tenant_rows:
                sub_id = tenant_rows[0].get("stripe_subscription_id") or ""
                plan_status = tenant_rows[0].get("plan_status") or ""
                if sub_id and plan_status == "active":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Cannot remove the Stripe key while the tenant has an active "
                            "subscription. Cancel or migrate the subscription first."
                        ),
                    )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "stripe subscription guard query failed tenant=%s", tenant_id
            )
            raise HTTPException(status_code=500, detail="Failed to check subscription status") from exc

    try:
        db = get_service_supabase()
        db.table("integrations").delete().eq("tenant_id", tenant_id).eq(
            "provider", provider
        ).execute()
    except Exception as exc:
        logger.exception(
            "delete_key DB delete failed tenant=%s provider=%s", tenant_id, provider
        )
        raise HTTPException(status_code=500, detail="Failed to delete integration key") from exc

    logger.info("integration key deleted tenant=%s provider=%s", tenant_id, provider)
    return {"deleted": True, "provider": provider}


# ---------------------------------------------------------------------------
# POST /keys/{provider}/verify — live health ping (rate limited)
# ---------------------------------------------------------------------------


@router.post("/keys/{provider}/verify", status_code=200)
@limiter.limit("10/minute")
async def verify_key(
    request: Request,
    provider: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Run a live health check for a single provider key.

    Rate limited to 10 requests per minute per IP to prevent credential enumeration.
    """
    tenant_id: str = claims["tenant_id"]
    provider = provider.lower().strip()

    if provider not in _ALLOWED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"provider must be one of: {', '.join(sorted(_ALLOWED_PROVIDERS))}",
        )

    result = check_provider(tenant_id, provider)
    logger.info(
        "verify_key tenant=%s provider=%s health=%s",
        tenant_id,
        provider,
        result["health"],
    )
    return {"health": result["health"], "detail": result["detail"]}


# ---------------------------------------------------------------------------
# GET /health — aggregate health for all providers
# ---------------------------------------------------------------------------


@router.get("/health", response_model=IntegrationsHealthResponse)
async def integrations_health(
    claims: dict = Depends(_get_current_tenant),
):
    """Aggregate health status across stripe, twilio, resend, and google_calendar."""
    tenant_id: str = claims["tenant_id"]

    provider_results = check_all_providers(tenant_id)
    overall = _overall_status(provider_results)

    provider_models = [
        ProviderHealth(
            provider=r["provider"],
            health=r["health"],
            detail=r["detail"],
            last_verified_at=r.get("last_verified_at"),
        )
        for r in provider_results
    ]

    return IntegrationsHealthResponse(
        providers=provider_models,
        overall=overall,
    )
