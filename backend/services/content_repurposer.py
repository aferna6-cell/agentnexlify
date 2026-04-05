"""Content Repurposer Service.

Extracts content from various sources (text, URL, YouTube, podcast transcript),
repurposes it into multiple platform-specific formats via Claude, and optionally
connects the outputs to existing social_posts and email_sequences tables.
"""

import ipaddress
import json
import logging
import re
from urllib.parse import urlparse

import httpx
from youtube_transcript_api import YouTubeTranscriptApi

from backend.models.database import get_supabase
from backend.services.llm_runtime import call_claude_messages_sync

logger = logging.getLogger(__name__)


def _strip_json_fences(raw_text: str) -> str:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _repair_truncated_json(raw_text: str) -> str:
    open_braces = raw_text.count("{") - raw_text.count("}")
    open_brackets = raw_text.count("[") - raw_text.count("]")

    # First try the least-destructive repair: only close still-open structures.
    direct_repair = raw_text + "]" * max(0, open_brackets) + "}" * max(0, open_braces)
    try:
        json.loads(direct_repair)
        return direct_repair
    except json.JSONDecodeError:
        pass

    # Fallback: truncate to the last likely-complete boundary, then close structures.
    repaired = raw_text
    last_complete = max(repaired.rfind("},"), repaired.rfind("],"), repaired.rfind('",'))
    if last_complete > 0:
        repaired = repaired[:last_complete + 1]
    repaired += "]" * max(0, open_brackets) + "}" * max(0, open_braces)
    return repaired


def _parse_repurpose_json(raw_text: str) -> dict:
    cleaned = _strip_json_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = _repair_truncated_json(cleaned)
        parsed = json.loads(repaired)
        logger.warning("Repaired truncated JSON response during repurpose parsing")
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected dict response, got {type(parsed).__name__}")
    return parsed

# --- Tone definitions ---
TONE_MAP = {
    "professional": "Write in a polished, authoritative, business-appropriate tone. No slang.",
    "engaging": "Write in an upbeat, energetic tone that hooks the reader. Use questions and storytelling.",
    "casual": "Write in a friendly, relaxed, conversational tone. Short sentences, contractions, light humor.",
    "indie_hacker": "Write like a scrappy founder sharing real lessons. Transparent, no-BS, personal anecdotes.",
}

# --- Platform constraints (copied from social_media router) ---
PLATFORM_LIMITS = {
    "facebook": {
        "max_chars": 2000,
        "hashtag_style": "Minimal or no hashtags. 0-3 at most.",
        "tone": "Casual and conversational. Short paragraphs. Emojis sparingly.",
    },
    "instagram": {
        "max_chars": 2200,
        "hashtag_style": "Include 15-25 relevant hashtags on a separate line at the end.",
        "tone": "Visual, emotive, punchy. Use emojis naturally.",
    },
    "twitter": {
        "max_chars": 280,
        "hashtag_style": "1-3 hashtags woven into the text naturally.",
        "tone": "Concise, witty, direct. Every word counts.",
    },
    "linkedin": {
        "max_chars": 3000,
        "hashtag_style": "3-5 professional hashtags at the end.",
        "tone": "Professional, thought-leadership, value-driven. Use line breaks for readability.",
    },
    "google_business": {
        "max_chars": 1500,
        "hashtag_style": "No hashtags.",
        "tone": "Local SEO optimized. Mention location/service area. Clear call to action.",
    },
}

ALL_FORMATS = {"x_thread", "linkedin_carousel", "email_sequence", "tiktok_scripts", "social_posts"}


