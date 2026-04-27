"""Local SEO scoring + JSON parsing helpers.

Extracted from `backend/routers/local_seo.py` to keep the router thin.
Pure functions (no I/O) plus tenant-claim verification.
"""

import json
from typing import Optional

from fastapi import HTTPException


def _strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw


def _parse_json_object_response(raw: str) -> dict:
    cleaned = _strip_json_fences(raw)
    result = json.loads(cleaned)
    if isinstance(result, dict):
        return result
    raise ValueError(f"Expected dict response, got {type(result).__name__}")


def _parse_json_array_response(raw: str) -> list:
    cleaned = _strip_json_fences(raw)
    result = json.loads(cleaned)
    if isinstance(result, list):
        return result
    raise ValueError(f"Expected list response, got {type(result).__name__}")


def _verify_tenant(claims: dict, tenant_id: str) -> None:
    if claims["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")


def _calculate_completeness(
    tenant: dict,
    widget_config: Optional[dict],
    faq_count: int,
    review_count: int,
    content_count: int,
) -> tuple[int, list[str], list[str]]:
    """Calculate completeness score (0-100), missing fields, and recommendations."""
    score = 0
    missing: list[str] = []
    recommendations: list[str] = []

    if tenant.get("business_name"):
        score += 10
    else:
        missing.append("business_name")
        recommendations.append("Add your business name to your profile.")

    if tenant.get("city"):
        score += 10
    else:
        missing.append("city")
        recommendations.append("Add your city to help with local search visibility.")

    if tenant.get("website_url"):
        score += 10
    else:
        missing.append("website_url")
        recommendations.append("Add your website URL to improve your online presence.")

    if tenant.get("business_type"):
        score += 10
    else:
        missing.append("business_type")
        recommendations.append("Set your business type to get better keyword suggestions.")

    if faq_count > 0:
        faq_score = min(faq_count, 10) / 10 * 15
        score += int(faq_score)
    else:
        missing.append("faq_entries")
        recommendations.append("Add FAQ entries to help your AI assistant and boost SEO content.")

    if review_count > 0:
        score += 15
    else:
        missing.append("reviews")
        recommendations.append("Collect customer reviews to build trust and improve local rankings.")

    if widget_config and widget_config.get("greeting_message"):
        score += 10
    else:
        missing.append("widget_greeting")
        recommendations.append("Set a custom widget greeting message for better visitor engagement.")

    if content_count > 0:
        score += 10
    else:
        missing.append("content_items")
        recommendations.append("Create content to establish authority in your local market.")

    if widget_config and widget_config.get("booking_enabled"):
        score += 10
    else:
        missing.append("booking_enabled")
        recommendations.append("Enable appointment booking to convert more website visitors.")

    return score, missing, recommendations
