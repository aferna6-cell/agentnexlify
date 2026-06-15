"""Tests for the Agent OS fail/abstain alert wiring in os_thread_runner.

Covers the transcript fetch, the fire helper (background-task + inline paths),
and the fail/abstain detection branches in process_user_turn. Collaborators
are monkeypatched so no engine, DB, or network is touched.
"""

import asyncio

import backend.services.os_thread_runner as thr


# --------------------------------------------------------------------------- #
# _thread_transcript
# --------------------------------------------------------------------------- #


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        return _Resp(self._rows)


class _DB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, *a, **k):
        return _Query(self._rows)


def test_thread_transcript_returns_rows(monkeypatch):
    rows = [{"role": "user", "content": "hi"}]
    monkeypatch.setattr(thr, "tenant_table", lambda db, name, cid: _Query(rows))
    out = thr._thread_transcript(_DB(rows), "ten1", "th1")
    assert out == rows


def test_thread_transcript_swallows_error(monkeypatch):
    def _boom(db, name, cid):
        raise RuntimeError("db down")

    monkeypatch.setattr(thr, "tenant_table", _boom)
    assert thr._thread_transcript(_DB([]), "ten1", "th1") == []


# --------------------------------------------------------------------------- #
# _fire_os_alert
# --------------------------------------------------------------------------- #


class _BG:
    def __init__(self):
        self.tasks = []

    def add_task(self, fn, *a, **k):
        self.tasks.append((fn, a, k))


def test_fire_alert_schedules_background_task(monkeypatch):
    monkeypatch.setattr(thr, "_thread_transcript", lambda db, cid, tid: [{"role": "user", "content": "x"}])
    bg = _BG()
    asyncio.run(
        thr._fire_os_alert(
            None, "ten1", "th1", kind="fail", reason="boom", error="E", background_tasks=bg
        )
    )
    assert len(bg.tasks) == 1
    fn, args, kw = bg.tasks[0]
    assert fn is thr.os_alert_notifications.notify_agent_os_event
    assert kw["kind"] == "fail"
    assert args[0] == "ten1"


def test_fire_alert_inline_when_no_background(monkeypatch):
    monkeypatch.setattr(thr, "_thread_transcript", lambda db, cid, tid: [{"role": "user", "content": "x"}])
    captured = {}
    monkeypatch.setattr(
        thr.os_alert_notifications,
        "notify_agent_os_event",
        lambda tenant_id, conv, **kw: captured.update({"tenant": tenant_id, **kw}),
    )
    asyncio.run(
        thr._fire_os_alert(
            None, "ten1", "th1", kind="abstain", reason="no draft", error=None, background_tasks=None
        )
    )
    assert captured["tenant"] == "ten1"
    assert captured["kind"] == "abstain"


# --------------------------------------------------------------------------- #
# process_user_turn — fail / abstain detection
# --------------------------------------------------------------------------- #


async def _anoop(*a, **k):
    return None


async def _alist(*a, **k):
    return []


def _wire_common(monkeypatch, *, persist_status):
    monkeypatch.setattr(thr.agent_sdk_client, "is_configured", lambda: True)
    monkeypatch.setattr(
        thr.agent_os_bridge, "assemble_shared_context",
        lambda db, cid: {"businessProfile": {"businessName": "B", "businessType": "plumbing"}},
    )
    monkeypatch.setattr(thr.os_kb_feed, "tenant_kb_entries", lambda *a, **k: [])
    monkeypatch.setattr(thr.os_graph_memory, "graph_kb_entries", _alist)
    monkeypatch.setattr(thr.os_graph_memory, "accumulate_background", _anoop)
    monkeypatch.setattr(thr.agent_sdk_client, "orchestrate_sync", lambda *a, **k: {"status": persist_status})
    monkeypatch.setattr(
        thr.agent_os_bridge, "persist_orchestration",
        lambda db, cid, tid, out: {
            "assistant_message": {"content": "reply"},
            "agent_run": None,
            "status": persist_status,
        },
    )
    monkeypatch.setattr(thr, "_mirror_to_channel", _anoop)
    monkeypatch.setattr(thr, "_dispatch_auto_send", _anoop)
    monkeypatch.setattr(thr, "_thread_transcript", lambda db, cid, tid: [{"role": "user", "content": "x"}])


def test_process_turn_abstain_fires_alert(monkeypatch):
    _wire_common(monkeypatch, persist_status="no_draft")
    fired = {}
    monkeypatch.setattr(
        thr.os_alert_notifications, "notify_agent_os_event",
        lambda tenant_id, conv, **kw: fired.update({"kind": kw.get("kind")}),
    )
    asyncio.run(
        thr.process_user_turn(None, "ten1", "th1", {"content": "help"}, None)
    )
    assert fired["kind"] == "abstain"


def test_process_turn_failed_status_fires_alert(monkeypatch):
    _wire_common(monkeypatch, persist_status="failed")
    fired = {}
    monkeypatch.setattr(
        thr.os_alert_notifications, "notify_agent_os_event",
        lambda tenant_id, conv, **kw: fired.update({"kind": kw.get("kind")}),
    )
    asyncio.run(
        thr.process_user_turn(None, "ten1", "th1", {"content": "help"}, None)
    )
    assert fired["kind"] == "fail"


def test_process_turn_exception_fires_fail_then_degrades(monkeypatch):
    _wire_common(monkeypatch, persist_status="completed")

    def _raise(*a, **k):
        raise RuntimeError("engine boom")

    monkeypatch.setattr(thr.agent_sdk_client, "orchestrate_sync", _raise)
    fired = {}
    monkeypatch.setattr(
        thr.os_alert_notifications, "notify_agent_os_event",
        lambda tenant_id, conv, **kw: fired.update({"kind": kw.get("kind"), "error": kw.get("error")}),
    )
    monkeypatch.setattr(thr, "_degrade_offline", _anoop)
    asyncio.run(
        thr.process_user_turn(None, "ten1", "th1", {"content": "help"}, None)
    )
    assert fired["kind"] == "fail"
    assert "engine boom" in (fired["error"] or "")


def test_process_turn_success_status_no_alert(monkeypatch):
    _wire_common(monkeypatch, persist_status="completed")
    fired = {"called": False}
    monkeypatch.setattr(
        thr.os_alert_notifications, "notify_agent_os_event",
        lambda *a, **k: fired.update({"called": True}),
    )
    asyncio.run(
        thr.process_user_turn(None, "ten1", "th1", {"content": "help"}, None)
    )
    assert fired["called"] is False
