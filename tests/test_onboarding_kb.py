"""Tests for backend/services/onboarding_kb.py orchestrators + helpers.

Mocks Supabase, Claude, and the website crawler. No network IO.
"""

import os

os.environ["TESTING"] = "1"

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_db_mock():
    """Return a MagicMock db where every chain ends with .execute() -> data=[]."""
    db = MagicMock()
    return db


def _make_req(**kwargs):
    """Build a SimpleNamespace request object matching pydantic request shapes."""
    defaults = {
        "business_name": "Test Co",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": "+15551234567",
        "website_url": "https://example.com",
        "services": ["Service A", "Service B"],
        "faqs": [],
        "hours": None,
        "url": "https://example.com",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _format_hours_for_prompt
# ---------------------------------------------------------------------------


def test_format_hours_for_prompt_empty_returns_not_specified():
    from backend.services.onboarding_kb import _format_hours_for_prompt

    assert _format_hours_for_prompt(None) == "Not specified"
    assert _format_hours_for_prompt({}) == "Not specified"


def test_format_hours_for_prompt_enabled_day_renders_range():
    from backend.services.onboarding_kb import _format_hours_for_prompt

    hours = {
        "monday": {"enabled": True, "open": "09:00", "close": "17:00"},
        "tuesday": {"enabled": False},
        "timezone": "America/New_York",
    }
    out = _format_hours_for_prompt(hours)
    assert "Monday: 09:00 – 17:00" in out
    assert "Tuesday: Closed" in out
    assert "Timezone: America/New_York" in out


def test_format_hours_for_prompt_open_close_without_enabled():
    from backend.services.onboarding_kb import _format_hours_for_prompt

    hours = {
        "wednesday": {"open": "10:00", "close": "16:00"},
    }
    out = _format_hours_for_prompt(hours)
    assert "Wednesday: 10:00 – 16:00" in out


# ---------------------------------------------------------------------------
# _build_auto_kb_prompt
# ---------------------------------------------------------------------------


def test_build_auto_kb_prompt_includes_business_info_and_markers():
    from backend.services.onboarding_kb import _build_auto_kb_prompt

    tenant_info = {
        "business_name": "Pipe Pros",
        "business_type": "plumbing",
        "city": "Miami",
        "phone": "+15550000000",
    }
    prompt = _build_auto_kb_prompt(tenant_info, "https://example.com", "WEBSITE TEXT")
    assert "Pipe Pros" in prompt
    assert "plumbing" in prompt
    assert "Miami" in prompt
    assert "WEBSITE TEXT" in prompt
    assert "===KNOWLEDGE_BASE===" in prompt
    assert "===CUSTOM_INSTRUCTIONS===" in prompt
    assert "===SERVICES===" in prompt
    assert "===HOURS===" in prompt
    assert "===FAQ_START===" in prompt
    assert "===FAQ_END===" in prompt


# ---------------------------------------------------------------------------
# _seed_preset_for_empty_scrape
# ---------------------------------------------------------------------------


def test_seed_preset_returns_none_when_business_type_unrecognized():
    from backend.services.onboarding_kb import _seed_preset_for_empty_scrape

    db = _make_db_mock()
    assert _seed_preset_for_empty_scrape(db, "tenant-1", "made-up-business") is None


def test_seed_preset_for_plumbing_writes_db_and_returns_result():
    from backend.services.onboarding_kb import _seed_preset_for_empty_scrape

    db = _make_db_mock()
    result = _seed_preset_for_empty_scrape(db, "tenant-1", "plumbing")
    assert result is not None
    assert "plumbing" in result.knowledge_base.lower()
    assert len(result.services) > 0
    assert len(result.faqs) > 0
    assert result.pages_crawled == 0
    # widget_configs and faq_entries were updated
    db.table.assert_any_call("widget_configs")
    db.table.assert_any_call("faq_entries")


def test_seed_preset_swallows_persist_errors_but_still_returns_result():
    from backend.services.onboarding_kb import _seed_preset_for_empty_scrape

    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        RuntimeError("db down")
    )
    db.table.return_value.insert.return_value.execute.side_effect = RuntimeError(
        "db down"
    )
    result = _seed_preset_for_empty_scrape(db, "tenant-1", "plumbing")
    assert result is not None
    assert result.knowledge_base


