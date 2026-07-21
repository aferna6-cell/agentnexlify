"""Automation-loop supervisor: a crashed loop restarts and stays observable.

Incident 2026-07-21: prod's bare create_task(_automation_loop()) died on an
uncaught exception and every scheduled automation silently stopped. These
tests pin the supervisor contract: crash -> loud log + restart; cancel ->
propagate; tick age surfaces through /health.
"""

import asyncio
import os
import time
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

import backend.main as main


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestSupervisor:
    def test_crash_logs_and_restarts(self):
        calls = {"n": 0}

        async def _loop_then_cancel():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            raise asyncio.CancelledError()

        with patch.object(main, "_automation_loop", new=_loop_then_cancel), \
             patch.object(main.asyncio, "sleep", new=AsyncMock()) as sleep, \
             patch.object(main.logger, "exception") as log_exc:
            with pytest.raises(asyncio.CancelledError):
                _run(main._automation_loop_supervisor())
        assert calls["n"] == 2
        log_exc.assert_called_once()
        sleep.assert_awaited_once_with(60)

    def test_cancellation_propagates_without_restart(self):
        async def _cancel_immediately():
            raise asyncio.CancelledError()

        with patch.object(main, "_automation_loop", new=_cancel_immediately), \
             patch.object(main.logger, "exception") as log_exc:
            with pytest.raises(asyncio.CancelledError):
                _run(main._automation_loop_supervisor())
        log_exc.assert_not_called()


class TestTickAge:
    def test_none_before_first_tick(self):
        with patch.object(main, "_automation_last_tick", 0.0):
            assert main._automation_tick_age_seconds() is None

    def test_age_after_tick(self):
        with patch.object(main, "_automation_last_tick", time.time() - 30):
            age = main._automation_tick_age_seconds()
        assert age is not None and 29 <= age <= 35
