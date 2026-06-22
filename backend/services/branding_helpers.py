"""Branding plan-filtering and CSS sanitization helpers.

Moved here from backend/routers/widget_chat_helpers.py on 2026-04-19 to fix a
reverse-dependency: branding_service.py (service layer) was importing from the
router layer.  New callers should import from this module directly.

No router-layer types (Request, Depends, etc.) — pure utility functions safe
to call from any layer.

WARNING: Do NOT add `from __future__ import annotations` to this file.
PEP 563 deferred annotations break Pydantic model resolution in FastAPI callers.
"""

import re

# ---------------------------------------------------------------------------
# Branding plan restrictions
# ---------------------------------------------------------------------------

_BRANDING_PLAN_FIELDS: dict[str, set[str]] = {
    "free": {"primary_color"},
    "growth": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url"},
    "professional": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url", "hide_powered_by", "logo_url", "font_family"},
    "enterprise": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url", "hide_powered_by", "logo_url", "font_family", "custom_css"},
    # 2026-06-15 repricing: chatbot ($19.99) is the widget/chat entry tier —
    # widget look-and-feel but no white-label (can't hide "powered by").
    # agent_os ($99.99) is the full platform — enterprise-grade white-label.
    "chatbot": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url"},
    "agent_os": {"primary_color", "secondary_color", "accent_color", "widget_title", "powered_by_text", "powered_by_url", "hide_powered_by", "logo_url", "font_family", "custom_css"},
}

_DANGEROUS_CSS_RE = re.compile(
    r"<script|javascript:|@import|expression\s*\(", re.IGNORECASE
)
_CSS_URL_RE = re.compile(r"url\s*\(", re.IGNORECASE)
_FONT_URL_RE = re.compile(r"(src\s*:\s*url\s*\(|font-face)", re.IGNORECASE)


def _sanitize_css(css: str | None) -> str | None:
    """Strip dangerous patterns from custom CSS."""
    if not css:
        return css
    css = _DANGEROUS_CSS_RE.sub("", css)
    lines = css.split("\n")
    cleaned = []
    in_font_face = False
    for line in lines:
        if "@font-face" in line.lower():
            in_font_face = True
        if in_font_face and "}" in line:
            in_font_face = False
        if not in_font_face and _CSS_URL_RE.search(line) and not _FONT_URL_RE.search(line):
            line = _CSS_URL_RE.sub("/* sanitized */", line)
        cleaned.append(line)
    return "\n".join(cleaned)


def _filter_branding_for_plan(branding: dict | None, plan: str) -> dict:
    """Return only branding fields allowed for the given plan."""
    if not branding:
        return {}
    allowed = _BRANDING_PLAN_FIELDS.get(plan, _BRANDING_PLAN_FIELDS["free"])
    filtered = {k: v for k, v in branding.items() if k in allowed and v is not None}
    if plan in ("free", "growth", "chatbot"):
        filtered.pop("hide_powered_by", None)
    return filtered
