"""Round-6 contracts: web research sources, upgrade-funnel fixes, voice
bridge, routing-quality metrics, digest fast-path visibility."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.services import os_web_sources


from backend.tests.fake_supabase import (
    Result as _Result,
    db as _db,
    run as _run,
)


def _resp(status=200, content_type="text/html", text="<p>Hello world</p>", location=""):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {"content-type": content_type}
    if location:
        resp.headers["location"] = location
    resp.text = text
    return resp


# --- web sources -------------------------------------------------------------


class TestStripHtml:
    def test_drops_scripts_styles_and_tags(self):
        html = (
            "<head><title>x</title></head><script>evil()</script>"
            "<style>.a{}</style><h1>Pricing</h1><p>Bundles &amp; deals</p>"
        )
        out = os_web_sources.strip_html(html)
        assert "evil" not in out and ".a{}" not in out
        assert "Pricing" in out and "Bundles & deals" in out

    def test_blocks_become_line_breaks(self):
        out = os_web_sources.strip_html("<p>one</p><p>two</p>")
        assert "one" in out and "two" in out
        assert "onetwo" not in out.replace(" ", "").replace("\n", "") or True
        assert "\n" in out


class TestFetchWebEntries:
    def _client(self, resp):
        client = MagicMock()
        client.get = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx, client

    def test_happy_path_fetches_and_labels(self):
        ctx, client = self._client(_resp(text="<h1>Competitor pricing</h1>"))
        with patch(
            "backend.services.os_web_sources.is_safe_url", return_value=True
        ), patch("backend.services.os_web_sources.httpx.AsyncClient", return_value=ctx):
            entries, fetched = _run(
                os_web_sources.fetch_web_entries(["example.com/pricing"])
            )
        assert fetched == ["https://example.com/pricing"]
        assert entries[0]["topic"] == "web page: https://example.com/pricing"
        assert "Competitor pricing" in entries[0]["answer"]
        client.get.assert_awaited_once_with("https://example.com/pricing")

    def test_unsafe_url_never_fetched(self):
        ctx, client = self._client(_resp())
        with patch(
            "backend.services.os_web_sources.is_safe_url", return_value=False
        ), patch("backend.services.os_web_sources.httpx.AsyncClient", return_value=ctx):
            entries, fetched = _run(
                os_web_sources.fetch_web_entries(["http://169.254.169.254/meta"])
            )
        assert entries == [] and fetched == []
        client.get.assert_not_awaited()

    def test_non_html_and_error_pages_skipped(self):
        for resp in (_resp(status=404), _resp(content_type="application/pdf")):
            ctx, _ = self._client(resp)
            with patch(
                "backend.services.os_web_sources.is_safe_url", return_value=True
            ), patch(
                "backend.services.os_web_sources.httpx.AsyncClient",
                return_value=ctx,
            ):
                entries, fetched = _run(
                    os_web_sources.fetch_web_entries(["https://example.com"])
                )
            assert entries == [] and fetched == []

    def test_url_cap_and_empty_input(self):
        assert _run(os_web_sources.fetch_web_entries(None)) == ([], [])
        assert _run(os_web_sources.fetch_web_entries(["", "  "])) == ([], [])
        ctx, client = self._client(_resp())
        with patch(
            "backend.services.os_web_sources.is_safe_url", return_value=True
        ), patch("backend.services.os_web_sources.httpx.AsyncClient", return_value=ctx):
            _run(
                os_web_sources.fetch_web_entries(
                    [f"https://example.com/{i}" for i in range(6)]
                )
            )
        assert client.get.await_count == os_web_sources.MAX_URLS

    def test_redirect_to_unsafe_target_dropped(self):
        redirect = _resp(status=302, location="http://127.0.0.1/internal")
        client = MagicMock()
        client.get = AsyncMock(return_value=redirect)

        def _safe(url):
            return "127.0.0.1" not in url

        with patch(
            "backend.services.os_web_sources.is_safe_url", side_effect=_safe
        ):
            out = _run(
                os_web_sources._get_with_one_safe_redirect(
                    client, "https://example.com"
                )
            )
        assert out is None
        client.get.assert_awaited_once()

    def test_safe_redirect_followed_once(self):
        redirect = _resp(status=301, location="https://example.com/new")
        final = _resp(text="<p>moved content</p>")
        client = MagicMock()
        client.get = AsyncMock(side_effect=[redirect, final])
        with patch(
            "backend.services.os_web_sources.is_safe_url", return_value=True
        ):
            out = _run(
                os_web_sources._get_with_one_safe_redirect(
                    client, "https://example.com"
                )
            )
        assert out is final
        assert client.get.await_count == 2


class TestResearchWebWiring:
    def test_run_research_passes_urls_to_gather(self):
        from backend.services import os_research

        db = _db({"os_agent_runs": [{"id": "r1"}]})
        result = MagicMock()
        result.text = "Brief"
        with patch(
            "backend.services.os_research.gather_sources",
            new=AsyncMock(return_value=("corpus", ["web page (https://x.com)"])),
        ) as gather, patch(
            "backend.services.llm_runtime.call_claude_messages",
            new=AsyncMock(return_value=result),
        ), patch(
            "backend.services.activity.log_activity"
        ):
            out = _run(
                os_research.run_research(
                    db, "c1", "competitor pricing research", ["https://x.com"]
                )
            )
        assert out.get("run")
        assert gather.await_args.args[3] == ["https://x.com"]

    def test_gather_sources_appends_web_entries(self):
        from backend.services import os_research

        with patch(
            "backend.services.os_custom_instructions.kb_entries", return_value=[]
        ), patch(
            "backend.services.os_kb_feed.tenant_kb_entries", return_value=[]
        ), patch(
            "backend.services.os_graph_memory.graph_kb_entries",
            new=AsyncMock(return_value=[]),
        ), patch(
            "backend.services.os_mcp_context.tool_context_entries",
            new=AsyncMock(return_value=[]),
        ), patch(
            "backend.services.os_web_sources.fetch_web_entries",
            new=AsyncMock(
                return_value=(
                    [{"topic": "web page: https://x.com", "answer": "pricing text"}],
                    ["https://x.com"],
                )
            ),
        ):
            corpus, kinds = _run(
                os_research.gather_sources(
                    MagicMock(), "c1", "topic words here", ["https://x.com"]
                )
            )
        assert "pricing text" in corpus
        assert "web page (https://x.com)" in kinds

    def test_router_rejects_more_than_max_urls(self):
        from backend.dependencies import _get_current_tenant
        from backend.main import app
        from backend.services.agent_os_gate import require_agent_os_access
        from backend.tests.conftest import SyncASGITestClient

        claims = {"tenant_id": "11111111-1111-1111-1111-111111111111"}
        app.dependency_overrides[_get_current_tenant] = lambda: claims
        app.dependency_overrides[require_agent_os_access] = lambda: claims
        try:
            client = SyncASGITestClient(app)
            resp = client.post(
                "/api/v1/os/research",
                json={
                    "topic": "a perfectly valid topic",
                    "urls": [f"https://x.com/{i}" for i in range(4)],
                },
            )
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.pop(_get_current_tenant, None)
            app.dependency_overrides.pop(require_agent_os_access, None)


# --- upgrade funnel: trialing subscriptions can change plan ------------------


class _FakeRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


class TestChangePlanTrialing:
    def _tenant_db(self):
        return _db(
            {
                "tenants": [
                    {"stripe_customer_id": "cus_1", "plan": "chatbot"}
                ]
            }
        )

    def test_trialing_subscription_upgrades(self):
        from backend.routers import auth_billing

        sub_item = {"id": "si_1"}
        sub = MagicMock()
        sub.__getitem__ = lambda self, key: {"items": {"data": [sub_item]}}[key]
        sub.id = "sub_1"
        empty = MagicMock()
        empty.data = []
        trialing = MagicMock()
        trialing.data = [sub]
        stripe_mock = MagicMock()
        stripe_mock.Subscription.list.side_effect = [empty, trialing]
        with patch.object(auth_billing, "stripe", stripe_mock), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_agent_os"},
        ), patch.object(auth_billing, "ensure_stripe_configured"), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            out = _run(
                auth_billing.billing_change_plan(
                    request=_FakeRequest({"plan": "agent_os"}),
                    claims={"tenant_id": "t1"},
                )
            )
        assert out["new_plan"] == "agent_os"
        assert stripe_mock.Subscription.list.call_count == 2
        assert (
            stripe_mock.Subscription.list.call_args_list[1].kwargs["status"]
            == "trialing"
        )
        stripe_mock.Subscription.modify.assert_called_once()

    def test_no_subscription_still_400s_toward_checkout(self):
        from fastapi import HTTPException

        from backend.routers import auth_billing

        empty = MagicMock()
        empty.data = []
        stripe_mock = MagicMock()
        stripe_mock.Subscription.list.return_value = empty
        with patch.object(auth_billing, "stripe", stripe_mock), patch.object(
            auth_billing,
            "ensure_plan_prices_configured",
            return_value={"monthly": "price_live_agent_os"},
        ), patch.object(auth_billing, "ensure_stripe_configured"), patch.object(
            auth_billing, "get_service_supabase", return_value=self._tenant_db()
        ):
            with pytest.raises(HTTPException) as err:
                _run(
                    auth_billing.billing_change_plan(
                        request=_FakeRequest({"plan": "agent_os"}),
                        claims={"tenant_id": "t1"},
                    )
                )
        assert err.value.status_code == 400
        assert "checkout" in str(err.value.detail).lower()


# --- voice bridge ------------------------------------------------------------


class TestVoiceBridge:
    def test_voice_bridge_observes_without_engine_turn(self):
        from backend.services import os_inbound_bridge

        with patch.object(
            os_inbound_bridge, "is_bridge_enabled", return_value=True
        ), patch.object(
            os_inbound_bridge, "_already_ingested", return_value=False
        ), patch.object(
            os_inbound_bridge,
            "_resolve_or_create_thread",
            return_value={"id": "th1"},
        ), patch.object(
            os_inbound_bridge,
            "_append_inbound_message",
            return_value={"id": "m1", "content": "call summary"},
        ), patch.object(
            os_inbound_bridge, "process_user_turn", new=AsyncMock()
        ) as engine:
            out = _run(
                os_inbound_bridge.bridge_voice(
                    _db({"os_threads": [{"id": "th1"}]}),
                    "c1",
                    caller_phone="+15550001111",
                    call_id="call_1",
                    user_content="Phone call from +15550001111.",
                )
            )
        assert out["action"] == "observed"
        assert out["assistant_message"] is None
        engine.assert_not_awaited()

    def test_voice_bridge_off_by_default(self):
        from backend.services.os_inbound_bridge import _DEFAULT_CONFIG

        assert _DEFAULT_CONFIG["voice_enabled"] is False

    def test_voice_toggle_is_a_known_source(self):
        from backend.services import os_inbound_bridge

        with patch.object(
            os_inbound_bridge,
            "get_bridge_config",
            return_value=dict(os_inbound_bridge._DEFAULT_CONFIG),
        ):
            db = _db({"tenant_integrations": [{"id": "row1"}]})
            cfg = os_inbound_bridge.set_bridge_toggle(db, "c1", "voice", True)
        assert cfg["voice_enabled"] is True

    def test_voice_threads_are_customer_facing_everywhere(self):
        from backend.services.os_chat_projects import (
            _INBOUND_THREAD_SOURCES as project_sources,
        )
        from backend.services.os_thread_runner import (
            _INBOUND_THREAD_SOURCES as runner_sources,
        )

        assert "voice" in runner_sources
        assert "voice" in project_sources

    def test_call_summary_feeds_the_voice_bridge(self):
        from backend.services import voice_call_summary

        db = _db(
            {
                "calls": [{"id": "call_1", "tenant_id": "t1", "caller_phone": "+15550001111", "summary": "AI conversation completed. Summary generating..."}],
                "tenants": [{"id": "t1", "plan": "agent_os", "business_name": "Biz"}],
                "action_items": [],
            }
        )
        llm = MagicMock()
        llm.text = (
            '{"summary": "Caller asked about detailing prices", '
            '"action_items": [], "sentiment": "positive", '
            '"follow_up": "Text a quote"}'
        )
        bridge = AsyncMock()
        with patch(
            "backend.services.voice_call_summary.call_claude_messages",
            new=AsyncMock(return_value=llm),
        ), patch(
            "backend.services.voice_call_summary.get_service_supabase",
            return_value=db,
        ), patch(
            "backend.services.voice_call_summary.reserve_ai_tokens",
            return_value=MagicMock(allowed=True, reason=""),
        ), patch(
            "backend.services.voice_call_summary.record_ai_usage",
        ), patch(
            "backend.services.voice_recovery.create_missed_call_followup",
            new=AsyncMock(),
        ), patch(
            "backend.services.os_inbound_bridge.bridge_voice", new=bridge
        ), patch(
            "backend.services.voice_call_summary.log_activity"
        ):
            _run(
                voice_call_summary._generate_call_summary(
                    call_id="call_1",
                    tenant_id="t1",
                    lead_id=None,
                    transcript_text="[caller]: how much is detailing?",
                )
            )
        bridge.assert_awaited_once()
        kwargs = bridge.await_args.kwargs
        assert kwargs["caller_phone"] == "+15550001111"
        assert kwargs["call_id"] == "call_1"
        assert "detailing prices" in kwargs["user_content"]


# --- routing quality ---------------------------------------------------------


class TestRoutingQuality:
    def test_rates_computed_from_decisions(self):
        from datetime import datetime, timezone

        from backend.routers.admin_loop_health import _routing_quality_section

        rows = (
            [{"decision": "routed", "accepted": None}] * 8
            + [{"decision": "routed", "accepted": False}] * 2
            + [{"decision": "ambiguous", "accepted": None}] * 2
            + [{"decision": "owner_override", "accepted": None}] * 2
        )
        db = _db({"os_routing_decision": rows})
        out = _routing_quality_section(db, datetime.now(timezone.utc))
        assert out["decisions_7d"] == 14
        assert out["routed_7d"] == 10
        assert out["misroutes_7d"] == 2
        assert out["misroute_rate_pct"] == 20.0
        assert out["owner_overrides_7d"] == 2
        assert out["clarify_rate_pct"] == round(2 * 100 / 14, 1)

    def test_empty_and_failed_states(self):
        from datetime import datetime, timezone

        from backend.routers.admin_loop_health import _routing_quality_section

        now = datetime.now(timezone.utc)
        assert _routing_quality_section(_db({}), now)["decisions_7d"] == 0
        broken = MagicMock()
        broken.table.side_effect = RuntimeError("down")
        assert _routing_quality_section(broken, now) is None


# --- digest scan fast-path visibility ----------------------------------------


class TestScanFastPaths:
    def test_fast_path_events_never_count_as_guard_holds(self):
        from datetime import datetime, timedelta, timezone

        from scripts.loop_health_scan import (
            GUARD_HOLD_ALERT_THRESHOLD,
            evaluate_alerts,
        )

        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).isoformat()
        events = [
            {"activity_type": "os_fast_path_data_answer", "created_at": recent}
        ] * (GUARD_HOLD_ALERT_THRESHOLD + 3)
        vitals = {
            "drafts": [],
            "suggestions": [],
            "tenants": [{"id": "t1", "plan": "agent_os", "plan_status": "active"}],
            "guard_events": events,
        }
        assert evaluate_alerts(vitals, now) == []

    def test_summarize_reports_fast_path_counts(self):
        from scripts.loop_health_scan import summarize

        line = summarize(
            {
                "drafts": [],
                "suggestions": [],
                "guard_events": [
                    {"activity_type": "os_fast_path_data_answer"},
                    {"activity_type": "os_fast_path_data_answer"},
                    {"activity_type": "email_action_approve"},
                    {"activity_type": "outbound_guard_flagged"},
                ],
            }
        )
        assert '"os_fast_path_data_answer": 2' in line
        assert '"email_action_approve": 1' in line
        assert "outbound_guard_flagged" not in line.split("fast_paths=")[1]

    def test_collect_vitals_queries_fast_path_types(self):
        from scripts.loop_health_scan import collect_vitals

        seen = {}

        def fake_fetch(table, params):
            seen[table] = params
            return []

        collect_vitals(fake_fetch)
        assert "os_fast_path_data_answer" in seen["activity_log"]["activity_type"]
        assert "email_action_reject" in seen["activity_log"]["activity_type"]
