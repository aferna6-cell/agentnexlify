"""Tests for the campaign Agent OS worker.

Covers: SPEC registration, happy path, title fallback, Claude failure fallback,
summary non-empty, and progress steps recorded.

asyncio_mode = auto (pytest.ini) — async test functions run without decorators.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import os_workers
from backend.services.os_workers.base import WorkerContext
from backend.services.os_workers.campaign import SPEC

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(message="Run a spring promo for 20% off", title="Campaign Draft"):
    """Build a WorkerContext backed by a MagicMock db (ctx.step chains on mock)."""
    return WorkerContext(
        db=MagicMock(),
        client_id="tenant-1",
        thread_id="thread-1",
        run_id="run-1",
        user_message=message,
        deliverable_title=title,
    )


_CLAUDE_TEXT = (
    "**Spring Sale — 20% Off All Services**\n\n"
    "It's that time of year! Book any service this spring and save 20%.\n\n"
    "**Call to action:** Book now at [link] before April 30.\n\n"
    "_Social post:_ Spring is here! Get 20% off all services — book today! 🌸"
)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_spec_registered():
    """SPEC auto-discovers and registers under the correct name."""
    worker = os_workers.get_worker("campaign")
    assert worker is not None
    assert SPEC.name == "campaign"
    assert worker is SPEC


async def test_happy_path_body_and_format():
    """Claude text appears verbatim in deliverable body; format is markdown; title respected."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.campaign.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["body"] == _CLAUDE_TEXT.strip()
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Campaign Draft"


async def test_deliverable_title_empty_string_fallback():
    """An empty deliverable_title falls back to the default 'Campaign Draft'."""
    ctx = _ctx(title="")
    with patch(
        "backend.services.os_workers.campaign.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert result.deliverable["title"] == "Campaign Draft"


async def test_claude_raises_deterministic_fallback(caplog):
    """When Claude raises, the worker falls back to a deterministic draft and logs a warning."""
    ctx = _ctx(message="Announce our summer BBQ event with a discount code SUMMER10")
    with patch(
        "backend.services.os_workers.campaign.call_claude_messages",
        new=AsyncMock(side_effect=RuntimeError("api unavailable")),
    ), caplog.at_level(logging.WARNING, logger="backend.services.os_workers.campaign"):
        result = await SPEC.run(ctx)

    # Result is still a valid WorkerResult with a non-empty body
    assert result.deliverable["body"]
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Campaign Draft"
    # The user_message is quoted in the fallback body
    assert (
        "Announce our summer BBQ event with a discount code SUMMER10"
        in result.deliverable["body"]
    )
    # Warning was logged
    assert any("Claude call failed" in r.message for r in caplog.records)


async def test_summary_is_non_empty_string():
    """result.summary is a non-empty string."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.campaign.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        result = await SPEC.run(ctx)

    assert isinstance(result.summary, str)
    assert result.summary.strip()


async def test_progress_steps_recorded():
    """ctx.thought is non-empty after the worker runs (progress steps were recorded)."""
    ctx = _ctx()
    with patch(
        "backend.services.os_workers.campaign.call_claude_messages",
        new=AsyncMock(return_value=SimpleNamespace(text=_CLAUDE_TEXT)),
    ):
        await SPEC.run(ctx)

    assert len(ctx.thought) >= 2
    labels = [s["label"] for s in ctx.thought]
    assert any("Planning" in lbl for lbl in labels)
    assert any("Draft prepared" in lbl for lbl in labels)
