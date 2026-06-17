"""Instant KB from a website URL.

Onboarding helper that turns a tenant's website URL into draft FAQ entries:

  1. fetch_website_text(url)   - fetch + strip HTML to plain text (SSRF-safe)
  2. draft_faq_entries(...)    - ask Claude for structured question/answer pairs
  3. persist_faq_entries(...)  - write confirmed entries to faq_entries

The draft step never writes to the database, so the dashboard can show the
owner the proposed FAQs and let them confirm before anything is saved. Every
stage degrades to a clear error rather than crashing the onboarding flow.

faq_entries is keyed by ``tenant_id`` (migration 001). This is not the leads
or conversations table, so tenant_id is the correct key here.
"""

import json
import logging
import re

import httpx

from backend.services.llm_runtime import call_claude_messages
from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)

# Caps keep oversized pages from blowing up the prompt or the DB row.
_FETCH_TIMEOUT_SECONDS = 15.0
_MAX_DOWNLOAD_BYTES = 3_000_000  # 3 MB - refuse to buffer giant pages
_MAX_TEXT_CHARS = 15000  # text handed to the model
_MIN_TEXT_CHARS = 40  # below this the page has no usable content
_MAX_FAQ_ENTRIES = 12
# A missing content-type header is tolerated; a present one must be htmlish.
_HTMLISH_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class InstantKbError(Exception):
    """Raised when a stage fails for a reason worth surfacing to the user.

    ``code`` is a short machine token; ``message`` is owner-facing copy.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def normalize_url(url: str) -> str:
    """Add an https:// scheme when the owner pasted a bare domain."""
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _strip_html(html: str) -> str:
    """Reduce HTML to readable plain text. Best-effort, never raises."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def fetch_website_text(url: str) -> str:
    """Fetch ``url`` and return plain text.

    Raises InstantKbError with an owner-facing message for: unsafe/invalid URL,
    unreachable site, non-HTML content, and empty pages. Oversized responses
    are truncated rather than rejected.
    """
    normalized = normalize_url(url)
    if not is_safe_url(normalized):
        raise InstantKbError(
            "unsafe_url",
            "That URL is not a public website we can read. Use a full http(s) address.",
        )

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = await client.get(
                normalized,
                headers={"User-Agent": "AgentNexLiFy-Bot/1.0 (+https://agentnexlify.com)"},
            )
    except httpx.HTTPError as exc:
        logger.warning("instant_kb.fetch_failed url=%s error=%s", normalized, exc)
        raise InstantKbError(
            "fetch_failed",
            "We could not reach that website. Check the URL and try again.",
        )

    if resp.status_code >= 400:
        logger.warning("instant_kb.fetch_status url=%s status=%d", normalized, resp.status_code)
        raise InstantKbError(
            "fetch_failed",
            f"The website returned an error (status {resp.status_code}). Try a different page.",
        )

    content_type = (resp.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type and not any(content_type.startswith(ok) for ok in _HTMLISH_CONTENT_TYPES):
        raise InstantKbError(
            "not_html",
            "That link is not a web page we can read (it looks like a file or media). "
            "Paste your homepage URL instead.",
        )

    raw = resp.content[:_MAX_DOWNLOAD_BYTES]
    try:
        html = raw.decode(resp.encoding or "utf-8", errors="replace")
    except (LookupError, UnicodeDecodeError):
        html = raw.decode("utf-8", errors="replace")

    text = _strip_html(html)
    if len(text) < _MIN_TEXT_CHARS:
        raise InstantKbError(
            "empty_page",
            "We could not find readable text on that page. The site may block bots "
            "or have little content. You can add FAQs by hand instead.",
        )

    return text[:_MAX_TEXT_CHARS]


def _build_prompt(business_name: str, business_type: str, website_text: str) -> str:
    name = business_name or "this business"
    btype = business_type or "local business"
    return (
        "You write FAQ entries for a small business AI chat assistant.\n"
        f"Business name: {name}\n"
        f"Business type: {btype}\n\n"
        "Website content:\n"
        f"{website_text}\n\n"
        "Produce 6 to 10 frequently asked questions a customer would ask, with "
        "clear, accurate answers grounded only in the website content above. "
        "Use facts present in the content. When a detail is absent, write a "
        "general but truthful answer and do not invent specifics like prices, "
        "addresses, or phone numbers.\n\n"
        "Return ONLY a JSON array, no prose, no markdown fences. Each element:\n"
        '{"question": "...", "answer": "...", "category": "..."}\n'
        'category is one of: services, pricing, hours, location, booking, general.'
    )


def _coerce_entries(parsed: object) -> list[dict]:
    """Validate and normalize the model output into clean FAQ dicts."""
    if isinstance(parsed, dict):
        # Tolerate {"faqs": [...]} or {"entries": [...]} wrappers.
        for key in ("faqs", "entries", "questions", "data"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
    if not isinstance(parsed, list):
        return []

    valid_categories = {"services", "pricing", "hours", "location", "booking", "general"}
    entries: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        if not question or not answer:
            continue
        category = str(item.get("category") or "general").strip().lower()
        if category not in valid_categories:
            category = "general"
        entries.append(
            {
                "question": question[:500],
                "answer": answer[:2000],
                "category": category,
            }
        )
        if len(entries) >= _MAX_FAQ_ENTRIES:
            break
    return entries


def _parse_faq_json(raw: str) -> list[dict]:
    """Parse the model response into FAQ dicts. Returns [] on unusable output."""
    text = (raw or "").strip()
    if not text:
        return []
    # Strip ```json fences if the model added them despite instructions.
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return _coerce_entries(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: pull the first JSON array out of mixed prose.
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return _coerce_entries(json.loads(match.group(0)))
        except (json.JSONDecodeError, ValueError):
            return []
    return []


async def draft_faq_entries(
    business_name: str,
    business_type: str,
    website_text: str,
) -> list[dict]:
    """Call Claude to draft FAQ entries from website text.

    Raises InstantKbError("llm_failed") on API failure and
    InstantKbError("no_entries") when the model returns nothing usable.
    """
    prompt = _build_prompt(business_name, business_type, website_text)
    try:
        result = await call_claude_messages(
            operation="instant_kb.draft_faqs",
            model="claude-sonnet-4-6",
            max_tokens=2000,
            temperature=0.3,
            timeout=60.0,
            messages=[{"role": "user", "content": prompt}],
            metadata={"business_type": business_type, "text_chars": len(website_text)},
        )
    except Exception as exc:
        logger.warning("instant_kb.llm_failed error=%s", type(exc).__name__, exc_info=True)
        raise InstantKbError(
            "llm_failed",
            "Could not generate FAQs right now. Try again in a moment or add them by hand.",
        )

    entries = _parse_faq_json(result.text)
    if not entries:
        raise InstantKbError(
            "no_entries",
            "We read your site but could not draft FAQs from it. You can add them by hand.",
        )
    return entries


def persist_faq_entries(db, tenant_id: str, entries: list[dict]) -> int:
    """Insert confirmed FAQ entries into faq_entries. Returns rows written.

    Skips entries missing a question or answer. Raises InstantKbError on the
    underlying DB failure so the caller can return a clean error.
    """
    rows = []
    for entry in entries or []:
        question = str(entry.get("question") or "").strip()
        answer = str(entry.get("answer") or "").strip()
        if not question or not answer:
            continue
        category = str(entry.get("category") or "instant_kb").strip().lower() or "instant_kb"
        rows.append(
            {
                "tenant_id": tenant_id,
                "question": question[:500],
                "answer": answer[:2000],
                "category": category,
                "is_active": True,
            }
        )
    if not rows:
        return 0
    try:
        db.table("faq_entries").insert(rows).execute()
    except Exception as exc:
        logger.warning("instant_kb.persist_failed tenant=%s error=%s", tenant_id, type(exc).__name__, exc_info=True)
        raise InstantKbError("persist_failed", "Could not save the FAQs. Please try again.")
    return len(rows)
