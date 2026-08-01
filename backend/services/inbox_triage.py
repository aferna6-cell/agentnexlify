"""Inbound-email AI triage — classify, draft, auto-send/escalate.

Runs after ``os_inbound_bridge.bridge_email`` has already persisted the
inbound message as an ``os_message`` (bridge owns idempotency). This module
only decides what happens NEXT with a message that was actually bridged:

  spam        -> tag the thread, stop (no LLM draft, no send)
  info_only   -> tag the thread, stop (nothing to answer)
  answerable  -> draft a grounded reply (support_agent pattern); auto-send
                 when the tenant opted in AND confidence clears the bar,
                 otherwise store as a pending_approval deliverable on the
                 OS thread (same shape the dashboard's Deliverables UI
                 already renders/approves/rejects)
  escalate    -> hand off via the escalations lane

Drafts-only is the default: auto-send requires an explicit tenant opt-in
via ``tenants.os_auto_send_rules['inbox']`` (or the global
``os_auto_send_enabled`` flag), checked through the SAME
``agent_os_bridge.resolve_deliverable_status`` gate the engine's own
deliverables use — no parallel approval mechanism.
"""

import html as html_lib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.services import gmail_connector, support_agent
from backend.services.agent_os_bridge import resolve_deliverable_status
from backend.services.llm_runtime import call_claude_messages
from backend.services.tenant_scope import tenant_table

logger = logging.getLogger(__name__)

_AGENT_NAME = "inbox_triage"
_ACTION_TYPE = "gmail.reply"

CATEGORIES = frozenset({"spam", "info_only", "answerable", "escalate"})

# Below this combined (classify x draft) confidence, an "answerable" message
# never auto-sends even if the tenant opted in — it always lands as a
# pending_approval draft instead.
CONFIDENCE_THRESHOLD = 0.75

_CLASSIFY_MODEL = "claude-haiku-4-5-20251001"
_DRAFT_MODEL = "claude-haiku-4-5-20251001"

_CLASSIFY_SYSTEM = """\
You triage one inbound customer email for a small business inbox. Classify
it into exactly one category:

- spam: unsolicited marketing, phishing, or obviously irrelevant mail.
- info_only: no reply needed (receipt, notification, FYI, thank-you with
  no question).
- answerable: a real customer question or request this business's staff
  or knowledge base can likely answer directly.
- escalate: anything sensitive, urgent, angry/complaint, legal/payment
  dispute, or where a wrong automated reply could hurt the business —
  a human should see this before anything goes out.

Return STRICT JSON: {"category": "...", "confidence": 0.0-1.0, "reason":
"short reason"}. When uncertain between answerable and escalate, prefer
escalate.\
"""

_CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "enum": ["spam", "info_only", "answerable", "escalate"],
        },
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["category", "confidence"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def triage_inbound_email(
    db: Any, *, tenant: str, parsed_email: dict, os_thread_id: str
) -> dict[str, Any]:
    """Classify + act on one bridged inbound email. Never raises.

    ``tenant`` is the client_id (tenant_id) that owns this Gmail inbox.
    ``parsed_email`` is a ``ParsedEmail``-shaped dict (see
    ``inbound_email_parser.ParsedEmail``). Returns a structured result dict
    describing what happened — {category, action, confidence, ...}.
    """
    client_id = tenant
    try:
        classification = await _classify(parsed_email)
    except Exception:
        logger.exception("inbox_triage: classify failed client_id=%s", client_id)
        escalation = _create_escalation_safe(
            db,
            client_id=client_id,
            source_ref=parsed_email.get("provider_message_id", ""),
            os_thread_id=os_thread_id,
            reason="triage_classification_failed",
        )
        return {
            "category": "escalate",
            "action": "escalated",
            "confidence": 0.0,
            "reason": "classification_failed",
            "escalation": escalation,
        }

    category = classification["category"]
    confidence = classification["confidence"]

    if category == "spam":
        _tag_thread(db, client_id, os_thread_id, "spam")
        return {"category": "spam", "action": "tagged", "confidence": confidence}

    if category == "info_only":
        _tag_thread(db, client_id, os_thread_id, "info_only")
        return {"category": "info_only", "action": "tagged", "confidence": confidence}

    if category == "escalate":
        escalation = _create_escalation_safe(
            db,
            client_id=client_id,
            source_ref=parsed_email.get("provider_message_id", ""),
            os_thread_id=os_thread_id,
            reason=classification.get("reason") or "triage_flagged_escalate",
        )
        return {
            "category": "escalate",
            "action": "escalated",
            "confidence": confidence,
            "escalation": escalation,
        }

    # answerable
    return await _handle_answerable(db, client_id, parsed_email, os_thread_id, confidence)


async def _handle_answerable(
    db: Any,
    client_id: str,
    parsed_email: dict,
    os_thread_id: str,
    classify_confidence: float,
) -> dict[str, Any]:
    try:
        draft = await _draft_reply(client_id, parsed_email)
    except Exception:
        logger.exception("inbox_triage: draft failed client_id=%s", client_id)
        escalation = _create_escalation_safe(
            db,
            client_id=client_id,
            source_ref=parsed_email.get("provider_message_id", ""),
            os_thread_id=os_thread_id,
            reason="triage_draft_failed",
        )
        return {
            "category": "answerable",
            "action": "escalated",
            "confidence": classify_confidence,
            "escalation": escalation,
        }

    if draft.get("escalate_reason"):
        escalation = _create_escalation_safe(
            db,
            client_id=client_id,
            source_ref=parsed_email.get("provider_message_id", ""),
            os_thread_id=os_thread_id,
            reason=draft["escalate_reason"],
        )
        return {
            "category": "answerable",
            "action": "escalated",
            "confidence": classify_confidence,
            "escalation": escalation,
        }

    draft_confidence = _confidence_to_float(draft.get("confidence"))
    overall_confidence = min(classify_confidence, draft_confidence)

    subject = _reply_subject(parsed_email.get("subject") or "")
    references = (parsed_email.get("headers") or {}).get("references", "")
    deliverable = {
        "title": subject,
        "body": draft["answer"],
        "channel": "email",
        "metadata": {
            "gmail_thread_id": parsed_email.get("thread_id") or "",
            "in_reply_to": parsed_email.get("provider_message_id") or "",
            "references": references,
            "to": parsed_email.get("sender_email") or "",
            "subject": subject,
        },
    }

    auto_send_ok = overall_confidence >= CONFIDENCE_THRESHOLD
    deliverable_status = resolve_deliverable_status(
        db, client_id, _AGENT_NAME, requires_approval=not auto_send_ok
    )

    run_row = {
        "thread_id": os_thread_id,
        "agent_name": _AGENT_NAME,
        "status": "succeeded",
        "deliverable": deliverable,
        "deliverable_status": deliverable_status,
        "action_type": _ACTION_TYPE,
        "completed_at": _now_iso(),
    }
    try:
        agent_run = (
            tenant_table(db, "os_agent_runs", client_id).insert(run_row).execute().data[0]
        )
    except Exception:
        logger.exception(
            "inbox_triage: failed to persist deliverable client_id=%s", client_id
        )
        escalation = _create_escalation_safe(
            db,
            client_id=client_id,
            source_ref=parsed_email.get("provider_message_id", ""),
            os_thread_id=os_thread_id,
            reason="triage_deliverable_persist_failed",
        )
        return {
            "category": "answerable",
            "action": "escalated",
            "confidence": overall_confidence,
            "escalation": escalation,
        }

    if deliverable_status != "approved":
        return {
            "category": "answerable",
            "action": "drafted",
            "confidence": overall_confidence,
            "agent_run_id": agent_run["id"],
        }

    send_result = gmail_connector.send_reply(
        db,
        client_id,
        thread_id=deliverable["metadata"]["gmail_thread_id"],
        to=deliverable["metadata"]["to"],
        subject=deliverable["metadata"]["subject"],
        body_html=_body_to_html(deliverable["body"]),
        in_reply_to=deliverable["metadata"]["in_reply_to"],
        references=deliverable["metadata"]["references"],
    )
    _log_action_run(db, client_id, agent_run["id"], send_result)

    return {
        "category": "answerable",
        "action": "sent" if send_result.get("success") else "send_failed",
        "confidence": overall_confidence,
        "agent_run_id": agent_run["id"],
        "send_result": send_result,
    }


async def _classify(parsed_email: dict) -> dict[str, Any]:
    subject = (parsed_email.get("subject") or "")[:300]
    body = (parsed_email.get("body_text") or "")[:4000]
    sender = parsed_email.get("sender_email") or "(unknown sender)"

    result = await call_claude_messages(
        operation="inbox_triage_classify",
        model=_CLASSIFY_MODEL,
        max_tokens=300,
        system=_CLASSIFY_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"From: {sender}\nSubject: {subject}\n\n{body}",
            }
        ],
        response_schema=_CLASSIFY_SCHEMA,
        metadata={"stage": "inbox_triage_classify"},
    )
    data = json.loads(result.text)
    category = data.get("category")
    if category not in CATEGORIES:
        category = "escalate"
    return {
        "category": category,
        "confidence": _confidence_to_float(data.get("confidence")),
        "reason": str(data.get("reason") or "")[:300],
    }


