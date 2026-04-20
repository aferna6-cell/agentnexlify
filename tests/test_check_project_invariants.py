from pathlib import Path

import pytest

from scripts import check_project_invariants as invariants


@pytest.fixture(autouse=True)
def _allow_marketing_addon_gate_for_endpoint_tests():
    yield


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def fake_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(invariants, "ROOT", tmp_path)
    monkeypatch.setattr(
        invariants,
        "CODE_ROOTS",
        tuple(
            tmp_path / name
            for name in (
                "backend",
                "frontend",
                "widget",
                "agent-service",
                "ai",
                "chrome-extension",
                "demo-platform",
                "config",
                "tools",
                "supabase",
            )
        ),
    )
    monkeypatch.setattr(invariants, "ROUTER_ROOT", tmp_path / "backend" / "routers")
    monkeypatch.setattr(
        invariants,
        "WIDGET_MIRRORS",
        (
            tmp_path / "frontend" / "public" / "widget",
            tmp_path / "landing-page-v2" / "widget",
        ),
    )
    monkeypatch.setattr(
        invariants,
        "APPROVED_ANTHROPIC_WRAPPER",
        tmp_path / "backend" / "services" / "llm_runtime.py",
    )
    return tmp_path


def test_router_future_import_is_flagged(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        fake_root / "backend" / "routers" / "demo.py",
        "from __future__ import annotations\n",
    )

    failures: list[str] = []
    invariants.check_router_future_imports(failures)

    out = capsys.readouterr().out
    assert failures == ["FastAPI router files avoid future annotations"]
    assert "FAIL FastAPI router files avoid future annotations" in out
    assert "backend/routers/demo.py" in out


def test_widget_mirror_matches_when_bytes_align(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    files = {
        "agentnexlify-widget.js": "console.log('widget');\n",
        "preview.html": "<!doctype html>\n",
    }
    for asset_name, body in files.items():
        _write(fake_root / "widget" / asset_name, body)
        _write(fake_root / "frontend" / "public" / "widget" / asset_name, body)
        _write(fake_root / "landing-page-v2" / "widget" / asset_name, body)

    failures: list[str] = []
    invariants.check_widget_assets(failures)

    out = capsys.readouterr().out
    assert failures == []
    assert "PASS widget assets are byte-identical across mirrors" in out


def test_widget_mirror_drift_is_flagged(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(fake_root / "widget" / "agentnexlify-widget.js", "console.log('widget');\n")
    _write(fake_root / "widget" / "preview.html", "<!doctype html>\n")
    _write(
        fake_root / "frontend" / "public" / "widget" / "agentnexlify-widget.js",
        "console.log('widget');\n",
    )
    _write(fake_root / "frontend" / "public" / "widget" / "preview.html", "<!doctype html>\n")
    _write(
        fake_root / "landing-page-v2" / "widget" / "agentnexlify-widget.js",
        "console.log('widget drift');\n",
    )
    _write(fake_root / "landing-page-v2" / "widget" / "preview.html", "<!doctype html>\n")

    failures: list[str] = []
    invariants.check_widget_assets(failures)

    out = capsys.readouterr().out
    assert failures == ["widget assets are byte-identical across mirrors"]
    assert "FAIL widget assets are byte-identical across mirrors" in out
    assert "drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js" in out


def test_active_backend_live_schema_field_is_flagged(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        fake_root / "backend" / "services" / "lead_sync.py",
        "rows = db.table('leads').select('id,lead_stage').execute()\n",
    )

    failures: list[str] = []
    invariants.check_live_schema_fields(failures)

    out = capsys.readouterr().out
    assert failures == ["active backend code avoids retired live-schema fields"]
    assert "FAIL active backend code avoids retired live-schema fields" in out
    assert "lead_stage" in out


def test_retired_plan_names_in_ignored_path_do_not_fail(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        fake_root / "_archive" / "backend" / "billing" / "schemas.py",
        "plan = 'foundation'\nprice = 'pro'\n",
    )

    failures: list[str] = []
    invariants.check_retired_plan_names(failures)

    out = capsys.readouterr().out
    assert failures == []
    assert "PASS retired plan names do not appear in plan-related code" in out


def test_direct_anthropic_messages_create_outside_wrapper_is_flagged(
    fake_root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        fake_root / "backend" / "services" / "llm_client.py",
        "response = client.messages.create(model='claude', max_tokens=1, messages=[])\n",
    )

    failures: list[str] = []
    invariants.check_anthropic_sdk_usage(failures)

    out = capsys.readouterr().out
    assert failures == [
        "direct Anthropic SDK message creation stays behind the runtime wrapper"
    ]
    assert "FAIL direct Anthropic SDK message creation stays behind the runtime wrapper" in out
    assert "messages.create" in out
