"""Paginated lead listing query builder.

Extracted from `backend/routers/leads.py` to keep the router under the
600-line god-class threshold. Owns the search-sanitization, sort-allowlist,
filter-application, and pagination math for the leads index endpoint.
Router still owns auth + HTTP-shape concerns.
"""

import logging
import re
from typing import Any

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

ALLOWED_SORT_COLUMNS = {
    "lead_score", "created_at", "name", "email", "status", "updated_at",
}
DEFAULT_SORT = "lead_score"
DEFAULT_SELECT = (
    "id, client_id, name, email, phone, status, lead_score, lead_temperature, "
    "areas_of_interest, tags, assigned_to, deal_value, created_at, updated_at, "
    "enrichment_source"
)
SEARCH_ALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9@_ \-+.]")
SEARCH_MAX_LEN = 100


def list_leads_paginated(
    db: Any,
    tenant_id: str,
    *,
    stage: str | None = None,
    search: str | None = None,
    sort: str = DEFAULT_SORT,
    order: str = "desc",
    assigned_to: str | None = None,
    page: int = 1,
    per_page: int = 100,
) -> dict:
    """Run paginated leads query, return {leads, total, page, per_page, total_pages}.

    Raises:
        RuntimeError("query_failed"): Supabase query raised. Router maps to 503.
    """
    sort_col = sort if sort in ALLOWED_SORT_COLUMNS else DEFAULT_SORT

    try:
        query = tenant_select(
            db, "leads", tenant_id, DEFAULT_SELECT, count="exact",
        )

        if stage:
            query = query.eq("status", stage)

        if assigned_to:
            if assigned_to == "unassigned":
                query = query.is_("assigned_to", "null")
            else:
                query = query.eq("assigned_to", assigned_to)

        if search:
            safe_search = SEARCH_ALLOWED_CHARS.sub("", search).strip()[:SEARCH_MAX_LEN]
            if safe_search:
                query = query.or_(
                    f"name.ilike.%{safe_search}%,"
                    f"email.ilike.%{safe_search}%,"
                    f"phone.ilike.%{safe_search}%"
                )

        desc = order.lower() == "desc"
        query = query.order(sort_col, desc=desc)

        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1)

        result = query.execute()
        total = result.count if result.count is not None else len(result.data or [])
        return {
            "leads": result.data or [],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total else 1,
        }
    except Exception:
        logger.warning(
            "Leads query failed for tenant %s", tenant_id, exc_info=True,
        )
        raise RuntimeError("query_failed")
