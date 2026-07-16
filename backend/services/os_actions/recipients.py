"""Deterministic recipient normalizers for Agent OS send actions.

The owner can attach an explicit ``recipient`` to a deliverable (phone for
sms.send, email for email.send). These helpers validate + normalize that
input with zero guessing beyond one documented default:

* Phones: formatting characters (spaces, dashes, dots, parens) are stripped.
  ``+``-prefixed numbers must already be E.164. Bare 10-digit numbers are
  treated as US (+1) — the platform's SMS stack (Twilio, TCPA compliance)
  is US-centric. Bare 11-digit numbers starting with 1 get a ``+``.
  Anything else is rejected (returns None), never "fixed up".
* Emails: trimmed and matched against the same pattern email.send already
  uses for validation. No case folding — local parts are case-sensitive.
"""

import re

_E164_RE = re.compile(r"\+[1-9]\d{7,14}")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_FORMATTING_RE = re.compile(r"[\s\-().]")


def normalize_phone(raw) -> str | None:
    """E.164 phone from owner input, or None when it cannot be normalized."""
    cleaned = _FORMATTING_RE.sub("", str(raw or "").strip())
    if not cleaned:
        return None
    if cleaned.startswith("+"):
        return cleaned if _E164_RE.fullmatch(cleaned) else None
    if re.fullmatch(r"\d{10}", cleaned):
        return f"+1{cleaned}"
    if re.fullmatch(r"1\d{10}", cleaned):
        return f"+{cleaned}"
    return None


def normalize_email(raw) -> str | None:
    """Trimmed email address from owner input, or None when invalid."""
    cleaned = str(raw or "").strip()
    if cleaned and _EMAIL_RE.fullmatch(cleaned):
        return cleaned
    return None
