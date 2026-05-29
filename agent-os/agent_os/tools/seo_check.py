"""Lightweight, offline-safe on-page SEO checker.

``seo_check(url)`` attempts a single short HTTP GET and extracts a handful of
on-page signals (title length, meta description, H1 count, viewport, image alt
coverage). It is built to *fail honestly*: any network error, timeout, or
non-HTML response yields ``fetched=False`` with no findings, so the calling
agent (``seo_recommendations``) gives best-practice guidance instead of
fabricating a live result. No third-party dependency — standard library only.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

_TIMEOUT_SECONDS = 6
_MAX_BYTES = 500_000
_USER_AGENT = "AgentOS-SEOCheck/1.0 (+https://agentnexlify.com)"


@dataclass
class SeoReport:
    """Result of an on-page check.

    ``fetched`` is True only when the page was actually retrieved and parsed.
    ``findings`` is empty unless ``fetched`` is True.
    """

    domain: str
    fetched: bool = False
    findings: list[str] = field(default_factory=list)


def _domain_of(url: str) -> str:
    cleaned = url.strip()
    cleaned = re.sub(r"^https?://", "", cleaned, flags=re.IGNORECASE)
    return cleaned.rstrip("/").split("/")[0] or url.strip()


def _normalize_url(url: str) -> str:
    if re.match(r"^https?://", url, flags=re.IGNORECASE):
        return url
    return f"https://{url}"


def seo_check(url: str) -> SeoReport:
    """Run on-page checks against *url*. Never raises — degrades to
    ``fetched=False`` on any failure."""

    domain = _domain_of(url)
    report = SeoReport(domain=domain)

    try:
        request = urllib.request.Request(
            _normalize_url(url), headers={"User-Agent": _USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "html" not in content_type.lower():
                return report  # not HTML — honestly nothing to check
            raw = resp.read(_MAX_BYTES)
        html = raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return report  # fetched stays False
    except Exception:  # pragma: no cover - defensive catch-all
        return report

    report.fetched = True
    report.findings = _analyze(html)
    return report


def _analyze(html: str) -> list[str]:
    findings: list[str] = []

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        if not title:
            findings.append("Title tag is empty — add a descriptive page title.")
        elif len(title) > 60:
            findings.append(f"Title tag is {len(title)} chars (aim for ≤60).")
        else:
            findings.append(f"Title tag present ({len(title)} chars).")
    else:
        findings.append("No <title> tag found — add one.")

    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]*>', html, re.IGNORECASE
    )
    if desc_match:
        content = re.search(
            r'content=["\'](.*?)["\']', desc_match.group(0), re.IGNORECASE | re.DOTALL
        )
        length = len((content.group(1) if content else "").strip())
        if length == 0:
            findings.append("Meta description is empty — write one (~150 chars).")
        elif length > 160:
            findings.append(f"Meta description is {length} chars (aim for ~150).")
        else:
            findings.append(f"Meta description present ({length} chars).")
    else:
        findings.append("No meta description — add one (~150 chars).")

    h1_count = len(re.findall(r"<h1[\s>]", html, re.IGNORECASE))
    if h1_count == 0:
        findings.append("No H1 heading found — add one primary heading.")
    elif h1_count > 1:
        findings.append(f"{h1_count} H1 headings found — use exactly one.")
    else:
        findings.append("Exactly one H1 heading — good.")

    if re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE):
        findings.append("Mobile viewport meta tag present.")
    else:
        findings.append("No mobile viewport meta tag — add one for mobile rendering.")

    images = re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
    if images:
        with_alt = sum(1 for img in images if re.search(r'alt=["\']', img, re.IGNORECASE))
        missing = len(images) - with_alt
        if missing:
            findings.append(f"{missing} of {len(images)} images missing alt text.")
        else:
            findings.append(f"All {len(images)} images have alt text.")

    return findings
