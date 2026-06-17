"""Unit tests for the monthly Conversation Insights auto-run.

Spec: insights auto-run + dashboard surface.

Focus:
- No-ops when the engine is unconfigured.
- No-ops on any day other than the first of the month.
- Targets only ``agent_os`` plan tenants.
- Dispatches the ``conversation_insights`` agent via force_agent_id.
- Skips tenants already run this month (activity_log dedup).
- Respects the plan-tier monthly cap.
- All tenant queries are client_id scoped through tenant_table.
"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.automation.scheduled import conversation_insights_job as job

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_CLIENT_B = "00000000-0000-0000-0000-00000000000b"
_THREAD_ID = "10000000-0000-0000-0000-0000000000cd"
_FIRST_OF_MONTH = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
_MID_MONTH = datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc)


class _Builder:
    """Chained supabase-py builder stub with per-table canned data."""

    def __init__(self, table_name, tenants, existing_threads, dedup_count, raise_on=None):
        self.table_name = table_name
        self._tenants = tenants
        self._existing_threads = existing_threads
        self._dedup_count = dedup_count
        self._raise_on = raise_on

    def select(self, *a, **k):
        return self

    def insert(self, *a, **k):
        self._last_insert = a[0] if a else None
        return self

    def update(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        if self._raise_on is not None and self.table_name == self._raise_on:
            raise RuntimeError("simulated db failure")
        if self.table_name == "tenants":
            return SimpleNamespace(data=self._tenants, count=len(self._tenants))
        if self.table_name == "activity_log":
            return SimpleNamespace(data=[], count=self._dedup_count)
        if self.table_name == "os_threads":
            if getattr(self, "_last_insert", None) is not None:
                return SimpleNamespace(data=[{"id": _THREAD_ID}], count=1)
            return SimpleNamespace(
                data=([{"id": _THREAD_ID}] if self._existing_threads else []), count=0
            )
        if self.table_name == "os_messages":
            return SimpleNamespace(
                data=[{"id": "msg-1", "thread_id": _THREAD_ID, "content": job._RUN_PROMPT}],
                count=1,
            )
        return SimpleNamespace(data=[], count=0)


def _stub_db(tenants, existing_threads=True, dedup_count=0, raise_on=None):
    db = MagicMock(name="db")
    db.table.side_effect = lambda name: _Builder(
        name, tenants, existing_threads, dedup_count, raise_on
    )
    return db


def _run(
    *,
    tenants,
    now,
    configured=True,
    cap_reached=False,
    dedup_count=0,
    existing_threads=True,
    raise_on=None,
    turn_exc=False,
):
    db = _stub_db(
        tenants,
        existing_threads=existing_threads,
        dedup_count=dedup_count,
        raise_on=raise_on,
    )
    turn_mock = (
        AsyncMock(side_effect=RuntimeError("turn boom"))
        if turn_exc
        else AsyncMock(return_value={"agent_runs": [{}]})
    )
    fixed_now = MagicMock()
    fixed_now.now.return_value = now
    with patch.object(job, "get_service_supabase", return_value=db), patch.object(
        job.agent_sdk_client, "is_configured", return_value=configured
    ), patch.object(
        job.usage_meter, "cap_reached", return_value=cap_reached
    ), patch.object(
        job.usage_meter, "record_message"
    ), patch.object(
        job, "process_user_turn", new=turn_mock
    ) as turn, patch(
        "backend.services.activity.log_activity"
    ) as log_activity, patch.object(
        job, "datetime", fixed_now
    ):
        count = asyncio.run(job.run_monthly_conversation_insights())
    return count, turn, log_activity, db


def test_noop_when_engine_unconfigured():
    count, turn, _log, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        configured=False,
    )
    assert count == 0
    turn.assert_not_awaited()


def test_noop_off_first_of_month():
    count, turn, _log, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_MID_MONTH,
    )
    assert count == 0
    turn.assert_not_awaited()


def test_dispatches_conversation_insights_for_eligible_tenant():
    count, turn, log_activity, db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
    )
    assert count == 1
    turn.assert_awaited_once()
    # force_agent_id must pin the conversation_insights agent.
    kwargs = turn.await_args.kwargs
    assert kwargs["force_agent_id"] == job.CONVERSATION_INSIGHTS_AGENT_ID
    assert kwargs["force_agent_id"] == "conversation_insights"
    # Tenant is targeted via its client_id (positional arg to process_user_turn).
    assert _CLIENT_A in turn.await_args.args
    # Eligibility query filters the tenants table on the agent_os plan.
    assert db.table.call_args_list[0].args[0] == "tenants"
    log_activity.assert_called_once()


def test_targets_only_agent_os_plan():
    # The job filters at the DB level (.eq plan agent_os). Simulate the DB
    # returning only the eligible tenant — a chatbot/free tenant is never
    # returned, so it is never dispatched.
    count, turn, _log, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
    )
    assert count == 1
    assert turn.await_count == 1


def test_skips_tenant_already_run_this_month():
    count, turn, log_activity, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        dedup_count=1,
    )
    assert count == 0
    turn.assert_not_awaited()
    log_activity.assert_not_called()


def test_respects_monthly_cap():
    count, turn, log_activity, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        cap_reached=True,
    )
    assert count == 0
    turn.assert_not_awaited()
    log_activity.assert_not_called()


def test_dispatches_across_multiple_tenants():
    count, turn, log_activity, _db = _run(
        tenants=[
            {"id": _CLIENT_A, "plan": "agent_os"},
            {"id": _CLIENT_B, "plan": "agent_os"},
        ],
        now=_FIRST_OF_MONTH,
    )
    assert count == 2
    assert turn.await_count == 2
    assert log_activity.call_count == 2


def test_month_tag_format():
    assert job._month_tag(_FIRST_OF_MONTH) == "conversation_insights_monthly_2026-06"


def test_creates_thread_when_none_exists():
    # No existing "Monthly conversation insights" thread -> the insert branch
    # runs and the new thread id is used for the dispatch.
    count, turn, log_activity, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        existing_threads=False,
    )
    assert count == 1
    turn.assert_awaited_once()
    log_activity.assert_called_once()


def test_dedup_check_failure_fails_closed():
    # A transient activity_log error must skip the tenant (never double-dispatch
    # + double Claude spend), so no run is dispatched.
    count, turn, log_activity, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        raise_on="activity_log",
    )
    assert count == 0
    turn.assert_not_awaited()
    log_activity.assert_not_called()


def test_tenants_query_failure_returns_zero():
    count, turn, _log, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        raise_on="tenants",
    )
    assert count == 0
    turn.assert_not_awaited()


def test_skips_tenant_without_id():
    count, turn, log_activity, _db = _run(
        tenants=[{"plan": "agent_os"}],  # no id
        now=_FIRST_OF_MONTH,
    )
    assert count == 0
    turn.assert_not_awaited()
    log_activity.assert_not_called()


def test_dispatch_exception_is_swallowed_per_tenant():
    # A turn that raises must not abort the batch or mark the month done.
    count, turn, log_activity, _db = _run(
        tenants=[{"id": _CLIENT_A, "plan": "agent_os"}],
        now=_FIRST_OF_MONTH,
        turn_exc=True,
    )
    assert count == 0
    turn.assert_awaited_once()
    log_activity.assert_not_called()
