"""Focused parser-seam tests for AI-generated route outputs."""

import os
os.environ["TESTING"] = "1"

from backend.routers.content import _parse_platform_versions
from backend.routers.marketing_campaigns import _parse_generated_email
from backend.routers.social_media import _parse_generated_campaign_posts


def test_parse_generated_email_extracts_subject_and_body():
    raw = "SUBJECT: Spring Promo\n---\n<h2>Hello</h2><p>Body here</p>"
    subject, body = _parse_generated_email(raw)
    assert subject == "Spring Promo"
    assert body == "<h2>Hello</h2><p>Body here</p>"


def test_parse_generated_email_falls_back_to_raw_body():
    raw = "<p>No subject provided</p>"
    subject, body = _parse_generated_email(raw)
    assert subject == ""
    assert body == raw


def test_parse_platform_versions_parses_delimited_sections():
    raw = (
        "===PLATFORM=== linkedin\nLinkedIn copy\n"
        "===PLATFORM=== facebook\nFacebook copy\n"
        "===PLATFORM=== instagram\nInstagram copy"
    )
    versions = _parse_platform_versions(raw, ["linkedin", "facebook", "instagram"])
    assert versions["linkedin"] == "LinkedIn copy"
    assert versions["facebook"] == "Facebook copy"
    assert versions["instagram"] == "Instagram copy"


def test_parse_platform_versions_positional_fallback():
    raw = (
        "===PLATFORM===\nFirst platform text\n"
        "===PLATFORM===\nSecond platform text\n"
        "===PLATFORM===\nThird platform text"
    )
    versions = _parse_platform_versions(raw, ["linkedin", "facebook", "instagram"])
    assert versions["linkedin"].startswith("First platform text")
    assert versions["facebook"].startswith("Second platform text")
    assert versions["instagram"].startswith("Third platform text")


def test_parse_generated_campaign_posts_extracts_posts():
    raw = (
        "===POST===\n"
        "DAY: 1\n"
        "PLATFORM: facebook\n"
        "CONTENT: First line\nSecond line\n"
        "HASHTAGS: #one, #two\n"
        "===POST===\n"
        "DAY: 3\n"
        "PLATFORM: instagram\n"
        "CONTENT: Another post\n"
        "HASHTAGS: none"
    )
    posts = _parse_generated_campaign_posts(raw, ["facebook", "instagram"])
    assert len(posts) == 2
    assert posts[0]["day"] == 1
    assert posts[0]["platform"] == "facebook"
    assert posts[0]["content"] == "First line\nSecond line"
    assert posts[0]["hashtags"] == ["#one", "#two"]
    assert posts[1]["platform"] == "instagram"
    assert posts[1]["hashtags"] == []
