"""Tests for backend.services.onboarding_workflow phase helpers + orchestrators."""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_db():
    """Chainable mock db for builder-style supabase calls."""
    db = MagicMock()
    return db


def _make_req(**kwargs):
    defaults = {
        "business_name": "Test Co",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": "+15551234567",
        "website_url": "https://example.com",
        "services": ["Service A", "Service B"],
        "faqs": [],
        "hours": None,
        "widget_bot_name": None,
        "widget_primary_color": None,
        "widget_greeting_message": None,
        "widget_position": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _load_tenant
# ---------------------------------------------------------------------------


def test_load_tenant_returns_first_row():
    from backend.services.onboarding_workflow import _load_tenant

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "t1", "business_name": "Test", "business_page_enabled": True}]
    )
    out = _load_tenant(db, "t1")
    assert out["id"] == "t1"
    assert out["business_page_enabled"] is True


def test_load_tenant_raises_404_when_missing():
    from backend.services.onboarding_workflow import _load_tenant

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with pytest.raises(HTTPException) as exc:
        _load_tenant(db, "missing")
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# _update_tenant_record
# ---------------------------------------------------------------------------


def test_update_tenant_record_marks_business_info_configured():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _update_tenant_record,
    )

    db = _make_db()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    _update_tenant_record(db, "t1", _make_req(), res)
    assert res.configured["business_info"] is True
    args, _ = db.table.return_value.update.call_args
    update_payload = args[0]
    assert update_payload["business_name"] == "Test Co"
    assert update_payload["notification_phone"] == "+15551234567"
    assert update_payload["website_url"] == "https://example.com"
    assert update_payload["business_services"] == ["Service A", "Service B"]


def test_update_tenant_record_raises_500_on_db_failure():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _update_tenant_record,
    )

    db = _make_db()
    db.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError("nope")
    with pytest.raises(HTTPException) as exc:
        _update_tenant_record(db, "t1", _make_req(), OnboardingCompleteResult())
    assert exc.value.status_code == 500


def test_update_tenant_record_skips_optional_fields_when_absent():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _update_tenant_record,
    )

    db = _make_db()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    req = _make_req(phone=None, website_url=None, services=None)
    _update_tenant_record(db, "t1", req, OnboardingCompleteResult())
    payload = db.table.return_value.update.call_args[0][0]
    assert "notification_phone" not in payload
    assert "website_url" not in payload
    assert "business_services" not in payload


# ---------------------------------------------------------------------------
# _update_widget_config
# ---------------------------------------------------------------------------


def test_update_widget_config_uses_existing_when_no_override():
    from backend.services.onboarding_workflow import _update_widget_config

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"bot_name": "ExistingBot", "primary_color": "#abcdef", "greeting_message": "hey", "position": "left"}]
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    _update_widget_config(db, "t1", _make_req())
    update_payload = db.table.return_value.update.call_args[0][0]
    assert update_payload["bot_name"] == "ExistingBot"
    assert update_payload["primary_color"] == "#abcdef"


def test_update_widget_config_swallows_read_error():
    from backend.services.onboarding_workflow import _update_widget_config

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
        "boom"
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    _update_widget_config(db, "t1", _make_req(widget_bot_name="MyBot"))
    update_payload = db.table.return_value.update.call_args[0][0]
    assert update_payload["bot_name"] == "MyBot"


def test_update_widget_config_swallows_write_error():
    from backend.services.onboarding_workflow import _update_widget_config

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    db.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError("nope")
    _update_widget_config(db, "t1", _make_req())


# ---------------------------------------------------------------------------
# _apply_industry_pack
# ---------------------------------------------------------------------------


def test_apply_industry_pack_marks_applied():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_industry_pack,
    )

    fake_pack = MagicMock(key="plumbing")
    fake_pack_result = MagicMock(errors=[])

    res = OnboardingCompleteResult()
    with patch("backend.services.industry_packs.load_pack", return_value=fake_pack), patch(
        "backend.services.industry_packs.seed.apply_pack_to_tenant",
        return_value=fake_pack_result,
    ):
        _apply_industry_pack(_make_db(), "t1", _make_req(), res)

    assert res.industry_pack_applied is True
    assert res.configured["industry_pack"] is True
    assert res.industry_pack_key == "plumbing"


def test_apply_industry_pack_swallows_errors():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_industry_pack,
    )

    res = OnboardingCompleteResult()
    with patch(
        "backend.services.industry_packs.load_pack",
        side_effect=RuntimeError("pack missing"),
    ):
        _apply_industry_pack(_make_db(), "t1", _make_req(), res)
    assert res.industry_pack_applied is False


