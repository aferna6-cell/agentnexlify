"""Round-7 contracts: stage-3 plan gate, audit-batch consolidation
(shared constants), calls.py split surface, and the owner-facing MCP
server (mount, header auth, key endpoints)."""

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("TESTING", "1")

from backend.tests.fake_supabase import db as _db


def _gated(router) -> bool:
    from backend.services.agent_os_gate import require_agent_os_access

    return any(
        getattr(dep, "dependency", None) is require_agent_os_access
        for dep in (router.dependencies or [])
    )


# --- item 1: stage-3 plan gate ----------------------------------------------


class TestStage3Gate:
    def test_all_ten_remaining_authed_os_routers_are_gated(self):
        from backend.routers import (
            os_agent_runs,
            os_backlog,
            os_files,
            os_graph,
            os_insights,
            os_memory,
            os_run_trace,
            os_sync,
            os_usage,
            os_usage_breakdown,
        )

        for module in (
            os_agent_runs,
            os_backlog,
            os_files,
            os_graph,
            os_insights,
            os_memory,
            os_run_trace,
            os_sync,
            os_usage,
            os_usage_breakdown,
        ):
            assert _gated(module.router), f"{module.__name__} lost the stage-3 gate"

    def test_public_surfaces_stay_ungated(self):
        from backend.routers import os_email_actions, os_inbound

        assert not _gated(os_email_actions.router)
        assert not _gated(os_inbound.router)


# --- item 2: audit batch - single-sourced constants and helpers --------------


class TestSingleSources:
    def test_inbound_thread_sources_is_one_object(self):
        from backend.services.os_chat_projects import (
            _INBOUND_THREAD_SOURCES as project_sources,
        )
        from backend.services.os_constants import INBOUND_THREAD_SOURCES
        from backend.services.os_thread_runner import (
            _INBOUND_THREAD_SOURCES as runner_sources,
        )

        assert project_sources is INBOUND_THREAD_SOURCES
        assert runner_sources is INBOUND_THREAD_SOURCES
        assert INBOUND_THREAD_SOURCES == {
            "widget",
            "email",
            "sms",
            "facebook",
            "instagram",
            "voice",
        }


# --- item 3: calls.py split -------------------------------------------------


class TestCallsSplit:
    def test_all_call_routes_survive_the_split(self):
        from backend.routers import calls

        paths = {r.path for r in calls.router.routes}
        assert {
            "/api/v1/calls/voice/call-status",
            "/api/v1/calls/voice/incoming",
            "/api/v1/calls/voice/respond",
            "/api/v1/calls/voice/recording-complete",
            "/api/v1/calls/voice/transcription-complete",
            "/api/v1/calls/{tenant_id}",
            "/api/v1/calls/{tenant_id}/stats",
            "/api/v1/calls/{tenant_id}/{call_id}",
        } <= paths

    def test_back_compat_reexports_are_the_moved_functions(self):
        from backend.routers import calls
        from backend.services import voice_phone_routing

        assert calls._find_tenant_by_phone is voice_phone_routing._find_tenant_by_phone
        assert calls._ai_voice_mode is voice_phone_routing._ai_voice_mode
        assert calls._AI_VOICE_PLANS is voice_phone_routing._AI_VOICE_PLANS


# --- item 4: owner-facing MCP server ----------------------------------------


class TestMcpServer:
    def test_mcp_app_is_mounted(self):
        from backend.main import app

        mounts = [r.path for r in app.routes if r.__class__.__name__ == "Mount"]
        assert "/mcp" in mounts

    def test_all_six_tools_registered(self):
        from backend import mcp_server

        assert set(mcp_server.mcp._tool_manager._tools) == {
            "list_recent_leads",
            "list_today_appointments",
            "get_unread_conversations",
            "get_action_items",
            "get_analytics_summary",
            "reply_to_conversation",
        }

    def test_header_api_key_reads_bearer(self):
        from backend import mcp_server

        request = MagicMock()
        request.headers = {"authorization": "Bearer mcp_abc123"}
        ctx = MagicMock()
        ctx.request_context.request = request
        with patch.object(mcp_server.mcp, "get_context", return_value=ctx):
            assert mcp_server._header_api_key() == "mcp_abc123"

    def test_header_api_key_falls_back_to_x_api_key(self):
        from backend import mcp_server

        request = MagicMock()
        request.headers = {"x-api-key": "mcp_xyz"}
        ctx = MagicMock()
        ctx.request_context.request = request
        with patch.object(mcp_server.mcp, "get_context", return_value=ctx):
            assert mcp_server._header_api_key() == "mcp_xyz"

    def test_header_api_key_empty_outside_http(self):
        from backend import mcp_server

        with patch.object(
            mcp_server.mcp, "get_context", side_effect=ValueError("no ctx")
        ):
            assert mcp_server._header_api_key() == ""

    def test_lookup_uses_header_when_no_explicit_key(self):
        from backend import mcp_server

        tenant = {"id": "t1", "business_name": "Biz", "mcp_enabled": True}
        db = _db({"tenants": [tenant]})
        with patch.object(
            mcp_server, "_header_api_key", return_value="mcp_headerkey"
        ), patch.object(mcp_server, "get_service_supabase", return_value=db):
            assert mcp_server._get_tenant_by_api_key("") == tenant

    def test_lookup_rejects_non_mcp_prefix(self):
        from backend import mcp_server

        with patch.object(mcp_server, "_header_api_key", return_value=""):
            # Widget keys (anx_...) must never authenticate the MCP surface.
            assert mcp_server._get_tenant_by_api_key("anx_widgetkey") is None
            assert mcp_server._get_tenant_by_api_key("") is None

    def test_tool_reports_error_text_on_bad_key(self):
        from backend import mcp_server

        with patch.object(mcp_server, "_get_tenant_by_api_key", return_value=None):
            out = mcp_server.list_recent_leads("anx_wrong")
        assert out.startswith("Error:")


class TestMcpKeyEndpoints:
    def test_generate_endpoint_is_plan_gated(self):
        from backend.main import app
        from backend.services.agent_os_gate import require_agent_os_access

        route = next(
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/auth/mcp-key/{tenant_id}"
            and "POST" in getattr(r, "methods", set())
        )
        deps = [d.call for d in route.dependant.dependencies]
        assert require_agent_os_access in deps

    def test_get_endpoint_exists_and_is_not_plan_gated(self):
        # Reading key state must work on any plan so the setup page can
        # render the upsell instead of erroring.
        from backend.main import app
        from backend.services.agent_os_gate import require_agent_os_access

        route = next(
            r
            for r in app.routes
            if getattr(r, "path", "") == "/api/v1/auth/mcp-key/{tenant_id}"
            and "GET" in getattr(r, "methods", set())
        )
        deps = [d.call for d in route.dependant.dependencies]
        assert require_agent_os_access not in deps
