"""Ask-your-business analytics (suite item 2 — NL-query BI, Quick Sight analog).

Deterministic-first by design: a question is keyword-matched to one of a
fixed library of safe, tenant-scoped aggregate templates and answered with
real counts from the tenant's own tables. No free-form SQL generation, no
LLM in the numbers path — the model never gets a chance to hallucinate a
metric. Unmatched questions return the supported-question list instead of a
guess.

Templates read only tables in the schema reference (leads/conversations use
client_id via tenant_scope; appointments/invoices/chat_messages use
tenant_id).
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from backend.services.tenant_scope import tenant_select

logger = logging.getLogger(__name__)

_PERIODS = {
    "today": 1,
    "week": 7,
    "month": 30,
    "quarter": 90,
}


def _period_from(question: str) -> tuple[str, int]:
    q = question.lower()
    if "today" in q:
        return "today", 1
    if "quarter" in q or "90" in q:
        return "quarter", 90
    if "week" in q or "7 day" in q:
        return "week", 7
    return "month", 30


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _count(db, table: str, client_id: str, since: str, date_col: str = "created_at"):
    return len(
        (
            tenant_select(db, table, client_id, "id")
            .gte(date_col, since)
            .limit(1000)
            .execute()
        ).data
        or []
    )


def _leads_by_source(db, client_id: str, since: str) -> dict[str, int]:
    rows = (
        tenant_select(db, "leads", client_id, "source")
        .gte("created_at", since)
        .limit(1000)
        .execute()
    ).data or []
    counts: dict[str, int] = {}
    for row in rows:
        source = (row.get("source") or "unknown").strip() or "unknown"
        counts[source] = counts.get(source, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))


TEMPLATES: list[tuple[str, re.Pattern]] = [
    ("leads_by_source", re.compile(r"lead.*(source|from|where)|source.*lead", re.I)),
    ("lead_count", re.compile(r"how many.*lead|lead.*(count|total)|new leads", re.I)),
    (
        "appointment_count",
        re.compile(r"appointment|booking|book.*(count|many)", re.I),
    ),
    ("invoice_count", re.compile(r"invoice|billed|revenue", re.I)),
    (
        "conversation_count",
        re.compile(r"conversation|chat|message.*(count|many)|how many.*(chat|talk)", re.I),
    ),
]

SUPPORTED = [
    "How many leads did I get this month/week/today?",
    "Which sources do my leads come from?",
    "How many appointments were booked this month?",
    "How many invoices were created this month?",
    "How many conversations happened this week?",
]


def match_template(question: str) -> str | None:
    for name, pattern in TEMPLATES:
        if pattern.search(question or ""):
            return name
    return None


def answer_question(db, client_id: str, question: str) -> dict:
    """Answer one business question from real data ({} facts, never a guess)."""
    template = match_template(question)
    period_name, days = _period_from(question)
    since = _since(days)

    if template is None:
        return {
            "matched": False,
            "answer": (
                "I can answer these from your live data right now: "
                + " ".join(SUPPORTED)
            ),
            "supported_questions": SUPPORTED,
        }

    try:
        if template == "lead_count":
            count = _count(db, "leads", client_id, since)
            answer = f"You got {count} new lead(s) in the last {period_name}."
            data: dict = {"leads": count}
        elif template == "leads_by_source":
            by_source = _leads_by_source(db, client_id, since)
            total = sum(by_source.values())
            top = ", ".join(f"{k}: {v}" for k, v in list(by_source.items())[:5])
            answer = (
                f"{total} lead(s) in the last {period_name}"
                + (f" - top sources: {top}." if top else ".")
            )
            data = {"total": total, "by_source": by_source}
        elif template == "appointment_count":
            count = _count(db, "appointments", client_id, since)
            answer = f"{count} appointment(s) were created in the last {period_name}."
            data = {"appointments": count}
        elif template == "invoice_count":
            count = _count(db, "invoices", client_id, since)
            answer = f"{count} invoice(s) were created in the last {period_name}."
            data = {"invoices": count}
        else:
            count = _count(db, "conversations", client_id, since, "last_message_at")
            answer = f"{count} conversation(s) were active in the last {period_name}."
            data = {"conversations": count}
    except Exception:
        logger.warning(
            "biz_answers: template %s failed tenant=%s", template, client_id,
            exc_info=True,
        )
        return {
            "matched": True,
            "template": template,
            "answer": "I could not read that metric right now - try again shortly.",
            "error": True,
        }

    return {
        "matched": True,
        "template": template,
        "period": period_name,
        "answer": answer,
        "data": data,
    }