def test_apply_industry_pack_logs_seed_warnings():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_industry_pack,
    )

    fake_pack = MagicMock(key="plumbing")
    fake_pack_result = MagicMock(errors=["soft warning"])
    res = OnboardingCompleteResult()
    with patch("backend.services.industry_packs.load_pack", return_value=fake_pack), patch(
        "backend.services.industry_packs.seed.apply_pack_to_tenant",
        return_value=fake_pack_result,
    ):
        _apply_industry_pack(_make_db(), "t1", _make_req(), res)
    assert res.industry_pack_applied is True


# ---------------------------------------------------------------------------
# _seed_business_hours
# ---------------------------------------------------------------------------


def test_seed_business_hours_skips_when_empty():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_business_hours,
    )

    res = OnboardingCompleteResult()
    _seed_business_hours(_make_db(), "t1", _make_req(hours=None), res)
    assert res.configured["hours"] is False


def test_seed_business_hours_inserts_new_when_none_exist():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_business_hours,
    )

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    _seed_business_hours(db, "t1", _make_req(hours={"Mon": "8-5"}), res)
    assert res.configured["hours"] is True


def test_seed_business_hours_updates_existing():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_business_hours,
    )

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": 99}]
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    _seed_business_hours(
        db,
        "t1",
        _make_req(hours={"Mon": "8-5", "timezone": "America/Chicago"}),
        res,
    )
    assert res.configured["hours"] is True
    payload = db.table.return_value.update.call_args[0][0]
    assert payload["timezone"] == "America/Chicago"


def test_seed_business_hours_swallows_db_error():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_business_hours,
    )

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
        "x"
    )
    res = OnboardingCompleteResult()
    _seed_business_hours(db, "t1", _make_req(hours={"Mon": "8-5"}), res)
    assert res.configured["hours"] is False


# ---------------------------------------------------------------------------
# _trigger_website_crawl
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_website_crawl_skips_when_no_url():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _trigger_website_crawl,
    )

    res = OnboardingCompleteResult()
    await _trigger_website_crawl("t1", _make_req(website_url=None), res)
    assert res.crawl_started is False


@pytest.mark.asyncio
@patch("backend.services.website_crawler.start_crawl", new_callable=AsyncMock)
async def test_trigger_website_crawl_marks_started(mock_start):
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _trigger_website_crawl,
    )

    res = OnboardingCompleteResult()
    await _trigger_website_crawl("t1", _make_req(), res)
    assert res.crawl_started is True
    assert res.configured["website_crawl"] is True
    assert mock_start.await_count == 1


@pytest.mark.asyncio
@patch("backend.services.website_crawler.start_crawl", new_callable=AsyncMock)
async def test_trigger_website_crawl_swallows_errors(mock_start):
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _trigger_website_crawl,
    )

    mock_start.side_effect = RuntimeError("network")
    res = OnboardingCompleteResult()
    await _trigger_website_crawl("t1", _make_req(), res)
    assert res.crawl_started is False


# ---------------------------------------------------------------------------
# _seed_service_faqs
# ---------------------------------------------------------------------------


def test_seed_service_faqs_skips_when_no_services():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_service_faqs,
    )

    res = OnboardingCompleteResult()
    _seed_service_faqs(_make_db(), "t1", _make_req(services=None), res)
    assert res.faqs_created == 0


def test_seed_service_faqs_creates_three_with_phone():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_service_faqs,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    _seed_service_faqs(db, "t1", _make_req(), res)
    assert res.faqs_created == 3
    assert res.configured["faqs"] is True


def test_seed_service_faqs_skips_phone_question_when_no_phone():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_service_faqs,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    _seed_service_faqs(db, "t1", _make_req(phone=None), res)
    assert res.faqs_created == 2


def test_seed_service_faqs_swallows_per_row_errors():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_service_faqs,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.side_effect = RuntimeError("nope")
    res = OnboardingCompleteResult()
    _seed_service_faqs(db, "t1", _make_req(), res)
    assert res.faqs_created == 0
    assert res.configured["faqs"] is False


# ---------------------------------------------------------------------------
# _seed_wizard_faqs
# ---------------------------------------------------------------------------


def test_seed_wizard_faqs_skips_when_empty():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_wizard_faqs,
    )

    res = OnboardingCompleteResult()
    _seed_wizard_faqs(_make_db(), "t1", _make_req(faqs=[]), res)
    assert res.configured["faqs"] is False


def test_seed_wizard_faqs_inserts_rows():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_wizard_faqs,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    faqs = [SimpleNamespace(question="Q1?", answer="A1"), SimpleNamespace(question="Q2?", answer="A2")]
    _seed_wizard_faqs(db, "t1", _make_req(faqs=faqs), res)
    assert res.configured["faqs"] is True
    payload = db.table.return_value.insert.call_args[0][0]
    assert len(payload) == 2
    assert payload[0]["question"] == "Q1?"


