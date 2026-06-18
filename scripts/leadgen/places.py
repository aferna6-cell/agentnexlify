"""
Google Places API (New, v1) client for leadgen.

Uses POST https://places.googleapis.com/v1/places:searchText with
X-Goog-Api-Key header and X-Goog-FieldMask to retrieve place details.
Follows nextPageToken pagination up to 3 pages or max_results cap.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.nationalPhoneNumber,"
    "places.websiteUri,"
    "places.businessStatus,"
    "places.rating,"
    "places.userRatingCount,"
    "places.primaryType,"
    "nextPageToken"
)

_PAGE_SIZE = 20
_MAX_PAGES = 3


def place_fields(place: dict) -> dict:
    """Normalize a single Places API result to a flat dict."""
    display_name = place.get("displayName") or {}
    return {
        "place_id": place.get("id", ""),
        "name": display_name.get("text", "") if isinstance(display_name, dict) else str(display_name),
        "category": place.get("primaryType", ""),
        "phone": place.get("nationalPhoneNumber", ""),
        "website": place.get("websiteUri", ""),
        "address": place.get("formattedAddress", ""),
        "rating": place.get("rating", ""),
        "rating_count": place.get("userRatingCount", ""),
        "business_status": place.get("businessStatus", ""),
    }


def is_usable(place: dict) -> bool:
    """Return True only if place is OPERATIONAL and has a website URL."""
    status = place.get("business_status", "")
    website = place.get("website", "")
    return status == "OPERATIONAL" and bool(website)


def search_text(query: str, api_key: str, max_results: int = 60) -> list:
    """
    Search Google Places for the given text query.

    Follows nextPageToken pagination up to _MAX_PAGES pages or max_results,
    whichever comes first. Returns a list of normalized dicts (via place_fields).
    Deduplicates by place_id.
    """
    results = []
    seen_ids = set()
    page_token: Optional[str] = None
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
        "Content-Type": "application/json",
    }

    for page_num in range(_MAX_PAGES):
        if len(results) >= max_results:
            break

        body = {
            "textQuery": query,
            "pageSize": _PAGE_SIZE,
        }
        if page_token:
            body["pageToken"] = page_token

        try:
            response = httpx.post(PLACES_SEARCH_URL, headers=headers, json=body, timeout=15.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Places API HTTP error on page %d: %s", page_num + 1, exc)
            break
        except httpx.RequestError as exc:
            logger.error("Places API request error on page %d: %s", page_num + 1, exc)
            break

        data = response.json()
        places_raw = data.get("places", [])

        for place in places_raw:
            if len(results) >= max_results:
                break
            normalized = place_fields(place)
            pid = normalized.get("place_id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                results.append(normalized)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    logger.info("search_text('%s') returned %d places", query, len(results))
    return results
