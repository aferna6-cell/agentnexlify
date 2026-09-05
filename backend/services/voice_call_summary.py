"""AI call summary, action-item extraction, and live-call finalization.

Extracted from backend/routers/calls.py (god-file split, 2026-06). These run
as background tasks after voice webhooks respond, so nothing here may block
or raise into a webhook path — every external step degrades gracefully.

Claude spend is metered like widget extract_tags: reserve → provider →
record, or release on provider / record-persist failure. Tenant/policy
load failure fails closed here (no provider call). A later reserve RPC
outage is different: reserve_ai_tokens returns allowed=True / reason=
guard_unavailable and this helper may still call the provider without
persisting usage.

Live-AI finalize and /voice/transcription-complete can both target the
same calls.id. A compare-and-swap on calls.summary claims the slot
before reserve/provider so two delivery paths cannot create two paid
summaries. Separate call ids still account independently.
"""

import json
import logging
import re
from typing import Any

from backend.models.database import get_service_supabase
from backend.services.activity import log_activity
from backend.services.ai_usage_guard import (
    estimate_widget_chat_tokens,
    record_ai_usage,
    release_ai_token_reservation,
    reserve_ai_tokens,
)
from backend.services.llm_runtime import (
    call_claude_messages,
    resolve_int_setting,
    resolve_string_setting,
)

logger = logging.getLogger(__name__)

SUMMARY_OPERATION = "calls.generate_summary"
# Claim written before the provider so a second trigger cannot also pay.
SUMMARY_CLAIM = "AI summary generating..."
# Pre-summary strings written by incoming / finalize / transcription /
# recording-complete. These are claimable. The claim marker itself is not.
_PRE_SUMMARY_PLACEHOLDERS = frozenset(
    {
        "AI conversation in progress.",
        "AI conversation completed. Summary generating...",
        "Transcription received. AI summary generating...",
        "Voicemail recorded. Transcription pending.",
    }
)


def _summary_max_tokens() -> int:
    return max(600, resolve_int_setting("voice_chat_max_tokens", 160) * 3)


def _is_pre_summary_placeholder(value: Any) -> bool:
    text = "" if value is None else str(value).strip()
    return text == "" or text in _PRE_SUMMARY_PLACEHOLDERS


def should_skip_summary_generation(value: Any) -> bool:
    """True when a real summary exists or another path already claimed."""
    text = "" if value is None else str(value).strip()
    if _is_pre_summary_placeholder(text):
        return False
    return bool(text)