def test_seed_wizard_faqs_swallows_errors():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _seed_wizard_faqs,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.side_effect = RuntimeError("x")
    res = OnboardingCompleteResult()
    _seed_wizard_faqs(
        db, "t1", _make_req(faqs=[SimpleNamespace(question="Q", answer="A")]), res
    )
    assert res.configured["faqs"] is False


# ---------------------------------------------------------------------------
# _apply_ai_content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_ai_content_swallows_generator_exception():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_ai_content,
    )

    res = OnboardingCompleteResult()
    fn = AsyncMock(side_effect=RuntimeError("boom"))
    await _apply_ai_content(_make_db(), "t1", _make_req(), res, fn)
    assert res.ai_content_generated is False


@pytest.mark.asyncio
async def test_apply_ai_content_noop_when_empty():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_ai_content,
    )

    res = OnboardingCompleteResult()
    fn = AsyncMock(return_value=None)
    await _apply_ai_content(_make_db(), "t1", _make_req(), res, fn)
    assert res.ai_content_generated is False


@pytest.mark.asyncio
async def test_apply_ai_content_inserts_faqs_and_updates_business_page():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_ai_content,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    res = OnboardingCompleteResult()
    res.tenant = {"business_page_enabled": True}
    fn = AsyncMock(
        return_value={
            "faqs": [{"question": "Q1?", "answer": "A1"}, {"question": "Q2?", "answer": "A2"}],
            "about_section": "About text",
        }
    )
    await _apply_ai_content(db, "t1", _make_req(), res, fn)
    assert res.ai_content_generated is True
    assert res.configured["ai_content"] is True
    assert res.faqs_created == 2


@pytest.mark.asyncio
async def test_apply_ai_content_swallows_faq_insert_error():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_ai_content,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.side_effect = RuntimeError("x")
    res = OnboardingCompleteResult()
    fn = AsyncMock(return_value={"faqs": [{"question": "Q", "answer": "A"}]})
    await _apply_ai_content(db, "t1", _make_req(), res, fn)
    assert res.faqs_created == 0
    assert res.ai_content_generated is True


@pytest.mark.asyncio
async def test_apply_ai_content_skips_business_page_when_disabled():
    from backend.services.onboarding_workflow import (
        OnboardingCompleteResult,
        _apply_ai_content,
    )

    db = _make_db()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()
    res = OnboardingCompleteResult()
    res.tenant = {"business_page_enabled": False}
    fn = AsyncMock(return_value={"faqs": [], "about_section": "About"})
    await _apply_ai_content(db, "t1", _make_req(), res, fn)
    db.table.return_value.update.assert_not_called()


# ---------------------------------------------------------------------------
# _seed_welcome_sequence
# ---------------------------------------------------------------------------


def test_seed_welcome_sequence_skips_when_exists():
    from backend.services.onboarding_workflow import _seed_welcome_sequence

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": 1}]
    )
    _seed_welcome_sequence(db, "t1", _make_req())
    db.table.return_value.insert.assert_not_called()


def test_seed_welcome_sequence_inserts_when_none_exist():
    from backend.services.onboarding_workflow import _seed_welcome_sequence

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "seq-1"}])
    _seed_welcome_sequence(db, "t1", _make_req())
    # First call: insert sequence; second: insert steps
    assert db.table.return_value.insert.call_count == 2


def test_seed_welcome_sequence_bails_when_seq_insert_returns_no_data():
    from backend.services.onboarding_workflow import _seed_welcome_sequence

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    _seed_welcome_sequence(db, "t1", _make_req())
    # Only the sequence insert happened, no steps
    assert db.table.return_value.insert.call_count == 1


def test_seed_welcome_sequence_swallows_errors():
    from backend.services.onboarding_workflow import _seed_welcome_sequence

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
        "x"
    )
    _seed_welcome_sequence(db, "t1", _make_req())


# ---------------------------------------------------------------------------
# run_onboarding_complete (orchestrator)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_onboarding_complete_runs_all_phases():
    from backend.services.onboarding_workflow import run_onboarding_complete

    db = _make_db()
    # _load_tenant returns the tenant
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "t1", "business_name": "Test", "business_page_enabled": False}]
    )
    db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "seq-1"}])

    ai_fn = AsyncMock(return_value=None)

    with patch("backend.services.industry_packs.load_pack", side_effect=RuntimeError("skip")), patch(
        "backend.services.website_crawler.start_crawl", new_callable=AsyncMock
    ) as mock_start:
        out = await run_onboarding_complete(
            db, "t1", _make_req(hours={"Mon": "8-5"}), ai_content_fn=ai_fn
        )

    assert out.tenant["id"] == "t1"
    assert out.configured["business_info"] is True
    assert mock_start.await_count == 1


