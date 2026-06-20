"""
Website email enrichment for leadgen.

Fetches homepage (and /contact) of a business website, extracts email
addresses via regex, filters junk addresses, and selects the best one.
"""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_JUNK_SUFFIXES = (
    ".png", ".jpg", ".gif", ".svg", ".webp",
    ".jpeg", ".ico", ".bmp", ".tiff",
)

_JUNK_SUBSTRINGS = (
    "@sentry",
    "@example.",
    "@2x",
    "wixpress",
    ".wixpress",
    "your@email",
    "sentry.io",
    "@godaddy",
)

_PREFERRED_PREFIXES = ("info@", "contact@", "hello@", "office@", "support@", "admin@")

_USER_AGENT = (
    "Mozilla/5.0 (compatible; AgentNexLiFy-LeadGen/1.0; "
    "+https://agentnexlify.com)"
)


def _is_junk_email(email: str) -> bool:
    """Return True if the email should be discarded."""
    lower = email.lower()
    for suffix in _JUNK_SUFFIXES:
        if lower.endswith(suffix):
            return True
    for substring in _JUNK_SUBSTRINGS:
        if substring in lower:
            return True
    return False


_MAX_REDIRECTS = 5


def _fetch_page(url: str, timeout: float) -> str:
    """Fetch a single URL and return its text body. Returns '' on error.

    SSRF guard: a scraped prospect URL (or a future server caller) must not be
    able to point this at internal/metadata addresses. Redirects are followed
    manually and re-validated each hop, since a safe host can 302 to an
    internal one.
    """
    try:
        current = url
        for _ in range(_MAX_REDIRECTS + 1):
            if not is_safe_url(current):
                logger.debug("skipping unsafe url: %s", current)
                return ""
            response = httpx.get(
                current,
                headers={"User-Agent": _USER_AGENT},
                timeout=timeout,
                follow_redirects=False,
            )
            if response.is_redirect and response.next_request is not None:
                current = str(response.next_request.url)
                continue
            return response.text
        logger.debug("too many redirects for %s", url)
        return ""
    except Exception as exc:
        logger.debug("fetch error for %s: %s", url, exc)
        return ""


def _emails_from_html(html: str) -> set:
    """Extract non-junk lowercase emails from one HTML blob."""
    found: set = set()
    for match in _EMAIL_REGEX.finditer(html or ""):
        email = match.group(0).lower()
        if not _is_junk_email(email):
            found.add(email)
    return found


def extract_emails_from_site(url: str, timeout: float = 10.0) -> list:
    """
    Fetch homepage and /contact page of url, extract emails, filter junk.

    Returns a deduplicated list of lowercase email addresses.
    Returns [] on network errors.
    """
    if not url:
        return []

    # Normalise URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    pages_to_try = [url]

    # Add /contact path
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    contact_url = urljoin(base, "/contact")
    if contact_url != url:
        pages_to_try.append(contact_url)

    found: set = set()
    for page_url in pages_to_try:
        found |= _emails_from_html(_fetch_page(page_url, timeout))

    return sorted(found)


def best_email(emails: list) -> Optional[str]:
    """
    Pick the best email from a list.

    Preference order:
    1. Starts with a preferred prefix (info@, contact@, hello@, office@, ...)
    2. First email in the list
    3. None if list is empty
    """
    if not emails:
        return None

    for email in emails:
        for prefix in _PREFERRED_PREFIXES:
            if email.startswith(prefix):
                return email

    return emails[0]


# --- Owner-name extraction (conservative: high precision, low recall) ---

