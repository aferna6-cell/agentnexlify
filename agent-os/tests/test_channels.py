"""Channel formatting (rule 3) — plain-text channels reject markdown."""

from __future__ import annotations

import pytest

from agent_os.channels import (
    channel_allows_markdown,
    find_markdown,
    validate_channel_format,
)
from agent_os.schema import MARKDOWN_CHANNELS, Channel


@pytest.mark.parametrize(
    "snippet",
    [
        "Spring **sale** today",
        "# Big heading",
        "Visit `code` now",
        "See [our site](https://x.com)",
        "> a blockquote",
    ],
)
def test_find_markdown_flags_tokens(snippet: str):
    assert find_markdown(snippet)


@pytest.mark.parametrize(
    "snippet",
    [
        "Plain text, no markup.",
        "Call 512-555-0100 — open Mon-Fri.",
        "Invoice #1042 is due.",
        "Cost is $1,100 for the brake job.",
    ],
)
def test_clean_text_has_no_markdown(snippet: str):
    assert find_markdown(snippet) == []


@pytest.mark.parametrize("channel", list(Channel))
def test_channel_allows_markdown_matches_set(channel: Channel):
    assert channel_allows_markdown(channel) == (channel in MARKDOWN_CHANNELS)


def test_plain_channel_rejects_markdown():
    findings = validate_channel_format(Channel.sms, "Get **20% off** now")
    assert findings


def test_markdown_channel_allows_markdown():
    assert validate_channel_format(Channel.email, "Get **20% off** now") == []
    assert validate_channel_format(Channel.report, "# Weekly brief") == []


def test_customer_facing_set_excludes_internal_report():
    # report + internal are owner-facing, never customer-facing.
    assert Channel.report not in {
        Channel.sms,
        Channel.email,
        Channel.post,
        Channel.widget_reply,
    }
