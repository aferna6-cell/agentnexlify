"""Content Studio endpoints — source content CRUD and AI repurposing."""

import logging
from datetime import datetime, timezone

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/content", tags=["content"])


# --- Models ---

class ContentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    source_type: str = "text"  # text, description, file
    source_content: str = Field(..., min_length=1, max_length=50000)
    tags: list[str] | None = None


class ContentUpdate(BaseModel):
    title: str | None = None
    source_content: str | None = None
    platform_versions: dict | None = None
    status: str | None = None
    tags: list[str] | None = None
    scheduled_for: str | None = None  # ISO date string (YYYY-MM-DD) or null to unschedule


# --- Helpers ---

def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


# --- Endpoints ---

@router.get("/{tenant_id}")
async def list_content(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List content items with optional status filter."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    query = (
        db.table("content_items")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    items = result.data or []

    # Get total count for pagination
    count_query = (
        db.table("content_items")
        .select("id", count="exact")
        .eq("tenant_id", tenant_id)
    )
    if status:
        count_query = count_query.eq("status", status)
    count_result = count_query.execute()
    total = count_result.count if count_result.count is not None else len(items)

    return {"items": items, "total": total}


@router.get("/{tenant_id}/{content_id}")
async def get_content(
    tenant_id: str,
    content_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single content item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("content_items")
        .select("*")
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")

    return result.data[0]


@router.post("/{tenant_id}")
async def create_content(
    tenant_id: str,
    req: ContentCreate,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new content item (source content for repurposing)."""
    _verify_tenant(claims, tenant_id)

    payload = {
        "tenant_id": tenant_id,
        "title": req.title,
        "source_type": req.source_type,
        "source_content": req.source_content,
        "status": "draft",
    }
    if req.tags:
        payload["tags"] = req.tags[:10]  # max 10 tags

    db = get_supabase()
    result = db.table("content_items").insert(payload).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create content")

    return result.data[0]


@router.patch("/{tenant_id}/{content_id}")
async def update_content(
    tenant_id: str,
    content_id: str,
    req: ContentUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a content item."""
    _verify_tenant(claims, tenant_id)

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "tags" in updates:
        updates["tags"] = updates["tags"][:10]

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    db = get_supabase()
    result = (
        db.table("content_items")
        .update(updates)
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")

    return result.data[0]


@router.delete("/{tenant_id}/{content_id}", status_code=204)
async def delete_content(
    tenant_id: str,
    content_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a content item."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("content_items")
        .delete()
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")


PLATFORM_SPECS = {
    "linkedin": {
        "name": "LinkedIn",
        "instructions": (
            "Professional tone. 150-300 words. Use line breaks for readability. "
            "Start with a hook that grabs attention. End with a question or call to action. "
            "No hashtags in the body — add 3-5 relevant hashtags at the end."
        ),
    },
    "facebook": {
        "name": "Facebook",
        "instructions": (
            "Casual and conversational. 100-200 words. "
            "Use short paragraphs. Can include emojis sparingly. "
            "End with a question to drive engagement. No hashtags."
        ),
    },
    "instagram": {
        "name": "Instagram Caption",
        "instructions": (
            "Short and punchy. 50-150 words. "
            "Visual and emotive language. Use emojis naturally. "
            "End with 10-15 relevant hashtags on a separate line."
        ),
    },
    "gbp": {
        "name": "Google Business Profile Update",
        "instructions": (
            "Local SEO optimized. 100-200 words. "
            "Mention the business location/service area naturally. "
            "Include a clear call to action (book now, call us, visit). "
            "Professional but approachable tone. No hashtags."
        ),
    },
    "email": {
        "name": "Email Newsletter Snippet",
        "instructions": (
            "Warm and personal. 150-250 words. "
            "Write as if speaking directly to a customer. "
            "Include a clear subject line on the first line (format: Subject: ...). "
            "End with a call to action."
        ),
    },
    "twitter": {
        "name": "Twitter/X Thread",
        "instructions": (
            "Break into a thread of 3-5 tweets. "
            "Each tweet is under 280 characters. "
            "Separate tweets with ---. "
            "First tweet is the hook. Last tweet is the call to action. "
            "Punchy, direct language. Minimal emojis."
        ),
    },
}


@router.post("/{tenant_id}/{content_id}/repurpose")
async def repurpose_content(
    tenant_id: str,
    content_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Generate platform-specific versions of source content using Claude AI."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    result = (
        db.table("content_items")
        .select("*")
        .eq("id", content_id)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Content not found")

    item = result.data[0]
    source = item["source_content"]

    # Get business context for better content
    tenant_result = (
        db.table("tenants")
        .select("business_name, business_type")
        .eq("id", tenant_id)
        .limit(1)
        .execute()
    )
    business_name = tenant_result.data[0]["business_name"] if tenant_result.data else "the business"
    business_type = tenant_result.data[0].get("business_type", "") if tenant_result.data else ""
    biz_context = f" for {business_name}" + (f", a {business_type}" if business_type else "")

    # Build one prompt for all platforms
    platform_block = "\n\n".join(
        f"### {spec['name']}\nRules: {spec['instructions']}"
        for spec in PLATFORM_SPECS.values()
    )
    platform_keys = list(PLATFORM_SPECS.keys())

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            temperature=0.7,
            system=(
                f"You are a social media content expert creating posts{biz_context}. "
                "Given source content, create optimized versions for each platform below. "
                "Each version should capture the key message but be tailored to the platform's "
                "audience, tone, and format. Never copy the source verbatim — rewrite for each platform.\n\n"
                "Output format: Return ONLY the content for each platform, separated by the exact delimiter "
                f"'===PLATFORM===' followed by the platform key. Platform keys in order: {', '.join(platform_keys)}.\n\n"
                f"Platform specifications:\n{platform_block}"
            ),
            messages=[{
                "role": "user",
                "content": f"Source content to repurpose:\n\n{source[:10000]}",
            }],
        )
        raw = resp.content[0].text.strip()
    except Exception:
        logger.error("Content repurpose failed for %s", content_id, exc_info=True)
        raise HTTPException(status_code=500, detail="AI content generation failed")

    # Parse the response into platform versions
    versions = {}
    current_platform = None
    current_lines = []

    for line in raw.split("\n"):
        stripped = line.strip()
        # Check for platform delimiter
        matched = False
        for key in platform_keys:
            if key.lower() in stripped.lower() and "===platform===" in stripped.lower():
                if current_platform and current_lines:
                    versions[current_platform] = "\n".join(current_lines).strip()
                current_platform = key
                current_lines = []
                matched = True
                break
        if not matched:
            current_lines.append(line)

    # Capture the last platform
    if current_platform and current_lines:
        versions[current_platform] = "\n".join(current_lines).strip()

    # Fallback: if parsing failed, try to split by platform names
    if len(versions) < 3:
        versions = {}
        sections = raw.split("===PLATFORM===")
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            # First line might be the platform key
            lines = section.split("\n", 1)
            key = lines[0].strip().lower().replace(" ", "")
            if key in platform_keys:
                versions[key] = lines[1].strip() if len(lines) > 1 else ""
            elif i - 1 < len(platform_keys):
                # Positional fallback
                versions[platform_keys[i - 1 if i > 0 else 0]] = section

    # Save platform versions and update status
    db.table("content_items").update({
        "platform_versions": versions,
        "status": "generated",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", content_id).execute()

    return {"platform_versions": versions, "status": "generated"}
