"""Instant quoting (#R2) — draft a Good/Better/Best quote GROUNDED in the
tenant's own `service_types` catalog.

The moat: quotes cite the tenant's real services/prices
(migrations/063_service_types.sql), never invented ones. If the catalog is
empty, the returned quote says pricing needs setup instead of guessing —
every price the model returns is checked against the catalog and dropped if
it doesn't match exactly.

Schema: migrations/171_photo_triage_and_quotes.sql — `quotes` table,
`tenant_id`-scoped (standard column, not the leads-table `client_id`
pattern).

Fault-tolerant like `backend/services/review_responder.py`: never raises.
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1500
TIER_KEYS = ("good", "better", "best")

_SYSTEM_PROMPT_WITH_CATALOG = (
    'You are drafting an itemized Good/Better/Best quote for {business_type} '
    'business "{business_name}". Use ONLY the services and prices from the '
    "catalog below — never invent a service or a price that is not in the "
    "catalog. If a described job needs multiple catalog services, list each "
    "as a separate line item. If the job cannot be reasonably matched to the "
    "catalog, say so in the tier's note instead of guessing a price.\n\n"
    "Catalog (name | price | description):\n{catalog_text}\n\n"
    "Respond with ONLY a JSON object, no markdown fences, no extra text:\n"
    '{{"good": {{"line_items": [{{"name": str, "description": str, "price": '
    'number}}], "total": number, "note": str|null}}, "better": {{...same '
    'shape...}}, "best": {{...same shape...}}}}\n\n'
    '"good" is the minimal viable scope from the catalog, "better" adds '
    'reasonable catalog add-ons, "best" is the most complete catalog-backed '
    "option. Every price in every line item MUST match a catalog price "
    "exactly."
)

_SYSTEM_PROMPT_NO_CATALOG = (
    'You are drafting a quote for {business_type} business "{business_name}", '
    "but this tenant has not set up their service catalog yet. Do NOT invent "
    "prices. Respond with ONLY a JSON object, no markdown fences, no extra "
    "text:\n"
    '{{"good": {{"line_items": [], "total": 0, "note": "Pricing needs setup — '
    'add services in the dashboard to generate a real quote."}}, "better": '
    '{{"line_items": [], "total": 0, "note": "Pricing needs setup — add '
    'services in the dashboard to generate a real quote."}}, "best": '
    '{{"line_items": [], "total": 0, "note": "Pricing needs setup — add '
    'services in the dashboard to generate a real quote."}}}}'
)


def _catalog_text(services: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for svc in services:
        price = svc.get("price")
        price_str = f"${price:.2f}" if isinstance(price, (int, float)) else "price not set"
        desc = (svc.get("description") or "").strip()
        lines.append(f"- {svc.get('name')} | {price_str} | {desc}")
    return "\n".join(lines)


def _strip_json_fence(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _valid_price_set(services: list[dict[str, Any]]) -> set[float]:
    prices: set[float] = set()
    for svc in services:
        price = svc.get("price")
        if isinstance(price, (int, float)):
            prices.add(round(float(price), 2))
    return prices


def _sanitize_tier(
    raw_tier: Any, allowed_prices: set[float], has_catalog: bool
) -> dict[str, Any]:
    """Coerce a model-drafted tier, dropping any line item whose price isn't
    an exact catalog match. This is the enforcement point for "never invent
    prices" — the prompt asks nicely, this makes it a hard guarantee."""
    if not isinstance(raw_tier, dict):
        return {"line_items": [], "total": 0.0, "note": None}

    raw_items = raw_tier.get("line_items")
    line_items: list[dict[str, Any]] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            price = item.get("price")
            try:
                price_val = round(float(price), 2)
            except (TypeError, ValueError):
                continue
            if has_catalog and price_val not in allowed_prices:
                logger.warning(
                    "quote_builder: dropped out-of-catalog price %s", price_val
                )
                continue
            line_items.append(
                {
                    "name": str(item.get("name") or "").strip()[:200],
                    "description": str(item.get("description") or "").strip()[:500],
                    "price": price_val,
                }
            )

    total = round(sum(item["price"] for item in line_items), 2)
    note = raw_tier.get("note")
    return {
        "line_items": line_items,
        "total": total,
        "note": note.strip() if isinstance(note, str) and note.strip() else None,
    }


