"""Tests for os_action_dispatch.queue_action_for_run().

Covers the five distinct execution paths:
1. No action_type → None immediately
2. Unknown action_type → None (warning logged)
3. Already-succeeded action run → idempotent return of existing id
4. New run with BackgroundTasks → add_task called
5. New run with background=None → run_action awaited inline
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.os_action_dispatch import queue_action_for_run


def _make_tenant_table_chain(
    succeeded_id: str | None = None, created_id: str = "action-run-1"
):
    """Return a patched tenant_table whose first .execute() returns the
    'existing succeeded' check and second .execute() returns the insert result.
    """
    succeeded_resp = MagicMock()
    succeeded_resp.data = [{"id": succeeded_id}] if succeeded_id else []

    created_resp = MagicMock()
    created_resp.data = [{"id": created_id}]

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.insert.return_value = chain
    # First execute() = idempotency check; second = insert result
    chain.execute.side_effect = [succeeded_resp, created_resp]
    return chain


@pytest.mark.asyncio
async def test_no_action_type_returns_none():
    """run dict without action_type → None, no DB calls."""
    result = await queue_action_for_run(MagicMock(), "client-1", {}, None)
    assert result is None


@pytest.mark.asyncio
async def test_unknown_action_type_returns_none():
    """action_type not in registry → None, warning logged."""
    with patch("backend.services.os_action_dispatch.get_action", return_value=None):
        result = await queue_action_for_run(
            MagicMock(),
            "client-1",
            {"id": "run-1", "action_type": "not_a_real_action"},
            None,
        )
    assert result is None


@pytest.mark.asyncio
async def test_idempotent_returns_existing_succeeded_id():
    """Existing succeeded row → return its id, no insert or re-queue."""
    chain = _make_tenant_table_chain(succeeded_id="existing-action-run-42")

    with patch(
        "backend.services.os_action_dispatch.get_action", return_value=AsyncMock()
    ):
        with patch(
            "backend.services.os_action_dispatch.tenant_table", return_value=chain
        ):
            result = await queue_action_for_run(
                MagicMock(),
                "client-1",
                {"id": "run-1", "action_type": "booking"},
                None,
            )

    assert result == "existing-action-run-42"
    chain.insert.assert_not_called()


@pytest.mark.asyncio
async def test_queues_background_task_when_provided():
    """BackgroundTasks provided → add_task called, new action_run_id returned."""
    chain = _make_tenant_table_chain(created_id="new-run-bg")
    background = MagicMock()

    with patch(
        "backend.services.os_action_dispatch.get_action", return_value=AsyncMock()
    ):
        with patch(
            "backend.services.os_action_dispatch.tenant_table", return_value=chain
        ):
            result = await queue_action_for_run(
                MagicMock(),
                "client-1",
                {"id": "run-1", "action_type": "booking"},
                background,
            )

    assert result == "new-run-bg"
    background.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_runs_action_inline_without_background():
    """background=None → run_action awaited directly (inbound bridge path)."""
    chain = _make_tenant_table_chain(created_id="inline-run-99")

    with patch(
        "backend.services.os_action_dispatch.get_action", return_value=AsyncMock()
    ):
        with patch(
            "backend.services.os_action_dispatch.run_action", new_callable=AsyncMock
        ) as mock_run:
            with patch(
                "backend.services.os_action_dispatch.tenant_table", return_value=chain
            ):
                result = await queue_action_for_run(
                    MagicMock(),
                    "client-1",
                    {"id": "run-1", "action_type": "booking"},
                    None,
                )

    assert result == "inline-run-99"
    mock_run.assert_awaited_once_with("inline-run-99", "client-1", "run-1", "booking")