@pytest.mark.asyncio
async def test_run_onboarding_complete_raises_when_tenant_missing():
    from backend.services.onboarding_workflow import run_onboarding_complete

    db = _make_db()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with pytest.raises(HTTPException) as exc:
        await run_onboarding_complete(db, "missing", _make_req(), ai_content_fn=AsyncMock())
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# compute_onboarding_status
# ---------------------------------------------------------------------------


def test_compute_onboarding_status_returns_full_breakdown():
    from backend.services.onboarding_workflow import compute_onboarding_status

    db = MagicMock()

    tenant_row = {
        "id": "t1",
        "business_name": "Co",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": "+15551234567",
        "website_url": "https://x",
        "autopilot_enabled": True,
        "onboarding_completed_at": "2026-05-01T00:00:00Z",
    }

    # Build per-table return values so each query returns the right shape.
    def table_side_effect(name):
        chain = MagicMock()
        execute_mock = MagicMock()
        if name == "tenants":
            execute_mock.data = [tenant_row]
        elif name == "business_hours":
            execute_mock.data = [{"id": 1}]
        elif name == "website_content":
            execute_mock.data = [{"id": 1, "crawl_status": "completed"}]
        elif name == "faq_entries":
            execute_mock.data = [{"id": 1}]
        elif name == "widget_configs":
            execute_mock.data = [
                {"bot_name": "Custom Bot", "primary_color": "#abcdef", "greeting_message": "hi"}
            ]
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_mock
        return chain

    db.table.side_effect = table_side_effect

    out = compute_onboarding_status(db, "t1")
    assert out.has_business_info is True
    assert out.has_hours is True
    assert out.has_website is True
    assert out.has_faqs is True
    assert out.has_widget_customized is True
    assert out.onboarding_completed is True
    assert out.completion_percentage == 100


def test_compute_onboarding_status_handles_empty_optionals():
    from backend.services.onboarding_workflow import compute_onboarding_status

    db = MagicMock()
    tenant_row = {
        "id": "t1",
        "business_name": None,
        "business_type": None,
        "city": None,
        "phone": None,
        "website_url": None,
        "autopilot_enabled": False,
        "onboarding_completed_at": None,
    }

    def table_side_effect(name):
        chain = MagicMock()
        execute_mock = MagicMock()
        execute_mock.data = [tenant_row] if name == "tenants" else []
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_mock
        return chain

    db.table.side_effect = table_side_effect
    out = compute_onboarding_status(db, "t1")
    assert out.has_business_info is False
    assert out.has_hours is False
    assert out.has_website is False
    assert out.has_faqs is False
    assert out.has_widget_customized is False
    assert out.onboarding_completed is False
    assert out.completion_percentage == 0


def test_compute_onboarding_status_raises_404_when_tenant_missing():
    from backend.services.onboarding_workflow import compute_onboarding_status

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    with pytest.raises(HTTPException) as exc:
        compute_onboarding_status(db, "missing")
    assert exc.value.status_code == 404


def test_compute_onboarding_status_swallows_per_check_errors():
    from backend.services.onboarding_workflow import compute_onboarding_status

    db = MagicMock()
    tenant_row = {
        "id": "t1",
        "business_name": "Co",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": None,
        "website_url": None,
        "autopilot_enabled": False,
        "onboarding_completed_at": None,
    }

    def table_side_effect(name):
        chain = MagicMock()
        if name == "tenants":
            chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[tenant_row]
            )
        else:
            chain.select.return_value.eq.return_value.limit.return_value.execute.side_effect = RuntimeError(
                "boom"
            )
        return chain

    db.table.side_effect = table_side_effect
    out = compute_onboarding_status(db, "t1")
    assert out.has_business_info is True
    assert out.has_hours is False
    assert out.has_website is False
    assert out.has_faqs is False
    assert out.has_widget_customized is False


def test_compute_onboarding_status_treats_default_widget_as_uncustomized():
    from backend.services.onboarding_workflow import compute_onboarding_status

    db = MagicMock()
    tenant_row = {
        "id": "t1",
        "business_name": "Co",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": None,
        "website_url": None,
        "autopilot_enabled": False,
        "onboarding_completed_at": None,
    }

    def table_side_effect(name):
        chain = MagicMock()
        execute_mock = MagicMock()
        if name == "tenants":
            execute_mock.data = [tenant_row]
        elif name == "widget_configs":
            execute_mock.data = [
                {"bot_name": "AI Assistant", "primary_color": "#00BFFF", "greeting_message": "hi"}
            ]
        else:
            execute_mock.data = []
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = execute_mock
        return chain

    db.table.side_effect = table_side_effect
    out = compute_onboarding_status(db, "t1")
    assert out.has_widget_customized is False
