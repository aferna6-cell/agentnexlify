"""Tests for the customer_question Agent OS worker.

Covers: SPEC registration, happy path, title fallback, Claude failure fallback,
summary non-empty, and progress steps recorded.

asyncio_mode = auto (pytest.ini) — async test functions run without decorators.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import os_workers
from backend.services.os_workers.base import WorkerContext
from backend.services.os_workers.customer_question import SPEC

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(message="What are your hours?", title="Customer Answer"):
    """Build a WorkerContext backed by a MagicMock db (ctx.step chains on mock)."""
    return WorkerContext(
        db=MagicMock(),
        client_id="tenant-1",
        thread_id="thread-1",
        run_id="run-1",
        user_message=message,
        deliverable_title=title,
    )


_CLAUDE_TEXT = "We are open Monday–Friday, 9 AM to 5 PM."

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_spec_registered():
    """SPEC auto-discovers and registers under the correct name."""
    worker = os_workers.get_worker("customer_question")
    assert worker is not None
    assert SPEC.name == "customer_question"
    assert worker is SPEC


async def test_happy_path_body_and_format():
    """Claude text appears verbatim in deliverable body; format is markdown."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.customer_question.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["body"] == _CLAUDE_TEXT
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Customer Answer"


async def test_deliverable_title_empty_string_fallback():
    """An empty deliverable_title falls back to the default 'Customer Answer'."""
    ctx = _ctx(title="")
    with patch(
        "backend.services.os_workers.customer_question.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["title"] == "Customer Answer"


async def test_claude_raises_deterministic_fallback(caplog):
    """When Claude raises, the worker falls back to a deterministic draft and logs a warning."""
    ctx = _ctx(message="Do you offer weekend appointments?")
    with patch(
        "backend.services.os_workers.customer_question.call_claude_messages",
        new=AsyncMock(side_effect=RuntimeError("api down")),
    ), caplog.at_level(
        logging.WARNING, logger="backend.services.os_workers.customer_question"
    ):
        result = await SPEC.run(ctx)

    # Result is still a valid WorkerResult with a non-empty body
    assert result.deliverable["body"]
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Customer Answer"
    # The user_message is quoted in the fallback body
    assert "Do you offer weekend appointments?" in result.deliverable["body"]
    # Warning was logged
    assert any("Claude call failed" in r.message for r in caplog.records)


async def test_summary_is_non_empty_string():
    """result.summary is a non-empty string."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.customer_question.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert isinstance(result.summary, str)
    assert result.summary.strip()


async def test_progress_steps_recorded():
    """ctx.thought is non-empty after the worker runs (progress steps were recorded)."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.customer_question.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        await SPEC.run(ctx)

    assert len(ctx.thought) >= 2
    labels = [s["label"] for s in ctx.thought]
    assert any("Analyzing" in lbl for lbl in labels)
    assert any("Draft prepared" in lbl for lbl in labels)
