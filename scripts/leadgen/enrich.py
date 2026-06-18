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


def _fetch_page(url: str, timeout: float) -> str:
    """Fetch a single URL and return its text body. Returns '' on error."""
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        )
        return response.text
    except Exception as exc:
        logger.debug("fetch error for %s: %s", url, exc)
        return ""


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
        html = _fetch_page(page_url, timeout)
        if not html:
            continue
        for match in _EMAIL_REGEX.finditer(html):
            email = match.group(0).lower()
            if not _is_junk_email(email):
                found.add(email)

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
