"""Meter only local SEO keyword generation. Fake provider, no network."""

import inspect
import logging
from unittest.mock import patch

import pytest

from backend.services import local_seo_ai
from backend.services.ai_usage_guard import AIUsageRecord, AIUsageReservation
from backend.services.llm_runtime import ClaudeCallResult
from backend.services.local_seo_ai import _generate_keywords
from backend.services.local_seo_execute import execute_analyze_seo_profile

_TENANT_ID = "00000000-0000-0000-0000-000000000827"
_CITY = "PII_CITY_ZZZ"
_API_KEY = "offline-meter-key"


def _tenant(**overrides):
    row = {
        "id": _TENANT_ID,
        "plan": "chatbot",
        "ai_monthly_token_alert_threshold": None,
        "ai_monthly_token_hard_limit": None,
        "business_name": "Biz",
        "business_type": "salon",
        "city": _CITY,
        "website_url": "https://biz.example",
    }
    row.update(overrides)
    return row


def _reservation(**overrides) -> AIUsageReservation:
    payload = {
        "allowed": True,
        "tenant_id": _TENANT_ID,
        "period_month": "2026-10-01",
        "estimated_tokens": 700,
        "alert_threshold_tokens": 640_000,
        "hard_limit_tokens": 800_000,
        "reason": "",
    }
    payload.update(overrides)
    return AIUsageReservation(**payload)


def _claude(text: str) -> ClaudeCallResult:
    return ClaudeCallResult(
        text=text,
        duration_ms=8,
        input_tokens=21,
        output_tokens=9,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def _enable_key(monkeypatch):
    monkeypatch.setattr(local_seo_ai.settings, "anthropic_api_key", _API_KEY)


@pytest.mark.parametrize("tenant", [None, {}, {"id": "   "}, {"plan": "chatbot"}])
async def test_missing_tenant_skips_provider(monkeypatch, tenant):
    _enable_key(monkeypatch)
    provider_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    with patch.object(local_seo_ai, "call_claude_messages", side_effect=provider):
        keywords = await _generate_keywords("salon", _CITY, tenant=tenant)

    assert keywords == []
    assert provider_calls == []


async def test_missing_policy_skips_provider(monkeypatch, caplog):
    _enable_key(monkeypatch)
    provider_calls: list[str] = []
    reserve_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    def reserve(**_kwargs):
        reserve_calls.append("called")
        return _reservation()

    with (
        caplog.at_level(logging.WARNING),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(local_seo_ai, "reserve_ai_tokens", side_effect=reserve),
    ):
        keywords = await _generate_keywords(
            "salon",
            _CITY,
            tenant={"id": _TENANT_ID, "business_type": "salon"},
        )

    assert keywords == []
    assert provider_calls == []
    assert reserve_calls == []
    assert "missing policy" in caplog.text
    assert _CITY not in caplog.text
    assert _API_KEY not in caplog.text


async def test_hard_denial_skips_provider(monkeypatch, caplog):
    _enable_key(monkeypatch)
    provider_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    with (
        caplog.at_level(logging.WARNING),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(
            local_seo_ai,
            "reserve_ai_tokens",
            return_value=_reservation(allowed=False, reason="hard_limit"),
        ),
    ):
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant(), session_id=_TENANT_ID)

    assert keywords == []
    assert provider_calls == []
    assert "hard_limit" in caplog.text
    assert _CITY not in caplog.text


async def test_guard_unavailable_skips_provider(monkeypatch):
    _enable_key(monkeypatch)
    provider_calls: list[str] = []
    release_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    def release(_reservation_obj):
        release_calls.append("released")

    with (
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(
            local_seo_ai,
            "reserve_ai_tokens",
            return_value=_reservation(allowed=True, reason="guard_unavailable"),
        ),
        patch.object(local_seo_ai, "release_ai_token_reservation", side_effect=release),
    ):
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant())

    assert keywords == []
    assert provider_calls == []
    assert release_calls == []


async def test_reserve_exception_skips_provider(monkeypatch, caplog):
    _enable_key(monkeypatch)
    provider_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    def reserve(**_kwargs):
        raise RuntimeError("guard blew up sentinel-token")

    with (
        caplog.at_level(logging.WARNING),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(local_seo_ai, "reserve_ai_tokens", side_effect=reserve),
    ):
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant())

    assert keywords == []
    assert provider_calls == []
    assert "guard unavailable" in caplog.text
    assert "sentinel-token" not in caplog.text
    assert _CITY not in caplog.text


async def test_provider_exception_releases_once_and_returns_empty(monkeypatch, caplog):
    _enable_key(monkeypatch)
    reservation = _reservation()
    released: list[str] = []
    recorded: list[str] = []

    async def provider(**_kwargs):
        raise RuntimeError("provider down sentinel-token")

    def release(active):
        released.append(active.tenant_id)

    def record(**_kwargs):
        recorded.append("recorded")
        return None

    with (
        caplog.at_level(logging.ERROR),
        patch.object(local_seo_ai, "reserve_ai_tokens", return_value=reservation),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(local_seo_ai, "release_ai_token_reservation", side_effect=release),
        patch.object(local_seo_ai, "record_ai_usage", side_effect=record),
    ):
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant())

    assert keywords == []
    assert released == [_TENANT_ID]
    assert recorded == []
    assert "sentinel-token" not in caplog.text
    assert _CITY not in caplog.text
    assert "Keyword generation failed unexpectedly" in caplog.text


