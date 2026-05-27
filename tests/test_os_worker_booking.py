"""Tests for the Agent OS booking worker (P2).

Covers: SPEC registration, happy path, title fallback, Claude failure fallback,
summary presence, and progress step recording.

asyncio_mode = auto in pytest.ini — no decorator needed on async tests.
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services import os_workers
from backend.services.os_workers.base import WorkerContext
from backend.services.os_workers.booking import SPEC


def _ctx(message="Can I book a haircut Friday?", title="Booking Reply"):
    return WorkerContext(
        db=MagicMock(),
        client_id="tenant-1",
        thread_id="thread-1",
        run_id="run-1",
        user_message=message,
        deliverable_title=title,
    )


# ---------------------------------------------------------------------------
# (a) SPEC registration
# ---------------------------------------------------------------------------


def test_spec_registered():
    """auto-discovery must expose the booking worker by name."""
    worker = os_workers.get_worker("booking")
    assert worker is not None
    assert SPEC.name == "booking"
    assert "booking" in os_workers.all_workers()


# ---------------------------------------------------------------------------
# (b) Happy path — Claude text flows through to deliverable
# ---------------------------------------------------------------------------


async def test_happy_path_body_and_format():
    claude_text = "Hi Jane, I'd be happy to book your haircut for Friday at 3 PM."
    mock_response = SimpleNamespace(text=claude_text)

    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await SPEC.run(_ctx())

    assert result.deliverable["body"] == claude_text.strip()
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Booking Reply"


async def test_happy_path_title_respected():
    """Custom deliverable_title must appear in the deliverable."""
    mock_response = SimpleNamespace(text="Your appointment is confirmed.")

    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await SPEC.run(_ctx(title="Appointment Confirmation"))

    assert result.deliverable["title"] == "Appointment Confirmation"


# ---------------------------------------------------------------------------
# (c) Empty deliverable_title falls back to default
# ---------------------------------------------------------------------------


async def test_empty_title_falls_back_to_default():
    mock_response = SimpleNamespace(text="Thanks for reaching out!")

    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await SPEC.run(_ctx(title=""))

    assert result.deliverable["title"] == "Booking Reply"


# ---------------------------------------------------------------------------
# (d) Claude raises — deterministic fallback body produced
# ---------------------------------------------------------------------------


async def test_claude_failure_produces_fallback(caplog):
    user_msg = "Can I reschedule my appointment to next Monday?"

    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(side_effect=RuntimeError("API unavailable")),
    ):
        with caplog.at_level(
            logging.WARNING, logger="backend.services.os_workers.booking"
        ):
            result = await SPEC.run(_ctx(message=user_msg))

    # Result is still a valid WorkerResult
    assert result.deliverable["format"] == "markdown"
    assert result.deliverable["title"] == "Booking Reply"
    # Fallback body must quote the original user message
    assert user_msg in result.deliverable["body"]
    # Warning must have been logged (not swallowed silently)
    assert any("fallback" in record.message.lower() for record in caplog.records)


# ---------------------------------------------------------------------------
# (e) summary is a non-empty string
# ---------------------------------------------------------------------------


async def test_summary_is_non_empty():
    mock_response = SimpleNamespace(text="We have you booked for Saturday at 10 AM.")

    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(return_value=mock_response),
    ):
        result = await SPEC.run(_ctx())

    assert isinstance(result.summary, str)
    assert len(result.summary.strip()) > 0


# ---------------------------------------------------------------------------
# (f) Progress steps recorded in ctx.thought
# ---------------------------------------------------------------------------


async def test_progress_steps_recorded():
    mock_response = SimpleNamespace(text="Your booking is confirmed for Tuesday.")

    ctx = _ctx()
    with patch(
        "backend.services.os_workers.booking.call_claude_messages",
        new=AsyncMock(return_value=mock_response),
    ):
        await SPEC.run(ctx)

    assert len(ctx.thought) >= 1
    labels = [step["label"] for step in ctx.thought]
    assert any(
        "booking" in label.lower() or "draft" in label.lower() for label in labels
    )
