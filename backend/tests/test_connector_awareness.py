"""Connector-need inference (backend/services/connector_awareness.py) and its
wiring into the Agent OS turn (os_thread_runner._post_connect_prompt).

Contracts:
  - inference is high-precision regex: product/feature mentions trigger,
    generic words never do
  - connection status maps the four stores (integrations, tenant_integrations,
    tenants.twilio_number, tenant_api_keys) and fails closed per connector
  - missing_for_message runs status lookups ONLY on an inference hit
  - the runner posts one connect prompt per connector per thread, appends it
    to the response as followup_messages, never posts on inbound-channel
    threads, and the engine context is told what is missing
"""

from unittest.mock import MagicMock

import pytest

from backend.services import connector_awareness as ca


def _chain(rows):
    result = MagicMock()
    result.data = rows
    c = MagicMock()
    for m in ("select", "eq", "in_", "order", "limit", "insert"):
        getattr(c, m).return_value = c
    c.execute.return_value = result
    return c


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


class TestInference:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Can you sync my Google Calendar?", ["calendar"]),
            ("push this lead to our CRM", ["hubspot"]),
            ("Add these leads to HubSpot please", ["hubspot"]),
            ("connect my google drive folder", ["drive"]),
            ("I want an AI receptionist to answer my calls", ["phone"]),
            ("set up a zapier automation for new leads", ["zapier"]),
            ("check my calendar and book them in", ["calendar"]),
        ],
    )
    def test_positive(self, text, expected):
        assert ca.infer_needed_connectors(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "please call the customer back",
            "what were my leads this week?",
            "draft an email to this customer",
            "the customer drives a truck",
            "my phone number is 555-1234",
            "",
        ],
    )
    def test_negative(self, text):
        assert ca.infer_needed_connectors(text) == []

    def test_multiple_connectors_in_one_ask(self):
        text = "sync my google calendar and push new bookings to hubspot"
        assert ca.infer_needed_connectors(text) == ["calendar", "hubspot"]


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------


def _status_db(
    integrations=(), drive_rows=(), tenant_rows=(), api_key_rows=()
):
    db = MagicMock()

    def route(name):
        return {
            "integrations": _chain([{"provider": p} for p in integrations]),
            "tenant_integrations": _chain(list(drive_rows)),
            "tenants": _chain(list(tenant_rows)),
            "tenant_api_keys": _chain(list(api_key_rows)),
        }.get(name) or _chain([])

    db.table.side_effect = route
    return db


class TestConnectionStatus:
    def test_all_disconnected(self):
        status = ca.connection_status(_status_db(), "t1")
        assert status == {
            "calendar": False,
            "hubspot": False,
            "drive": False,
            "phone": False,
            "zapier": False,
        }

    def test_all_connected(self):
        db = _status_db(
            integrations=("google_calendar", "hubspot"),
            drive_rows=[{"provider": "drive", "enabled": True}],
            tenant_rows=[{"twilio_number": "+15550001111"}],
            api_key_rows=[{"id": "k1"}],
        )
        assert all(ca.connection_status(db, "t1").values())

    def test_m365_counts_as_calendar(self):
        db = _status_db(integrations=("m365_calendar",))
        assert ca.connection_status(db, "t1")["calendar"] is True

    def test_disabled_drive_is_not_connected(self):
        db = _status_db(drive_rows=[{"provider": "drive", "enabled": False}])
        assert ca.connection_status(db, "t1")["drive"] is False

    def test_lookup_failure_fails_closed_for_that_connector_only(self):
        db = _status_db(tenant_rows=[{"twilio_number": "+15550001111"}])
        broken = _chain([])
        broken.execute.side_effect = RuntimeError("db down")

        def route(name):
            if name == "integrations":
                return broken
            if name == "tenants":
                return _chain([{"twilio_number": "+15550001111"}])
            return _chain([])

        db.table.side_effect = route
        status = ca.connection_status(db, "t1")
        assert status["calendar"] is False
        assert status["phone"] is True