async def test_provider_success_records_actual_result_without_release(monkeypatch, caplog):
    _enable_key(monkeypatch)
    reservation = _reservation()
    result = _claude('["salon near me", "color salon"]')
    released: list[str] = []
    recorded: list[dict] = []
    seen: dict = {}

    async def provider(**kwargs):
        seen.update(kwargs)
        return result

    def release(_active):
        released.append("released")

    def record(**kwargs):
        recorded.append(kwargs)
        return AIUsageRecord(total_tokens=30, alert_triggered=False, hard_limit_reached=False)

    with (
        caplog.at_level(logging.DEBUG),
        patch.object(local_seo_ai, "reserve_ai_tokens", return_value=reservation),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(local_seo_ai, "release_ai_token_reservation", side_effect=release),
        patch.object(local_seo_ai, "record_ai_usage", side_effect=record),
    ):
        keywords = await _generate_keywords(
            "salon",
            _CITY,
            tenant=_tenant(),
            session_id=_TENANT_ID,
        )

    assert keywords == ["salon near me", "color salon"]
    assert released == []
    assert len(recorded) == 1
    assert recorded[0]["result"] is result
    assert recorded[0]["result"].input_tokens == 21
    assert recorded[0]["result"].output_tokens == 9
    assert recorded[0]["operation"] == "seo.generate_keywords"
    assert recorded[0]["session_id"] == _TENANT_ID
    assert recorded[0]["model"] == "claude-sonnet-4-6"
    assert seen["model"] == "claude-sonnet-4-6"
    assert seen["max_tokens"] == 400
    assert seen["temperature"] == 0.5
    assert seen["timeout"] == 30.0
    assert seen["operation"] == "seo.generate_keywords"
    assert seen["metadata"] == {"tenant_id": _TENANT_ID}
    assert "JSON array" in seen["system"]
    assert _CITY not in caplog.text
    assert "emergency plumber near me" not in caplog.text
    assert _API_KEY not in caplog.text


async def test_provider_success_parse_failure_still_records(monkeypatch, caplog):
    _enable_key(monkeypatch)
    result = _claude("not json at all")
    released: list[str] = []
    recorded: list[ClaudeCallResult] = []

    async def provider(**_kwargs):
        return result

    def release(_active):
        released.append("released")

    def record(**kwargs):
        recorded.append(kwargs["result"])
        return AIUsageRecord(total_tokens=30, alert_triggered=False, hard_limit_reached=False)

    with (
        caplog.at_level(logging.ERROR),
        patch.object(local_seo_ai, "reserve_ai_tokens", return_value=_reservation()),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch.object(local_seo_ai, "release_ai_token_reservation", side_effect=release),
        patch.object(local_seo_ai, "record_ai_usage", side_effect=record),
    ):
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant())

    assert keywords == []
    assert recorded == [result]
    assert released == []
    assert "Failed to parse keyword suggestions JSON from Claude" in caplog.text
    assert "not json at all" not in caplog.text
    assert _CITY not in caplog.text


async def test_provider_success_record_failure_retains_debt(monkeypatch, caplog):
    _enable_key(monkeypatch)
    rpc_calls: list[str] = []

    def rpc(name, _payload):
        rpc_calls.append(name)
        raise RuntimeError("sentinel-token prompt body")

    async def provider(**_kwargs):
        return _claude('["kept keyword"]')

    with (
        caplog.at_level(logging.WARNING),
        patch.object(local_seo_ai, "reserve_ai_tokens", return_value=_reservation()),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
        patch("backend.services.ai_usage_guard.get_service_supabase") as mock_supa,
    ):
        mock_supa.return_value.rpc.side_effect = rpc
        keywords = await _generate_keywords("salon", _CITY, tenant=_tenant(), session_id=_TENANT_ID)

    assert keywords == ["kept keyword"]
    assert rpc_calls == ["record_ai_token_usage"]
    assert "accounting_debt" in caplog.text
    assert "record_rpc_failed" in caplog.text
    assert "sentinel-token" not in caplog.text
    assert _CITY not in caplog.text
    assert "emergency plumber near me" not in caplog.text


def test_other_local_seo_helpers_stay_unmetered():
    for name in ("_run_seo_audit_ai", "_run_geo_score_ai", "_analyze_keywords_ai"):
        source = inspect.getsource(getattr(local_seo_ai, name))
        assert "reserve_ai_tokens" not in source
        assert "record_ai_usage" not in source
        assert "release_ai_token_reservation" not in source


def _table_chain(data, count=None):
    from unittest.mock import MagicMock

    chain = MagicMock()
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    result = MagicMock()
    result.data = data
    result.count = count
    chain.execute.return_value = result
    return chain


async def test_profile_stays_deterministic_when_keywords_are_denied(monkeypatch, mock_supabase):
    _enable_key(monkeypatch)
    tenant_chain = _table_chain([_tenant()])
    empty = _table_chain([])
    saved = _table_chain([{"id": "profile-1", "created_at": "2026-10-06T00:00:00+00:00"}])
    mock_supabase.table.side_effect = [
        tenant_chain,
        empty,
        empty,
        empty,
        empty,
        empty,
        saved,
    ]
    provider_calls: list[str] = []

    async def provider(**_kwargs):
        provider_calls.append("called")
        return _claude("[]")

    with (
        patch.object(
            local_seo_ai,
            "reserve_ai_tokens",
            return_value=_reservation(allowed=False, reason="hard_limit"),
        ),
        patch.object(local_seo_ai, "call_claude_messages", side_effect=provider),
    ):
        profile = await execute_analyze_seo_profile(_TENANT_ID)

    select_columns = tenant_chain.select.call_args.args[0]
    assert "plan" in select_columns
    assert "ai_monthly_token_hard_limit" in select_columns
    assert "ai_monthly_token_alert_threshold" in select_columns
    assert profile["completeness_score"] == 40
    assert profile["keyword_suggestions"] == []
    assert "faq_entries" in profile["missing_fields"]
    assert profile["tenant_id"] == _TENANT_ID
    assert provider_calls == []
