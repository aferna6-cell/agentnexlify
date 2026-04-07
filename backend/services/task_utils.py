"""Safe asyncio task creation with error logging.

Prevents the silent-failure pattern where asyncio.create_task() swallows
exceptions in fire-and-forget coroutines.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


def _log_task_exception(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error(
            "Background task '%s' failed: %s",
            task.get_name(),
            exc,
            exc_info=exc,
        )


def safe_create_task(coro, *, name: str | None = None) -> asyncio.Task:
    """Like asyncio.create_task() but logs exceptions instead of swallowing them."""
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(_log_task_exception)
    return task
