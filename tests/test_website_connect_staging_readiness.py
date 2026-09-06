"""Website Connect staging readiness — check-only preflight + semantic smoke."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from backend.services.website_connect import (
    PageFetch,
    upsert_connection,
    verify_connection,
)
from backend.tests.test_website_connect import (
    KEY_A,
    KEY_B,
    TENANT_A,
    FakeDB,
    _page,
    _wp_html,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

spec = importlib.util.spec_from_file_location(
    "website_connect_migration201_preflight",
    SCRIPTS / "website_connect_migration201_preflight.py",
)
assert spec is not None and spec.loader is not None
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def _blocked_page(url="https://example.com", error="http_403") -> PageFetch:
    return PageFetch(url=url, html="", headers={"server": "cloudflare"}, ok=False, error=error)


class TestMigration201CheckOnly:
    def test_preflight_is_ready_and_never_applies(self, capsys):
        code = preflight.main([])
        out = capsys.readouterr().out
        assert code == 0
        assert "mode: check-only" in out
        assert "connect → fetch → tenant-widget-key → connected" in out
        assert "drop table if exists website_connections;" in out
        payload = json.loads(out[out.index("{") :])
        assert payload["applied"] is False
        assert payload["deployed"] is False
        assert payload["rollback"]["executed"] is False
        assert payload["migration"]["schema_log_not_applied"] is True
        assert payload["ready"] is True

    def test_apply_flag_is_refused(self, capsys):
        code = preflight.main(["--apply"])
        out = capsys.readouterr().out
        assert code == 3
        assert "applied: False" in out or '"applied": false' in out.lower()
        payload = json.loads(out[out.index("{") :])
        assert payload["apply_requested"] is True
        assert payload["applied"] is False
        assert any("check-only" in item for item in payload["blockers"])

    def test_apply_env_is_refused(self, monkeypatch):
        monkeypatch.setenv("WEBSITE_CONNECT_APPLY", "1")
        report = preflight.run_preflight()
        assert report["apply_requested"] is True
        assert report["applied"] is False
        assert report["ready"] is False

    def test_preconditions_and_bot_blocked_are_explicit(self):
        report = preflight.run_preflight()
        joined = " ".join(report["preconditions"]).lower()
        assert "not apply" in joined or "do not apply" in joined
        assert "bot-blocked" in joined
        assert report["bot_blocked"]["never"] == "connected"
        assert report["bot_blocked"]["verify_status"] == "failed"
        assert report["rollback"]["sql"].startswith("drop table if exists")


class TestConnectFetchKeyConnectedSmoke:
    def test_connect_fetch_tenant_key_marks_connected(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_A), url=url),
        )
        assert row["status"] == "connected"
        assert row["connected"] is True
        assert row["verification_method"] == "html_presence"

    def test_other_tenant_key_is_not_connected(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _page(_wp_html(KEY_B), url=url),
        )
        assert row["status"] != "connected"
        assert row["connected"] is False

    def test_bot_blocked_verify_is_failed_never_connected(self):
        db = FakeDB(
            {
                "website_connections": [
                    {
                        "id": "row-a",
                        "tenant_id": TENANT_A,
                        "website_url": "https://example.com",
                        "platform": "wordpress",
                        "platform_override": False,
                        "status": "needs_action",
                    }
                ],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = verify_connection(
            db,
            TENANT_A,
            fetch_page=lambda url: _blocked_page(url, "http_403"),
        )
        assert row["status"] == "failed"
        assert row["status"] != "connected"
        assert row["connected"] is False
        assert "reach" in (row.get("verification_detail") or "").lower()

    def test_bot_blocked_upsert_stays_needs_action(self):
        db = FakeDB(
            {
                "website_connections": [],
                "widget_configs": [{"tenant_id": TENANT_A, "api_key": KEY_A}],
                "tenants": [],
            }
        )
        row = upsert_connection(
            db,
            TENANT_A,
            "https://example.com",
            fetch_page=lambda url: _blocked_page(url, "fetch_error"),
        )
        assert row["status"] == "needs_action"
        assert row["connected"] is False
