"""Website crawl endpoints — start crawl, check status, get content."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from backend.routers.auth import require_role
from backend.services.website_crawler import get_crawl_status, get_crawled_content, start_crawl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/crawl", tags=["crawl"])


@router.post("/{tenant_id}/start")
async def trigger_crawl(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin")),
):
    """Start a website crawl for the tenant's website URL."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    from backend.models.database import get_supabase
    db = get_supabase()

    # Get tenant's website_url
    result = (
        db.table("tenants")
        .select("website_url")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    url = result.data[0].get("website_url")
    if not url:
        raise HTTPException(status_code=400, detail="No website URL configured. Add your website URL in Settings first.")

    crawl_record = await start_crawl(tenant_id, url)
    return crawl_record


@router.get("/{tenant_id}/status")
async def crawl_status(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Get the latest crawl status for a tenant."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    status = get_crawl_status(tenant_id)
    if not status:
        return {"crawl_status": "none"}
    return status


@router.get("/{tenant_id}/content")
async def crawl_content(
    tenant_id: str,
    claims: dict = Depends(require_role("owner", "admin", "member")),
):
    """Get the extracted website content (for AI knowledge base preview)."""
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    content = get_crawled_content(tenant_id)
    if not content:
        return {"content": None, "message": "No crawled content available. Scan your website first."}
    return {"content": content}
