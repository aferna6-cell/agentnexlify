# Content Repurposer — Design Spec

**Date:** 2026-04-04
**Status:** Approved
**Author:** Aidan + Claude

---

## Overview

A content repurposing engine that takes any source content (URL, text, YouTube link, podcast transcript) and generates 5 output formats: X/Twitter threads, LinkedIn carousels, email newsletter sequences, TikTok/Reels scripts, and social post variations. Two equal entry points: dashboard page and chat widget (Mode 2). Outputs connect to existing email sequence and social posting systems, plus new X/Twitter and TikTok integrations.

**Plan gate:** Professional ($499) and Enterprise ($899) only.

---

## Architecture

```
Source Input (URL/text/YouTube/podcast)
        ↓
Content Repurposer Service (backend/services/content_repurposer.py)
  ├── extract_source() — URL fetch, YouTube transcript, raw text
  ├── repurpose() — Claude API generates all 5 formats in one call
  └── connect_outputs() — push to email_sequences + social_posts + X + TikTok
        ↓
Two entry points:
  1. Dashboard API (backend/routers/content_repurpose.py)
  2. Widget chat (keyword detection in widget_chat.py)
        ↓
Storage: repurpose_jobs table (new)
        ↓
Outputs connect to:
  - social_posts table (existing) → scheduling/publishing
  - email_sequence_steps table (existing) → drip campaigns
  - X/Twitter API v2 (new) → thread posting
  - TikTok Content Posting API (new) → caption posting
```

---

## Database Schema

### Table: `repurpose_jobs`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | uuid | PK, default gen_random_uuid() | |
| tenant_id | uuid | FK→tenants, not null | |
| source_type | text | not null | `url`, `text`, `youtube`, `podcast` |
| source_url | text | | Original URL (null for raw text) |
| source_content | text | not null | Extracted/pasted source text |
| source_title | text | | Auto-extracted or user-provided |
| tone | text | default 'professional' | `professional`, `engaging`, `casual`, `indie_hacker` |
| outputs | JSONB | | All generated formats |
| status | text | default 'processing' | `processing`, `completed`, `failed` |
| connected_social_post_ids | uuid[] | default '{}' | Social posts created from this job |
| connected_email_sequence_id | uuid | | Email sequence created from this job |
| created_via | text | default 'dashboard' | `dashboard` or `widget` |
| created_at | timestamptz | default now() | |

Index on `tenant_id`.

### `outputs` JSONB structure

```json
{
  "x_thread": [
    {"tweet_num": 1, "content": "Hook tweet...", "posted": false},
    {"tweet_num": 2, "content": "Follow-up...", "posted": false}
  ],
  "linkedin_carousel": {
    "slides": [
      {"slide_num": 1, "text": "Title slide...", "image_suggestion": "..."},
      {"slide_num": 2, "text": "Key point...", "image_suggestion": "..."}
    ]
  },
  "email_sequence": [
    {"email_num": 1, "subject": "...", "body": "...", "day": 1},
    {"email_num": 2, "subject": "...", "body": "...", "day": 3}
  ],
  "tiktok_scripts": [
    {"script_num": 1, "hook": "First 3 seconds...", "body": "Main content...", "cta": "Follow for more..."}
  ],
  "social_posts": {
    "facebook": "...",
    "instagram": "...",
    "google_business": "..."
  }
}
```

Migration: next available number in `migrations/`.

---

## Service Layer

### `backend/services/content_repurposer.py`

#### `extract_source(source_type: str, source_input: str) -> dict`

| Source Type | Method |
|-------------|--------|
| `text` | Pass through, strip HTML tags |
| `url` | httpx fetch + HTML extraction (reuse pattern from `website_crawler.py`) |
| `youtube` | `youtube-transcript-api` package — extract transcript from video ID |
| `podcast` | Pass through (user pastes transcript) |

Returns: `{"title": str, "content": str, "word_count": int, "source_url": str|None}`

#### `repurpose(source_content: str, title: str, tenant_id: str, tone: str, formats: list[str]) -> dict`

Single Claude API call (`claude-sonnet-4-6`) generating all requested formats. Structured JSON output. System prompt includes platform-specific constraints from existing `PLATFORM_LIMITS` in `social_media.py`.

Tone options: `professional`, `engaging`, `casual`, `indie_hacker`.

Returns: the `outputs` JSONB structure.

#### `connect_outputs(job_id: str, tenant_id: str, outputs: dict, targets: list[str]) -> dict`

| Target | Action |
|--------|--------|
| `social_posts` | Insert into `social_posts` table with `status: "draft"` for each platform |
| `email_sequence` | Create `email_sequence` + `email_sequence_steps` with `is_active: false` |
| `x_thread` | Post via Twitter API v2 — create first tweet, reply-to-self for rest |
| `tiktok` | Post caption via TikTok Content Posting API |

