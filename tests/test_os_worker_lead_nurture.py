"""Tests for the lead_nurture Agent OS worker.

Covers: SPEC registration, happy path, title fallback, Claude failure fallback,
summary non-empty, and progress steps recorded.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import os_workers
from backend.services.os_workers.base import WorkerContext
from backend.services.os_workers.lead_nurture import SPEC

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    message: str = "Follow up with the lead from last week",
    title: str = "Lead Follow-Up",
) -> WorkerContext:
    return WorkerContext(
        db=MagicMock(),
        client_id="tenant-1",
        thread_id="thread-1",
        run_id="run-1",
        user_message=message,
        deliverable_title=title,
    )


_CLAUDE_REPLY = "Hi there! Just wanted to follow up on our earlier conversation."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_spec_registered():
    """SPEC is discoverable by name through the worker registry."""
    worker = os_workers.get_worker("lead_nurture")
    assert worker is not None, "lead_nurture not found in os_workers registry"
    assert SPEC.name == "lead_nurture"
    assert worker is SPEC


async def test_happy_path_body_and_format():
    """Claude text lands in deliverable body; format is markdown; title respected."""
    ctx = _ctx()
    mock_result = SimpleNamespace(text=_CLAUDE_REPLY)

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["body"] == _CLAUDE_REPLY.strip()
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Lead Follow-Up"


async def test_empty_deliverable_title_falls_back_to_default():
    """An empty deliverable_title string falls back to 'Lead Follow-Up'."""
    ctx = _ctx(title="")
    mock_result = SimpleNamespace(text=_CLAUDE_REPLY)

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(return_value=mock_result),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["title"] == "Lead Follow-Up"


async def test_claude_failure_produces_deterministic_fallback():
    """When Claude raises, a deterministic fallback body is returned and result is valid."""
    ctx = _ctx()

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(side_effect=RuntimeError("API timeout")),
    ):
        result = await SPEC.run(ctx)

    # Result is still a valid WorkerResult
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Lead Follow-Up"
    # Fallback body quotes the original user message
    assert ctx.user_message in result.deliverable["body"]


async def test_fallback_logs_warning(caplog):
    """Claude failure emits a warning log — exceptions are never swallowed silently."""
    ctx = _ctx()

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(side_effect=ValueError("model unavailable")),
    ):
        with caplog.at_level(
            logging.WARNING, logger="backend.services.os_workers.lead_nurture"
        ):
            await SPEC.run(ctx)

    assert any("lead_nurture worker" in record.message for record in caplog.records)


async def test_summary_is_non_empty_string():
    """result.summary is a non-empty string on both happy path and fallback."""
    ctx_ok = _ctx()
    ctx_fail = _ctx()

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_REPLY)),
    ):
        result_ok = await SPEC.run(ctx_ok)

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(side_effect=RuntimeError("down")),
    ):
        result_fail = await SPEC.run(ctx_fail)

    assert isinstance(result_ok.summary, str) and result_ok.summary.strip()
    assert isinstance(result_fail.summary, str) and result_fail.summary.strip()


async def test_progress_steps_recorded():
    """ctx.thought is non-empty after the worker runs, proving steps were recorded."""
    ctx = _ctx()

    with patch(
        "backend.services.os_workers.lead_nurture.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_REPLY)),
    ):
        await SPEC.run(ctx)

    assert len(ctx.thought) >= 1, "expected at least one progress step in ctx.thought"
    labels = [s["label"] for s in ctx.thought]
    assert any("draft" in lbl.lower() or "reviewing" in lbl.lower() for lbl in labels)
