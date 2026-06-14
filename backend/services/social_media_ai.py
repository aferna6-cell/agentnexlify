"""Social media AI helpers — platform constants, validators, prompt builders, response parsers.

Extracted from backend/routers/social_media.py to keep the router under the
god-class threshold. The router still owns the actual LLM call so existing
tests can patch backend.routers.social_media.call_claude_messages.
"""

from fastapi import HTTPException

VALID_PLATFORMS: set[str] = {"facebook", "instagram", "twitter", "linkedin", "google_business"}
VALID_STATUSES: set[str] = {"draft", "scheduled", "published", "failed"}

# Platform-specific constraints for AI generation
PLATFORM_LIMITS: dict[str, dict[str, str | int]] = {
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


def validate_platform(platform: str) -> None:
    if platform not in VALID_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}",
        )


def validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )


def build_post_system_prompt(
    business_name: str | None,
    business_type: str | None,
    platform: str,
    tone: str | None,
    include_hashtags: bool,
) -> str:
    """Compose the system prompt for single-post generation."""
    platform_info = PLATFORM_LIMITS[platform]
    biz_context = f" for {business_name}" + (f", a {business_type}" if business_type else "")
    tone_instruction = (
        f"\nTone: {tone}." if tone else f"\nTone: {platform_info['tone']}"
    )
    hashtag_instruction = (
        f"\nHashtags: {platform_info['hashtag_style']}"
        if include_hashtags
        else "\nDo NOT include any hashtags."
    )
    return (
        f"You are a social media marketing expert creating content{biz_context}. "
        f"Generate a {platform} post about the given topic. "
        f"Keep it under {platform_info['max_chars']} characters."
        f"{tone_instruction}"
        f"{hashtag_instruction}\n\n"
        "Return ONLY the post content. If hashtags are included, put them on a separate "
        "line at the end prefixed with 'HASHTAGS:' on its own line, then the hashtags."
    )


def parse_post_response(raw: str, platform: str) -> dict:
    """Split AI response into content + hashtags."""
    content = raw
    hashtags: list[str] = []
    if "HASHTAGS:" in raw:
        parts = raw.split("HASHTAGS:", 1)
        content = parts[0].strip()
        hashtag_text = parts[1].strip()
        hashtags = [h.strip().lstrip("#") for h in hashtag_text.replace(",", " ").split() if h.strip()]
        hashtags = [f"#{h}" for h in hashtags if h]
    return {
        "content": content,
        "hashtags": hashtags,
        "character_count": len(content),
        "platform": platform,
    }


def build_campaign_system_prompt(
    business_name: str | None,
    business_type: str | None,
    platforms: list[str],
    posts_per_week: int,
) -> str:
    """Compose the system prompt for a multi-platform campaign."""
    biz_context = f" for {business_name}" + (f", a {business_type}" if business_type else "")
    platforms_desc = "\n".join(
        f"- {p}: max {PLATFORM_LIMITS[p]['max_chars']} chars, "
        f"{PLATFORM_LIMITS[p]['tone']} {PLATFORM_LIMITS[p]['hashtag_style']}"
        for p in platforms
    )
    return (
        f"You are a social media content strategist{biz_context}. "
        f"Create a week-long content calendar with {posts_per_week} posts about the given topic. "
        "Distribute posts across the specified platforms.\n\n"
        f"Platforms and guidelines:\n{platforms_desc}\n\n"
        "For each post, output in this exact format:\n"
        "===POST===\n"
        "DAY: [1-7]\n"
        "PLATFORM: [platform_name]\n"
        "CONTENT: [the post content]\n"
        "HASHTAGS: [comma-separated hashtags or 'none']\n\n"
        "Generate exactly the requested number of posts. Vary the days and platforms. "
        "Each post should have a unique angle on the topic."
    )


def parse_generated_campaign_posts(raw: str, default_platforms: list[str]) -> list[dict]:
    """Parse AI campaign output separated by ===POST=== markers."""
    posts: list[dict] = []
    sections = raw.split("===POST===")
    for section in sections:
        section = section.strip()
        if not section:
            continue

        post: dict = {"day": 1, "platform": default_platforms[0], "content": "", "hashtags": []}
        lines = section.split("\n")
        content_lines: list[str] = []
        in_content = False

        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith("DAY:"):
                try:
                    post["day"] = int(stripped.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
                in_content = False
            elif stripped.upper().startswith("PLATFORM:"):
                plat = stripped.split(":", 1)[1].strip().lower().replace(" ", "_")
                if plat in VALID_PLATFORMS:
                    post["platform"] = plat
                in_content = False
            elif stripped.upper().startswith("CONTENT:"):
                content_start = stripped.split(":", 1)[1].strip()
                if content_start:
                    content_lines.append(content_start)
                in_content = True
            elif stripped.upper().startswith("HASHTAGS:"):
                hashtag_text = stripped.split(":", 1)[1].strip()
                if hashtag_text.lower() != "none":
                    post["hashtags"] = [
                        h.strip() if h.strip().startswith("#") else f"#{h.strip()}"
                        for h in hashtag_text.split(",")
                        if h.strip()
                    ]
                in_content = False
            elif in_content:
                content_lines.append(line)

        post["content"] = "\n".join(content_lines).strip()
        if post["content"]:
            posts.append(post)

    return posts