class TestMissingForMessage:
    def test_no_inference_no_status_queries(self):
        db = MagicMock()
        assert ca.missing_for_message(db, "t1", "what were my leads?") == []
        db.table.assert_not_called()

    def test_connected_connector_not_reported(self):
        db = _status_db(integrations=("hubspot",))
        assert ca.missing_for_message(db, "t1", "push this to hubspot") == []

    def test_missing_connector_reported_with_path(self):
        db = _status_db()
        missing = ca.missing_for_message(db, "t1", "push this to hubspot")
        assert missing == [
            {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
        ]


class TestPromptText:
    def test_single_names_connector_and_path(self):
        text = ca.connect_prompt(
            [{"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}]
        )
        assert "HubSpot" in text and "/dashboard/integrations" in text

    def test_multi_lists_each(self):
        text = ca.connect_prompt(
            [
                {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"},
                {"key": "drive", "label": "Google Drive", "path": "/dashboard/knowledge"},
            ]
        )
        assert "- HubSpot: /dashboard/integrations" in text
        assert "- Google Drive: /dashboard/knowledge" in text


class TestAlreadyPrompted:
    def test_filters_connectors_already_nudged(self):
        prior = [
            {"role": "assistant", "content": "connect here: /dashboard/integrations"},
            {"role": "user", "content": "/dashboard/knowledge"},  # user text ignored
        ]
        missing = [
            {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"},
            {"key": "drive", "label": "Google Drive", "path": "/dashboard/knowledge"},
        ]
        fresh = ca.already_prompted(prior, missing)
        assert [m["key"] for m in fresh] == ["drive"]


# ---------------------------------------------------------------------------
# Runner wiring
# ---------------------------------------------------------------------------


class _RunnerDB:
    """Routes table() calls; records inserts into os_messages."""

    def __init__(self, thread_source=None, prior_messages=None):
        self.inserts: list = []
        self._thread = {"id": "th-1", "source": thread_source}
        self._prior = prior_messages or []

    def table(self, name):
        if name == "os_threads":
            return _chain([self._thread])
        if name == "os_messages":
            chain = _chain(self._prior)

            def capture(payload):
                self.inserts.append(payload)
                inserted = _chain([{**payload, "id": "msg-new"}])
                return inserted

            chain.insert.side_effect = capture
            return chain
        return _chain([])


@pytest.mark.asyncio
async def test_runner_posts_connect_prompt_and_returns_followup(monkeypatch):
    from backend.services import os_thread_runner

    db = _RunnerDB()
    missing = [
        {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
    ]
    message = await os_thread_runner._post_connect_prompt(db, "t1", "th-1", missing)
    assert message and message["role"] == "assistant"
    assert "/dashboard/integrations" in message["content"]
    assert db.inserts and db.inserts[0]["thread_id"] == "th-1"


@pytest.mark.asyncio
async def test_runner_skips_inbound_channel_threads():
    from backend.services import os_thread_runner

    db = _RunnerDB(thread_source="widget")
    missing = [
        {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
    ]
    assert await os_thread_runner._post_connect_prompt(db, "t1", "th-1", missing) is None
    assert db.inserts == []


@pytest.mark.asyncio
async def test_runner_prompts_once_per_thread():
    from backend.services import os_thread_runner

    db = _RunnerDB(
        prior_messages=[
            {"role": "assistant", "content": "connect: /dashboard/integrations"}
        ]
    )
    missing = [
        {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
    ]
    assert await os_thread_runner._post_connect_prompt(db, "t1", "th-1", missing) is None
    assert db.inserts == []


@pytest.mark.asyncio
async def test_runner_never_raises_into_the_turn():
    from backend.services import os_thread_runner

    db = MagicMock()
    db.table.side_effect = RuntimeError("db down")
    missing = [
        {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
    ]
    assert await os_thread_runner._post_connect_prompt(db, "t1", "th-1", missing) is None


@pytest.mark.asyncio
async def test_engine_context_carries_missing_connectors(monkeypatch):
    """Full-turn test: missing connector -> context['integrations'] set,
    connect prompt returned as followup_messages."""
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

    seen_context = {}

    def _orchestrate(client_id, content, context, force_agent_id=None):
        seen_context.update(context)
        return {"result": {}}

    monkeypatch.setattr(
        os_thread_runner.agent_sdk_client, "orchestrate_sync", _orchestrate
    )
    monkeypatch.setattr(
        os_thread_runner.agent_os_bridge,
        "persist_orchestration",
        lambda db, cid, tid, out: {
            "assistant_message": {"id": "a1", "role": "assistant", "content": "ok"},
            "status": "answered",
        },
    )

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(os_thread_runner, "_mirror_to_channel", _noop)
    monkeypatch.setattr(
        os_thread_runner.os_graph_memory, "accumulate_background", _noop
    )
    monkeypatch.setattr(
        os_thread_runner.connector_awareness,
        "missing_for_message",
        lambda db, cid, text: [
            {"key": "hubspot", "label": "HubSpot", "path": "/dashboard/integrations"}
        ],
    )

    db = _RunnerDB()
    out = await os_thread_runner.process_user_turn(
        db, "t1", "th-1", {"id": "m1", "content": "push this to hubspot"}, None
    )

    assert seen_context["integrations"]["missing_for_this_request"] == ["hubspot"]
    assert out["followup_messages"]
    assert "/dashboard/integrations" in out["followup_messages"][0]["content"]


@pytest.mark.asyncio
async def test_no_followup_when_everything_connected(monkeypatch):
    from backend.services import os_thread_runner

    monkeypatch.setattr(
        os_thread_runner.agent_sdk_client, "is_configured", lambda: False
    )

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(os_thread_runner, "_mirror_to_channel", _noop)
    monkeypatch.setattr(
        os_thread_runner.os_failure_notify, "notify_agent_failure", _noop
    )
    monkeypatch.setattr(
        os_thread_runner.connector_awareness,
        "missing_for_message",
        lambda db, cid, text: [],
    )

    db = _RunnerDB()
    out = await os_thread_runner.process_user_turn(
        db, "t1", "th-1", {"id": "m1", "content": "hello"}, None
    )
    # Engine offline path returns no followup key at all - additive shape.
    assert not out.get("followup_messages")