def _load_summary_budget_tenant(db: Any, tenant_id: str) -> dict[str, Any] | None:
    """Load the tenant row needed for a pack-aware reservation.

    Returns None when the row is missing or the lookup throws. Callers must
    fail closed before the provider — do not invent a free-plan cap (that
    would falsely block a paying tenant or ignore purchased packs) and do
    not call Claude unmetered.
    """
    try:
        rows = (
            db.table("tenants")
            .select(
                "id, plan, ai_monthly_token_alert_threshold, ai_monthly_token_hard_limit"
            )
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        # Do not attach the lookup exception: it may contain connection or
        # customer context. Tenant id is enough to find the row.
        logger.warning(
            "call summary: tenant load failed tenant=%s",
            tenant_id,
        )
        return None
    if not rows:
        logger.warning(
            "call summary: tenant missing tenant=%s — failing closed before provider",
            tenant_id,
        )
        return None
    return {**rows[0], "id": tenant_id}


def _claim_call_summary_slot(db: Any, call_id: str, tenant_id: str) -> bool:
    """Atomically claim calls.summary before a paid Claude call.

    Returns True only for the winning writer. A persisted summary or an
    in-flight claim causes the loser to skip reserve and provider.
    """
    try:
        result = (
            db.table("calls")
            .select("summary")
            .eq("id", call_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.warning(
            "call summary: claim load failed tenant=%s call=%s",
            tenant_id,
            call_id,
        )
        return False
    rows = result.data or []
    if not rows:
        logger.warning(
            "call summary: call missing tenant=%s call=%s — failing closed before provider",
            tenant_id,
            call_id,
        )
        return False
    current = rows[0].get("summary")
    if should_skip_summary_generation(current):
        logger.info(
            "call summary: already claimed or persisted tenant=%s call=%s — skipping provider",
            tenant_id,
            call_id,
        )
        return False
    try:
        query = (
            db.table("calls")
            .update({"summary": SUMMARY_CLAIM})
            .eq("id", call_id)
            .eq("tenant_id", tenant_id)
        )
        if current is None:
            query = query.is_("summary", "null")
        else:
            query = query.eq("summary", current)
        updated = query.execute()
    except Exception:
        logger.warning(
            "call summary: claim update failed tenant=%s call=%s",
            tenant_id,
            call_id,
        )
        return False
    if not (updated.data or []):
        logger.info(
            "call summary: lost claim tenant=%s call=%s — skipping provider",
            tenant_id,
            call_id,
        )
        return False
    return True


def _summary_prompt(transcript_text: str) -> str:
    return (
        "Analyze this phone call transcript and provide:\n"
        "1. A one-paragraph summary\n"
        "2. Action items (list)\n"
        "3. Caller sentiment (positive/neutral/negative)\n"
        "4. Suggested follow-up\n\n"
        "Respond in this exact JSON format:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "action_items": ["item 1", "item 2"],\n'
        '  "sentiment": "positive|neutral|negative",\n'
        '  "follow_up": "..."\n'
        "}\n\n"
        f"Transcript:\n{transcript_text}"
    )


async def _generate_call_summary(call_id: str, tenant_id: str, lead_id: str | None, transcript_text: str) -> None:
    """Generate an AI summary of a call transcript and store it.

    Calls Claude to produce:
    - A one-paragraph summary
    - Action items (list)
    - Caller sentiment (positive/neutral/negative)
    - Suggested follow-up

    Then updates the call record and inserts action items into action_items table.
    This runs as a background task so it does not block the webhook response.

    Hard-cap, missing tenant, provider errors, persist failures, and a lost
    summary claim must not raise into the already-completed call or
    transcription webhook.
    """
    if not transcript_text or not transcript_text.strip():
        logger.warning("Skipping summary generation for call %s: empty transcript", call_id)
        return

    prompt = _summary_prompt(transcript_text)
    max_tokens = _summary_max_tokens()
    model = resolve_string_setting("voice_chat_model", "claude-sonnet-4-6")

    try:
        db = get_service_supabase()
    except Exception:
        logger.warning(
            "call summary: tenant load failed tenant=%s",
            tenant_id,
        )
        return

    tenant = _load_summary_budget_tenant(db, tenant_id)
    if tenant is None:
        logger.warning(
            "call summary: budget tenant unavailable tenant=%s — "
            "failing closed before provider",
            tenant_id,
        )
        return

    if not _claim_call_summary_slot(db, call_id, tenant_id):
        return

    reservation = reserve_ai_tokens(
        tenant=tenant,
        estimated_tokens=estimate_widget_chat_tokens(
            system_prompt="",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        ),
        operation=SUMMARY_OPERATION,
        session_id=call_id,
    )
    if not reservation.allowed:
        logger.warning(
            "call summary: hard cap blocked tenant=%s call=%s",
            tenant_id,
            call_id,
        )
        return

    try:
        llm_result = await call_claude_messages(
            operation=SUMMARY_OPERATION,
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            timeout=30.0,
            metadata={
                "tenant_id": tenant_id,
                "call_id": call_id,
                "transcript_chars": len(transcript_text),
            },
        )
        raw_text = (llm_result.text or "").strip()
    except Exception:
        release_ai_token_reservation(reservation)
        logger.warning(
            "call summary: provider error tenant=%s call=%s",
            tenant_id,
            call_id,
        )
        return

    record_ai_usage(
        reservation=reservation,
        result=llm_result,
        operation=SUMMARY_OPERATION,
        session_id=call_id,
        model=model,
    )

    # Parse the JSON response from Claude
    summary = ""
    action_items: list[str] = []
    sentiment = "neutral"
    follow_up = ""

    try:
        # Extract JSON from the response (Claude may wrap it in markdown code blocks)
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            parsed = json.loads(json_match.group())
            summary = parsed.get("summary", "")
            action_items = parsed.get("action_items", [])
            raw_sentiment = parsed.get("sentiment", "neutral").lower().strip()
            if raw_sentiment in ("positive", "neutral", "negative"):
                sentiment = raw_sentiment
            else:
                sentiment = "neutral"
            follow_up = parsed.get("follow_up", "")
        else:
            logger.warning(
                "call summary: no JSON in provider response tenant=%s call=%s",
                tenant_id,
                call_id,
            )
            summary = raw_text[:500]
    except (json.JSONDecodeError, AttributeError):
        logger.warning(
            "call summary: parse skipped tenant=%s call=%s",
            tenant_id,
            call_id,
        )
        summary = raw_text[:500]

    # Build action_taken from follow-up and action items
    action_taken_parts: list[str] = []
    if follow_up:
        action_taken_parts.append(f"Follow-up: {follow_up}")
    if action_items:
        action_taken_parts.append("Action items: " + "; ".join(action_items))
    action_taken = " | ".join(action_taken_parts) if action_taken_parts else None

    # Update the call record with summary, sentiment, and action_taken
    try:
        update_data: dict[str, Any] = {
            "summary": summary,
            "sentiment": sentiment,
        }
        if action_taken:
            update_data["action_taken"] = action_taken

        db.table("calls").update(update_data).eq("id", call_id).eq("tenant_id", tenant_id).execute()
        logger.info(
            "Updated call %s with AI summary (sentiment=%s, %d action items)",
            call_id, sentiment, len(action_items),
        )
    except Exception:
        logger.warning(
            "call summary: persist skipped tenant=%s call=%s",
            tenant_id,
            call_id,
        )

    # Feature 3: Insert action items into action_items table
    if action_items:
        await _insert_call_action_items(
            tenant_id=tenant_id,
            lead_id=lead_id,
            call_id=call_id,
            items=action_items,
        )

    # G3 Phase 1: file a callback-text draft into the Agent OS approval flow.
    # The owner sees "Missed call from X" with the summary and a one-tap
    # text-back; per-agent auto-send rules (G6) can send it automatically.
    try:
        caller_phone = ""
        business_name = ""
        call_row = (
            db.table("calls")
            .select("caller_phone")
            .eq("id", call_id)
            .limit(1)
            .execute()
        )
        if call_row.data:
            caller_phone = call_row.data[0].get("caller_phone") or ""
        tenant_row = (
            db.table("tenants")
            .select("business_name")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
        if tenant_row.data:
            business_name = tenant_row.data[0].get("business_name") or "us"

        if caller_phone:
            from backend.services.voice_recovery import create_missed_call_followup

            await create_missed_call_followup(
                db,
                tenant_id=tenant_id,
                business_name=business_name,
                caller=caller_phone,
                call_id=call_id,
                lead_id=lead_id,
                summary=summary,
                follow_up=follow_up,
                transcript_excerpt=transcript_text,
            )
    except Exception:
        logger.warning(
            "call summary: missed-call recovery skipped tenant=%s call=%s",
            tenant_id,
            call_id,
        )

    # Round 6: mirror the call into the owner's AI Workforce as an
    # observe-only thread (voice bridge, opt-in per tenant). Calls were the
    # one live channel invisible where the owner works. Best-effort - a
    # bridge failure never disturbs the saved summary.
    try:
        from backend.services.os_inbound_bridge import bridge_voice

        parts = [f"Phone call from {caller_phone or 'unknown number'}."]
        if summary:
            parts.append(f"Summary: {summary}")
        if sentiment:
            parts.append(f"Caller sentiment: {sentiment}.")
        if follow_up:
            parts.append(f"Suggested follow-up: {follow_up}")
        await bridge_voice(
            db,
            tenant_id,
            caller_phone=caller_phone,
            call_id=call_id,
            user_content="\n".join(parts)[:4000],
            sender_metadata={"caller_phone": caller_phone, "call_id": call_id},
        )
    except Exception:
        logger.warning(
            "call summary: voice bridge skipped tenant=%s call=%s",
            tenant_id,
            call_id,
        )


async def _insert_call_action_items(
    tenant_id: str,
    lead_id: str | None,
    call_id: str,
    items: list[str],
) -> None:
    """Insert action items extracted from a call into the action_items table.

    Phone call action items are always high priority since they represent
    direct customer communication.
    """
    if not items:
        return

    db = get_service_supabase()
    inserted = 0
    for item_text in items:
        if not item_text or not item_text.strip():
            continue
        row: dict[str, Any] = {
            "tenant_id": tenant_id,
            "description": item_text.strip()[:500],
            "priority": "high",
            "status": "pending",
        }
        if lead_id:
            row["lead_id"] = lead_id
        try:
            db.table("action_items").insert(row).execute()
            inserted += 1
        except Exception:
            logger.warning(
                "call summary: action item insert skipped tenant=%s call=%s",
                tenant_id,
                call_id,
            )
    if inserted:
        logger.info("Inserted %d action items from call %s for tenant %s", inserted, call_id, tenant_id)

    # Log activity for the action items creation
    log_activity(
        tenant_id=tenant_id,
        activity_type="call_action_items",
        description=f"AI extracted {inserted} action item(s) from phone call",
        lead_id=lead_id,
        metadata={"call_id": call_id, "action_item_count": inserted},
    )


async def _finalize_ai_call(
    db, tenant_id: str, call_sid: str, duration_seconds: int
) -> None:
    """Close out a live-AI call: persist the transcript from chat_messages,
    mark the call completed, and kick off summary + recovery draft.

    Idempotent — a call already marked completed is skipped, so the inline
    max-rounds finalize and the Twilio status callback can both fire.
    A persisted or in-flight summary is not overwritten and does not
    start a second paid Claude call.
    """
    if not call_sid:
        return
    result = (
        db.table("calls")
        .select("id, tenant_id, lead_id, status, summary")
        .eq("twilio_call_sid", call_sid)
        .eq("tenant_id", tenant_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return
    call = result.data[0]
    if call.get("status") == "completed":
        return

    already_summarized = should_skip_summary_generation(call.get("summary"))
    session_id = f"call_{call_sid}"
    transcript: list[dict[str, Any]] = []
    transcript_text = ""
    try:
        history = (
            db.table("chat_messages")
            .select("role, content")
            .eq("tenant_id", tenant_id)
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(40)
            .execute()
        )
        for i, msg in enumerate(history.data or []):
            speaker = "assistant" if msg.get("role") == "assistant" else "caller"
            transcript.append(
                {"timestamp": i, "speaker": speaker, "text": msg.get("content") or ""}
            )
        transcript_text = "\n".join(
            f"[{t['speaker']}]: {t['text']}" for t in transcript if t["text"]
        )
    except Exception:
        logger.warning(
            "call summary: transcript build skipped tenant=%s call_sid=%s",
            tenant_id,
            call_sid,
        )

    update: dict[str, Any] = {"status": "completed"}
    if duration_seconds:
        update["duration_seconds"] = duration_seconds
    if transcript:
        update["transcript"] = transcript
        if not already_summarized:
            update["summary"] = "AI conversation completed. Summary generating..."
    db.table("calls").update(update).eq("id", call["id"]).eq(
        "tenant_id", tenant_id
    ).execute()

    if transcript_text and not already_summarized:
        await _generate_call_summary(
            call_id=call["id"],
            tenant_id=tenant_id,
            lead_id=call.get("lead_id"),
            transcript_text=transcript_text,
        )
