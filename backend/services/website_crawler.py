"""Website crawling service using Cloudflare Browser Rendering API.

Crawls a tenant's website and extracts business content for AI knowledge base.
Two-step flow: POST /crawl to start → poll for completion → extract content.
"""

import logging
from datetime import datetime, timezone

import httpx

from backend.config import settings
from backend.models.database import get_service_supabase
from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)

_CF_BASE = "https://api.cloudflare.com/client/v4/accounts"
_MAX_PAGES = 20


def _cf_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.cloudflare_api_token}",
        "Content-Type": "application/json",
    }


async def start_crawl(tenant_id: str, url: str) -> dict:
    """Start a website crawl for a tenant. Returns the crawl record."""
    db = get_service_supabase()

    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # SSRF protection (resolves DNS; blocks rebind/metadata pivots)
    if not is_safe_url(url):
        raise ValueError("Invalid or unsafe URL. Please provide a public website URL.")

    # Create or update crawl record
    existing = (
        db.table("website_content")
        .select("id")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    crawl_data = {
        "tenant_id": tenant_id,
        "url": url,
        "crawl_status": "crawling",
        "pages_json": [],
        "extracted_text": None,
        "error_message": None,
        "pages_found": 0,
        "crawled_at": None,
    }

    if existing.data:
        result = (
            db.table("website_content")
            .update(crawl_data)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        result = db.table("website_content").insert(crawl_data).execute()

    if not result.data:
        raise RuntimeError("Failed to create crawl record")

    crawl_record = result.data[0]

    # Fire the actual crawl in background
    try:
        await _execute_crawl(crawl_record["id"], tenant_id, url)
    except Exception:
        logger.exception("Crawl failed for tenant_id=%s url=%s", tenant_id, url)
        db.table("website_content").update({
            "crawl_status": "failed",
            "error_message": "Could not reach website. Please check the URL and try again.",
        }).eq("id", crawl_record["id"]).execute()

    # Return fresh status
    fresh = (
        db.table("website_content")
        .select("*")
        .eq("id", crawl_record["id"])
        .limit(1)
        .execute()
    )
    return fresh.data[0] if fresh.data else crawl_record


async def _execute_crawl(crawl_id: str, tenant_id: str, url: str) -> None:
    """Call Cloudflare Browser Rendering /crawl endpoint and store results."""
    db = get_service_supabase()

    if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
        # Fallback: mark as needing config
        db.table("website_content").update({
            "crawl_status": "failed",
            "error_message": "Website scanning is not yet configured. Your business info can be added manually via the FAQ manager.",
        }).eq("id", crawl_id).execute()
        return

    crawl_url = f"{_CF_BASE}/{settings.cloudflare_account_id}/browser-rendering/crawl"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            crawl_url,
            headers=_cf_headers(),
            json={
                "url": url,
                "scrapeOptions": {
                    "formats": ["markdown"],
                },
                "limit": _MAX_PAGES,
            },
        )

        if resp.status_code != 200:
            error_text = resp.text[:500]
            logger.warning("Cloudflare crawl failed: status=%d body=%s", resp.status_code, error_text)
            db.table("website_content").update({
                "crawl_status": "failed",
                "error_message": f"Website scan failed (status {resp.status_code}). Please try again later.",
            }).eq("id", crawl_id).execute()
            return

        data = resp.json()

        # Cloudflare returns { success: true, result: [...pages...] }
        pages = []
        if data.get("success") and data.get("result"):
            raw_pages = data["result"] if isinstance(data["result"], list) else [data["result"]]
            for page in raw_pages[:_MAX_PAGES]:
                pages.append({
                    "url": page.get("url", url),
                    "markdown": page.get("markdown", page.get("content", "")),
                    "title": page.get("metadata", {}).get("title", ""),
                })

        if not pages:
            db.table("website_content").update({
                "crawl_status": "failed",
                "error_message": "No content found on the website. The site may be empty or block automated access.",
            }).eq("id", crawl_id).execute()
            return

        # Combine all markdown for extracted_text
        combined_text = "\n\n---\n\n".join(
            f"# {p['title']}\n\n{p['markdown']}" if p.get("title") else p["markdown"]
            for p in pages
            if p.get("markdown")
        )

        # Truncate to ~50KB to avoid oversized DB entries
        if len(combined_text) > 50000:
            combined_text = combined_text[:50000] + "\n\n[Content truncated]"

        db.table("website_content").update({
            "crawl_status": "completed",
            "pages_json": pages,
            "extracted_text": combined_text,
            "pages_found": len(pages),
            "crawled_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", crawl_id).execute()

        logger.info(
            "Crawl completed for tenant_id=%s: %d pages, %d chars",
            tenant_id, len(pages), len(combined_text),
        )


def get_crawl_status(tenant_id: str) -> dict | None:
    """Get the latest crawl status for a tenant."""
    db = get_service_supabase()
    result = (
        db.table("website_content")
        .select("id, url, crawl_status, error_message, pages_found, crawled_at, created_at")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_crawled_content(tenant_id: str) -> str | None:
    """Get the extracted text content for injection into AI system prompt."""
    db = get_service_supabase()
    result = (
        db.table("website_content")
        .select("extracted_text")
        .eq("tenant_id", tenant_id)
        .eq("crawl_status", "completed")
        .order("crawled_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data and result.data[0].get("extracted_text"):
        return result.data[0]["extracted_text"]
    return None
