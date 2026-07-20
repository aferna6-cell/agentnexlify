"""Golden-question eval harness (enterprise-audit item 2).

Deterministic grounding checks for the widget bot: each enabled question
carries the phrases the tenant's compiled knowledge MUST contain for the bot
to answer it. A question passes when every expected phrase appears
(case-insensitive) in the grounding corpus — widget_configs.knowledge_base
plus faq_entries — which is exactly the text build_chat_context feeds the
model, so corpus presence is the right proxy for "the bot can answer this".

A REGRESSION is a question that passed on the previous run and fails now
(a deleted doc, a bad compile, an FAQ edit). Regressions land in
activity_log as ``kb_eval_regression`` so the digest and dashboard surface
them without polling.

Deterministic-first by design: no LLM judge, no token spend, safe to run on
every KB compile.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

_QUESTION_CAP = 50
_MAX_PHRASES = 10
MAX_QUESTION_LEN = 500
MAX_PHRASE_LEN = 200


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def grounding_corpus(db, client_id: str) -> str:
    """The tenant's compiled widget knowledge, lowercased for matching."""
    parts: list[str] = []
    try:
        widget_rows = (
            db.table("widget_configs")
            .select("knowledge_base")
            .eq("tenant_id", client_id)
            .limit(1)
            .execute()
        ).data or []
        if widget_rows:
            parts.append(str(widget_rows[0].get("knowledge_base") or ""))
    except Exception:
        logger.warning(
            "kb_evals: widget_configs read failed tenant=%s", client_id, exc_info=True
        )
    try:
        faq_rows = (
            db.table("faq_entries")
            .select("question, answer")
            .eq("tenant_id", client_id)
            .limit(200)
            .execute()
        ).data or []
        for row in faq_rows:
            parts.append(str(row.get("question") or ""))
            parts.append(str(row.get("answer") or ""))
    except Exception:
        logger.warning(
            "kb_evals: faq_entries read failed tenant=%s", client_id, exc_info=True
        )
    return "\n".join(parts).lower()


def evaluate_question(corpus: str, question_row: dict) -> dict:
    """One question's result: pass iff every expected phrase is grounded."""
    phrases = [
        str(p) for p in (question_row.get("expected_phrases") or []) if str(p).strip()
    ]
    missing = [p for p in phrases if p.lower() not in corpus]
    return {
        "question_id": question_row.get("id"),
        "question": question_row.get("question"),
        "passed": not missing and bool(phrases),
        "missing_phrases": missing,
    }


def _previous_outcomes(db, client_id: str) -> dict[str, bool]:
    """question_id -> passed from the most recent run (empty on none)."""
    try:
        runs = (
            tenant_select(db, "tenant_eval_runs", client_id, "results")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "kb_evals: previous run read failed tenant=%s", client_id, exc_info=True
        )
        return {}
    if not runs:
        return {}
    outcomes: dict[str, bool] = {}
    for result in runs[0].get("results") or []:
        if isinstance(result, dict) and result.get("question_id"):
            outcomes[str(result["question_id"])] = bool(result.get("passed"))
    return outcomes


def run_evals(client_id: str, trigger: str = "manual") -> dict:
    """Run every enabled question; persist a run row; alert on regressions.

    Returns the run summary (also persisted). Never raises — the KB-compile
    hook calls this best-effort and a broken eval must not break a compile.
    """
    db = get_service_supabase()
    try:
        questions = (
            tenant_select(db, "tenant_eval_questions", client_id, "*")
            .eq("enabled", True)
            .limit(_QUESTION_CAP)
            .execute()
        ).data or []
    except Exception:
        logger.warning(
            "kb_evals: question read failed tenant=%s", client_id, exc_info=True
        )
        return {"total": 0, "passed": 0, "failed": 0, "regressions": 0, "results": []}

    corpus = grounding_corpus(db, client_id)
    previous = _previous_outcomes(db, client_id)

    results = [evaluate_question(corpus, q) for q in questions]
    regressions = [
        r
        for r in results
        if not r["passed"] and previous.get(str(r.get("question_id"))) is True
    ]
    summary = {
        "trigger": trigger,
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "regressions": len(regressions),
        "results": results,
    }

    try:
        tenant_table(db, "tenant_eval_runs", client_id).insert(
            {**summary, "created_at": _now()}
        ).execute()
    except Exception:
        logger.warning(
            "kb_evals: run persist failed tenant=%s", client_id, exc_info=True
        )

    if regressions:
        log_activity(
            tenant_id=client_id,
            activity_type="kb_eval_regression",
            description=(
                f"{len(regressions)} golden question(s) stopped passing after "
                "the latest knowledge update"
            ),
            metadata={
                "trigger": trigger,
                "questions": [r["question"] for r in regressions][:10],
            },
        )
    return summary


def run_evals_after_compile(client_id: str) -> None:
    """Best-effort post-compile hook — never raises into the compile path."""
    try:
        run_evals(client_id, trigger="kb_compile")
    except Exception:
        logger.warning(
            "kb_evals: post-compile run failed tenant=%s", client_id, exc_info=True
        )
