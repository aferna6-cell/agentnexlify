"""Channel formatting rules (rule 3).

SMS-channel agents must produce plain text — no markdown, no asterisks, no
headers. Email/report/sequence/internal channels may use markdown that converts
at send time. This module is the single source of truth for what "plain text"
means and is used by both the registry's output validator and the agents
themselves when they build drafts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_os.schema import MARKDOWN_CHANNELS, Channel

# Markdown tokens that must never appear in a plain-text channel. We keep this
# conservative to avoid false positives on legitimate prose:
#   - "#1042" (invoice number) is fine; an ATX header "# Heading" is not.
#   - a hyphen "-" is fine; an asterisk bullet "*" is not.
_MARKDOWN_PATTERNS: tuple[tuple[str, str], ...] = (
    ("bold/italic asterisk", r"\*"),
    ("bold/italic underscore", r"(?<!\w)__[^_]+__(?!\w)"),
    ("atx header", r"(?m)^\s{0,3}#{1,6}\s"),
    ("code fence/inline code", r"`"),
    ("markdown link", r"\[[^\]]*\]\([^)]*\)"),
    ("blockquote", r"(?m)^\s{0,3}>\s"),
)


@dataclass(frozen=True)
class ChannelFinding:
    token: str
    snippet: str


def find_markdown(text: str) -> list[ChannelFinding]:
    """Return markdown tokens found in *text* (empty list if none)."""

    findings: list[ChannelFinding] = []
    for label, pattern in _MARKDOWN_PATTERNS:
        match = re.search(pattern, text)
        if match:
            start = max(0, match.start() - 12)
            end = min(len(text), match.end() + 12)
            findings.append(
                ChannelFinding(token=label, snippet=text[start:end].strip())
            )
    return findings


def channel_allows_markdown(channel: Channel) -> bool:
    return channel in MARKDOWN_CHANNELS


def validate_channel_format(channel: Channel, text: str) -> list[ChannelFinding]:
    """Return formatting violations for *text* on *channel*.

    For markdown channels this is always empty. For plain-text channels (sms,
    post, widget_reply) any markdown token is a violation.
    """

    if channel_allows_markdown(channel):
        return []
    return find_markdown(text)


# Soft length guidance per channel (used by agents to shape drafts; not a hard
# validation failure because real-world copy varies).
CHANNEL_SOFT_MAX_CHARS: dict[Channel, int] = {
    Channel.sms: 320,
    Channel.post: 500,
    Channel.widget_reply: 600,
}
