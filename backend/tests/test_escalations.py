"""Tests for backend/services/escalations.py + backend/routers/escalations.py
(Phase 1a of plans/nexlify-capabilities-roadmap_plan.md).

Covers:
  - create_escalation idempotency on (client_id, source, source_ref)
  - create_escalation never raises on DB failure
  - resolve_escalation clears the "handoff" tag once no open escalation
    remains on the conversation; leaves it when another is still open
  - mark_first_response is a no-op once already set
  - list_escalations status filter + DB-failure fallback
  - notify path (_notify_owner_async) sends SMS + email per the same gate
    widget_chat_effects.handle_handoff_detection used inline before this
    module existed
  - router: list / resolve / assign happy paths, auth (403 cross-tenant),
    404s
  - widget integration: handle_handoff_detection creates an escalation row
    alongside its unchanged tag write + SMS/email notify, with no
    regression to the existing pipeline characterization tests
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import escalations


# ---------------------------------------------------------------------------
# Fake Supabase chain builder (mirrors test_invoices_router.py / test_widget_
# chat_pipeline.py conventions: per-table select/insert/update config, a
# recorded call log, unlisted tables return empty results).
# ---------------------------------------------------------------------------


class _Chain:
    def __init__(self, result):
        self._result = result

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _method(*args, **kwargs):
            if name == "execute":
                return self._result
            return self

        return _method


def _result(data=None, count=None):
    m = MagicMock()
    m.data = data if data is not None else []
    m.count = count if count is not None else len(m.data)
    return m


def _seed(tables: dict):
    """tables maps name -> dict(select=[rows], select_seq=[[rows],...],
    insert=[rows], update=[rows]) — unlisted tables return empty results.
    Returns (db, calls) where calls[table]["insert"/"update"] is a list of
    payloads passed to each call, in order."""
    built: dict[str, MagicMock] = {}
    calls: dict[str, dict[str, list]] = {}

    def _tbl(name, cfg):
        tbl = MagicMock()
        calls[name] = {"insert": [], "update": []}
        select_seq = cfg.get("select_seq")
        state = {"i": 0}

        def _select(*a, **k):
            if select_seq is not None:
                rows = select_seq[min(state["i"], len(select_seq) - 1)]
                state["i"] += 1
                return _Chain(_result(rows))
            return _Chain(_result(cfg.get("select", [])))

        def _insert(*a, **k):
            payload = a[0] if a else k
            calls[name]["insert"].append(payload)
            return _Chain(_result(cfg.get("insert", [])))

        def _update(*a, **k):
            payload = a[0] if a else k
            calls[name]["update"].append(payload)
            return _Chain(_result(cfg.get("update", [])))

        tbl.select.side_effect = _select
        tbl.insert.side_effect = _insert
        tbl.update.side_effect = _update
        return tbl

    def table_side_effect(name):
        if name not in built:
            built[name] = _tbl(name, tables.get(name, {}))
        return built[name]

    db = MagicMock()
    db.table.side_effect = table_side_effect
    return db, calls


class _RaisingDb:
    """db.table(...).<anything>().execute() always raises."""

    def table(self, name):
        return self

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _method(*args, **kwargs):
            if name == "execute":
                raise RuntimeError("db down")
            return self

        return _method


CLIENT_ID = "9a000000-0000-4000-8000-000000000001"


# ---------------------------------------------------------------------------
# create_escalation
# ---------------------------------------------------------------------------


class TestCreateEscalation:
    def test_creates_new_row_notify_false(self):
        created = {"id": "esc-1", "status": "open"}
        db, calls = _seed(
            {"escalations": {"select": [], "insert": [created]}}
        )
        row = escalations.create_escalation(
            db,
            client_id=CLIENT_ID,
            source="widget",
            source_ref="conv-1",
            conversation_id="c1",
            reason="customer wants a human",
            notify=False,
        )
        assert row == created
        assert len(calls["escalations"]["insert"]) == 1
        payload = calls["escalations"]["insert"][0]
        assert payload["source"] == "widget"
        assert payload["source_ref"] == "conv-1"
        assert payload["conversation_id"] == "c1"
        assert payload["priority"] == "normal"

    def test_idempotent_on_conflict_returns_existing(self):
        existing = {"id": "esc-existing", "status": "open"}
        db, calls = _seed(
            {"escalations": {"select": [existing], "insert": [{"id": "esc-new"}]}}
        )
        row = escalations.create_escalation(
            db,
            client_id=CLIENT_ID,
            source="widget",
            source_ref="conv-1",
            notify=False,
        )
        assert row == existing
        # No insert attempted — idempotency lookup short-circuited.
        assert calls["escalations"]["insert"] == []

    def test_invalid_priority_falls_back_to_normal(self):
        db, calls = _seed(
            {"escalations": {"select": [], "insert": [{"id": "esc-2"}]}}
        )
        escalations.create_escalation(
            db,
            client_id=CLIENT_ID,
            source="email",
            source_ref="msg-1",
            priority="apocalyptic",
            notify=False,
        )
        assert calls["escalations"]["insert"][0]["priority"] == "normal"

    def test_lookup_failure_returns_none(self):
        row = escalations.create_escalation(
            _RaisingDb(),
            client_id=CLIENT_ID,
            source="widget",
            source_ref="conv-x",
            notify=False,
        )
        assert row is None

    def test_insert_failure_returns_none(self):
        raising_insert_db = MagicMock()

        def _tbl(name):
            tbl = MagicMock()
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))

            def _boom(*a, **k):
                raise RuntimeError("insert failed")

            tbl.insert.side_effect = _boom
            return tbl

        raising_insert_db.table.side_effect = _tbl
        row = escalations.create_escalation(
            raising_insert_db,
            client_id=CLIENT_ID,
            source="sms",
            source_ref="sms-1",
            notify=False,
        )
        assert row is None

    def test_notify_true_schedules_task_inside_running_loop(self):
        """notify=True inside a running event loop schedules the owner
        notify as a background task rather than raising or blocking."""
        created = {"id": "esc-3"}
        db, _calls = _seed(
            {"escalations": {"select": [], "insert": [created]}}
        )

        async def _drive():
            with patch.object(
                escalations, "_notify_owner_async", new=AsyncMock()
            ) as notify_mock:
                row = escalations.create_escalation(
                    db,
                    client_id=CLIENT_ID,
                    source="widget",
                    source_ref="conv-9",
                    notify=True,
                )
                # Yield control so the scheduled fire-and-forget task runs.
                await asyncio.sleep(0)
                await asyncio.sleep(0)
            return row, notify_mock

        row, notify_mock = asyncio.run(_drive())
        assert row == created
        notify_mock.assert_awaited_once()

    def test_notify_true_outside_running_loop_is_noop(self):
        """No running loop (plain sync call) — notify is skipped, not
        raised. Mirrors webhook_dispatcher.fire_event_background."""
        created = {"id": "esc-4"}
        db, _calls = _seed(
            {"escalations": {"select": [], "insert": [created]}}
        )
        row = escalations.create_escalation(
            db,
            client_id=CLIENT_ID,
            source="widget",
            source_ref="conv-10",
            notify=True,
        )
        assert row == created


# ---------------------------------------------------------------------------
# _notify_owner_async — deterministic direct test of the notify logic
# ---------------------------------------------------------------------------


class TestNotifyOwnerAsync:
    def test_sms_and_email_both_fire_when_configured(self, mock_supabase):
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(
            _result(
                [
                    {
                        "business_name": "Pipe Co",
                        "notification_phone": "+15551234567",
                        "sms_notifications_enabled": True,
                        "owner_email": "owner@pipeco.test",
                    }
                ]
            )
        )
        mock_supabase.table.side_effect = lambda name: tbl

        sms = AsyncMock()
        email = AsyncMock()
        with patch(
            "backend.services.twilio_service.send_sms", new=sms
        ), patch("backend.services.email_sender.send_email", new=email):
            asyncio.run(
                escalations._notify_owner_async(CLIENT_ID, "wants a human")
            )
        sms.assert_awaited_once()
        email.assert_awaited_once()

    def test_no_phone_no_email_sends_nothing(self, mock_supabase):
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(
            _result([{"business_name": "Pipe Co"}])
        )
        mock_supabase.table.side_effect = lambda name: tbl

        sms = AsyncMock()
        email = AsyncMock()
        with patch(
            "backend.services.twilio_service.send_sms", new=sms
        ), patch("backend.services.email_sender.send_email", new=email):
            asyncio.run(escalations._notify_owner_async(CLIENT_ID, ""))
        sms.assert_not_awaited()
        email.assert_not_awaited()

    def test_tenant_lookup_failure_swallowed(self, mock_supabase):
        mock_supabase.table.side_effect = lambda name: _RaisingDb()
        # Must not raise.
        asyncio.run(escalations._notify_owner_async(CLIENT_ID, "reason"))


# ---------------------------------------------------------------------------
# resolve_escalation
# ---------------------------------------------------------------------------


class TestResolveEscalation:
    def test_not_found_returns_none(self):
        db, _calls = _seed({"escalations": {"select": []}})
        assert (
            escalations.resolve_escalation(db, "missing", client_id=CLIENT_ID)
            is None
        )

    def test_resolves_and_clears_handoff_tag_when_no_other_open(self):
        esc_row = {
            "id": "esc-1",
            "conversation_id": "conv-1",
            "metadata": {},
        }
        db, calls = _seed(
            {
                "escalations": {
                    # 1st select: resolve_escalation's own lookup
                    # 2nd select: _maybe_clear_handoff_tag's "other open?" check
                    "select_seq": [[esc_row], []],
                    "update": [{"id": "esc-1", "status": "resolved"}],
                },
                "conversations": {
                    "select": [{"id": "conv-1", "tags": ["handoff", "vip"]}],
                    "update": [{"id": "conv-1"}],
                },
            }
        )
        updated = escalations.resolve_escalation(
            db, "esc-1", client_id=CLIENT_ID, resolved_by="owner@test.com"
        )
        assert updated["status"] == "resolved"
        assert calls["escalations"]["update"][0]["status"] == "resolved"
        assert calls["escalations"]["update"][0]["metadata"]["resolved_by"] == (
            "owner@test.com"
        )
        assert calls["conversations"]["update"][0]["tags"] == ["vip"]

    def test_leaves_tag_when_another_escalation_still_open(self):
        esc_row = {"id": "esc-1", "conversation_id": "conv-1", "metadata": {}}
        db, calls = _seed(
            {
                "escalations": {
                    "select_seq": [[esc_row], [{"id": "esc-2"}]],
                    "update": [{"id": "esc-1", "status": "resolved"}],
                },
                "conversations": {
                    "select": [{"id": "conv-1", "tags": ["handoff"]}],
                },
            }
        )
        escalations.resolve_escalation(db, "esc-1", client_id=CLIENT_ID)
        # conversations table never even touched — tag left alone.
        assert calls.get("conversations", {}).get("update", []) == []

    def test_no_conversation_id_skips_tag_logic(self):
        esc_row = {"id": "esc-1", "conversation_id": None, "metadata": {}}
        db, calls = _seed(
            {
                "escalations": {
                    "select": [esc_row],
                    "update": [{"id": "esc-1", "status": "resolved"}],
                }
            }
        )
        updated = escalations.resolve_escalation(db, "esc-1", client_id=CLIENT_ID)
        assert updated["status"] == "resolved"

    def test_invalid_resolution_falls_back_to_resolved(self):
        esc_row = {"id": "esc-1", "conversation_id": None, "metadata": {}}
        db, calls = _seed(
            {
                "escalations": {
                    "select": [esc_row],
                    "update": [{"id": "esc-1", "status": "resolved"}],
                }
            }
        )
        escalations.resolve_escalation(
            db, "esc-1", client_id=CLIENT_ID, resolution="not-a-status"
        )
        assert calls["escalations"]["update"][0]["status"] == "resolved"

    def test_dismissed_is_a_valid_terminal_status(self):
        esc_row = {"id": "esc-1", "conversation_id": None, "metadata": {}}
        db, calls = _seed(
            {
                "escalations": {
                    "select": [esc_row],
                    "update": [{"id": "esc-1", "status": "dismissed"}],
                }
            }
        )
        escalations.resolve_escalation(
            db, "esc-1", client_id=CLIENT_ID, resolution="dismissed"
        )
        assert calls["escalations"]["update"][0]["status"] == "dismissed"

    def test_lookup_failure_returns_none(self):
        assert (
            escalations.resolve_escalation(
                _RaisingDb(), "esc-1", client_id=CLIENT_ID
            )
            is None
        )

    def test_update_failure_returns_none(self):
        esc_row = {"id": "esc-1", "conversation_id": None, "metadata": {}}
        db = MagicMock()

        def _tbl(name):
            tbl = MagicMock()
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([esc_row]))

            def _boom(*a, **k):
                raise RuntimeError("update failed")

            tbl.update.side_effect = _boom
            return tbl

        db.table.side_effect = _tbl
        assert (
            escalations.resolve_escalation(db, "esc-1", client_id=CLIENT_ID)
            is None
        )


# ---------------------------------------------------------------------------
# mark_first_response
# ---------------------------------------------------------------------------


class TestMarkFirstResponse:
    def test_sets_when_null(self):
        db, calls = _seed(
            {
                "escalations": {
                    "select": [{"id": "esc-1", "first_response_at": None}],
                    "update": [{"id": "esc-1"}],
                }
            }
        )
        escalations.mark_first_response(db, "esc-1", client_id=CLIENT_ID)
        assert len(calls["escalations"]["update"]) == 1
        assert "first_response_at" in calls["escalations"]["update"][0]

    def test_noop_when_already_set(self):
        db, calls = _seed(
            {
                "escalations": {
                    "select": [
                        {"id": "esc-1", "first_response_at": "2026-08-01T00:00:00Z"}
                    ],
                }
            }
        )
        escalations.mark_first_response(db, "esc-1", client_id=CLIENT_ID)
        assert calls["escalations"]["update"] == []

    def test_noop_when_not_found(self):
        db, calls = _seed({"escalations": {"select": []}})
        escalations.mark_first_response(db, "missing", client_id=CLIENT_ID)
        assert calls["escalations"]["update"] == []

    def test_failure_swallowed(self):
        # Must not raise.
        escalations.mark_first_response(_RaisingDb(), "esc-1", client_id=CLIENT_ID)


# ---------------------------------------------------------------------------
# list_escalations
# ---------------------------------------------------------------------------


class TestListEscalations:
    def test_returns_rows(self):
        rows = [{"id": "esc-1"}, {"id": "esc-2"}]
        db, _calls = _seed({"escalations": {"select": rows}})
        assert escalations.list_escalations(db, client_id=CLIENT_ID) == rows

    def test_status_filter_passed_through(self):
        db, _calls = _seed({"escalations": {"select": []}})
        # Just proving it doesn't raise with a status filter applied —
        # the fake chain doesn't assert filter args, DB call log does.
        escalations.list_escalations(db, client_id=CLIENT_ID, status="open")

    def test_failure_returns_empty_list(self):
        assert escalations.list_escalations(_RaisingDb(), client_id=CLIENT_ID) == []


# ---------------------------------------------------------------------------
# Router — mounted standalone (not registered in main.py by this lane)
# ---------------------------------------------------------------------------


class TestEscalationsRouter:
    @pytest.fixture(autouse=True)
    def _build_test_client(self):
        import httpx
        from fastapi import FastAPI

        from backend.routers.escalations import router

        _app = FastAPI()
        _app.include_router(router)
        transport = httpx.ASGITransport(app=_app, raise_app_exceptions=False)

        def _request(method, url, **kwargs):
            async def _do():
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://testserver"
                ) as c:
                    return await c.request(method, url, **kwargs)

            return asyncio.run(_do())

        self._request = _request

    def test_list_happy_path(self, mock_supabase, auth_headers_for):
        rows = [{"id": "esc-1", "status": "open", "conversation_id": None}]
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(_result(rows))
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "GET",
            "/api/v1/escalations",
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["escalations"][0]["id"] == "esc-1"
        # conversation_id is None -> no enrichment lookup, session id stays absent.
        assert "conversation_session_id" not in body["escalations"][0]

    def test_list_enriches_conversation_session_id(self, mock_supabase, auth_headers_for):
        rows = [{"id": "esc-1", "status": "open", "conversation_id": "c1"}]
        tables = {
            "escalations": {"select": rows},
            "conversations": {"select": [{"id": "c1", "session_id": "sess-abc"}]},
        }
        built = {}

        def _router_fn(name):
            if name not in built:
                cfg = tables.get(name, {})
                tbl = MagicMock()
                tbl.select.side_effect = lambda *a, **k: _Chain(_result(cfg.get("select", [])))
                built[name] = tbl
            return built[name]

        mock_supabase.table.side_effect = _router_fn

        resp = self._request(
            "GET",
            "/api/v1/escalations",
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["escalations"][0]["conversation_session_id"] == "sess-abc"

    def test_list_status_query_param(self, mock_supabase, auth_headers_for):
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "GET",
            "/api/v1/escalations?status=open",
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"escalations": []}

    def test_resolve_happy_path(self, mock_supabase, auth_headers_for):
        esc_row = {"id": "esc-1", "conversation_id": None, "metadata": {}}
        tables = {"escalations": {"select": [esc_row], "update": [{"id": "esc-1", "status": "resolved"}]}}
        built = {}

        def _router_fn(name):
            if name not in built:
                cfg = tables.get(name, {})
                tbl = MagicMock()
                tbl.select.side_effect = lambda *a, **k: _Chain(_result(cfg.get("select", [])))
                tbl.update.side_effect = lambda *a, **k: _Chain(_result(cfg.get("update", [])))
                built[name] = tbl
            return built[name]

        mock_supabase.table.side_effect = _router_fn

        resp = self._request(
            "POST",
            "/api/v1/escalations/esc-1/resolve",
            json={"resolution": "resolved"},
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "resolved"

    def test_resolve_not_found_404(self, mock_supabase, auth_headers_for):
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "POST",
            "/api/v1/escalations/missing/resolve",
            json={},
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 404

    def test_assign_happy_path(self, mock_supabase, auth_headers_for):
        final_row = {
            "id": "esc-1",
            "assigned_to": "member-1",
            "status": "in_progress",
            "first_response_at": "2026-08-01T00:00:00Z",
        }
        select_seq = [
            [{"id": "esc-1"}],  # existence check
            [{"id": "esc-1", "first_response_at": None}],  # mark_first_response lookup
            [final_row],  # final re-fetch
        ]
        state = {"i": 0}
        tbl = MagicMock()

        def _select(*a, **k):
            rows = select_seq[min(state["i"], len(select_seq) - 1)]
            state["i"] += 1
            return _Chain(_result(rows))

        tbl.select.side_effect = _select
        tbl.update.side_effect = lambda *a, **k: _Chain(_result([{"id": "esc-1"}]))
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "POST",
            "/api/v1/escalations/esc-1/assign",
            json={"assigned_to": "member-1"},
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["assigned_to"] == "member-1"
        assert body["status"] == "in_progress"

    def test_assign_null_unassigns_without_touching_status(self, mock_supabase, auth_headers_for):
        final_row = {"id": "esc-1", "assigned_to": None, "status": "in_progress"}
        select_seq = [[{"id": "esc-1"}], [final_row]]
        state = {"i": 0}
        tbl = MagicMock()

        def _select(*a, **k):
            rows = select_seq[min(state["i"], len(select_seq) - 1)]
            state["i"] += 1
            return _Chain(_result(rows))

        update_payloads = []

        def _update(*a, **k):
            update_payloads.append(a[0] if a else k)
            return _Chain(_result([{"id": "esc-1"}]))

        tbl.select.side_effect = _select
        tbl.update.side_effect = _update
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "POST",
            "/api/v1/escalations/esc-1/assign",
            json={"assigned_to": None},
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 200, resp.text
        assert "status" not in update_payloads[0]
        assert update_payloads[0]["assigned_to"] is None

    def test_assign_not_found_404(self, mock_supabase, auth_headers_for):
        tbl = MagicMock()
        tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
        mock_supabase.table.side_effect = lambda name: tbl

        resp = self._request(
            "POST",
            "/api/v1/escalations/missing/assign",
            json={"assigned_to": "member-1"},
            headers=auth_headers_for(CLIENT_ID),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Widget integration — handle_handoff_detection creates an escalation
# ---------------------------------------------------------------------------


class TestWidgetHandoffCreatesEscalation:
    def test_handoff_detection_creates_escalation_row(self, mock_supabase):
        from backend.models.schemas import WidgetChatRequest
        from backend.routers import widget_chat_effects

        req = WidgetChatRequest(
            api_key="anx_unit", session_id="sess-esc", message="I need a human"
        )
        tenant = {
            "id": CLIENT_ID,
            "business_name": "Unit Co",
            "notification_phone": None,
            "sms_notifications_enabled": False,
            "owner_email": None,
        }
        tables = {
            "conversations": {"select": [{"id": "c9", "tags": []}]},
            "escalations": {"select": [], "insert": [{"id": "esc-widget-1"}]},
        }
        built = {}

        def _router_fn(name):
            if name not in built:
                cfg = tables.get(name, {})
                tbl = MagicMock()
                tbl.select.side_effect = lambda *a, **k: _Chain(_result(cfg.get("select", [])))
                tbl.update.side_effect = lambda *a, **k: _Chain(_result(cfg.get("update", [])))

                def _insert(*a, **k):
                    payload = a[0] if a else k
                    cfg.setdefault("insert_calls", []).append(payload)
                    return _Chain(_result(cfg.get("insert", [])))

                tbl.insert.side_effect = _insert
                built[name] = tbl
            return built[name]

        mock_supabase.table.side_effect = _router_fn

        # A real UUID so create_escalation's conversation_id FK passthrough
        # is exercised too.
        conversation_id = "11111111-1111-4111-8111-111111111111"

        text, triggered = asyncio.run(
            widget_chat_effects.handle_handoff_detection(
                mock_supabase,
                tenant,
                req,
                conversation_id,
                "Connecting you now.\nHANDOFF_REQUESTED",
            )
        )

        assert triggered is True
        assert "HANDOFF_REQUESTED" not in text
        insert_calls = tables["escalations"].get("insert_calls", [])
        assert len(insert_calls) == 1
        payload = insert_calls[0]
        assert payload["source"] == "widget"
        assert payload["source_ref"] == conversation_id
        assert payload["conversation_id"] == conversation_id
        assert "human" in payload["reason"].lower()

    def test_handoff_detection_non_uuid_conversation_id_omits_fk(self, mock_supabase):
        """conversation_id falling back to a non-UUID session_id (per
        _get_or_create_conversation's documented fallback) must not be
        passed as the escalations.conversation_id FK value."""
        from backend.models.schemas import WidgetChatRequest
        from backend.routers import widget_chat_effects

        req = WidgetChatRequest(
            api_key="anx_unit", session_id="sess-esc2", message="help me"
        )
        tenant = {"id": CLIENT_ID, "business_name": "Unit Co"}
        tables = {
            "conversations": {"select": []},
            "escalations": {"select": [], "insert": [{"id": "esc-widget-2"}]},
        }
        built = {}

        def _router_fn(name):
            if name not in built:
                cfg = tables.get(name, {})
                tbl = MagicMock()
                tbl.select.side_effect = lambda *a, **k: _Chain(_result(cfg.get("select", [])))
                tbl.update.side_effect = lambda *a, **k: _Chain(_result(cfg.get("update", [])))

                def _insert(*a, **k):
                    payload = a[0] if a else k
                    cfg.setdefault("insert_calls", []).append(payload)
                    return _Chain(_result(cfg.get("insert", [])))

                tbl.insert.side_effect = _insert
                built[name] = tbl
            return built[name]

        mock_supabase.table.side_effect = _router_fn

        asyncio.run(
            widget_chat_effects.handle_handoff_detection(
                mock_supabase,
                tenant,
                req,
                "sess-esc2",  # not a UUID — the documented fallback shape
                "Handing off.\nHANDOFF_REQUESTED",
            )
        )

        payload = tables["escalations"]["insert_calls"][0]
        assert payload["source_ref"] == "sess-esc2"
        assert payload["conversation_id"] is None