_TAG_RE = re.compile(r"<[^>]+>")
# Words that signal a company/role string, not a person's name.
_NON_PERSON_TOKENS = (
    "llc", "inc", "corp", "co.", "ltd", "company", "services", "service",
    "roofing", "plumbing", "hvac", "electric", "dental", "salon", "group",
    "construction", "contractors", "solutions", "associates", "team",
)
# "Owner: Jane Doe" / "Founded by Jane Doe" / "Owner/Operator - Jane Doe".
# Label is case-insensitive (scoped (?i:...)); the NAME stays case-sensitive so
# a trailing lowercase word ("...Smith in 1998") is not swallowed into the name.
_OWNER_LABEL_RE = re.compile(
    r"(?i:owner/operator|owner|founded by|owned by|founder|proprietor)"
    r"\s*[:\-–]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,2}?)"
)
# "Jane Doe, Owner" / "Jane Doe - Founder"
_NAME_LABEL_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,2})\s*[,\-–]\s*(?i:owner|founder|proprietor)"
)
# JSON-LD: "founder"/"owner": {"name": "Jane Doe"} or "founder": "Jane Doe"
_JSONLD_RE = re.compile(
    r'"(?:founder|owner)"\s*:\s*(?:\{[^}]*?"name"\s*:\s*"([^"]{3,60})"|"([^"]{3,60})")',
    re.IGNORECASE,
)


def _looks_like_person(name: str) -> bool:
    """True only for a plausible 2-3 word personal name (not a company/role)."""
    name = (name or "").strip()
    parts = name.split()
    if not (2 <= len(parts) <= 3):
        return False
    low = name.lower()
    if any(tok in low for tok in _NON_PERSON_TOKENS):
        return False
    # Each part starts uppercase, alphabetic-ish.
    return all(p[:1].isupper() and re.fullmatch(r"[A-Za-z'\-]+", p) for p in parts)


def extract_owner_name(html: str) -> str:
    """Best-effort owner/founder name from page HTML. Returns '' unless a
    high-confidence pattern matches a plausible person name. Never guesses —
    a wrong name in a cold email is worse than none."""
    if not html:
        return ""
    # JSON-LD first (most structured/reliable).
    for m in _JSONLD_RE.finditer(html):
        cand = m.group(1) or m.group(2) or ""
        if _looks_like_person(cand):
            return cand.strip()
    text = _TAG_RE.sub(" ", html)
    for rx in (_OWNER_LABEL_RE, _NAME_LABEL_RE):
        for m in rx.finditer(text):
            cand = m.group(1)
            if _looks_like_person(cand):
                return cand.strip()
    return ""


# --- Contact-form URL discovery (for the no-email channel) ---

_CONTACT_HREF_RE = re.compile(
    r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE
)
_CONTACT_KEYWORDS = (
    "contact", "get-a-quote", "get-quote", "free-quote", "request",
    "estimate", "book", "schedule", "appointment", "get-started",
)


def find_contact_form_url(html: str, base_url: str) -> str:
    """Return an absolute URL of a likely contact/quote page link, else ''."""
    if not html:
        return ""
    for m in _CONTACT_HREF_RE.finditer(html):
        href = m.group(1)
        low = href.lower()
        if low.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        if any(k in low for k in _CONTACT_KEYWORDS):
            return urljoin(base_url, href)
    return ""


def enrich_site(url: str, timeout: float = 10.0) -> dict:
    """Fetch a business site once and pull email + owner name + contact-form URL.

    Returns {"email": str, "owner_name": str, "contact_form": str} (empty
    strings when not found). Degrades to all-empty on network failure.
    Reuses one homepage fetch; only fetches /contact if the homepage yields
    no email (keeps requests minimal + polite)."""
    result = {"email": "", "owner_name": "", "contact_form": ""}
    if not url:
        return result
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    home = _fetch_page(url, timeout)
    emails = _emails_from_html(home)
    owner = extract_owner_name(home)
    form = find_contact_form_url(home, base)

    if not emails or not owner or not form:
        contact_url = urljoin(base, "/contact")
        if contact_url != url:
            contact_html = _fetch_page(contact_url, timeout)
            emails |= _emails_from_html(contact_html)
            owner = owner or extract_owner_name(contact_html)
            form = form or find_contact_form_url(contact_html, base)
            # If we fetched /contact and it exists, it IS a usable form target.
            if not form and contact_html:
                form = contact_url

    result["email"] = best_email(sorted(emails)) or ""
    result["owner_name"] = owner
    result["contact_form"] = form
    return result
