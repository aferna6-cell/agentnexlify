"""Deterministic support-chat signals for the website widget.

Two production bugs (MTOptions, 2026-11-09) motivate this module:

1. An existing customer wrote "I seem to have stopped getting text message
   alerts." The model replied "I'll pass this along to support@..." but no
   escalation was created and nobody was notified — the promise was only
   text. ``promises_handoff`` catches that kind of first-person handoff
   promise so the widget pipeline can make it real (or make the reply honest).
2. Three minutes later the same chat was captured as a sales lead and
   auto-enrolled in a free-trial nurture sequence. ``is_support_request``
   recognizes existing-customer / support issues so lead capture can skip
   sales sequences for them.

Both are plain regexes on purpose: they run inline on the visitor reply path
and in lead capture, where an extra model call is not acceptable.
"""

import re

# Existing-customer / support phrasing. Kept specific: generic sales
# questions ("what's your refund policy?", "do you offer text alerts?") must
# NOT match, or prospects would silently lose their follow-up sequence.
_SUPPORT_RE = re.compile(
    r"\b("
    r"stopped (getting|receiving|working|sending|coming)"
    r"|(not|never|no longer|isn'?t|aren'?t|haven'?t been) (getting|receiving) (my |any |the )?"
    r"(alerts?|texts?|text messages?|sms|emails?|notifications?|messages?)"
    r"|(isn'?t|is not|aren'?t|are not|doesn'?t|does not|don'?t|won'?t|can'?t|cannot|couldn'?t)"
    r" (work|working|load|log ?in|sign ?in|access|connect)"
    r"|my (account|subscription|membership|login|password|billing|invoice|order|alerts?|service|plan|payment)"
    r"|cancel (my|the) (subscription|membership|account|plan|service)"
    r"|(want|need|request|get|issue) a refund|refund (me|my)"
    r"|(was|been|got) (double |over)?charged"
    r"|i(?:'m| am) an? (current |existing |paying )?(customer|subscriber|member|client)"
    r"|i (already )?(pay|subscribe) (for|to)"
    r")\b",
    re.IGNORECASE,
)

# First-person promises that someone else will be told. Deliberately does
# not match the prompt-sanctioned soft line "someone can follow up" on its
# own — only an explicit "I'll / I've / let me <hand it over>" commitment.
_HANDOFF_PROMISE_RE = re.compile(
    r"\b(i['’]?ll|i will|i['’]?ve|i have|let me|i['’]?m going to|i am going to)\s+(also\s+)?("
    # "pass this along", "forward your request to", "share your details with"
    r"(pass(ed)?|forward(ed)?|sen[dt]|share(d)?|hand(ed)?)\s+"
    r"(this|that|it|these|your [\w ]{0,30}?)\s+(along|on|over|to|with)\b"
    # "notify the team", "flag this" — but not "alert you when it ships"
    r"|(escalate(d)?|flag(ged)?|notif(y|ied)|alert(ed)?|loop(ed)? in)\b(?!\s+you\b)"
    r"|let (our|the|my) [\w ]{0,20}?(team|staff|support|owner|manager) know"
    r"|connect(ed)? you (with|to)"
    r"|get (our|the|a) [\w ]{0,20}?(team|staff|support|person|human)"
    r")",
    re.IGNORECASE,
)


def support_issue(messages: list[dict]) -> str | None:
    """The first visitor message that reads as an existing-customer issue."""
    for m in messages:
        content = m.get("content") or ""
        if m.get("role") == "user" and _SUPPORT_RE.search(content):
            return content
    return None


def is_support_request(messages: list[dict]) -> bool:
    """True when any visitor message reads as an existing-customer issue."""
    return support_issue(messages) is not None


def promises_handoff(assistant_text: str) -> bool:
    """True when the reply commits to handing the issue to a person."""
    return bool(_HANDOFF_PROMISE_RE.search(assistant_text or ""))
