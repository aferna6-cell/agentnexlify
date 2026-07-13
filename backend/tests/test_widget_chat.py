"""Tests for widget chat endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class _Chain:
    """Mimics a Supabase PostgREST query builder.

    Any attribute access returns a chainable callable — calling it returns
    the same `_Chain` instance (so `.select(...).eq(...).eq(...).limit(...)`
    all resolve fine regardless of call shape) — except `.execute()`, which
    returns the canned terminal result.
    """

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


def _result(data=None, count=0):
    return MagicMock(data=data if data is not None else [], count=count)


class TestWidgetChat:
    """POST /api/v1/widget/chat"""

    def test_chat_missing_api_key(self, client):
        """Missing api_key returns 422."""
        resp = client.post("/api/v1/widget/chat", json={
            "message": "Hello",
            "session_id": "sess-123",
        })
        assert resp.status_code == 422

    def test_chat_invalid_api_key(self, client, mock_supabase):
        """Invalid api_key returns 404 (tenant not found)."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.post("/api/v1/widget/chat", json={
            "api_key": "invalid-key",
            "message": "Hello",
            "session_id": "sess-123",
        })
        assert resp.status_code in (404, 400)


class TestWidgetChatDemoPlumbingTenant:
    """Regression test for GH #422 — POST /api/v1/widget/chat 500s for the
    demo plumbing tenant while working fine for real tenants.

    Full end-to-end reproduction: seeds the mock Supabase client with the
    demo tenant's exact field values (business_type=plumbing, plan=professional,
    is_demo=true, bot_name set, booking_enabled/enable_ai_fallback/
    enable_structured_lead_parser all false, non-empty knowledge_base so the
    null-state guard is bypassed) and drives the real router end to end.
    """

    API_KEY = "anx_demo_plumbing_422_test"
    TENANT_ID = "a49be389-1111-2222-3333-444455556666"
    SESSION_ID = "sess-demo-plumbing-422"

    def _seed(self, mock_supabase):
        widget_row = {
            "id": "wc-demo-001",
            "tenant_id": self.TENANT_ID,
            "api_key": self.API_KEY,
            "allowed_domains": None,
            "booking_enabled": False,
            "enable_ai_fallback": False,
            "enable_structured_lead_parser": False,
            "greeting_message": "Hi! Welcome to Reliable Plumbing Co.",
            "teaser_message": "Need a plumber? Chat with us!",
            "bot_name": "Reliable Plumbing Co. (DEMO) Scheduling Desk",
            "pre_chat_form": None,
            "branding": {},
            "show_watermark": True,
            "knowledge_base": (
                "We are Reliable Plumbing Co. We offer leak repair, drain "
                "cleaning, water heater installation, and 24/7 emergency "
                "service. Free estimates on all jobs."
            ),
            "custom_instructions": None,
        }
        tenant_row = {
            "id": self.TENANT_ID,
            "business_name": "Reliable Plumbing Co.",
            "business_type": "plumbing",
            "city": "Austin",
            "plan": "professional",
            "plan_status": "active",
            "is_demo": True,
            "phone": "555-321-7700",
            "free_trial_started_at": None,
            "conversations_used_this_month": 3,
            "sms_notifications_enabled": False,
            "notification_phone": None,
            "owner_email": None,
            "conversation_email_notify_enabled": False,
            "conversation_notify_email": None,
            "ai_monthly_token_alert_threshold": None,
            "ai_monthly_token_hard_limit": None,
        }
        conv_row = {"id": "8b8e6b0a-0000-4000-8000-000000000001"}
        saved_user_row = {
            "id": "cm-0001",
            "role": "user",
            "content": "Hi, do you handle emergency leak repair?",
        }
        saved_assistant_row = {
            "id": "cm-0002",
            "role": "assistant",
            "content": "Canned test reply.",
        }

        tables: dict[str, MagicMock] = {}

        def _widget_configs_tbl():
            tbl = MagicMock()
            tbl.select.side_effect = lambda *a, **k: _Chain(
                _result([widget_row])
            )
            return tbl

        def _tenants_tbl():
            tbl = MagicMock()
            # Covers both `_get_tenant`'s select AND the conversations-used
            # CAS select in the usage-counter increment step — both are
            # `.select(...).eq("id", ...).limit(1).execute()` shaped.
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([tenant_row]))
            tbl.update.side_effect = lambda *a, **k: _Chain(_result([tenant_row]))
            return tbl

        def _conversations_tbl():
            tbl = MagicMock()
            # First lookup (by session_id) → no existing conversation.
            # Handoff-tag lookup later in the flow also returns no rows.
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
            tbl.upsert.side_effect = lambda *a, **k: _Chain(_result([conv_row]))
            tbl.update.side_effect = lambda *a, **k: _Chain(_result([conv_row]))
            return tbl

        def _chat_messages_tbl():
            tbl = MagicMock()
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
            tbl.insert.side_effect = lambda *a, **k: _Chain(
                _result([saved_user_row, saved_assistant_row])
            )
            return tbl

        def _empty_select_tbl():
            tbl = MagicMock()
            tbl.select.side_effect = lambda *a, **k: _Chain(_result([]))
            tbl.insert.side_effect = lambda *a, **k: _Chain(_result([]))
            return tbl

        def table_side_effect(name):
            if name not in tables:
                if name == "widget_configs":
                    tables[name] = _widget_configs_tbl()
                elif name == "tenants":
                    tables[name] = _tenants_tbl()
                elif name == "conversations":
                    tables[name] = _conversations_tbl()
                elif name == "chat_messages":
                    tables[name] = _chat_messages_tbl()
                else:
                    # faq_entries, business_hours, ai_feedback, chat_flows,
                    # tenant_usage_packs, tenant_integrations, etc. — all
                    # empty-result tables not central to this repro.
                    tables[name] = _empty_select_tbl()
            return tables[name]

        mock_supabase.table.side_effect = table_side_effect
        mock_supabase.rpc.side_effect = lambda name, params=None, **k: _Chain(
            _result(True) if name == "reserve_ai_token_budget" else _result({})
        )

    def test_demo_plumbing_tenant_chat_returns_200(self, client, mock_supabase):
        """GH #422 regression: business_type=plumbing + plan=professional +
        is_demo=true must not 500. Response must be a sane 200 with a reply.
        """
        self._seed(mock_supabase)

        canned = MagicMock(
            text="Sure, we handle emergency leak repair 24/7. What's your address?",
            duration_ms=42,
            input_tokens=123,
            output_tokens=17,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            stop_reason="end_turn",
            raw_response=None,
        )

        with patch(
            "backend.routers.widget_chat.call_claude_messages",
            new=AsyncMock(return_value=canned),
        ), patch(
            "backend.routers.widget_chat._query_kb_articles",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.post(
                "/api/v1/widget/chat",
                json={
                    "api_key": self.API_KEY,
                    "message": "Hi, do you handle emergency leak repair?",
                    "session_id": self.SESSION_ID,
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["response"]
        assert body["session_id"] == self.SESSION_ID
        assert body["handoff"] is False


class TestWidgetConfig:
    """GET /api/v1/widget/config/{api_key}"""

    def test_config_invalid_key(self, client, mock_supabase):
        """Invalid api_key returns 404."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        resp = client.get("/api/v1/widget/config/nonexistent-key")
        assert resp.status_code == 404


class TestWidgetChatStringHours(TestWidgetChatDemoPlumbingTenant):
    """GH #422 root cause: demo seeder double-encoded business_hours.hours
    (json.dumps into jsonb), so prod rows hold a JSON *string*. That crashed
    _format_hours_block with AttributeError('str' has no 'get') -> 500.
    This test reproduces the exact prod data shape through the real router.
    """

    SESSION_ID = "sess-demo-string-hours-422"

    def _seed(self, mock_supabase):
        super()._seed(mock_supabase)
        import json as _json

        bh_row = {
            "timezone": "America/Los_Angeles",
            # The prod bug: a JSON STRING, not a dict.
            "hours": _json.dumps(
                {
                    "monday": {"enabled": True, "start": "07:00", "end": "18:00"},
                    "tuesday": {"enabled": True, "start": "07:00", "end": "18:00"},
                }
            ),
        }
        seeded = mock_supabase.table.side_effect

        def route(name):
            if name == "business_hours":
                tbl = MagicMock()
                tbl.select.side_effect = lambda *a, **k: _Chain(_result([bh_row]))
                return tbl
            return seeded(name)

        mock_supabase.table.side_effect = route

    def test_demo_plumbing_tenant_chat_returns_200(self, client, mock_supabase):
        # Same assertions as the parent - the double-encoded hours row is the
        # only difference, and it must not 500.
        super().test_demo_plumbing_tenant_chat_returns_200(client, mock_supabase)


class TestCoerceHours:
    def test_dict_passthrough(self):
        from backend.services.booking import coerce_hours

        hours = {"monday": {"enabled": True}}
        assert coerce_hours(hours) is hours

    def test_double_encoded_string_parsed(self):
        import json

        from backend.services.booking import coerce_hours

        hours = {"monday": {"enabled": True, "start": "07:00", "end": "18:00"}}
        assert coerce_hours(json.dumps(hours)) == hours

    def test_garbage_and_none_return_empty(self):
        from backend.services.booking import coerce_hours

        assert coerce_hours("not json at all") == {}
        assert coerce_hours(None) == {}
        assert coerce_hours(42) == {}
        assert coerce_hours('["a","list"]') == {}

    def test_get_business_hours_normalises(self):
        import json
        from unittest.mock import MagicMock, patch

        from backend.services import booking

        row = {
            "tenant_id": "t1",
            "timezone": "America/New_York",
            "hours": json.dumps({"monday": {"enabled": True}}),
            "slot_duration_minutes": 30,
            "buffer_minutes": 0,
            "max_advance_days": 30,
        }
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[row])
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(booking, "get_service_supabase", return_value=db):
            config = booking.get_business_hours("t1")
        assert config["hours"] == {"monday": {"enabled": True}}