def _is_safe_url(url: str) -> bool:
    """Block internal/private URLs to prevent SSRF."""
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
        pass  # hostname is a domain name, not an IP — that's fine
    if hostname.endswith((".local", ".internal", ".lan")):
        return False
    return True


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    # Remove script, style, nav, header, footer blocks entirely
    for tag in ("script", "style", "nav", "header", "footer", "noscript"):
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_title(html: str) -> str:
    """Extract <title> content from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_youtube_id(source_input: str) -> str | None:
    """Extract YouTube video ID from a URL or bare ID string."""
    # Try URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, source_input)
        if match:
            return match.group(1)
    # Bare 11-character ID
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", source_input.strip()):
        return source_input.strip()
    return None


async def extract_source(source_type: str, source_input: str) -> dict:
    """Extract content from the given source.

    Returns: {"title": str, "content": str, "word_count": int, "source_url": str | None}
    """
    if source_type in ("text", "podcast"):
        content = _strip_html(source_input)
        return {
            "title": "",
            "content": content,
            "word_count": len(content.split()),
            "source_url": None,
        }

    if source_type == "url":
        if not source_input.startswith(("http://", "https://")):
            source_input = f"https://{source_input}"
        if not _is_safe_url(source_input):
            raise ValueError("Invalid or unsafe URL. Please provide a public website URL.")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(source_input, headers={"User-Agent": "AgentNexLiFy/1.0"})
            resp.raise_for_status()
            html = resp.text
        title = _extract_title(html)
        content = _strip_html(html)
        # Cap at 50K characters
        if len(content) > 50_000:
            content = content[:50_000]
        return {
            "title": title,
            "content": content,
            "word_count": len(content.split()),
            "source_url": source_input,
        }

    if source_type == "youtube":
        video_id = _extract_youtube_id(source_input)
        if not video_id:
            raise ValueError("Could not extract a valid YouTube video ID from the input.")
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        content = " ".join(snippet.text for snippet in transcript)
        return {
            "title": "",
            "content": content,
            "word_count": len(content.split()),
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
        }

    raise ValueError(f"Unsupported source_type: {source_type}")


async def repurpose(
    source_content: str,
    title: str,
    tenant_id: str,
    tone: str = "professional",
    formats: list[str] | None = None,
) -> dict:
    """Repurpose source content into multiple platform-specific formats via a single Claude call.

    Returns a dict keyed by format name, each containing the generated content.
    """
    requested_formats = set(formats) if formats else ALL_FORMATS
    tone_desc = TONE_MAP.get(tone, TONE_MAP["professional"])

    # Build format-specific instructions
    format_instructions = []
    if "x_thread" in requested_formats:
        format_instructions.append(
            '"x_thread": An array of 7-10 tweets. First tweet is the hook. Last tweet is a CTA. '
            "Each tweet MUST be 280 characters or fewer. Include relevant hashtags in 1-2 tweets."
        )
    if "linkedin_carousel" in requested_formats:
        format_instructions.append(
            '"linkedin_carousel": An object with "slides" (array of 8-12 objects, each with '
            '"headline", "body", and "image_suggestion" fields). First slide is the title/hook. '
            "Last slide is a CTA."
        )
    if "email_sequence" in requested_formats:
        format_instructions.append(
            '"email_sequence": An array of 3-5 email objects, each with "subject", "body", and '
            '"send_day" (use days 1, 3, 5, 7, 10). Emails should tell a narrative arc from the source.'
        )
    if "tiktok_scripts" in requested_formats:
        format_instructions.append(
            '"tiktok_scripts": An array of 2-3 script objects, each with "hook" (first 3 seconds), '
            '"body" (main content), and "cta" (closing call to action). Keep scripts under 60 seconds of speech.'
        )
    if "social_posts" in requested_formats:
        platform_rules = "\n".join(
            f'  - "{p}": max {info["max_chars"]} chars, {info["tone"]} {info["hashtag_style"]}'
            for p, info in PLATFORM_LIMITS.items()
        )
        format_instructions.append(
            '"social_posts": An object with keys "facebook", "instagram", "google_business", each '
            "containing the post text for that platform. Follow these platform rules:\n" + platform_rules
        )

    system_prompt = (
        "You are a content repurposing expert. Given source content, create platform-specific "
        "versions optimized for engagement on each platform.\n\n"
        f"TONE: {tone_desc}\n\n"
        "Return ONLY valid JSON with these keys (no markdown, no explanation):\n"
        + "\n".join(f"- {inst}" for inst in format_instructions)
    )

    user_prompt = f"Source title: {title}\n\nSource content:\n{source_content[:30_000]}"

    result = call_claude_messages_sync(
        operation="content.repurpose",
        model="claude-sonnet-4-6",
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=60.0,
        max_retries=1,
        retry_delay_seconds=1.0,
        metadata={
            "tenant_id": tenant_id,
            "tone": tone,
            "formats": sorted(requested_formats),
            "source_chars": min(len(source_content), 30000),
        },
    )

    # Parse the response
    raw_text = result.text
    try:
        result = _parse_repurpose_json(raw_text)
    except (json.JSONDecodeError, ValueError):
        logger.error("Failed to parse or repair Claude repurpose response: %s", raw_text[:500])
        raise ValueError("AI returned invalid JSON. Please try again.")

    # Only return requested formats
    return {k: v for k, v in result.items() if k in requested_formats}


async def connect_outputs(
    job_id: str,
    tenant_id: str,
    outputs: dict,
    targets: list[str],
    db=None,
) -> dict:
    """Connect repurposed outputs to existing platform tables.

    - 'social_posts' target: inserts into social_posts table as drafts
    - 'email_sequence' target: creates email_sequences + email_sequence_steps rows

    Returns: {"social_post_ids": [...], "email_sequence_id": str | None}
    """
    if db is None:
        db = get_supabase()

    result = {"social_post_ids": [], "email_sequence_id": None}

    # --- Social posts ---
    if "social_posts" in targets and "social_posts" in outputs:
        posts_data = outputs["social_posts"]
        for platform, content in posts_data.items():
            if not isinstance(content, str):
                continue
            row = {
                "tenant_id": tenant_id,
                "platform": platform,
                "content": content,
                "status": "draft",
                "hashtags": [],
                "media_urls": [],
            }
            insert_resp = db.table("social_posts").insert(row).execute()
            if insert_resp.data:
                result["social_post_ids"].append(insert_resp.data[0]["id"])

    # --- Email sequence ---
    if "email_sequence" in targets and "email_sequence" in outputs:
        emails = outputs["email_sequence"]
        if isinstance(emails, list) and len(emails) > 0:
            seq_resp = db.table("email_sequences").insert({
                "tenant_id": tenant_id,
                "name": f"Repurposed content — Job {job_id[:8]}",
                "trigger_type": "manual",
                "trigger_config": {},
                "is_active": False,
            }).execute()

            if seq_resp.data:
                seq_id = seq_resp.data[0]["id"]
                result["email_sequence_id"] = seq_id

                for i, email in enumerate(emails):
                    step_row = {
                        "sequence_id": seq_id,
                        "step_order": i + 1,
                        "delay_days": email.get("send_day", (i + 1) * 2),
                        "delay_hours": 0,
                        "subject": email.get("subject", f"Email {i + 1}"),
                        "body": email.get("body", ""),
                        "email_type": "content",
                        "is_active": True,
                    }
                    db.table("email_sequence_steps").insert(step_row).execute()

    # --- Update the repurpose job with connected IDs ---
    try:
        db.table("repurpose_jobs").update({
            "connected_ids": result,
        }).eq("id", job_id).execute()
    except Exception:
        logger.warning("Could not update repurpose_jobs with connected IDs for job %s", job_id)

    return result
