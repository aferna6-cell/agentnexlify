"""Phase 4 cutover contracts: engine-only turns, auto-send gate, plan caps.

Covers the three behaviors the cutover added:
1. ``agent_os_bridge.resolve_deliverable_status`` — a draft auto-approves only
   when the engine says no approval is needed AND the tenant opted in AND the
   agent is outside the never-auto-send set. Failures land on the safe side.
2. ``os_action_dispatch.queue_action_for_run`` — one shared dispatch path for
   human approval and auto-send: idempotent, unknown handlers are a no-op,
   inline execution when no BackgroundTasks is available.
3. ``usage_meter.plan_cap`` — plan-tier-aware agent-run caps with a safe
   default for unknown plans or read failures.
4. ``os_thread_runner.process_user_turn`` — engine offline degrades honestly:
   the saved user message gets an explicit "engine unavailable" reply, never a
   silent re-route (the legacy orchestrator is deleted).
"""

import pytest

from backend.services import agent_os_bridge, os_action_dispatch, usage_meter


# --- tiny chainable supabase stub -------------------------------------------


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink=None):
        self._rows = rows
        self._sink = sink

    def select(self, *_a, **_k):
        return self

    def insert(self, payload):
        if self._sink is not None:
            self._sink.append(payload)
        return _Query([{**payload, "id": "new-row-id"}], self._sink)

    def update(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return _Result(self._rows)


class _FakeDB:
    """db.table(name) -> chainable query returning per-table canned rows."""

    def __init__(self, rows_by_table=None, sinks=None):
        self.rows_by_table = rows_by_table or {}
        self.sinks = sinks or {}

    def table(self, name):
        return _Query(self.rows_by_table.get(name, []), self.sinks.get(name))


class _FailDB:
    def table(self, name):
        raise RuntimeError("db down")


# --- 1. auto-send gate --------------------------------------------------------


def _db_with_flag(enabled: bool) -> _FakeDB:
    return _FakeDB({"tenants": [{"os_auto_send_enabled": enabled}]})


def test_requires_approval_always_pends_even_with_auto_send_on():
    status = agent_os_bridge.resolve_deliverable_status(
        _db_with_flag(True), "t1", "sales", requires_approval=True
    )
    assert status == "pending_approval"


def test_auto_send_needs_tenant_opt_in():
    status = agent_os_bridge.resolve_deliverable_status(
        _db_with_flag(False), "t1", "sales", requires_approval=False
    )
    assert status == "pending_approval"


def test_auto_send_fires_when_engine_and_tenant_agree():
    status = agent_os_bridge.resolve_deliverable_status(
        _db_with_flag(True), "t1", "sales", requires_approval=False
    )
    assert status == "approved"


@pytest.mark.parametrize("agent", sorted(agent_os_bridge.NEVER_AUTO_SEND_AGENTS))
def test_never_auto_send_agents_pend_regardless(agent):
    status = agent_os_bridge.resolve_deliverable_status(
        _db_with_flag(True), "t1", agent, requires_approval=False
    )
    assert status == "pending_approval"


def test_flag_read_failure_lands_on_pending():
    status = agent_os_bridge.resolve_deliverable_status(
        _FailDB(), "t1", "sales", requires_approval=False
    )
    assert status == "pending_approval"


def test_channel_action_map_covers_send_channels_only():
    assert agent_os_bridge.CHANNEL_ACTION_MAP == {
        "sms": "sms.send",
        "email": "email.send",
        "widget_reply": "widget.message",
    }


# --- 2. shared action dispatch -------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_skips_runs_without_action_type():
    out = await os_action_dispatch.queue_action_for_run(
        _FakeDB(), "t1", {"id": "run-1"}, background=None
    )
    assert out is None


@pytest.mark.asyncio
async def test_dispatch_skips_unknown_handler(monkeypatch):
    monkeypatch.setattr(os_action_dispatch, "get_action", lambda name: None)
    out = await os_action_dispatch.queue_action_for_run(
        _FakeDB(), "t1", {"id": "run-1", "action_type": "nope.send"}, background=None
    )
    assert out is None


@pytest.mark.asyncio
async def test_dispatch_is_idempotent_on_succeeded_action(monkeypatch):
    monkeypatch.setattr(os_action_dispatch, "get_action", lambda name: object())
    ran = []

    async def fake_run_action(*args):
        ran.append(args)

    monkeypatch.setattr(os_action_dispatch, "run_action", fake_run_action)
    db = _FakeDB({"os_action_runs": [{"id": "prior-success"}]})
    out = await os_action_dispatch.queue_action_for_run(
        db, "t1", {"id": "run-1", "action_type": "sms.send"}, background=None
    )
    assert out == "prior-success"
    assert ran == []  # no duplicate side effect


@pytest.mark.asyncio
async def test_dispatch_inline_runs_action_when_no_background(monkeypatch):
    monkeypatch.setattr(os_action_dispatch, "get_action", lambda name: object())
    ran = []

    async def fake_run_action(action_run_id, client_id, run_id, action_type):
        ran.append((action_run_id, client_id, run_id, action_type))

    monkeypatch.setattr(os_action_dispatch, "run_action", fake_run_action)
    inserts: list = []
    db = _FakeDB({"os_action_runs": []}, sinks={"os_action_runs": inserts})
    out = await os_action_dispatch.queue_action_for_run(
        db, "t1", {"id": "run-1", "action_type": "sms.send"}, background=None
    )
    assert out == "new-row-id"
    assert ran == [("new-row-id", "t1", "run-1", "sms.send")]
    assert inserts and inserts[0]["status"] == "queued"


# --- 3. plan-tier caps ----------------------------------------------------------


# Caps for the two-plan model (2026-06-15 repricing): the old 5-tier caps
# (growth/autopilot/professional/enterprise) were retired with the plan model.
@pytest.mark.parametrize(
    "plan,cap",
    [
        ("free", 25),
        ("chatbot", 100),
        ("agent_os", 2000),
    ],
)
def test_plan_caps_match_tiers(plan, cap):
    db = _FakeDB({"tenants": [{"plan": plan}]})
    assert usage_meter.plan_cap(db, "t1") == cap


def test_unknown_plan_falls_back_to_default():
    db = _FakeDB({"tenants": [{"plan": "foundation"}]})  # retired name
    assert usage_meter.plan_cap(db, "t1") == usage_meter.DEFAULT_AGENT_RUN_CAP


def test_plan_read_failure_falls_back_to_default():
    assert usage_meter.plan_cap(_FailDB(), "t1") == usage_meter.DEFAULT_AGENT_RUN_CAP


# --- 4. honest offline degradation ----------------------------------------------


@pytest.mark.asyncio
async def test_engine_offline_replies_honestly(monkeypatch):
    from backend.services import os_thread_runner

    monkeypatch.setattr(
        os_thread_runner.agent_sdk_client, "is_configured", lambda: False
    )

    async def fake_mirror(db, client_id, thread_id, message):
        return None

    monkeypatch.setattr(os_thread_runner, "_mirror_to_channel", fake_mirror)

    inserts: list = []
    db = _FakeDB(
        {"os_messages": [], "os_threads": [{"id": "th-1"}]},
        sinks={"os_messages": inserts},
    )
    user_row = {"id": "m-1", "content": "book me tomorrow"}
    out = await os_thread_runner.process_user_turn(db, "t1", "th-1", user_row, None)

    assert out["action"] == "answer"
    assert out["agent_runs"] == []
    assert out["assistant_message"]["content"] == os_thread_runner.ENGINE_OFFLINE_REPLY
    assert inserts and inserts[0]["role"] == "assistant"


# --- 5. platform-owner alert on fail / abstain ----------------------------------


def _patch_engine_turn(monkeypatch, persisted):
    """Wire process_user_turn so it reaches persist + the alert branch."""
    from backend.services import os_thread_runner

    monkeypatch.setattr(
        os_thread_runner.agent_sdk_client, "is_configured", lambda: True
    )
    monkeypatch.setattr(
        os_thread_runner.agent_os_bridge,
        "assemble_shared_context",
        lambda db, cid: {"businessProfile": {"businessName": "Biz"}},
    )
    monkeypatch.setattr(
        os_thread_runner.os_kb_feed, "tenant_kb_entries", lambda *a, **k: []
    )

    async def _graph_kb(*a, **k):
        return []

    monkeypatch.setattr(os_thread_runner.os_graph_memory, "graph_kb_entries", _graph_kb)

    async def _inline(fn, *a, **k):
        return fn(*a, **k)

    monkeypatch.setattr(os_thread_runner, "run_in_threadpool", _inline)
    monkeypatch.setattr(
        os_thread_runner.agent_sdk_client,
        "orchestrate_sync",
        lambda *a, **k: {"result": {}, "record": {}},
    )
    monkeypatch.setattr(
        os_thread_runner.agent_os_bridge,
        "persist_orchestration",
        lambda db, cid, tid, out: persisted,
    )

    async def _mirror(*a, **k):
        return None

    monkeypatch.setattr(os_thread_runner, "_mirror_to_channel", _mirror)

    async def _accum(*a, **k):
        return None

    monkeypatch.setattr(os_thread_runner.os_graph_memory, "accumulate_background", _accum)

    calls = []

    async def _notify(db, cid, tid, reason, business_name=None):
        calls.append((cid, tid, reason, business_name))
        return True

    monkeypatch.setattr(
        os_thread_runner.os_failure_notify, "notify_agent_failure", _notify
    )
    return os_thread_runner, calls


@pytest.mark.asyncio
async def test_failed_run_alerts_owner(monkeypatch):
    runner, calls = _patch_engine_turn(
        monkeypatch,
        {
            "assistant_message": {"content": "Run failed: boom"},
            "agent_run": {"status": "failed", "id": "r1"},
            "status": "routed",
        },
    )
    db = _FakeDB({"os_threads": [{"id": "th-1"}]})
    out = await runner.process_user_turn(
        db, "t1", "th-1", {"id": "m-1", "content": "quote pls"}, None
    )
    assert out["action"] == "delegate"
    assert calls == [("t1", "th-1", "failed", "Biz")]


@pytest.mark.asyncio
async def test_wishlist_fallback_alerts_owner(monkeypatch):
    runner, calls = _patch_engine_turn(
        monkeypatch,
        {
            "assistant_message": {"content": "I wasn't sure which department fits."},
            "agent_run": None,
            "status": "wishlist_fallback",
        },
    )
    db = _FakeDB({"os_threads": [{"id": "th-2"}]})
    out = await runner.process_user_turn(
        db, "t1", "th-2", {"id": "m-2", "content": "do a thing"}, None
    )
    assert out["action"] == "answer"
    assert calls == [("t1", "th-2", "wishlist_fallback", "Biz")]


@pytest.mark.asyncio
async def test_succeeded_run_does_not_alert(monkeypatch):
    runner, calls = _patch_engine_turn(
        monkeypatch,
        {
            "assistant_message": {"content": "Done."},
            "agent_run": {"status": "succeeded", "id": "r3"},
            "status": "routed",
        },
    )
    db = _FakeDB({"os_threads": [{"id": "th-3"}]})
    await runner.process_user_turn(
        db, "t1", "th-3", {"id": "m-3", "content": "all good"}, None
    )
    assert calls == []  # routine success never alerts