Returns: `{"social_post_ids": [], "email_sequence_id": str, "x_thread_url": str, "tiktok_post_id": str}`

---

## API Endpoints

### `backend/routers/content_repurpose.py`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/repurpose/{tenant_id}` | Create repurpose job |
| GET | `/api/v1/repurpose/{tenant_id}` | List jobs (paginated) |
| GET | `/api/v1/repurpose/{tenant_id}/{job_id}` | Get job with outputs |
| PUT | `/api/v1/repurpose/{tenant_id}/{job_id}` | Edit outputs |
| POST | `/api/v1/repurpose/{tenant_id}/{job_id}/connect` | Push to social/email/X/TikTok |
| DELETE | `/api/v1/repurpose/{tenant_id}/{job_id}` | Delete job |

**Plan gate:** All endpoints verify `plan in ("professional", "enterprise")`. Returns 403 for lower plans.

**Create request:**
```json
{
  "source_type": "url",
  "source_input": "https://blog.example.com/article",
  "tone": "professional",
  "formats": ["x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"]
}
```

**Connect request:**
```json
{
  "targets": ["social_posts", "email_sequence"]
}
```

---

## Widget Integration

### Auto-detection (in `widget_chat.py`)

Detect content mode triggers in incoming messages:
- Keywords: `"repurpose"`, `"content mode"`, `"turn this into"`, `"create content from"`
- Long paste: text >500 chars that doesn't contain a question mark
- URL patterns: YouTube links, blog URLs pasted alone

When triggered, call `content_repurposer.extract_source()` + `repurpose()` instead of normal chat flow.

### Toggle button (in `agentnexlify-widget.js`)

- Small pen/content icon in widget header, next to existing controls
- Only visible when `widget_config.plan` is Professional+
- Toggles `content_mode` on/off
- Visual indicator when active (highlighted, "Content Mode" badge)

### Chat flow in content mode

1. AI responds: "Got it — I'll repurpose this for you. Generating X thread, LinkedIn carousel, email sequence, TikTok scripts, and social posts..."
2. Creates the repurpose job via the service
3. Returns summary of what was generated + "View full results in dashboard →" link
4. Does NOT display all 5 formats inline — links to dashboard for editing

---

## Frontend Dashboard

### `frontend/src/pages/ContentRepurposePage.jsx`

**Top section — Input:**
- Source type selector: Text | URL | YouTube | Podcast
- Input area: textarea or URL field depending on type
- Tone selector dropdown: Professional | Engaging | Casual | Indie Hacker
- Format checkboxes: all 5 checked by default
- "Repurpose" button → creates job, loading state

**Main section — Tabbed output:**
- Tabs: X Thread | LinkedIn Carousel | Email Sequence | TikTok Scripts | Social Posts
- Each tab: generated content with inline edit capability
- Action buttons per tab:
  - Social tabs → "Push to Social (Draft)"
  - Email tab → "Create Email Sequence (Draft)"
  - X tab → "Post Thread" (or "Connect X Account" if not connected)
  - TikTok tab → "Post to TikTok" (or "Connect TikTok" if not connected)

**Sidebar — History:**
- List of past repurpose jobs: title, date, source type, status
- Click to reload

**Plan gate:** Free/Growth users see the page with `UpgradePrompt` component.

**Sidebar nav:** "Content Repurpose" under Content Studio section. Professional+ only.

---

## X/Twitter Integration

- OAuth 2.0 with PKCE (Twitter API v2)
- Tokens in `integrations` table (`provider: "twitter"`)
- Thread posting: POST first tweet, then POST replies to each previous tweet_id
- "Connect X Account" in IntegrationsPage (same pattern as Google Calendar)
- Env vars: `TWITTER_CLIENT_ID`, `TWITTER_CLIENT_SECRET`

## TikTok Integration

- OAuth 2.0 (TikTok Content Posting API)
- Tokens in `integrations` table (`provider: "tiktok"`)
- Posts caption/description — user uploads video separately
- "Connect TikTok" in IntegrationsPage
- Env vars: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`

### Graceful degradation

If X or TikTok isn't connected, "Post" buttons show "Connect [Platform]" instead. Content still generated and available for copy-paste.

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `TWITTER_CLIENT_ID` | X/Twitter OAuth app ID |
| `TWITTER_CLIENT_SECRET` | X/Twitter OAuth secret |
| `TIKTOK_CLIENT_KEY` | TikTok OAuth app key |
| `TIKTOK_CLIENT_SECRET` | TikTok OAuth app secret |

---

## New Dependencies

- `youtube-transcript-api` — extract YouTube video transcripts (no API key needed)

---

## Out of Scope

- Video upload to TikTok (we provide the script, user records the video)
- Instagram Reels posting (requires Meta Business API approval)
- Automated scheduling of repurposed content (user manually schedules from dashboard)
- AI image generation for LinkedIn carousel slides (we suggest images, user provides them)
