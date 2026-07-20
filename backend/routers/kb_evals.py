"""Golden-question eval CRUD + run endpoints (enterprise-audit item 2).

Owner-facing management of the tenant's grounding regression suite:
questions customers ask + the phrases the compiled knowledge must contain.
Runs are deterministic (see backend/services/kb_evals.py).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import kb_evals
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kb-evals", tags=["kb-evals"])


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=kb_evals.MAX_QUESTION_LEN)
    expected_phrases: list[str] = Field(min_length=1, max_length=10)
    enabled: bool = True


class QuestionUpdate(BaseModel):
    question: str | None = Field(
        default=None, min_length=3, max_length=kb_evals.MAX_QUESTION_LEN
    )
    expected_phrases: list[str] | None = Field(
        default=None, min_length=1, max_length=10
    )
    enabled: bool | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_phrases(phrases: list[str]) -> list[str]:
    cleaned = [p.strip()[: kb_evals.MAX_PHRASE_LEN] for p in phrases if p.strip()]
    if not cleaned:
        raise HTTPException(
            status_code=422, detail="expected_phrases must contain non-empty text"
        )
    return cleaned


@router.get("/questions")
async def list_questions(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()
    rows = (
        tenant_select(db, "tenant_eval_questions", claims["tenant_id"], "*")
        .order("created_at", desc=False)
        .limit(200)
        .execute()
    ).data or []
    return {"questions": rows}


@router.post("/questions")
async def create_question(
    body: QuestionIn, claims: dict = Depends(_get_current_tenant)
):
    db = get_service_supabase()
    created = (
        tenant_table(db, "tenant_eval_questions", claims["tenant_id"])
        .insert(
            {
                "question": body.question.strip(),
                "expected_phrases": _clean_phrases(body.expected_phrases),
                "enabled": body.enabled,
            }
        )
        .execute()
    )
    return created.data[0]


@router.put("/questions/{question_id}")
async def update_question(
    question_id: str, body: QuestionUpdate, claims: dict = Depends(_get_current_tenant)
):
    db = get_service_supabase()
    payload: dict = {"updated_at": _now()}
    if body.question is not None:
        payload["question"] = body.question.strip()
    if body.expected_phrases is not None:
        payload["expected_phrases"] = _clean_phrases(body.expected_phrases)
    if body.enabled is not None:
        payload["enabled"] = body.enabled
    updated = (
        tenant_table(db, "tenant_eval_questions", claims["tenant_id"])
        .update(payload)
        .eq("id", question_id)
        .execute()
    )
    if not updated.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return updated.data[0]


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str, claims: dict = Depends(_get_current_tenant)
):
    db = get_service_supabase()
    deleted = (
        tenant_table(db, "tenant_eval_questions", claims["tenant_id"])
        .delete()
        .eq("id", question_id)
        .execute()
    )
    if not deleted.data:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"deleted": True}


@router.post("/run")
async def run_now(claims: dict = Depends(_get_current_tenant)):
    return kb_evals.run_evals(claims["tenant_id"], trigger="manual")


@router.get("/runs/latest")
async def latest_run(claims: dict = Depends(_get_current_tenant)):
    db = get_service_supabase()
    rows = (
        tenant_select(db, "tenant_eval_runs", claims["tenant_id"], "*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []
    return rows[0] if rows else None
