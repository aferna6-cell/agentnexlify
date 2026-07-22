"""Owner-provided web pages as research sources (research v2, round 6).

Deep research read only owned sources (KB, FAQs, instructions, memory, MCP
context) - honest, but blind to the one thing owners ask about most: "what
does this competitor's page say?" A research request may now carry up to
three URLs; each is fetched server-side, stripped to text, and appended to
the corpus as an explicitly-labeled web source. The synthesis rules are
unchanged: cite only provided sources, name gaps plainly.

Safety: every URL passes url_validation.is_safe_url (public DNS only - no
private ranges, loopback, or metadata endpoints), redirects are followed at
most one hop and the redirect target is re-validated, responses are capped
per page, and any per-URL failure just drops that source.
"""

import logging
import re

import httpx

from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)

MAX_URLS = 3
MAX_URL_LEN = 500
_FETCH_TIMEOUT = 8.0
_MAX_CHARS_PER_PAGE = 4000
_MAX_RESPONSE_BYTES = 1_500_000
_USER_AGENT = "AgentNexlifyResearch/1.0 (+https://agentnexlify.com)"

_TAG_BLOCKS_RE = re.compile(
    r"<(script|style|noscript|svg|head)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\r\f\v]+")
_NL_RE = re.compile(r"\n{3,}")


def strip_html(html: str) -> str:
    """Plain text from an HTML page - deterministic, no parser dependency."""
    text = _TAG_BLOCKS_RE.sub(" ", html or "")
    # Block-level closers become newlines so headings/paragraphs stay separated.
    text = re.sub(r"</(p|div|li|h[1-6]|tr|br)\s*>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
    text = _WS_RE.sub(" ", text)
    return _NL_RE.sub("\n\n", text).strip()


def _normalize(raw: str) -> str:
    url = (raw or "").strip()[:MAX_URL_LEN]
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


async def _get_with_one_safe_redirect(client: httpx.AsyncClient, url: str):
    """GET without auto-redirects; follow at most one hop, re-validated.

    Auto-follow would let a public page 302 us into a private address - the
    redirect target must pass the same SSRF gate as the original URL.
    """
    resp = await client.get(url)
    if resp.status_code in (301, 302, 307, 308):
        target = str(resp.headers.get("location") or "")
        if target.startswith("/"):
            target = str(httpx.URL(url).join(target))
        if not target or not is_safe_url(target):
            return None
        resp = await client.get(target)
    return resp


async def fetch_web_entries(urls: list[str] | None) -> tuple[list[dict], list[str]]:
    """(kb-entry-shaped dicts, fetched urls) for up to MAX_URLS pages.

    Best-effort per URL - an unreachable or unsafe page is skipped, never
    fatal to the research run.
    """
    entries: list[dict] = []
    fetched: list[str] = []
    candidates = [u for u in (urls or []) if (u or "").strip()][:MAX_URLS]
    if not candidates:
        return entries, fetched

    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT,
        follow_redirects=False,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        for raw in candidates:
            url = _normalize(raw)
            if not url or not is_safe_url(url):
                logger.info("os_web_sources: rejected unsafe url")
                continue
            try:
                resp = await _get_with_one_safe_redirect(client, url)
                if resp is None or resp.status_code != 200:
                    continue
                content_type = str(resp.headers.get("content-type") or "")
                if not any(
                    kind in content_type for kind in ("text/html", "text/plain")
                ):
                    continue
                body = resp.text[:_MAX_RESPONSE_BYTES]
                text = (
                    strip_html(body)
                    if "text/html" in content_type
                    else body.strip()
                )[:_MAX_CHARS_PER_PAGE]
                if not text.strip():
                    continue
                entries.append({"topic": f"web page: {url}", "answer": text})
                fetched.append(url)
            except Exception:
                logger.info(
                    "os_web_sources: fetch failed url=%s", url, exc_info=True
                )
    return entries, fetched
