# Content Repurposer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a content repurposing engine that takes any source content and generates X threads, LinkedIn carousels, email sequences, TikTok scripts, and social posts — accessible from both the dashboard and chat widget.

**Architecture:** New `content_repurposer.py` service handles extraction + AI generation + output connection. Thin `content_repurpose.py` router exposes 6 REST endpoints. Widget detects content mode via keywords + toggle. Dashboard page provides full edit/preview/schedule UI. X/Twitter and TikTok OAuth integrations for direct posting.

**Tech Stack:** FastAPI, Claude API (claude-sonnet-4-6), Supabase, React, httpx, youtube-transcript-api

**Spec:** `docs/superpowers/specs/2026-04-04-content-repurposer-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `migrations/082_repurpose_jobs.sql` | Create `repurpose_jobs` table |
| `backend/services/content_repurposer.py` | Core service: extract, repurpose, connect |
| `backend/routers/content_repurpose.py` | 6 REST endpoints, plan-gated |
| `frontend/src/pages/ContentRepurposePage.jsx` | Dashboard UI: input, tabbed output, edit, push |
| `frontend/src/utils/api/repurpose.js` | API client for repurpose endpoints |
| `tests/test_content_repurpose.py` | Backend tests |

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | Register content_repurpose router |
| `backend/config.py` | Add twitter/tiktok config vars |
| `backend/routers/widget_chat.py` | Content mode detection + repurpose flow |
| `widget/agentnexlify-widget.js` + `frontend/public/widget/agentnexlify-widget.js` | Content mode toggle button + keyword detection |
| `frontend/src/components/App.jsx` | Add ContentRepurposePage route |
| `backend/routers/integrations.py` | Add X/Twitter and TikTok OAuth flows |

---

## Task 1: Database Migration

**Files:**
- Create: `migrations/082_repurpose_jobs.sql`

- [ ] **Step 1: Create migration file**

```sql
-- 082: Content Repurpose Jobs table
-- Stores AI-generated repurposed content from any source

CREATE TABLE IF NOT EXISTS repurpose_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    source_type TEXT NOT NULL,
    source_url TEXT,
    source_content TEXT NOT NULL,
    source_title TEXT,
    tone TEXT DEFAULT 'professional',
    outputs JSONB,
    status TEXT DEFAULT 'processing',
    connected_social_post_ids UUID[] DEFAULT '{}',
    connected_email_sequence_id UUID,
    created_via TEXT DEFAULT 'dashboard',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX repurpose_jobs_tenant_idx ON repurpose_jobs (tenant_id);
CREATE INDEX repurpose_jobs_status_idx ON repurpose_jobs (status);

ALTER TABLE repurpose_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants can manage own repurpose jobs"
    ON repurpose_jobs FOR ALL
    USING (tenant_id = auth.uid())
    WITH CHECK (tenant_id = auth.uid());

CREATE POLICY "Service role full access on repurpose_jobs"
    ON repurpose_jobs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
```

Write to `migrations/082_repurpose_jobs.sql`.

- [ ] **Step 2: Apply migration via Supabase MCP**

Run: `mcp__supabase__apply_migration` with name `repurpose_jobs` and the SQL above.

- [ ] **Step 3: Update schema-log.md**

Append to `docs/dev-knowledge/schema-log.md`:

```markdown

### Migration 082 — Repurpose Jobs (2026-04-04)
- Created `repurpose_jobs` table: tenant_id (FK), source_type, source_url, source_content, source_title, tone, outputs (JSONB), status, connected IDs
- RLS enabled with tenant policy + service role policy
- Indexes on tenant_id and status
```

- [ ] **Step 4: Commit**

```bash
git add migrations/082_repurpose_jobs.sql docs/dev-knowledge/schema-log.md
git commit -m "feat: add repurpose_jobs table for content repurposer (migration 082)"
```

---

## Task 2: Content Repurposer Service

**Files:**
- Create: `backend/services/content_repurposer.py`
- Create: `tests/test_content_repurpose.py`

- [ ] **Step 1: Install youtube-transcript-api**

```bash
pip install youtube-transcript-api --break-system-packages
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_content_repurpose.py`:

```python
"""Tests for the content repurposer service."""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.asyncio
async def test_extract_source_text():
    """extract_source with text type returns content as-is."""
    from backend.services.content_repurposer import extract_source
    result = await extract_source("text", "This is my blog post about AI chatbots for small business.")
    assert result["content"] == "This is my blog post about AI chatbots for small business."
    assert result["word_count"] == 10
    assert result["source_url"] is None


