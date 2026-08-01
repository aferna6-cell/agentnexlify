"""Lead prospecting pipeline: discover -> enrich -> verify -> score -> promote.

Productizes the intent of the offline scripts in `prospects/` (bulk business
discovery + contact enrichment) as a tenant-scoped, API-first service. Unlike
the offline scripts, discovery is Google Places API only (no SERP/Yelp
scraping) and every row is scoped to a tenant via `client_id` on the
`prospects` table (migration 191).

Pipeline stages:
    discover()        Google Places Text Search -> upsert prospects rows,
                       deduped on (client_id, source, external_ref).
    enrich_prospect()  Fetch the prospect's website, extract email/phone via
                       regex (deterministic-first — no LLM call).
    verify_email()     Provider-abstracted syntax/deliverability check.
                       Fails OPEN to unverified, never blocks the pipeline.
    score_prospect()   Deterministic rubric (see _score_prospect_row).
    promote_to_lead()  Create a `leads` row (client_id, status, source=
                       "prospecting") from a qualified prospect. Idempotent.
    run_pipeline()     Orchestrates all of the above for one discovery batch.

All DB access goes through backend.services.tenant_scope so prospects and
leads both stay scoped by `client_id` (CLAUDE.md invariant #1).
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import settings
from backend.services.tenant_scope import tenant_insert, tenant_select, tenant_update, tenant_upsert
from backend.services.url_validation import is_safe_url

logger = logging.getLogger(__name__)


class ProspectingNotConfigured(Exception):
    """Raised when GOOGLE_PLACES_API_KEY is unset. Routers must map this to
    a clean 422, never a 500 — see backend/routers/prospecting.py."""


# ---------------------------------------------------------------------------
# Discovery — Google Places API (New) Text Search
# ---------------------------------------------------------------------------

_PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_PLACES_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.nationalPhoneNumber,"
    "places.websiteUri,"
    "places.businessStatus,"
    "places.rating,"
    "places.userRatingCount,"
    "places.primaryType"
)
# Google Places Text Search caps pageSize at 20; the router additionally
# bounds incoming `limit` to <=25 (see backend/routers/prospecting.py).
_MAX_DISCOVER_LIMIT = 25
_PLACES_PAGE_SIZE_CAP = 20


async def _search_places_text(text_query: str, api_key: str, page_size: int) -> list[dict]:
    """Isolated HTTP call so tests can monkeypatch this one function.

    Returns the raw `places` list from the Places API v1 response. Raises
    httpx.HTTPError on network/HTTP failure — callers log + propagate.
    """
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": _PLACES_FIELD_MASK,
        "Content-Type": "application/json",
    }
    body = {"textQuery": text_query, "pageSize": page_size}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(_PLACES_SEARCH_URL, headers=headers, json=body)
    resp.raise_for_status()
    data = resp.json()
    return data.get("places", []) or []


def _parse_location(location: str) -> tuple[str, str]:
    """Best-effort split of a 'City, ST' style location string."""
    parts = [p.strip() for p in (location or "").split(",") if p.strip()]
    city = parts[0] if parts else ""
    region = parts[1] if len(parts) > 1 else ""
    return city, region


def _normalize_place(place: dict, location: str) -> dict[str, Any]:
    """Normalize one Places API v1 result into a prospects row (sans client_id)."""
    display_name = place.get("displayName") or {}
    name = display_name.get("text") if isinstance(display_name, dict) else str(display_name or "")
    city, region = _parse_location(location)
    return {
        "source": "places_api",
        "external_ref": place.get("id") or "",
        "business_name": (name or "").strip() or "Unknown Business",
        "category": place.get("primaryType") or "",
        "address": place.get("formattedAddress") or "",
        "city": city,
        "region": region,
        "phone": place.get("nationalPhoneNumber") or "",
        "website": place.get("websiteUri") or "",
        "status": "new",
        "enrichment": {
            "rating": place.get("rating"),
            "rating_count": place.get("userRatingCount"),
            "business_status": place.get("businessStatus"),
        },
    }


async def discover(
    db: Any, *, client_id: str, query: str, location: str, limit: int = 20
) -> list[dict]:
    """Google Places Text Search -> upsert prospects, deduped on external_ref."""
    api_key = settings.google_places_api_key
    if not api_key:
        raise ProspectingNotConfigured("GOOGLE_PLACES_API_KEY is not set")

    bounded_limit = max(1, min(limit, _MAX_DISCOVER_LIMIT))
    page_size = min(bounded_limit, _PLACES_PAGE_SIZE_CAP)
    text_query = f"{query} {location}".strip()

    try:
        raw_places = await _search_places_text(text_query, api_key, page_size)
    except httpx.HTTPError:
        logger.exception(
            "Places API discovery failed client_id=%s query=%r", client_id, text_query
        )
        raise

    rows = []
    for place in raw_places[:bounded_limit]:
        normalized = _normalize_place(place, location)
        if not normalized.get("external_ref"):
            continue
        rows.append(normalized)

    if not rows:
        return []

    try:
        result = tenant_upsert(
            db, "prospects", client_id, rows, on_conflict="client_id,source,external_ref"
        ).execute()
    except Exception:
        logger.exception("Prospect upsert failed client_id=%s", client_id)
        raise
    return result.data or []


# ---------------------------------------------------------------------------
# Enrichment — fetch website, extract contact info via regex
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

_JUNK_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")
_JUNK_EMAIL_SUBSTRINGS = ("@sentry", "@example.", "noreply", "no-reply", "wixpress", "@godaddy")

_ENRICH_USER_AGENT = (
    "Mozilla/5.0 (compatible; AgentNexLiFy-Prospecting/1.0; "
    "+https://agentnexlify.com)"
)
_ENRICH_TIMEOUT = 8.0
_ENRICH_MAX_BYTES = 200_000


async def _fetch_page_text(url: str) -> str:
    """Fetch a single page's HTML text. Returns '' on any failure — enrichment
    degrades gracefully, it never raises into the pipeline."""
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    if not is_safe_url(url):
        logger.debug("Enrichment skipped unsafe url: %s", url)
        return ""
    try:
        async with httpx.AsyncClient(timeout=_ENRICH_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": _ENRICH_USER_AGENT})
        if resp.status_code != 200:
            return ""
        return resp.text[:_ENRICH_MAX_BYTES]
    except httpx.HTTPError:
        logger.warning("Enrichment fetch failed for %s", url, exc_info=True)
        return ""


def _is_junk_email(email: str) -> bool:
    lower = email.lower()
    if lower.endswith(_JUNK_EMAIL_SUFFIXES):
        return True
    return any(sub in lower for sub in _JUNK_EMAIL_SUBSTRINGS)


def _extract_email(text: str) -> str | None:
    for match in _EMAIL_RE.finditer(text or ""):
        candidate = match.group(0)
        if not _is_junk_email(candidate):
            return candidate.lower()
    return None


def _extract_phone(text: str) -> str | None:
    for match in _PHONE_RE.finditer(text or ""):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return None


async def enrich_prospect(db: Any, *, client_id: str, prospect_id: str) -> dict | None:
    """Fetch the prospect's website and fill in missing email/phone.

    Returns the updated prospect row, or None if the prospect doesn't exist
    (or belongs to another tenant — tenant_select already scopes the query).
    """
    result = (
        tenant_select(db, "prospects", client_id, "*").eq("id", prospect_id).limit(1).execute()
    )
    if not result.data:
        return None
    prospect = result.data[0]

    website = prospect.get("website") or ""
    page_text = await _fetch_page_text(website) if website else ""

    email = prospect.get("email")
    if not email and page_text:
        email = _extract_email(page_text)

    phone = prospect.get("phone")
    if not phone and page_text:
        phone = _extract_phone(page_text)

    enrichment = dict(prospect.get("enrichment") or {})
    enrichment["enriched_at"] = datetime.now(timezone.utc).isoformat()
    enrichment["page_fetched"] = bool(page_text)

    updates: dict[str, Any] = {"enrichment": enrichment, "status": "enriched"}
    if email:
        updates["email"] = email
    if phone:
        updates["phone"] = phone

    try:
        updated = (
            tenant_update(db, "prospects", client_id, updates).eq("id", prospect_id).execute()
        )
    except Exception:
        logger.exception(
            "Prospect enrichment update failed client_id=%s prospect_id=%s",
            client_id,
            prospect_id,
        )
        raise
    return updated.data[0] if updated.data else None


# ---------------------------------------------------------------------------
# Verification — provider-abstracted, fail-open to unverified
# ---------------------------------------------------------------------------


def verify_email(email: str) -> bool:
    """Return True only when the email is positively verified.

    Provider is chosen by EMAIL_VERIFY_PROVIDER ("none" default, or
    "zerobounce"). Never raises — any provider failure (network error, bad
    response, missing key) fails OPEN to False (unverified), not to True.
    Verification is advisory input to score_prospect(), never a hard gate.
    """
    if not email:
        return False

    provider = (settings.email_verify_provider or "none").lower()

    if provider == "zerobounce":
        api_key = settings.email_verify_api_key
        if not api_key:
            logger.warning("EMAIL_VERIFY_PROVIDER=zerobounce but no API key set — fail-open")
            return _verify_email_syntax_only(email)
        try:
            resp = httpx.get(
                "https://api.zerobounce.net/v2/validate",
                params={"api_key": api_key, "email": email},
                timeout=8.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("status", "")).lower() == "valid"
        except Exception:
            logger.warning("ZeroBounce verification failed for %s — fail-open", email, exc_info=True)
            return False

    return _verify_email_syntax_only(email)


def _verify_email_syntax_only(email: str) -> bool:
    """Deterministic syntax check via email-validator (no network call)."""
    try:
        from email_validator import EmailNotValidError, validate_email

        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False
    except Exception:
        logger.warning("Email syntax check errored for %s — fail-open", email, exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Scoring — deterministic rubric, 0-100
# ---------------------------------------------------------------------------

# Weights (documented, not tuned against real data yet — mirrors the
# deterministic-first style of backend/services/lead_scoring.py):
#   has website        20
#   has phone          15
#   has verified email 30 (has email but unverified: 10)
#   category present   10
#   rating >= 4.0       15
#   rating 3.0-3.99      5
_SCORE_WEBSITE = 20
_SCORE_PHONE = 15
_SCORE_EMAIL_VERIFIED = 30
_SCORE_EMAIL_UNVERIFIED = 10
_SCORE_CATEGORY = 10
_SCORE_RATING_HIGH = 15
_SCORE_RATING_MID = 5


def score_prospect(row: dict) -> float:
    """Deterministic 0-100 rubric. Pure function — no DB/network access."""
    score = 0.0

    if row.get("website"):
        score += _SCORE_WEBSITE
    if row.get("phone"):
        score += _SCORE_PHONE

    if row.get("email"):
        score += _SCORE_EMAIL_VERIFIED if row.get("email_verified") else _SCORE_EMAIL_UNVERIFIED

    if row.get("category"):
        score += _SCORE_CATEGORY

    rating = (row.get("enrichment") or {}).get("rating")
    try:
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None
    if rating is not None:
        if rating >= 4.0:
            score += _SCORE_RATING_HIGH
        elif rating >= 3.0:
            score += _SCORE_RATING_MID

    return min(100.0, score)


# ---------------------------------------------------------------------------
# Promotion — prospect -> leads row
# ---------------------------------------------------------------------------


async def promote_to_lead(db: Any, *, client_id: str, prospect_id: str) -> dict | None:
    """Create (or reuse) a `leads` row from a qualified prospect. Idempotent:
    re-promoting an already-promoted prospect returns the existing lead
    without inserting a duplicate.
    """
    result = (
        tenant_select(db, "prospects", client_id, "*").eq("id", prospect_id).limit(1).execute()
    )
    if not result.data:
        return None
    prospect = result.data[0]

    if prospect.get("promoted_lead_id"):
        existing_lead = (
            tenant_select(db, "leads", client_id, "*")
            .eq("id", prospect["promoted_lead_id"])
            .limit(1)
            .execute()
        )
        if existing_lead.data:
            return existing_lead.data[0]
        # Dangling reference (lead deleted separately) — fall through and
        # re-promote rather than returning None for a "promoted" prospect.

    # Dedup against existing leads by email (mirrors migration 166's
    # leads_client_email_uniq arbiter — the same pattern the CSV importer in
    # backend/routers/leads.py uses for batch dedup).
    email = prospect.get("email")
    existing_lead_row = None
    if email:
        dup = (
            tenant_select(db, "leads", client_id, "id")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if dup.data:
            existing_lead_row = dup.data[0]

    if existing_lead_row:
        lead_id = existing_lead_row["id"]
    else:
        lead_data = {
            "name": prospect.get("business_name"),
            "email": prospect.get("email"),
            "phone": prospect.get("phone"),
            "status": "new",
            "areas_of_interest": prospect.get("category"),
            "source": "prospecting",
        }
        lead_data = {k: v for k, v in lead_data.items() if v is not None}
        try:
            insert_result = tenant_insert(db, "leads", client_id, lead_data).execute()
        except Exception:
            logger.exception(
                "Lead insert failed during promotion client_id=%s prospect_id=%s",
                client_id,
                prospect_id,
            )
            raise
        if not insert_result.data:
            return None
        lead_id = insert_result.data[0]["id"]

    try:
        tenant_update(
            db, "prospects", client_id, {"status": "promoted", "promoted_lead_id": lead_id}
        ).eq("id", prospect_id).execute()
    except Exception:
        logger.exception(
            "Prospect status update failed after promotion client_id=%s prospect_id=%s",
            client_id,
            prospect_id,
        )
        raise

    lead_result = tenant_select(db, "leads", client_id, "*").eq("id", lead_id).limit(1).execute()
    return lead_result.data[0] if lead_result.data else {"id": lead_id, **lead_data}


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------


async def run_pipeline(
    db: Any,
    *,
    client_id: str,
    query: str,
    location: str,
    limit: int = 20,
    auto_promote_threshold: float | None = None,
) -> dict:
    """discover -> enrich -> verify -> score, then optionally auto-promote
    rows scoring at or above `auto_promote_threshold`. Returns a summary."""
    discovered = await discover(db, client_id=client_id, query=query, location=location, limit=limit)

    enriched_rows: list[dict] = []
    for row in discovered:
        try:
            updated = await enrich_prospect(db, client_id=client_id, prospect_id=row["id"])
        except Exception:
            logger.warning(
                "Enrichment step failed for prospect_id=%s — continuing pipeline",
                row.get("id"),
                exc_info=True,
            )
            updated = row
        enriched_rows.append(updated or row)

    scored_rows: list[dict] = []
    for row in enriched_rows:
        email = row.get("email")
        email_verified = verify_email(email) if email else False
        score = score_prospect({**row, "email_verified": email_verified})

        updates = {"score": score}
        if email and email_verified != row.get("email_verified"):
            updates["email_verified"] = email_verified

        try:
            persisted = (
                tenant_update(db, "prospects", client_id, updates)
                .eq("id", row["id"])
                .execute()
            )
        except Exception:
            logger.warning(
                "Score persist failed for prospect_id=%s — continuing pipeline",
                row.get("id"),
                exc_info=True,
            )
            persisted = None
        scored_rows.append(persisted.data[0] if persisted and persisted.data else {**row, **updates})

    promoted_ids: list[str] = []
    if auto_promote_threshold is not None:
        for row in scored_rows:
            if row.get("score", 0) >= auto_promote_threshold:
                try:
                    lead = await promote_to_lead(db, client_id=client_id, prospect_id=row["id"])
                except Exception:
                    logger.warning(
                        "Auto-promote failed for prospect_id=%s — continuing pipeline",
                        row.get("id"),
                        exc_info=True,
                    )
                    lead = None
                if lead:
                    promoted_ids.append(row["id"])

    return {
        "client_id": client_id,
        "discovered": len(discovered),
        "enriched": len(enriched_rows),
        "scored": len(scored_rows),
        "promoted": len(promoted_ids),
        "prospects": scored_rows,
    }
