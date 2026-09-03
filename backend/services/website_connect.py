"""Website / chatbot connect — detect platform, persist status, verify widget.

Connected means the tenant's public widget key is present on the live site
together with the AgentNexLiFy loader. A widget_configs row, a self-report
checkbox, or another tenant's key is never enough.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin, urlparse

import httpx

from backend.services.url_validation import ValidatedIPTransport, is_safe_url

logger = logging.getLogger(__name__)

PLATFORMS = ("wordpress", "wix", "squarespace", "godaddy", "custom", "unknown")
STATUSES = ("needs_action", "verifying", "connected", "failed")
WIDGET_SCRIPT_MARKER = "agentnexlify-widget.js"
MAX_HTML_BYTES = 1_500_000
MAX_REDIRECTS = 5
FETCH_TIMEOUT_S = 8.0

FORBIDDEN_CREDENTIAL_FIELDS = frozenset(
    {
        "password",
        "cms_password",
        "wp_password",
        "wordpress_password",
        "application_password",
        "app_password",
        "secret",
        "api_secret",
    }
)

_PLATFORM_ACTIONS = {
    "wordpress": {
        "code": "wordpress_plugin",
        "title": "Install the WordPress plugin",
        "steps": [
            "Download the AgentNexLiFy WordPress plugin.",
            "In WordPress go to Plugins → Add New → Upload Plugin and activate it.",
            "Open Settings → AgentNexLiFy, paste your public widget key, and save.",
            "Come back here and click Verify. We check your live site for this key.",
        ],
        "snippet_fallback": True,
    },
    "wix": {
        "code": "wix_custom_code",
        "title": "Add the snippet in Wix Custom Code",
        "steps": [
            "In Wix open Settings → Custom Code → Add Custom Code.",
            "Paste the snippet, set it to All Pages, and place it in Body - end.",
            "Publish the site, then click Verify.",
        ],
        "snippet_fallback": True,
    },
    "squarespace": {
        "code": "squarespace_code_injection",
        "title": "Paste the snippet in Squarespace Code Injection",
        "steps": [
            "In Squarespace open Settings → Developer Tools → Code Injection.",
            "Paste the snippet into the Footer box and save.",
            "Click Verify after the change is live.",
        ],
        "snippet_fallback": True,
    },
    "godaddy": {
        "code": "godaddy_html_section",
        "title": "Add an HTML section in GoDaddy Website Builder",
        "steps": [
            "Open Edit Site in GoDaddy Website Builder.",
            "Add an HTML section and paste the snippet.",
            "Publish, then click Verify.",
        ],
        "snippet_fallback": True,
    },
    "custom": {
        "code": "custom_snippet",
        "title": "Paste the snippet before </body>",
        "steps": [
            "Copy the embed snippet.",
            "Paste it before the closing </body> tag on every page.",
            "Deploy the change, then click Verify.",
        ],
        "snippet_fallback": True,
    },
    "unknown": {
        "code": "choose_platform",
        "title": "Choose how your site is built",
        "steps": [
            "We could not tell which platform hosts this site.",
            "Select WordPress, Wix, Squarespace, GoDaddy, or Custom.",
            "Follow the next step, then click Verify.",
        ],
        "snippet_fallback": True,
    },
}


@dataclass(frozen=True)
class PageFetch:
    url: str
    html: str
    headers: dict
    ok: bool
    error: str | None = None


FetchPage = Callable[[str], PageFetch]


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "…"
    return f"{value[:4]}…"


def reject_credential_fields(payload: dict) -> None:
    """Refuse CMS / application passwords. We never persist them."""
    bad = [k for k in payload if str(k).lower() in FORBIDDEN_CREDENTIAL_FIELDS]
    if bad:
        raise ValueError("CMS passwords are not accepted")


def _http_netloc(parsed) -> str | None:
    """Host[:port] with IPv6 brackets. Drops userinfo so credentials never persist."""
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return None
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return netloc


def _drop_url_userinfo(url: str) -> str:
    parsed = urlparse(url)
    netloc = _http_netloc(parsed)
    if parsed.scheme not in ("http", "https") or not netloc:
        return url
    rebuilt = f"{parsed.scheme}://{netloc}{parsed.path or ''}"
    if parsed.query:
        rebuilt += f"?{parsed.query}"
    return rebuilt


def normalize_website_url(raw: str) -> str:
    url = (raw or "").strip()
    if not url:
        raise ValueError("Website URL is required")
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    netloc = _http_netloc(parsed)
    if parsed.scheme not in ("http", "https") or not netloc:
        raise ValueError("Enter a public http(s) website URL")
    path = parsed.path.rstrip("/")
    normalized = f"{parsed.scheme}://{netloc}{path}"
    if not is_safe_url(normalized):
        raise ValueError("That URL is not a public website we can check")
    return normalized


def detect_platform(
    url: str,
    html: str,
    headers: dict | None,
    *,
    fetched: bool = True,
) -> str:
    if not fetched:
        return "unknown"
    blob = f"{url}\n{html or ''}".lower()
    hdrs = {str(k).lower(): str(v).lower() for k, v in (headers or {}).items()}
    header_blob = " ".join(f"{k}:{v}" for k, v in hdrs.items())

    wp_hits = sum(
        1
        for token in (
            "wp-content/",
            "wp-includes/",
            "name=\"generator\" content=\"wordpress",
            "/wp-json",
            "href=\"https://api.w.org/",
        )
        if token in blob
    )
    if "x-powered-by" in hdrs and "wordpress" in hdrs["x-powered-by"]:
        wp_hits += 1
    if wp_hits:
        return "wordpress"

    if (
        "static.wixstatic.com" in blob
        or "x-wix-request-id" in hdrs
        or "wix.com" in blob
        and "static.parastorage.com" in blob
    ):
        return "wix"

    if (
        "static1.squarespace.com" in blob
        or "squarespace-cdn.com" in blob
        or hdrs.get("server") == "squarespace"
    ):
        return "squarespace"

    if (
        "godaddysites.com" in blob
        or "secureserver.net" in blob
        or "wsimg.com" in blob
        or "godaddy website builder" in blob
    ):
        return "godaddy"

    return "custom"


class _WidgetScriptParser(HTMLParser):
    """True only when loader src + tenant key sit on one live <script> tag."""

    def __init__(self, api_key: str):
        super().__init__(convert_charrefs=True)
        self.api_key = api_key
        self.found = False

    def handle_starttag(self, tag, attrs):
        if self.found or tag != "script":
            return
        attr_map = {str(name).lower(): (value or "") for name, value in attrs}
        src = attr_map.get("src", "")
        key = attr_map.get("data-api-key", "")
        if WIDGET_SCRIPT_MARKER in src and key == self.api_key:
            self.found = True


def widget_is_present(html: str, api_key: str | None) -> bool:
    if not html or not api_key:
        return False
    parser = _WidgetScriptParser(api_key)
    parser.feed(html)
    parser.close()
    return parser.found


def next_action(platform: str, *, connected: bool) -> dict:
    if connected:
        return {
            "code": "live",
            "title": "AI receptionist is live",
            "steps": ["Visitors on this site now get your Agent NexLiFy widget."],
            "snippet_fallback": False,
        }
    key = platform if platform in _PLATFORM_ACTIONS else "unknown"
    return dict(_PLATFORM_ACTIONS[key])


def fetch_public_page(url: str) -> PageFetch:
    """GET a public page with SSRF + redirect re-validation.

    ``is_safe_url`` is the pre-check. The request itself uses
    ``ValidatedIPTransport`` so the TCP connect is opened to a public IP
    from that hop's resolve, not a second hostname lookup that could
    rebind to a private address.
    """
    current = _drop_url_userinfo(url)
    try:
        with httpx.Client(
            timeout=FETCH_TIMEOUT_S,
            follow_redirects=False,
            transport=ValidatedIPTransport(),
        ) as client:
            for _hop in range(MAX_REDIRECTS + 1):
                if not is_safe_url(current):
                    return PageFetch(current, "", {}, False, "unsafe_url")
                resp = client.get(current, headers={"User-Agent": "AgentNexLiFy-WebsiteConnect/1.0"})
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        return PageFetch(current, "", dict(resp.headers), False, "redirect")
                    current = _drop_url_userinfo(urljoin(current, location))
                    continue
                raw = resp.content[:MAX_HTML_BYTES]
                html = raw.decode(resp.encoding or "utf-8", errors="replace")
                return PageFetch(
                    url=str(resp.url),
                    html=html,
                    headers={k: v for k, v in resp.headers.items()},
                    ok=resp.is_success,
                    error=None if resp.is_success else f"http_{resp.status_code}",
                )
    except httpx.HTTPError as exc:
        logger.info("website_connect fetch failed url_host=%s err=%s", urlparse(url).hostname, type(exc).__name__)
        return PageFetch(url, "", {}, False, "fetch_error")
    return PageFetch(current, "", {}, False, "too_many_redirects")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tenant_widget_key(db, tenant_id: str) -> str | None:
    result = (
        db.table("widget_configs")
        .select("api_key")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    key = result.data[0].get("api_key")
    return key if isinstance(key, str) and key.strip() else None


def _get_row(db, tenant_id: str) -> dict | None:
    result = (
        db.table("website_connections")
        .select("*")
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _serialize(row: dict) -> dict:
    platform = row.get("platform") or "unknown"
    status = row.get("status") or "needs_action"
    connected = status == "connected"
    action = next_action(platform, connected=connected)
    return {
        "id": row.get("id"),
        "tenant_id": row.get("tenant_id"),
        "website_url": row.get("website_url"),
        "platform": platform,
        "detected_platform": row.get("detected_platform"),
        "platform_override": bool(row.get("platform_override")),
        "status": status,
        "verification_method": row.get("verification_method"),
        "verification_detail": row.get("verification_detail"),
        "last_verified_at": row.get("last_verified_at"),
        "last_checked_at": row.get("last_checked_at"),
        "next_action": action,
        "connected": connected,
    }


def get_connection(db, tenant_id: str) -> dict | None:
    row = _get_row(db, tenant_id)
    return _serialize(row) if row else None


def upsert_connection(
    db,
    tenant_id: str,
    website_url: str,
    *,
    platform: str | None = None,
    fetch_page: FetchPage | None = None,
) -> dict:
    url = normalize_website_url(website_url)
    fetch = fetch_page or fetch_public_page
    page = fetch(url)
    detected = detect_platform(url, page.html, page.headers, fetched=page.ok)
    override = bool(platform) and platform in PLATFORMS and platform != "unknown"
    chosen = platform if override else detected
    if chosen not in PLATFORMS:
        chosen = detected

    api_key = _tenant_widget_key(db, tenant_id)
    present = widget_is_present(page.html, api_key) if page.ok else False
    now = _now()
    if present:
        status = "connected"
        method = "html_presence"
        detail = "Live HTML includes this tenant's widget key."
        verified_at = now
    elif page.ok:
        status = "needs_action"
        method = None
        detail = "Site reachable. Widget for this tenant not found yet."
        verified_at = None
    else:
        status = "needs_action"
        method = None
        detail = "Could not fetch the site yet. Choose a platform and install, then verify."
        verified_at = None

    payload = {
        "tenant_id": tenant_id,
        "website_url": url,
        "platform": chosen,
        "detected_platform": detected,
        "platform_override": override,
        "status": status,
        "verification_method": method,
        "verification_detail": detail,
        "last_checked_at": now,
        "last_verified_at": verified_at,
        "next_action_code": next_action(chosen, connected=present)["code"],
        "updated_at": now,
    }

    existing = _get_row(db, tenant_id)
    logger.info(
        "website_connect upsert tenant=%s platform=%s detected=%s status=%s key=%s",
        tenant_id,
        chosen,
        detected,
        status,
        redact_secret(api_key),
    )
    if existing:
        result = (
            db.table("website_connections")
            .update(payload)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        row = result.data[0] if result.data else {**existing, **payload}
    else:
        payload["created_at"] = now
        result = db.table("website_connections").insert(payload).execute()
        row = result.data[0] if result.data else payload

    _maybe_store_tenant_url(db, tenant_id, url)
    return _serialize(row)


def verify_connection(
    db,
    tenant_id: str,
    *,
    fetch_page: FetchPage | None = None,
) -> dict:
    row = _get_row(db, tenant_id)
    if not row:
        raise ValueError("Connect a website first")
    url = row["website_url"]
    fetch = fetch_page or fetch_public_page
    page = fetch(url)
    api_key = _tenant_widget_key(db, tenant_id)
    present = widget_is_present(page.html, api_key) if page.ok else False
    now = _now()
    if present:
        status = "connected"
        method = "html_presence"
        detail = "Live HTML includes this tenant's widget key."
        verified_at = now
    elif page.ok:
        status = "needs_action"
        method = None
        detail = "Checked the live site. This tenant's widget key was not found."
        verified_at = row.get("last_verified_at")
    else:
        status = "failed"
        method = None
        detail = "Could not reach the website to verify."
        verified_at = row.get("last_verified_at")

    update = {
        "status": status,
        "verification_method": method,
        "verification_detail": detail,
        "last_checked_at": now,
        "last_verified_at": verified_at,
        "next_action_code": next_action(row.get("platform") or "unknown", connected=present)["code"],
        "updated_at": now,
    }
    if page.ok:
        detected = detect_platform(url, page.html, page.headers, fetched=True)
        update["detected_platform"] = detected
        if not row.get("platform_override"):
            update["platform"] = detected

    logger.info(
        "website_connect verify tenant=%s status=%s key=%s",
        tenant_id,
        status,
        redact_secret(api_key),
    )
    result = (
        db.table("website_connections")
        .update(update)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    saved = result.data[0] if result.data else {**row, **update}
    return _serialize(saved)


def _maybe_store_tenant_url(db, tenant_id: str, url: str) -> None:
    try:
        db.table("tenants").update({"website_url": url}).eq("id", tenant_id).execute()
    except Exception:
        logger.info("website_connect tenant website_url update skipped tenant=%s", tenant_id)