async def build_quote(
    *,
    tenant_id: str,
    job_description: str,
    triage: dict[str, Any] | None = None,
    lead_id: str | None = None,
) -> dict[str, Any] | None:
    """Draft a Good/Better/Best quote grounded in the tenant's service_types.

    `lead_id` is optional and, when given, stored as an FK-less pointer on
    the inserted row (see migrations/171_photo_triage_and_quotes.sql).

    Never raises. Returns the inserted `quotes` row, or None on invalid
    input or any failed step (logged either way).
    """
    job_description = (job_description or "").strip()
    if not job_description:
        logger.warning("quote_builder: empty job_description tenant=%s", tenant_id)
        return None

    db = get_service_supabase()

    business_name = "our business"
    business_type = ""
    try:
        tenant_result = (
            db.table("tenants")
            .select("business_name, business_type")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_result.data:
            business_name = tenant_result.data[0].get("business_name") or business_name
            business_type = tenant_result.data[0].get("business_type") or ""
    except Exception:
        logger.warning(
            "quote_builder: tenant lookup failed tenant=%s — using generic business name",
            tenant_id,
            exc_info=True,
        )

    try:
        services_result = (
            tenant_table(db, "service_types", tenant_id)
            .select("name, description, price")
            .eq("is_active", True)
            .execute()
        )
        services = services_result.data or []
    except Exception:
        logger.error(
            "quote_builder: service_types lookup failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        return None

    has_catalog = bool(services)
    allowed_prices = _valid_price_set(services)

    if has_catalog:
        system_prompt = _SYSTEM_PROMPT_WITH_CATALOG.format(
            business_type=business_type or "service",
            business_name=business_name,
            catalog_text=_catalog_text(services),
        )
    else:
        system_prompt = _SYSTEM_PROMPT_NO_CATALOG.format(
            business_type=business_type or "service",
            business_name=business_name,
        )

    user_text = f"Job description: {job_description}"
    if triage:
        user_text += (
            f"\n\nPhoto triage context: urgency={triage.get('urgency')}, "
            f"category={triage.get('category')}, "
            f"scope_summary={triage.get('scope_summary')}"
        )

    try:
        result = await call_claude_messages(
            operation="quote_builder.draft",
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
            timeout=45.0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_text}],
            metadata={
                "tenant_id": tenant_id,
                "has_catalog": has_catalog,
                "service_count": len(services),
            },
        )
        raw_text = result.text
    except Exception:
        logger.error("quote_builder: LLM call failed tenant=%s", tenant_id, exc_info=True)
        return None

    cleaned = _strip_json_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "quote_builder: unparseable LLM response tenant=%s: %r",
            tenant_id,
            raw_text[:300],
        )
        return None

    if not isinstance(parsed, dict):
        logger.warning(
            "quote_builder: LLM response was not a JSON object tenant=%s", tenant_id
        )
        return None

    tiers = {
        key: _sanitize_tier(parsed.get(key), allowed_prices, has_catalog)
        for key in TIER_KEYS
    }

    row: dict[str, Any] = {
        "job_description": job_description,
        "triage": triage,
        "tiers": tiers,
        "status": "draft",
    }
    if lead_id:
        row["lead_id"] = lead_id

    try:
        created = tenant_table(db, "quotes", tenant_id).insert(row).execute()
    except Exception:
        logger.error("quote_builder: insert failed tenant=%s", tenant_id, exc_info=True)
        return None

    inserted = created.data[0] if created.data else None
    if inserted:
        logger.info(
            "quote_builder: drafted quote id=%s tenant=%s has_catalog=%s",
            inserted.get("id"),
            tenant_id,
            has_catalog,
        )
    return inserted