async def _draft_reply(client_id: str, parsed_email: dict) -> dict[str, Any]:
    """Draft a grounded reply using the support_agent prompt-build + reply-
    parse contract (tenant business context + KB/FAQ + answer/confidence/
    escalate_reason), without spinning up a full Managed Agent session —
    inbox triage runs unattended and needs to stay cheap."""
    customer_question = (parsed_email.get("body_text") or "").strip()
    if not customer_question:
        customer_question = f"(no body) Subject: {parsed_email.get('subject') or ''}"

    prompt = support_agent.build_support_prompt(client_id, customer_question)

    result = await call_claude_messages(
        operation="inbox_triage_draft",
        model=_DRAFT_MODEL,
        max_tokens=700,
        system=(
            "You draft an email reply on behalf of a small business, grounded "
            "ONLY in the tenant context/KB/FAQ provided. If you cannot answer "
            "confidently from that context, set escalate_reason instead of "
            "guessing. Respond with JSON: answer, confidence "
            "(high/medium/low), escalate_reason (string or null)."
        ),
        messages=[{"role": "user", "content": prompt}],
        metadata={"client_id_present": bool(client_id)},
    )
    return support_agent.parse_support_reply(result.text)


def _confidence_to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "high":
            return 0.9
        if lowered == "medium":
            return 0.6
        if lowered == "low":
            return 0.3
    return 0.5


def _reply_subject(original_subject: str) -> str:
    original_subject = original_subject.strip()
    if not original_subject:
        return "Re: your message"
    if original_subject.lower().startswith("re:"):
        return original_subject
    return f"Re: {original_subject}"


def _body_to_html(body: str) -> str:
    """Deterministic plain-text -> HTML: escape, blank lines split paragraphs."""
    paragraphs = [p.strip() for p in (body or "").split("\n\n") if p.strip()]
    if not paragraphs:
        return f"<p>{html_lib.escape(body or '')}</p>"
    return "".join(
        "<p>" + html_lib.escape(p).replace("\n", "<br>") + "</p>" for p in paragraphs
    )


def _tag_thread(db: Any, client_id: str, os_thread_id: str, category: str) -> None:
    """Best-effort: merge a triage_category tag onto the thread's
    source_metadata. Never raises — a tagging failure must not block the
    poll loop."""
    try:
        existing = (
            tenant_table(db, "os_threads", client_id)
            .select("source_metadata")
            .eq("id", os_thread_id)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        meta = dict((rows[0].get("source_metadata") or {}) if rows else {})
        meta["triage_category"] = category
        tenant_table(db, "os_threads", client_id).update(
            {"source_metadata": meta}
        ).eq("id", os_thread_id).execute()
    except Exception:
        logger.warning(
            "inbox_triage: tag_thread failed client_id=%s os_thread_id=%s",
            client_id,
            os_thread_id,
            exc_info=True,
        )


def _log_action_run(
    db: Any, client_id: str, deliverable_id: str, send_result: dict[str, Any]
) -> None:
    """Best-effort audit row so an auto-sent reply shows up in the same
    os_action_runs history the dashboard's approve-flow writes to."""
    try:
        status = "succeeded" if send_result.get("success") else "failed"
        row: dict[str, Any] = {
            "deliverable_id": deliverable_id,
            "action_type": _ACTION_TYPE,
            "status": status,
            "request_payload": {},
            "response_payload": send_result if status == "succeeded" else None,
            "error_detail": None if status == "succeeded" else {"message": send_result.get("detail")},
            "started_at": _now_iso(),
            "finished_at": _now_iso(),
        }
        result = (
            tenant_table(db, "os_action_runs", client_id).insert(row).execute().data[0]
        )
        tenant_table(db, "os_agent_runs", client_id).update(
            {"action_run_id": result["id"], "updated_at": _now_iso()}
        ).eq("id", deliverable_id).execute()
    except Exception:
        logger.warning(
            "inbox_triage: failed to log action run client_id=%s deliverable_id=%s",
            client_id,
            deliverable_id,
            exc_info=True,
        )


def _create_escalation_safe(
    db: Any,
    *,
    client_id: str,
    source_ref: str,
    os_thread_id: str,
    reason: str,
    priority: str = "normal",
) -> dict | None:
    """Best-effort call into the escalations lane's ``create_escalation``.

    Lazy-imported at call time so this module (and its tests) load and run
    independently of whether ``backend.services.escalations`` has landed
    yet from its own lane. Tests monkeypatch THIS wrapper directly rather
    than the underlying import.
    """
    try:
        from backend.services.escalations import create_escalation
    except ImportError:
        logger.warning(
            "inbox_triage: escalations module unavailable; skipping escalation "
            "record client_id=%s",
            client_id,
        )
        return None
    try:
        return create_escalation(
            db,
            client_id=client_id,
            source="email",
            source_ref=source_ref,
            os_thread_id=os_thread_id,
            reason=reason,
            priority=priority,
        )
    except Exception:
        logger.exception("inbox_triage: create_escalation raised client_id=%s", client_id)
        return None