# ---------------------------------------------------------------------------
# run_generate_kb
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock)
async def test_run_generate_kb_persists_and_returns_text(mock_call):
    from backend.services.onboarding_kb import run_generate_kb

    mock_call.return_value = SimpleNamespace(text=" ## About\nGenerated KB\n ")
    db = _make_db_mock()
    req = _make_req(hours={"monday": {"open": "09:00", "close": "17:00"}})
    result = await run_generate_kb(db, "tenant-1", req)
    assert result.generated is True
    assert result.knowledge_base == "## About\nGenerated KB"
    db.table.assert_any_call("widget_configs")
    assert mock_call.await_count == 1


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock)
async def test_run_generate_kb_returns_failure_when_claude_raises(mock_call):
    from backend.services.onboarding_kb import run_generate_kb

    mock_call.side_effect = RuntimeError("api down")
    db = _make_db_mock()
    req = _make_req()
    result = await run_generate_kb(db, "tenant-1", req)
    assert result.generated is False
    assert result.knowledge_base is None


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock)
async def test_run_generate_kb_swallows_persist_errors(mock_call):
    """KB generation is best-effort: persist failure does NOT flip generated=False."""
    from backend.services.onboarding_kb import run_generate_kb

    mock_call.return_value = SimpleNamespace(text="KB text")
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.execute.side_effect = (
        RuntimeError("db down")
    )
    req = _make_req(
        faqs=[SimpleNamespace(question="Q1", answer="A1")],
    )
    result = await run_generate_kb(db, "tenant-1", req)
    assert result.generated is True
    assert result.knowledge_base == "KB text"


# ---------------------------------------------------------------------------
# run_auto_populate_kb
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_auto_populate_kb_rejects_unsafe_url():
    from backend.services.onboarding_kb import run_auto_populate_kb

    db = _make_db_mock()
    req = _make_req(url="ftp://not-allowed.example.com")
    with pytest.raises(HTTPException) as exc_info:
        await run_auto_populate_kb(db, "tenant-1", req)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.start_crawl", new_callable=AsyncMock)
