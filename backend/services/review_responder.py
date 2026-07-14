"""Reviews AI — approval-gated AI review responses.

GoHighLevel AI Employee parity: draft an AI reply to a customer review and
hold it for human approval before it is ever posted anywhere. Mirrors the
approval-gated shape of `backend/services/os_sms_approval.py` — the AI only
proposes (see `.claude/rules/propose-only-records.md`), a human approves,
and posting to the external platform is a separate, not-yet-implemented step.

Schema: migrations/168_review_responses.sql — `review_responses` table,
`tenant_id` scoped (standard column, not the leads-table `client_id` pattern).

Invariant: there is NO code path in this module that posts a response
anywhere. `approve_response` only flips status draft -> approved. Actually
publishing the reply to Google/Yelp/etc. is `post_response_stub` below,
which raises NotImplementedError and is never called from the approve path.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_VALID_STATUSES = {"draft", "approved", "posted", "rejected"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tone_instruction(rating: int) -> str:
    """House-voice tone guidance keyed off the review rating."""
    if rating <= 2:
        return (
            "This is a low rating. Apologize sincerely, acknowledge the specific "
            "issue raised, and offer a concrete path to make it right (contact "
            "info, a fix, or a refund/credit if one is implied). Do not be "
            "defensive and do not make excuses."
        )
    if rating == 3:
        return (
            "This is a mixed rating. Thank the reviewer, acknowledge what fell "
            "short without being defensive, and note the intent to improve."
        )
    return (
        "This is a high rating. Be genuinely gracious, thank the reviewer by "
        "name if one is given, and invite them back."
    )


async def draft_response(
    db: Any,
    *,
    tenant_id: str,
    review: dict[str, Any],
) -> dict[str, Any] | None:
    """Draft an AI reply to a customer review and store it as status='draft'.

    `review` keys:
      review_text (str, required)
      review_rating (int 1-5, required) — drives tone
      review_id (uuid str, optional) — set when the review already exists in
        the `reviews` table
      external_ref (str, optional) — set when the review comes from an
        external platform and has no `reviews` row yet

    Fault-tolerant: never raises. Returns the inserted review_responses row,
    or None if input is invalid or any step fails (logged either way).
    """
    review_text = (review.get("review_text") or "").strip()
    raw_rating = review.get("review_rating")
    if not review_text or raw_rating is None:
        logger.warning(
            "review_responder: missing review_text or review_rating tenant=%s",
            tenant_id,
        )
        return None
    try:
        rating = int(raw_rating)
    except (TypeError, ValueError):
        logger.warning(
            "review_responder: non-numeric review_rating=%r tenant=%s",
            raw_rating,
            tenant_id,
        )
        return None
    if not 1 <= rating <= 5:
        logger.warning(
            "review_responder: review_rating out of range=%s tenant=%s",
            rating,
            tenant_id,
        )
        return None

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
            "review_responder: tenant lookup failed tenant=%s — using generic business name",
            tenant_id,
            exc_info=True,
        )

    system_prompt = (
        f"You are drafting a review response for {business_name}"
        f"{f', a {business_type}' if business_type else ''}. "
        "Write in a direct, professional house voice: no marketing language, "
        "no exclamation-point enthusiasm, no generic template phrasing. "
        "Keep it to 2-4 sentences. "
        f"{_tone_instruction(rating)} "
        "This is a draft a human will review before anything is posted — "
        "write the actual reply text, not a placeholder or explanation of "
        "what you would write."
    )

    try:
        result = await call_claude_messages(
            operation="review_responder.draft",
            model="claude-sonnet-4-6",
            max_tokens=300,
            temperature=0.7,
            timeout=30.0,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Customer review ({rating}/5 stars):\n\n{review_text}",
                }
            ],
            metadata={"tenant_id": tenant_id, "rating": rating},
        )
        draft_reply = result.text.strip()
    except Exception:
        logger.error(
            "review_responder: draft generation failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        return None

    if not draft_reply:
        logger.warning(
            "review_responder: empty draft returned tenant=%s",
            tenant_id,
        )
        return None

    row: dict[str, Any] = {
        "review_text": review_text,
        "review_rating": rating,
        "draft_reply": draft_reply,
        "status": "draft",
    }
    if review.get("review_id"):
        row["review_id"] = review["review_id"]
    if review.get("external_ref"):
        row["external_ref"] = review["external_ref"]

    try:
        created = tenant_table(db, "review_responses", tenant_id).insert(row).execute()
    except Exception:
        logger.error(
            "review_responder: insert failed tenant=%s",
            tenant_id,
            exc_info=True,
        )
        return None

    inserted = created.data[0] if created.data else None
    if inserted:
        logger.info(
            "review_responder: drafted response id=%s tenant=%s rating=%s",
            inserted.get("id"),
            tenant_id,
            rating,
        )
    return inserted


async def _flip_status(
    db: Any,
    *,
    tenant_id: str,
    response_id: str,
    approver: str,
    new_status: str,
    action_label: str,
) -> dict[str, Any] | None:
    """Shared draft -> {approved,rejected} transition. Only 'draft' rows are
    eligible — this is what makes the approval gate a real gate rather than
    a status label anyone can flip at any time.
    """
    try:
        existing = (
            tenant_table(db, "review_responses", tenant_id)
            .select("*")
            .eq("id", response_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.error(
            "review_responder: %s lookup failed tenant=%s id=%s",
            action_label,
            tenant_id,
            response_id,
            exc_info=True,
        )
        return None

    rows = existing.data or []
    if not rows:
        logger.warning(
            "review_responder: %s target not found tenant=%s id=%s",
            action_label,
            tenant_id,
            response_id,
        )
        return None

    current = rows[0]
    if current.get("status") != "draft":
        logger.warning(
            "review_responder: %s blocked — status=%s not 'draft' tenant=%s id=%s",
            action_label,
            current.get("status"),
            tenant_id,
            response_id,
        )
        return None

    update_fields: dict[str, Any] = {
        "status": new_status,
        "approved_by": approver,
        "updated_at": _now(),
    }
    if new_status == "approved":
        update_fields["approved_at"] = _now()

    try:
        updated = (
            tenant_table(db, "review_responses", tenant_id)
            .update(update_fields)
            .eq("id", response_id)
            .execute()
        )
    except Exception:
        logger.error(
            "review_responder: %s update failed tenant=%s id=%s",
            action_label,
            tenant_id,
            response_id,
            exc_info=True,
        )
        return None

    result = updated.data[0] if updated.data else None
    if result:
        logger.info(
            "review_responder: %s id=%s tenant=%s approver=%s",
            action_label,
            response_id,
            tenant_id,
            approver,
        )
    return result


async def approve_response(
    db: Any,
    *,
    tenant_id: str,
    response_id: str,
    approver: str,
) -> dict[str, Any] | None:
    """Approve a pending draft. Flips status draft -> approved.

    Approval NEVER posts the response anywhere — it only records the human
    decision. Actually publishing the reply is a separate, not-yet-built
    step (`post_response_stub`). Never raises.
    """
    return await _flip_status(
        db,
        tenant_id=tenant_id,
        response_id=response_id,
        approver=approver,
        new_status="approved",
        action_label="approve",
    )


async def reject_response(
    db: Any,
    *,
    tenant_id: str,
    response_id: str,
    approver: str,
) -> dict[str, Any] | None:
    """Reject a pending draft. Flips status draft -> rejected. Never raises."""
    return await _flip_status(
        db,
        tenant_id=tenant_id,
        response_id=response_id,
        approver=approver,
        new_status="rejected",
        action_label="reject",
    )


def post_response_stub(*_args: Any, **_kwargs: Any) -> None:
    """TODO — NOT IMPLEMENTED. Extension point for posting an approved
    response to the external review platform (Google Business Profile,
    Yelp, etc.).

    This project already has an OAuth scaffold for Google Business Profile
    ("GBP OAuth: scaffold built, awaiting credentials" — see
    docs/dev-knowledge/architecture-decisions.md) that a real implementation
    of this function would build on once credentials are configured.

    No code path in this module calls this function. `approve_response()`
    only flips status to 'approved' — it never posts. When this is wired up,
    it must still only ever act on a row whose status is already 'approved'
    (never post a 'draft' directly) and should flip status to 'posted' on
    success, preserving the approval gate end to end.
    """
    raise NotImplementedError(
        "review_responder.post_response_stub is not implemented. Posting to "
        "external review platforms requires platform API credentials and is "
        "out of scope for the approval-gated drafts loop."
    )
