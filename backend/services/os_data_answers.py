"""Deterministic data answers inside the workforce chat (round-3 item 2).

A typed owner ask like "how many leads this week?" used to burn a full
engine turn that could hallucinate a number. When the ask matches one of
the biz_answers templates, this fast path answers straight from the
tenant's own tables - instant, token-free, and every figure is real - and
the engine is never invoked for that turn.

Guardrails: only interactive typed asks take the fast path. Scheduled-task
and project-step prompts pass ``force_agent_id`` and always reach the
engine, as do long messages (the templates target short data questions).
Any failure returns None and the normal engine turn proceeds.
"""

import logging
from datetime import datetime, timezone

from fastapi.concurrency import run_in_threadpool

from backend.services import biz_answers
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_MAX_DATA_QUESTION_LEN = 160


async def try_data_answer(
    db, client_id: str, thread_id: str, user_message_row: dict
) -> dict | None:
    """Answer a matching data question deterministically, or None."""
    content = str(user_message_row.get("content") or "").strip()
    if not content or len(content) > _MAX_DATA_QUESTION_LEN:
        return None
    if biz_answers.match_template(content) is None:
        return None

    try:
        result = await run_in_threadpool(
            biz_answers.answer_question, db, client_id, content
        )
    except Exception:
        logger.warning(
            "os_data_answers: answer failed client_id=%s", client_id, exc_info=True
        )
        return None
    if not result.get("matched") or result.get("error"):
        return None

    reply = (
        f"{result['answer']}\n\n"
        "(Answered directly from your live business data.)"
    )
    try:
        assistant_message = (
            tenant_table(db, "os_messages", client_id)
            .insert(
                {"thread_id": thread_id, "role": "assistant", "content": reply}
            )
            .execute()
            .data[0]
        )
        tenant_table(db, "os_threads", client_id).update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", thread_id).execute()
    except Exception:
        logger.warning(
            "os_data_answers: persist failed client_id=%s", client_id, exc_info=True
        )
        return None

    try:
        from backend.services.activity import log_activity

        log_activity(
            tenant_id=client_id,
            activity_type="os_fast_path_data_answer",
            description=f"Chat BI fast path: {result.get('template') or 'template'}",
        )
    except Exception:
        logger.warning("os_data_answers: usage log failed", exc_info=True)

    return {
        "user_message": user_message_row,
        "assistant_message": assistant_message,
        "action": "answer",
        "agent_runs": [],
        "data_answer": True,
        "template": result.get("template"),
    }
