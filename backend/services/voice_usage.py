"""Voice minutes metering — cap live-AI answering cost per tenant (G3 Phase 3).

Twilio per-minute + a Claude call per round make live AI answering the only
tenant-triggerable unbounded spend: duration_seconds is stored per call but
was never aggregated or capped. This module sums the current calendar month's
call seconds and answers one question for /voice/incoming: has this tenant
used up their included live-AI minutes?

Over-cap behavior is DEGRADE, never drop: the caller gets voicemail mode
(record + transcribe + text-back draft), which costs cents, not dollars.

The allowance is the runtime setting ``voice_included_minutes`` (default 300)
so it can move without a deploy; a value <= 0 means unmetered. Metering FAILS
OPEN — an aggregation error must never push a paying tenant to voicemail.

Refs: audits/audit-voice-g3-scope-2026-07-09.md Phase 3.
Do NOT add 'from __future__ import annotations' — breaks Pydantic on FastAPI.
"""

import logging
from datetime import datetime, timezone

from backend.models.database import get_service_supabase
from backend.services.llm_runtime import resolve_int_setting

logger = logging.getLogger(__name__)

DEFAULT_INCLUDED_MINUTES = 300


def included_voice_minutes() -> int:
    """Monthly live-AI minutes allowance. <= 0 means unmetered."""
    return resolve_int_setting("voice_included_minutes", DEFAULT_INCLUDED_MINUTES)


def month_start_iso(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()


def monthly_voice_seconds(tenant_id: str) -> int:
    """Total call seconds for the tenant this calendar month. 0 on error."""
    try:
        db = get_service_supabase()
        result = (
            db.table("calls")
            .select("duration_seconds")
            .eq("tenant_id", tenant_id)
            .gte("created_at", month_start_iso())
            .execute()
        )
        return sum(
            int(r["duration_seconds"])
            for r in (result.data or [])
            if r.get("duration_seconds")
        )
    except Exception:
        logger.warning(
            "voice_usage: monthly aggregation failed for tenant %s — treating as 0",
            tenant_id,
            exc_info=True,
        )
        return 0


def voice_minutes_exhausted(tenant_id: str) -> bool:
    """True when the tenant has used their included live-AI minutes.

    Fails open (False) on any error — a metering hiccup must never take a
    paying tenant's AI answering offline.
    """
    try:
        allowance = included_voice_minutes()
        if allowance <= 0:
            return False
        used_seconds = monthly_voice_seconds(tenant_id)
        exhausted = used_seconds >= allowance * 60
        if exhausted:
            logger.info(
                "voice_usage: tenant %s over included minutes (%ds used / %d min allowed) — voicemail mode",
                tenant_id,
                used_seconds,
                allowance,
            )
        return exhausted
    except Exception:
        logger.warning(
            "voice_usage: exhaustion check failed for tenant %s — failing open",
            tenant_id,
            exc_info=True,
        )
        return False
