"""Cold-start starter tasks — the AI staff's "here's what I can do first".

Why this exists: the Agent OS insights card hid itself for tenants with no
week activity and no proactive suggestions, so a brand-new owner saw only a
blank composer. The model-call ledger (os_model_call_log) showed 16 drafts
ever across all tenants — the engine works, activation is the bottleneck.
These starters give an idle owner three one-click first tasks, personalized
from whatever real data they already have.

Deterministic-first: cheap count queries + the tenants profile row, no LLM.
Schema notes: leads use client_id; appointments use tenant_id
(see .claude/rules/schema-discipline.md).

WARNING: imported by a FastAPI router — do NOT add
``from __future__ import annotations`` here.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_STARTER_COUNT = 3


def _count(db: Any, table: str, tenant_col: str, client_id: str) -> int:
    """Cheap head-count for one tenant-scoped table. 0 on any failure."""
    try:
        r = (
            db.table(table)
            .select("id", count="exact")
            .eq(tenant_col, client_id)
            .limit(1)
            .execute()
        )
        return r.count or 0
    except Exception:
        logger.warning(
            "starter_tasks: %s count failed for %s", table, client_id, exc_info=True
        )
        return 0


def _business_type(db: Any, client_id: str) -> str:
    """tenants.business_type or '' — never raises."""
    try:
        rows = (
            db.table("tenants")
            .select("business_type")
            .eq("id", client_id)
            .limit(1)
            .execute()
        ).data or []
        return (rows[0].get("business_type") or "").strip() if rows else ""
    except Exception:
        logger.warning(
            "starter_tasks: profile read failed for %s", client_id, exc_info=True
        )
        return ""


def compute_starter_tasks(db: Any, client_id: str) -> list[dict[str, str]]:
    """Exactly 3 {"label", "prompt"} starters for an idle tenant.

    Data-aware starters come first (leads on file -> follow-up; appointments
    on file -> reminders), then generic ones personalized on business_type
    fill to 3. Never raises; total failure still returns the 3 generics.
    """
    biz = _business_type(db, client_id)
    biz_phrase = biz.replace("_", " ") if biz else "business"

    starters: list[dict[str, str]] = []

    if _count(db, "leads", "client_id", client_id) > 0:
        starters.append(
            {
                "label": "Follow up with your leads",
                "prompt": (
                    "Draft a friendly follow-up message for my most recent "
                    "leads who haven't replied yet."
                ),
            }
        )

    if _count(db, "appointments", "tenant_id", client_id) > 0:
        starters.append(
            {
                "label": "Remind upcoming appointments",
                "prompt": "Draft reminder texts for my upcoming appointments.",
            }
        )

    generics = [
        {
            "label": "Ask happy customers for reviews",
            "prompt": (
                "Write a short, friendly text I can send to happy customers "
                f"of my {biz_phrase} asking for a Google review."
            ),
        },
        {
            "label": "Draft a promo message",
            "prompt": (
                "Draft a short promotional message I can send to my "
                f"{biz_phrase} customers about a limited-time offer."
            ),
        },
        {
            "label": "Welcome new customers",
            "prompt": (
                "Write a warm welcome message to send new customers of my "
                f"{biz_phrase} after their first visit."
            ),
        },
    ]
    for g in generics:
        if len(starters) >= _STARTER_COUNT:
            break
        starters.append(g)

    return starters[:_STARTER_COUNT]
