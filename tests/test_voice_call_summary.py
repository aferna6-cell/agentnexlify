"""Degradation tests for voice_call_summary (audit HIGH).

Contract: these functions run as background work behind live phone
webhooks — an AI failure, a DB blip, or malformed model output must NEVER
raise out. Idempotency: a completed call is never finalized twice.
"""

import os
os.environ["TESTING"] = "1"

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.ai_usage_guard import AIUsageReservation
from backend.services.voice_call_summary import (
    _finalize_ai_call,
    _generate_call_summary,
)


def _chain_table(rows=None, raise_on_execute=False):
    table = MagicMock()
    for m in ["select", "insert", "update", "eq", "order", "limit", "gte", "is_"]:
        getattr(table, m).return_value = table
    if raise_on_execute:
        table.execute.side_effect = RuntimeError("db down")
    else:
        table.execute.return_value = MagicMock(data=rows or [])
    return table


def _allowed(**kwargs):
    return AIUsageReservation(
        allowed=True,
        tenant_id="t1",
        period_month="2026-09-01",
        estimated_tokens=kwargs.get("estimated_tokens", 800),
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
    )


def _budget_db(raise_on_persist=False):
    tenant_table = _chain_table(rows=[{"id": "t1", "plan": "agent_os"}])
    calls_table = _chain_table(
        rows=[
            {
                "id": "c1",
                "tenant_id": "t1",
                "summary": "AI conversation completed. Summary generating...",
            }
        ]
    )
    if raise_on_persist:
        persist_n = {"n": 0}

        def update(payload):
            persist_n["n"] += 1
            if persist_n["n"] > 1:
                calls_table.execute.side_effect = RuntimeError("db down")
            return calls_table

        calls_table.update.side_effect = update
    db = MagicMock()
    db.table.side_effect = lambda name: tenant_table if name == "tenants" else calls_table
    return db


class TestGenerateCallSummaryDegradation:
    @pytest.mark.asyncio
    async def test_claude_failure_never_raises(self):
        with patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            side_effect=RuntimeError("api down"),
        ), patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=_budget_db(),
        ), patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ), patch(
            "backend.services.voice_call_summary.release_ai_token_reservation",
        ):
            # Must swallow and return — a raise here would bubble into
            # the transcription webhook's background task.
            result = await _generate_call_summary("c1", "t1", None, "caller said hi")
        assert result is None

    @pytest.mark.asyncio
    async def test_db_update_failure_never_raises(self):
        db = _budget_db(raise_on_persist=True)
        with patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            return_value=MagicMock(text='{"summary": "s", "action_items": [], "sentiment": "neutral", "follow_up": ""}'),
        ), patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ), patch(
            "backend.services.voice_call_summary.record_ai_usage",
        ):
            result = await _generate_call_summary("c1", "t1", None, "caller said hi")
        assert result is None

    @pytest.mark.asyncio
    async def test_garbage_model_output_never_raises(self):
        db = _budget_db()
        with patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new_callable=AsyncMock,
            return_value=MagicMock(text="not json at all {{{"),
        ), patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            side_effect=_allowed,
        ), patch(
            "backend.services.voice_call_summary.record_ai_usage",
        ):
            result = await _generate_call_summary("c1", "t1", None, "caller said hi")
        assert result is None


class TestFinalizeAiCallDegradation:
    @pytest.mark.asyncio
    async def test_completed_call_is_skipped(self):
        db = MagicMock()
        db.table.return_value = _chain_table(
            rows=[{"id": "c1", "tenant_id": "t1", "lead_id": None, "status": "completed"}]
        )
        with patch(
            "backend.services.voice_call_summary._generate_call_summary",
            new_callable=AsyncMock,
        ) as mock_summary:
            result = await _finalize_ai_call(db, "t1", "CA123", 60)
        # Idempotent no-op: a completed call returns early (None), no summary.
        assert result is None
        mock_summary.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_transcript_query_failure_still_completes_call(self):
        """A chat_messages blip must not block marking the call done."""
        calls_table = _chain_table(
            rows=[{"id": "c1", "tenant_id": "t1", "lead_id": None, "status": "in-progress"}]
        )
        chat_table = _chain_table(raise_on_execute=True)
        update_payloads = []

        def record_update(payload):
            update_payloads.append(payload)
            return calls_table

        calls_table.update.side_effect = record_update

        db = MagicMock()
        db.table.side_effect = lambda name: chat_table if name == "chat_messages" else calls_table

        with patch(
            "backend.services.voice_call_summary._generate_call_summary",
            new_callable=AsyncMock,
        ) as mock_summary:
            await _finalize_ai_call(db, "t1", "CA123", 60)

        assert update_payloads and update_payloads[0]["status"] == "completed"
        mock_summary.assert_not_awaited()  # no transcript -> no summary call