@patch("backend.services.onboarding_kb.get_crawled_content", return_value="")
@patch("backend.services.onboarding_kb._fallback_http_fetch", new_callable=AsyncMock)
async def test_run_auto_populate_kb_seeds_preset_when_scrape_empty(
    mock_fallback, _mock_get_content, mock_start_crawl
):
    from backend.services.onboarding_kb import run_auto_populate_kb

    mock_start_crawl.return_value = {"pages_found": 0}
    mock_fallback.return_value = ("", 0)

    db = MagicMock()
    tenant_resp = MagicMock(data={"business_type": "plumbing"})
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
        tenant_resp
    )
    req = _make_req(url="https://example.com")
    result = await run_auto_populate_kb(db, "tenant-1", req)
    assert result.knowledge_base
    assert result.pages_crawled == 0


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.start_crawl", new_callable=AsyncMock)
@patch("backend.services.onboarding_kb.get_crawled_content", return_value="")
@patch("backend.services.onboarding_kb._fallback_http_fetch", new_callable=AsyncMock)
async def test_run_auto_populate_kb_raises_422_when_no_content_and_no_preset(
    mock_fallback, _mock_get_content, mock_start_crawl
):
    from backend.services.onboarding_kb import run_auto_populate_kb

    mock_start_crawl.return_value = {"pages_found": 0}
    mock_fallback.return_value = ("", 0)

    db = MagicMock()
    tenant_resp = MagicMock(data={"business_type": "unknown-vertical-xyz"})
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
        tenant_resp
    )
    req = _make_req(url="https://example.com")
    with pytest.raises(HTTPException) as exc_info:
        await run_auto_populate_kb(db, "tenant-1", req)
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock)
@patch("backend.services.onboarding_kb.start_crawl", new_callable=AsyncMock)
@patch(
    "backend.services.onboarding_kb.get_crawled_content",
    return_value="Pipe Pros is a Miami plumbing service.",
)
async def test_run_auto_populate_kb_happy_path(
    _mock_get_content, mock_start_crawl, mock_call_claude
):
    from backend.services.onboarding_kb import run_auto_populate_kb

    mock_start_crawl.return_value = {"pages_found": 3}
    raw_response = (
        "===KNOWLEDGE_BASE===\n"
        "## About\nPipe Pros is a Miami plumbing service.\n"
        "===CUSTOM_INSTRUCTIONS===\n"
        "You are the Pipe Pros Assistant.\n"
        "===SERVICES===\n"
        "Drain cleaning\n"
        "Water heater repair\n"
        "===FAQ_START===\n"
        "Q: Do you offer emergency service?\nA: Yes, 24/7.\nC: services\n"
        "===FAQ_END==="
    )
    mock_call_claude.return_value = SimpleNamespace(text=raw_response)

    db = MagicMock()
    tenant_resp = MagicMock(
        data={
            "business_name": "Pipe Pros",
            "business_type": "plumbing",
            "city": "Miami",
            "phone": "+15550000000",
        }
    )
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
        tenant_resp
    )
    req = _make_req(url="https://example.com")
    result = await run_auto_populate_kb(db, "tenant-1", req)

    assert result.pages_crawled == 3
    assert result.chars_extracted > 0
    assert "Pipe Pros" in result.knowledge_base
    assert "Drain cleaning" in result.services
    assert any(f.question.startswith("Do you offer") for f in result.faqs)
    assert mock_call_claude.await_count == 1


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock)
@patch("backend.services.onboarding_kb.start_crawl", new_callable=AsyncMock)
@patch(
    "backend.services.onboarding_kb.get_crawled_content",
    return_value="some website content here",
)
async def test_run_auto_populate_kb_raises_502_when_claude_fails(
    _mock_get_content, mock_start_crawl, mock_call_claude
):
    from backend.services.onboarding_kb import run_auto_populate_kb

    mock_start_crawl.return_value = {"pages_found": 1}
    mock_call_claude.side_effect = RuntimeError("api down")
    db = MagicMock()
    tenant_resp = MagicMock(data={"business_name": "X", "business_type": "plumbing"})
    db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
        tenant_resp
    )
    req = _make_req(url="https://example.com")
    with pytest.raises(HTTPException) as exc_info:
        await run_auto_populate_kb(db, "tenant-1", req)
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
@patch("backend.services.onboarding_kb.start_crawl", new_callable=AsyncMock)
@patch("backend.services.onboarding_kb.get_crawled_content", return_value="")
async def test_run_auto_populate_kb_uses_fallback_http_fetch(
    _mock_get_content, mock_start_crawl
):
    """Crawler returns empty, fallback HTTP fetch returns text → flow continues."""
    from backend.services.onboarding_kb import run_auto_populate_kb

    mock_start_crawl.return_value = {"pages_found": 0}

    raw_response = (
        "===KNOWLEDGE_BASE===\n## About\nFallback text\n"
        "===CUSTOM_INSTRUCTIONS===\nBe helpful\n"
        "===SERVICES===\nService A\n"
        "===FAQ_START===\n===FAQ_END==="
    )

    with patch(
        "backend.services.onboarding_kb._fallback_http_fetch", new_callable=AsyncMock
    ) as mock_fallback, patch(
        "backend.services.onboarding_kb.call_claude_messages", new_callable=AsyncMock
    ) as mock_claude:
        mock_fallback.return_value = ("fallback-extracted content body", 1)
        mock_claude.return_value = SimpleNamespace(text=raw_response)

        db = MagicMock()
        tenant_resp = MagicMock(
            data={"business_name": "X", "business_type": "plumbing"}
        )
        db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = (
            tenant_resp
        )
        req = _make_req(url="https://example.com")
        result = await run_auto_populate_kb(db, "tenant-1", req)
        assert result.pages_crawled == 1
        assert "Fallback text" in result.knowledge_base
        assert mock_fallback.await_count == 1


@pytest.mark.asyncio
async def test_fallback_http_fetch_handles_non_200_status():
    """Fallback returns empty when HTTP status != 200."""
    from backend.services.onboarding_kb import _fallback_http_fetch

    with patch("backend.services.onboarding_kb.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock(status_code=503, text="<html>err</html>")
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        text, pages = await _fallback_http_fetch("https://example.com")
        assert text == ""
        assert pages == 0


@pytest.mark.asyncio
async def test_fallback_http_fetch_strips_html_tags():
    """200 response gets script/style stripped + tags removed."""
    from backend.services.onboarding_kb import _fallback_http_fetch

    html = (
        "<html><head><script>var x=1</script><style>.a{}</style></head>"
        "<body><p>Hello   world</p><div>More text</div></body></html>"
    )
    with patch("backend.services.onboarding_kb.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock(status_code=200, text=html)
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        text, pages = await _fallback_http_fetch("https://example.com")
        assert pages == 1
        assert "Hello" in text
        assert "world" in text
        assert "var x" not in text
        assert "<" not in text
