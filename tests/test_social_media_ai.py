"""Unit tests for backend.services.social_media_ai.

Covers platform/status validators (HTTPException codes + messages),
prompt builders (input → expected substrings), and response parsers
(hashtag extraction, malformed input, edge cases).
"""

import pytest
from fastapi import HTTPException

from backend.services.social_media_ai import (
    PLATFORM_LIMITS,
    VALID_PLATFORMS,
    VALID_STATUSES,
    build_campaign_system_prompt,
    build_post_system_prompt,
    parse_generated_campaign_posts,
    parse_post_response,
    validate_platform,
    validate_status,
)


class TestValidators:
    def test_validate_platform_accepts_known(self):
        for p in VALID_PLATFORMS:
            validate_platform(p)

    def test_validate_platform_rejects_unknown(self):
        with pytest.raises(HTTPException) as exc:
            validate_platform("myspace")
        assert exc.value.status_code == 400
        assert "myspace" in exc.value.detail
        assert "facebook" in exc.value.detail

    def test_validate_status_accepts_known(self):
        for s in VALID_STATUSES:
            validate_status(s)

    def test_validate_status_rejects_unknown(self):
        with pytest.raises(HTTPException) as exc:
            validate_status("archived")
        assert exc.value.status_code == 400
        assert "archived" in exc.value.detail

    def test_all_platforms_have_limits(self):
        for p in VALID_PLATFORMS:
            assert p in PLATFORM_LIMITS
            assert "max_chars" in PLATFORM_LIMITS[p]


class TestBuildPostSystemPrompt:
    def test_includes_business_name_and_type(self):
        prompt = build_post_system_prompt("Acme", "plumber", "facebook", None, True)
        assert "Acme" in prompt
        assert "plumber" in prompt
        assert "facebook" in prompt

    def test_no_business_name_skips_context(self):
        prompt = build_post_system_prompt(None, None, "twitter", None, False)
        assert "Acme" not in prompt
        assert "twitter" in prompt

    def test_custom_tone_overrides_default(self):
        prompt = build_post_system_prompt("Biz", None, "instagram", "Hype-marketing energy", True)
        assert "Hype-marketing energy" in prompt

    def test_no_hashtags_instruction(self):
        prompt = build_post_system_prompt("Biz", None, "facebook", None, False)
        assert "Do NOT include any hashtags" in prompt

    def test_with_hashtags_uses_platform_style(self):
        prompt = build_post_system_prompt("Biz", None, "instagram", None, True)
        assert "15-25 relevant hashtags" in prompt

    def test_max_chars_included(self):
        prompt = build_post_system_prompt("Biz", None, "twitter", None, True)
        assert "280" in prompt


class TestParsePostResponse:
    def test_no_hashtag_block(self):
        result = parse_post_response("Just a simple post body.", "facebook")
        assert result["content"] == "Just a simple post body."
        assert result["hashtags"] == []
        assert result["character_count"] == len("Just a simple post body.")
        assert result["platform"] == "facebook"

    def test_with_hashtag_block(self):
        raw = "Loving the new menu!\nHASHTAGS:\n#food #yum #local"
        result = parse_post_response(raw, "instagram")
        assert result["content"] == "Loving the new menu!"
        assert result["hashtags"] == ["#food", "#yum", "#local"]

    def test_hashtags_comma_separated_normalized(self):
        raw = "Body\nHASHTAGS: food, yum, local"
        result = parse_post_response(raw, "instagram")
        assert result["hashtags"] == ["#food", "#yum", "#local"]

    def test_hashtags_mixed_with_and_without_hash(self):
        raw = "Body\nHASHTAGS: #food yum #local"
        result = parse_post_response(raw, "instagram")
        assert result["hashtags"] == ["#food", "#yum", "#local"]

    def test_empty_hashtag_block(self):
        result = parse_post_response("Body\nHASHTAGS:", "facebook")
        assert result["content"] == "Body"
        assert result["hashtags"] == []

    def test_character_count_uses_content_not_raw(self):
        raw = "Hello\nHASHTAGS: #one"
        result = parse_post_response(raw, "twitter")
        assert result["character_count"] == len("Hello")


class TestBuildCampaignSystemPrompt:
    def test_includes_all_platforms(self):
        prompt = build_campaign_system_prompt(
            "Acme", "salon", ["facebook", "instagram"], 5
        )
        assert "facebook" in prompt
        assert "instagram" in prompt
        assert "Acme" in prompt
        assert "salon" in prompt
        assert "5 posts" in prompt

    def test_no_business_context(self):
        prompt = build_campaign_system_prompt(None, None, ["twitter"], 3)
        assert "twitter" in prompt
        assert "===POST===" in prompt

    def test_post_format_template_present(self):
        prompt = build_campaign_system_prompt("Biz", None, ["facebook"], 1)
        assert "DAY:" in prompt
        assert "PLATFORM:" in prompt
        assert "CONTENT:" in prompt
        assert "HASHTAGS:" in prompt


class TestParseGeneratedCampaignPosts:
    def test_empty_string(self):
        assert parse_generated_campaign_posts("", ["facebook"]) == []

    def test_whitespace_only_sections_skipped(self):
        assert parse_generated_campaign_posts("===POST===\n\n===POST===\n   ", ["facebook"]) == []

    def test_single_post_full_fields(self):
        raw = (
            "===POST===\n"
            "DAY: 2\n"
            "PLATFORM: instagram\n"
            "CONTENT: Sunny days ahead\n"
            "HASHTAGS: summer, vibes"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert len(posts) == 1
        assert posts[0]["day"] == 2
        assert posts[0]["platform"] == "instagram"
        assert posts[0]["content"] == "Sunny days ahead"
        assert posts[0]["hashtags"] == ["#summer", "#vibes"]

    def test_multiline_content_after_content_marker(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: facebook\n"
            "CONTENT: First line\n"
            "Second line\n"
            "HASHTAGS: none"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert posts[0]["content"] == "First line\nSecond line"
        assert posts[0]["hashtags"] == []

    def test_unknown_platform_falls_back_to_default(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: myspace\n"
            "CONTENT: Hello"
        )
        posts = parse_generated_campaign_posts(raw, ["linkedin"])
        assert posts[0]["platform"] == "linkedin"

    def test_invalid_day_left_at_default(self):
        raw = (
            "===POST===\n"
            "DAY: abc\n"
            "PLATFORM: facebook\n"
            "CONTENT: hi"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert posts[0]["day"] == 1

    def test_hashtags_with_existing_hash_preserved(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: instagram\n"
            "CONTENT: x\n"
            "HASHTAGS: #already, plain"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert posts[0]["hashtags"] == ["#already", "#plain"]

    def test_empty_content_post_dropped(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: facebook\n"
            "HASHTAGS: none"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert posts == []

    def test_multiple_posts(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: facebook\n"
            "CONTENT: first\n"
            "===POST===\n"
            "DAY: 3\n"
            "PLATFORM: twitter\n"
            "CONTENT: second"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert len(posts) == 2
        assert posts[0]["day"] == 1
        assert posts[1]["day"] == 3
        assert posts[1]["platform"] == "twitter"

    def test_platform_with_spaces_normalized(self):
        raw = (
            "===POST===\n"
            "DAY: 1\n"
            "PLATFORM: google business\n"
            "CONTENT: hi"
        )
        posts = parse_generated_campaign_posts(raw, ["facebook"])
        assert posts[0]["platform"] == "google_business"
