"""Outbound guardrail pass for Agent OS deliverables (enterprise-audit item 6).

Deterministic screen that runs on a draft AFTER auto-send resolves to
"approved" and BEFORE the action handler fires. A flagged draft is downgraded
to pending_approval so a human sees it — the guard never blocks the owner's
explicit Approve button, only the automatic path.

Deliberately deterministic (regex + Luhn), no LLM: the failure mode being
prevented is an agent auto-sending a message that leaks a secret/SSN/card
number or redirects payments. False positives cost one extra approval click;
false negatives cost a tenant. Patterns err toward flagging.

Emails and phone numbers are NOT flagged — drafts legitimately carry contact
details; those are the message working, not leaking.
"""

import logging
import re

from backend.services.activity import log_activity

logger = logging.getLogger(__name__)

# Secrets that must never leave in an outbound message. Ordered list of
# (flag_name, compiled_pattern) so scan output is stable for tests + UI.
_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.")),
]

_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# 13-16 digit runs, allowing space/dash separators (card-shaped); each hit is
# Luhn-checked before flagging so order numbers and phone strings pass through.
_CARD_CANDIDATE_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")

# Payment-redirection language an agent should never auto-send. The classic
# invoice-fraud shapes: new bank details, wire instructions, gift cards.
_PAYMENT_REDIRECT_RE = re.compile(
    r"routing number|new bank (?:account|details)|updated bank (?:account|details)"
    r"|wire (?:the money|payment|funds|transfer to)|western union"
    r"|pay(?:ment)? (?:in|with|via) gift ?cards?",
    re.IGNORECASE,
)


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def scan_text(text: str) -> list[str]:
    """Return ordered, deduped flag names found in *text* ([] = clean)."""
    if not text:
        return []
    flags: list[str] = []

    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            flags.append(name)

    if _SSN_RE.search(text):
        flags.append("ssn")

    for match in _CARD_CANDIDATE_RE.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 16 and _luhn_ok(digits):
            flags.append("card_number")
            break

    if _PAYMENT_REDIRECT_RE.search(text):
        flags.append("payment_redirect")

    return flags


def scan_deliverable(deliverable: dict | None) -> list[str]:
    """Scan a draft's title + body. Never raises."""
    if not isinstance(deliverable, dict):
        return []
    try:
        parts = [
            str(deliverable.get("title") or ""),
            str(deliverable.get("body") or ""),
        ]
        return scan_text("\n".join(parts))
    except Exception:
        logger.warning("os_outbound_guard: scan failed", exc_info=True)
        return []


def apply_outbound_guard(
    client_id: str,
    agent_name: str,
    deliverable: dict | None,
    status: str | None,
) -> tuple[str | None, list[str]]:
    """Downgrade an auto-approved draft to pending_approval when flagged.

    Returns ``(status, flags)``. Non-approved statuses pass through unscanned —
    they already stop at the human gate. On downgrade, the reason lands in
    activity_log so the digest and the owner can see the guard fired.
    """
    if status != "approved":
        return status, []
    flags = scan_deliverable(deliverable)
    if not flags:
        return status, []
    log_activity(
        tenant_id=client_id,
        activity_type="outbound_guard_flagged",
        description=(
            "Auto-send held for review: draft matched outbound guardrail "
            f"patterns ({', '.join(flags)})"
        ),
        metadata={
            "agent_name": agent_name,
            "flags": flags,
            "channel": (deliverable or {}).get("channel"),
            "title": (deliverable or {}).get("title"),
        },
    )
    return "pending_approval", flags