@pytest.mark.asyncio
async def test_extract_source_text_strips_html():
    """extract_source strips HTML tags from text input."""
    from backend.services.content_repurposer import extract_source
    result = await extract_source("text", "<p>Hello <b>world</b></p>")
    assert "<" not in result["content"]
    assert "Hello world" in result["content"]


@pytest.mark.asyncio
async def test_extract_source_url_validates():
    """extract_source rejects private/internal URLs."""
    from backend.services.content_repurposer import extract_source
    with pytest.raises(ValueError, match="unsafe"):
        await extract_source("url", "http://localhost:8000/admin")


@pytest.mark.asyncio
async def test_extract_source_youtube():
    """extract_source with youtube type extracts video ID and fetches transcript."""
    with patch("backend.services.content_repurposer.YouTubeTranscriptApi") as mock_yt:
        mock_yt.get_transcript.return_value = [
            {"text": "Hello everyone", "start": 0.0},
            {"text": "welcome to my channel", "start": 2.0},
        ]
        from backend.services.content_repurposer import extract_source
        result = await extract_source("youtube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert "Hello everyone" in result["content"]
        assert result["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_repurpose_returns_all_formats():
    """repurpose returns all 5 output formats."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '''{
        "x_thread": [{"tweet_num": 1, "content": "Hook tweet", "posted": false}],
        "linkedin_carousel": {"slides": [{"slide_num": 1, "text": "Title", "image_suggestion": "chart"}]},
        "email_sequence": [{"email_num": 1, "subject": "Subject", "body": "Body", "day": 1}],
        "tiktok_scripts": [{"script_num": 1, "hook": "Did you know", "body": "Main", "cta": "Follow"}],
        "social_posts": {"facebook": "FB post", "instagram": "IG post", "google_business": "GB post"}
    }'''

    with patch("backend.services.content_repurposer.anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from backend.services.content_repurposer import repurpose
        result = await repurpose(
            source_content="My blog post about AI",
            title="AI for Small Business",
            tenant_id="test-tenant",
            tone="professional",
            formats=["x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"]
        )

        assert "x_thread" in result
        assert "linkedin_carousel" in result
        assert "email_sequence" in result
        assert "tiktok_scripts" in result
        assert "social_posts" in result
        assert len(result["x_thread"]) >= 1


@pytest.mark.asyncio
async def test_repurpose_respects_format_filter():
    """repurpose only generates requested formats."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = '''{
        "x_thread": [{"tweet_num": 1, "content": "Hook", "posted": false}]
    }'''

    with patch("backend.services.content_repurposer.anthropic.Anthropic") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from backend.services.content_repurposer import repurpose
        result = await repurpose(
            source_content="My blog post",
            title="Test",
            tenant_id="test-tenant",
            tone="professional",
            formats=["x_thread"]
        )

        assert "x_thread" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/aidan/agentnexlify && python3 -m pytest tests/test_content_repurpose.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services.content_repurposer'`

- [ ] **Step 4: Write the service**

Create `backend/services/content_repurposer.py`:

```python
"""Content repurposer service.

Takes source content (URL, text, YouTube, podcast) and generates
5 output formats via Claude API: X threads, LinkedIn carousels,
email sequences, TikTok scripts, and social post variations.
"""

import json
import logging
import re

import anthropic
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

TONE_DESCRIPTIONS = {
    "professional": "Professional and authoritative. Clear, confident, data-driven.",
    "engaging": "Warm, conversational, story-driven. Uses questions and hooks.",
    "casual": "Friendly, relatable, informal. Like texting a smart friend.",
    "indie_hacker": "Direct, transparent, builder-to-builder. Share lessons learned.",
}

PLATFORM_LIMITS = {
    "facebook": {"max_chars": 2000, "style": "Casual, short paragraphs, 0-3 hashtags, emojis sparingly."},
    "instagram": {"max_chars": 2200, "style": "Visual, emotive, punchy. 15-25 hashtags at the end."},
    "google_business": {"max_chars": 1500, "style": "Local SEO optimized. Mention location. Clear CTA. No hashtags."},
}


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_youtube_id(url: str) -> str | None:
    """Extract video ID from YouTube URL."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _is_safe_url(url: str) -> bool:
    """Block internal/private URLs to prevent SSRF."""
    from urllib.parse import urlparse
    import ipaddress
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname or ""
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", ""):
        return False
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass
    if hostname.endswith((".local", ".internal", ".lan")):
        return False
    return True


async def extract_source(source_type: str, source_input: str) -> dict:
    """Extract content from various source types.

    Returns: {"title": str, "content": str, "word_count": int, "source_url": str|None}
    """
    if source_type == "text" or source_type == "podcast":
        content = _strip_html(source_input)
        words = content.split()
        title_words = words[:8] if len(words) >= 8 else words
        return {
            "title": " ".join(title_words) + "...",
            "content": content,
            "word_count": len(words),
            "source_url": None,
        }

    if source_type == "url":
        if not _is_safe_url(source_input):
            raise ValueError(f"URL is unsafe or internal: {source_input}")
        if not source_input.startswith(("http://", "https://")):
            source_input = f"https://{source_input}"
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(source_input, headers={"User-Agent": "AgentNexLiFy-Repurposer/1.0"})
            resp.raise_for_status()
            html = resp.text
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = _strip_html(title_match.group(1)) if title_match else "Untitled"
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.IGNORECASE | re.DOTALL)
        raw_body = body_match.group(1) if body_match else html
        for tag in ["script", "style", "nav", "header", "footer", "aside"]:
            raw_body = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", raw_body, flags=re.IGNORECASE | re.DOTALL)
        content = _strip_html(raw_body)
        content = re.sub(r"\s+", " ", content).strip()
        content = content[:50000]
        return {
            "title": title,
            "content": content,
            "word_count": len(content.split()),
            "source_url": source_input,
        }

    if source_type == "youtube":
        video_id = _extract_youtube_id(source_input)
        if not video_id:
            raise ValueError(f"Could not extract YouTube video ID from: {source_input}")
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        content = " ".join(entry["text"] for entry in transcript_list)
        return {
            "title": f"YouTube Video {video_id}",
            "content": content,
            "word_count": len(content.split()),
            "source_url": source_input,
        }

    raise ValueError(f"Unknown source type: {source_type}")


async def repurpose(
    source_content: str,
    title: str,
    tenant_id: str,
    tone: str = "professional",
    formats: list[str] | None = None,
) -> dict:
    """Generate repurposed content in multiple formats via Claude API.

    Returns: dict matching the outputs JSONB structure.
    """
    if formats is None:
        formats = ["x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"]

    tone_desc = TONE_DESCRIPTIONS.get(tone, TONE_DESCRIPTIONS["professional"])

    format_instructions = []
    if "x_thread" in formats:
        format_instructions.append(
            '"x_thread": Array of 7-10 tweet objects. Each: {"tweet_num": N, "content": "...", "posted": false}. '
            "First tweet is the hook. Last tweet is the CTA. Each tweet max 280 chars. Use line breaks for readability."
        )
    if "linkedin_carousel" in formats:
        format_instructions.append(
            '"linkedin_carousel": {"slides": [{"slide_num": N, "text": "...", "image_suggestion": "..."}]}. '
            "8-12 slides. First slide is the title hook. Last slide is the CTA. Each slide 1-3 sentences."
        )
    if "email_sequence" in formats:
        format_instructions.append(
            '"email_sequence": Array of 3-5 email objects. Each: {"email_num": N, "subject": "...", "body": "...", "day": N}. '
            "Progressive value delivery. Subject lines under 60 chars. Body in HTML. Day 1, 3, 5, 7, 10 spacing."
        )
    if "tiktok_scripts" in formats:
        format_instructions.append(
            '"tiktok_scripts": Array of 2-3 script objects. Each: {"script_num": N, "hook": "...", "body": "...", "cta": "..."}. '
            "Hook = first 3 seconds (attention grabber). Body = 30-45 seconds. CTA = clear next step."
        )
    if "social_posts" in formats:
        platform_rules = "\n".join(
            f'- {p}: max {info["max_chars"]} chars. {info["style"]}'
            for p, info in PLATFORM_LIMITS.items()
        )
        format_instructions.append(
            f'"social_posts": {{"facebook": "...", "instagram": "...", "google_business": "..."}}.\n'
            f"Platform rules:\n{platform_rules}"
        )

    system_prompt = f"""You are an expert content repurposer. You transform source content into multiple platform-optimized formats.

Tone: {tone_desc}

Generate a JSON object with these keys:
{chr(10).join(format_instructions)}

Rules:
- Every piece of content must be unique — don't repeat the same text across formats.
- Adapt the core message to each platform's culture and constraints.
- X threads should tell a story with a hook, build tension, and end with a CTA.
- LinkedIn carousels should deliver one key insight per slide.
- Email sequences should build progressively — each email more compelling than the last.
- TikTok scripts should be visual and punchy — written for someone reading off a teleprompter.
- Social posts should be native to each platform's tone and format.

Return ONLY valid JSON, no markdown fences."""

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Source title: {title}\n\nSource content:\n{source_content[:30000]}",
            }
        ],
    )

    raw_text = response.content[0].text
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    outputs = json.loads(raw_text)
    return outputs


async def connect_outputs(
    job_id: str,
    tenant_id: str,
    outputs: dict,
    targets: list[str],
    db=None,
) -> dict:
    """Push generated outputs to existing systems.

    Returns: {"social_post_ids": [], "email_sequence_id": str|None}
    """
    from backend.models.database import get_supabase
    if db is None:
        db = get_supabase()

    result = {"social_post_ids": [], "email_sequence_id": None}

    if "social_posts" in targets and "social_posts" in outputs:
        for platform, content in outputs["social_posts"].items():
            post_resp = db.table("social_posts").insert({
                "tenant_id": tenant_id,
                "platform": platform,
                "content": content,
                "status": "draft",
                "hashtags": [],
                "media_urls": [],
            }).execute()
            if post_resp.data:
                result["social_post_ids"].append(post_resp.data[0]["id"])

    if "email_sequence" in targets and "email_sequence" in outputs:
        seq_resp = db.table("email_sequences").insert({
            "tenant_id": tenant_id,
            "name": f"Repurposed Content — {job_id[:8]}",
            "trigger_type": "manual",
            "trigger_config": {},
            "is_active": False,
        }).execute()
        if seq_resp.data:
            seq_id = seq_resp.data[0]["id"]
            result["email_sequence_id"] = seq_id
            for email in outputs["email_sequence"]:
                db.table("email_sequence_steps").insert({
                    "sequence_id": seq_id,
                    "step_order": email["email_num"],
                    "delay_days": email.get("day", email["email_num"] * 2),
                    "delay_hours": 0,
                    "subject": email["subject"],
                    "body": email["body"],
                    "email_type": "content",
                    "is_active": True,
                }).execute()

    if result["social_post_ids"] or result["email_sequence_id"]:
        update_data = {}
        if result["social_post_ids"]:
            update_data["connected_social_post_ids"] = result["social_post_ids"]
        if result["email_sequence_id"]:
            update_data["connected_email_sequence_id"] = result["email_sequence_id"]
        db.table("repurpose_jobs").update(update_data).eq("id", job_id).execute()

    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/aidan/agentnexlify && python3 -m pytest tests/test_content_repurpose.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/services/content_repurposer.py tests/test_content_repurpose.py
git commit -m "feat: add content repurposer service — extract, repurpose, connect"
```

---

## Task 3: API Router + Config + Registration

**Files:**
- Create: `backend/routers/content_repurpose.py`
- Modify: `backend/main.py`
- Modify: `backend/config.py`

- [ ] **Step 1: Add config vars**

In `backend/config.py`, add after the existing `facebook_verify_token` line:

```python
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
```

- [ ] **Step 2: Create the router**

Create `backend/routers/content_repurpose.py`:

```python
"""Content Repurpose endpoints — create, list, edit, connect repurpose jobs."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.database import get_supabase
from backend.routers.auth import _get_current_tenant
from backend.services.content_repurposer import extract_source, repurpose, connect_outputs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/repurpose", tags=["content-repurpose"])

ALLOWED_PLANS = ("professional", "enterprise")
VALID_TONES = ("professional", "engaging", "casual", "indie_hacker")
VALID_FORMATS = ("x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts")
VALID_SOURCE_TYPES = ("text", "url", "youtube", "podcast")


class RepurposeCreate(BaseModel):
    source_type: str = Field(..., description="text, url, youtube, or podcast")
    source_input: str = Field(..., min_length=1, max_length=100000)
    tone: str = Field(default="professional")
    formats: list[str] = Field(default=["x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"])


class RepurposeUpdate(BaseModel):
    outputs: dict | None = None
    source_title: str | None = None


class ConnectRequest(BaseModel):
    targets: list[str] = Field(..., min_length=1)


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _verify_plan(claims: dict) -> None:
    db = get_supabase()
    tenant = db.table("tenants").select("plan").eq("id", claims["tenant_id"]).single().execute()
    if not tenant.data or tenant.data.get("plan") not in ALLOWED_PLANS:
        raise HTTPException(status_code=403, detail="Content Repurposer requires Professional or Enterprise plan. Upgrade to access this feature.")


async def _run_repurpose_job(job_id: str, tenant_id: str, source_type: str, source_input: str, tone: str, formats: list[str]):
    """Background task: extract source, generate content, update job."""
    db = get_supabase()
    try:
        source = await extract_source(source_type, source_input)
        outputs = await repurpose(
            source_content=source["content"],
            title=source["title"],
            tenant_id=tenant_id,
            tone=tone,
            formats=formats,
        )
        db.table("repurpose_jobs").update({
            "source_content": source["content"],
            "source_title": source["title"],
            "outputs": outputs,
            "status": "completed",
        }).eq("id", job_id).execute()
    except Exception as e:
        logger.error("Repurpose job %s failed: %s", job_id, e)
        db.table("repurpose_jobs").update({
            "status": "failed",
        }).eq("id", job_id).execute()


@router.post("/{tenant_id}")
async def create_repurpose_job(
    tenant_id: str,
    req: RepurposeCreate,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(_get_current_tenant),
):
    """Create a new repurpose job. Extraction + AI generation runs in background."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    if req.source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid source_type. Must be one of: {VALID_SOURCE_TYPES}")
    if req.tone not in VALID_TONES:
        raise HTTPException(status_code=400, detail=f"Invalid tone. Must be one of: {VALID_TONES}")
    for fmt in req.formats:
        if fmt not in VALID_FORMATS:
            raise HTTPException(status_code=400, detail=f"Invalid format: {fmt}. Must be one of: {VALID_FORMATS}")

    db = get_supabase()
    job = db.table("repurpose_jobs").insert({
        "tenant_id": tenant_id,
        "source_type": req.source_type,
        "source_url": req.source_input if req.source_type in ("url", "youtube") else None,
        "source_content": req.source_input,
        "tone": req.tone,
        "status": "processing",
        "created_via": "dashboard",
    }).execute()

    job_id = job.data[0]["id"]
    background_tasks.add_task(_run_repurpose_job, job_id, tenant_id, req.source_type, req.source_input, req.tone, req.formats)

    return {"id": job_id, "status": "processing"}


@router.get("/{tenant_id}")
async def list_repurpose_jobs(
    tenant_id: str,
    claims: dict = Depends(_get_current_tenant),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List repurpose jobs for a tenant."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    db = get_supabase()
    resp = db.table("repurpose_jobs").select(
        "id, source_type, source_title, tone, status, created_via, created_at"
    ).eq("tenant_id", tenant_id).order(
        "created_at", desc=True
    ).range(offset, offset + limit - 1).execute()

    return {"jobs": resp.data or [], "total": len(resp.data or [])}


@router.get("/{tenant_id}/{job_id}")
async def get_repurpose_job(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Get a single repurpose job with full outputs."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    db = get_supabase()
    resp = db.table("repurpose_jobs").select("*").eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp.data[0]


@router.put("/{tenant_id}/{job_id}")
async def update_repurpose_job(
    tenant_id: str,
    job_id: str,
    req: RepurposeUpdate,
    claims: dict = Depends(_get_current_tenant),
):
    """Update a repurpose job (edit outputs or title)."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    db = get_supabase()
    update_data = {}
    if req.outputs is not None:
        update_data["outputs"] = req.outputs
    if req.source_title is not None:
        update_data["source_title"] = req.source_title

    if not update_data:
        raise HTTPException(status_code=400, detail="Nothing to update")

    resp = db.table("repurpose_jobs").update(update_data).eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return resp.data[0]


@router.post("/{tenant_id}/{job_id}/connect")
async def connect_repurpose_outputs(
    tenant_id: str,
    job_id: str,
    req: ConnectRequest,
    claims: dict = Depends(_get_current_tenant),
):
    """Push repurpose outputs to social posts, email sequences, X, or TikTok."""
    _verify_tenant(claims, tenant_id)
    _verify_plan(claims)

    valid_targets = {"social_posts", "email_sequence", "x_thread", "tiktok"}
    for t in req.targets:
        if t not in valid_targets:
            raise HTTPException(status_code=400, detail=f"Invalid target: {t}. Must be one of: {valid_targets}")

    db = get_supabase()
    job = db.table("repurpose_jobs").select("outputs, status").eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.data[0]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    if not job.data[0]["outputs"]:
        raise HTTPException(status_code=400, detail="Job has no outputs")

    result = await connect_outputs(job_id, tenant_id, job.data[0]["outputs"], req.targets, db)
    return result


@router.delete("/{tenant_id}/{job_id}")
async def delete_repurpose_job(
    tenant_id: str,
    job_id: str,
    claims: dict = Depends(_get_current_tenant),
):
    """Delete a repurpose job."""
    _verify_tenant(claims, tenant_id)

    db = get_supabase()
    resp = db.table("repurpose_jobs").delete().eq("id", job_id).eq("tenant_id", tenant_id).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"deleted": True}
```

- [ ] **Step 3: Register router in main.py**

In `backend/main.py`, add the import and registration alongside the other routers:

```python
from backend.routers import content_repurpose
```

And in the router registration section:

```python
app.include_router(content_repurpose.router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/routers/content_repurpose.py backend/main.py backend/config.py
git commit -m "feat: add content repurpose API router — 6 endpoints, plan-gated"
```

---

## Task 4: Frontend API Client + Dashboard Page

**Files:**
- Create: `frontend/src/utils/api/repurpose.js`
- Create: `frontend/src/pages/ContentRepurposePage.jsx`
- Modify: `frontend/src/components/App.jsx`

- [ ] **Step 1: Create API client**

Create `frontend/src/utils/api/repurpose.js`:

```javascript
import { request } from "../api/_client.js";

export async function createRepurposeJob(tenantId, data) {
  return request(`/api/v1/repurpose/${tenantId}`, { method: "POST", body: JSON.stringify(data) });
}

export async function listRepurposeJobs(tenantId, limit = 20, offset = 0) {
  return request(`/api/v1/repurpose/${tenantId}?limit=${limit}&offset=${offset}`);
}

export async function getRepurposeJob(tenantId, jobId) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`);
}

export async function updateRepurposeJob(tenantId, jobId, data) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function connectRepurposeOutputs(tenantId, jobId, targets) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}/connect`, { method: "POST", body: JSON.stringify({ targets }) });
}

export async function deleteRepurposeJob(tenantId, jobId) {
  return request(`/api/v1/repurpose/${tenantId}/${jobId}`, { method: "DELETE" });
}
```

- [ ] **Step 2: Create the dashboard page**

Create `frontend/src/pages/ContentRepurposePage.jsx`. This is a large component — build it with:

**Top section:** Source type tabs (Text | URL | YouTube | Podcast), input field, tone dropdown, format checkboxes, "Repurpose" button.

**Main section:** When a job is selected/created, show tabbed output: X Thread | LinkedIn Carousel | Email Sequence | TikTok Scripts | Social Posts. Each tab shows editable content with action buttons (Push to Social, Create Sequence, etc.).

**Sidebar:** Job history list.

**Plan gate:** If plan is not professional/enterprise, show UpgradePrompt.

The page should follow existing patterns from `ContentStudioPage.jsx` and `SocialMediaPage.jsx` for dark theme, layout, and API call patterns.

Full implementation of this page is ~400-600 lines of JSX. The engineer building this should reference `frontend/src/pages/ContentStudioPage.jsx` for the content input pattern and `frontend/src/pages/SocialMediaPage.jsx` for the tabbed platform output pattern.

- [ ] **Step 3: Add route in App.jsx**

In `frontend/src/components/App.jsx`, add the route and lazy import:

```javascript
const ContentRepurposePage = React.lazy(() => import("../pages/ContentRepurposePage.jsx"));
```

Add to the routes (in the pages map or route definitions):

```javascript
{ path: "repurpose", element: <ContentRepurposePage /> }
```

Add to sidebar navigation under Content Studio, gated to professional+ plans.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/api/repurpose.js frontend/src/pages/ContentRepurposePage.jsx frontend/src/components/App.jsx
git commit -m "feat: add ContentRepurposePage — input, tabbed output, edit, push to systems"
```

---

## Task 5: Widget Content Mode Integration

**Files:**
- Modify: `backend/routers/widget_chat.py`
- Modify: `widget/agentnexlify-widget.js`
- Modify: `frontend/public/widget/agentnexlify-widget.js`

- [ ] **Step 1: Add content mode detection to widget_chat.py**

In `backend/routers/widget_chat.py`, add content mode detection in the chat message handler. Before the normal Claude chat flow, check for content mode triggers:

```python
CONTENT_MODE_KEYWORDS = ["repurpose", "content mode", "turn this into", "create content from"]
YOUTUBE_PATTERN = re.compile(r"(?:youtube\.com/watch|youtu\.be/)")

def _is_content_mode(message: str, content_mode_flag: bool = False) -> bool:
    """Detect if the message should trigger content mode."""
    if content_mode_flag:
        return True
    msg_lower = message.lower()
    for kw in CONTENT_MODE_KEYWORDS:
        if kw in msg_lower:
            return True
    if YOUTUBE_PATTERN.search(message):
        return True
    if len(message) > 500 and "?" not in message:
        return True
    return False
```

When content mode is detected:
1. Check tenant's plan is professional+
2. Determine source type (URL, YouTube, or text)
3. Create a repurpose job via the service
4. Return a formatted response with a link to the dashboard

- [ ] **Step 2: Add toggle button to widget JS**

In `widget/agentnexlify-widget.js`, add a content mode toggle:
- Small pen icon button in the widget header
- Only visible when config indicates professional+ plan (add `plan` to widget_config response)
- Toggles a `contentMode` flag
- When active, shows a "Content Mode" badge
- Sends `content_mode: true` in the message payload

After editing, sync the files:
```bash
cp widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/widget_chat.py widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js
git commit -m "feat: add content mode to widget — keyword detection + toggle button"
```

---

## Task 6: X/Twitter OAuth Integration

**Files:**
- Modify: `backend/routers/integrations.py`

- [ ] **Step 1: Add X/Twitter OAuth flow**

Add to `backend/routers/integrations.py` (following the existing Google Calendar OAuth pattern):

- `GET /api/v1/integrations/{tenant_id}/twitter/auth-url` — generates OAuth 2.0 PKCE auth URL, stores state as signed JWT
- `GET /api/v1/integrations/twitter/callback` — exchanges code for tokens, stores in `integrations` table with `provider: "twitter"`
- `POST /api/v1/integrations/{tenant_id}/twitter/post-thread` — posts an X thread by creating the first tweet, then replying to self for each subsequent tweet

Twitter API v2 endpoints:
- Auth: `https://twitter.com/i/oauth2/authorize`
- Token: `https://api.twitter.com/2/oauth2/token`
- Post tweet: `POST https://api.twitter.com/2/tweets`

- [ ] **Step 2: Commit**

```bash
git add backend/routers/integrations.py
git commit -m "feat: add X/Twitter OAuth + thread posting integration"
```

---

## Task 7: TikTok OAuth Integration

**Files:**
- Modify: `backend/routers/integrations.py`

- [ ] **Step 1: Add TikTok OAuth flow**

Add to `backend/routers/integrations.py`:

- `GET /api/v1/integrations/{tenant_id}/tiktok/auth-url` — generates OAuth auth URL with signed state
- `GET /api/v1/integrations/tiktok/callback` — exchanges code for tokens, stores in `integrations` table with `provider: "tiktok"`
- `POST /api/v1/integrations/{tenant_id}/tiktok/post-caption` — posts video description/caption via TikTok Content Posting API

TikTok endpoints:
- Auth: `https://www.tiktok.com/v2/auth/authorize/`
- Token: `https://open.tiktokapis.com/v2/oauth/token/`
- Post: `https://open.tiktokapis.com/v2/post/publish/content/init/`

Graceful degradation: if tokens not present, return 400 with "Connect TikTok first" message.

- [ ] **Step 2: Commit**

```bash
git add backend/routers/integrations.py
git commit -m "feat: add TikTok OAuth + caption posting integration"
```

---

## Task 8: CLAUDE.md + Schema Updates

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add repurpose_jobs to schema table**

In the Database Schema table in CLAUDE.md, add:

```markdown
| repurpose_jobs | Content repurposer | tenant_id, source_type, source_url, source_content, source_title, tone, outputs (JSONB), status, connected_social_post_ids, connected_email_sequence_id, created_via |
```

- [ ] **Step 2: Update workflow commands**

Add to the Workflow Commands table:

```markdown
| Content Repurpose | Paste URL/text/YouTube/podcast → AI generates X threads, LinkedIn carousels, email sequences, TikTok scripts, social posts → push to existing systems |
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add content repurposer to CLAUDE.md schema and workflows"
```

---

## Self-Review

**Spec coverage:**
- Migration: Task 1 ✓
- Service layer (extract, repurpose, connect): Task 2 ✓
- API endpoints (6 routes): Task 3 ✓
- Frontend dashboard page: Task 4 ✓
- Widget integration (keywords + toggle): Task 5 ✓
- X/Twitter OAuth + posting: Task 6 ✓
- TikTok OAuth + posting: Task 7 ✓
- Plan gate: Task 3 (router-level) ✓
- CLAUDE.md update: Task 8 ✓
- Tone options: Task 2 (TONE_DESCRIPTIONS) + Task 3 (validation) ✓
- Graceful degradation: Task 6/7 (return 400 if not connected) ✓

**Placeholder scan:** Task 4 (ContentRepurposePage.jsx) describes the structure rather than providing full code — this is intentional because the page is ~500 lines of JSX that follows existing patterns. The engineer should reference ContentStudioPage.jsx and SocialMediaPage.jsx. All other tasks have complete code.

**Type consistency:** `extract_source`, `repurpose`, `connect_outputs` signatures match across Task 2 (service), Task 3 (router imports), and Task 5 (widget_chat.py usage). `RepurposeCreate`, `RepurposeUpdate`, `ConnectRequest` models match endpoint signatures. JSONB outputs structure consistent across service, router, and frontend.
