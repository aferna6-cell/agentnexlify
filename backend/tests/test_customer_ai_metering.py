"""Budget gates for the customer-facing AI call sites in #827.

Insights, lead summary, and both review-draft paths must not call the
provider when the tenant policy is missing or the reservation is denied.
A provider failure releases once and does not log the exception text.
"""

import logging

import pytest
from fastapi import HTTPException

from backend.services.ai_usage_guard import AIUsageReservation
from backend.services.llm_runtime import ClaudeCallResult
from backend.tests.fake_supabase import db, run

TENANT = "t1"
LEAD = "lead-1"
REVIEW = "review-1"


def _tenant(**extra):
    row = {
        "id": TENANT,
        "business_name": "Keys Koffee",
        "business_type": "cafe",
        "plan": "agent_os",
        "ai_monthly_token_alert_threshold": None,
        "ai_monthly_token_hard_limit": None,
    }
    row.update(extra)
    return row


def _reservation(*, allowed=True, reason=""):
    return AIUsageReservation(
        allowed=allowed,
        tenant_id=TENANT,
        period_month="2026-11-01",
        estimated_tokens=400,
        alert_threshold_tokens=4_000_000,
        hard_limit_tokens=5_000_000,
        reason=reason,
    )


def _result(text="A useful draft."):
    return ClaudeCallResult(
        text=text,
        duration_ms=5,
        input_tokens=20,
        output_tokens=10,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def _patch_provider(monkeypatch, module, *, result=None, error=None):
    calls = {"n": 0}

    async def fake_call(**_kwargs):
        calls["n"] += 1
        if error is not None:
            raise error
        return result or _result()

    monkeypatch.setattr(module, "call_claude_messages", fake_call)
    return calls


def test_insights_denial_skips_provider_and_keeps_metrics(monkeypatch):
    from backend.routers.analytics import insights

    monkeypatch.setattr(insights, "_get_cached", lambda _key: None)
    monkeypatch.setattr(
        "backend.config.settings.anthropic_api_key", "test-key", raising=False
    )
    monkeypatch.setattr(
        insights,
        "get_service_supabase",
        lambda: db({"tenants": [_tenant()], "leads": [], "chat_messages": []}),
    )
    provider = _patch_provider(monkeypatch, insights)
    monkeypatch.setattr(
        insights, "reserve_ai_tokens", lambda **_kwargs: _reservation(allowed=False, reason="hard_limit")
    )

    payload = run(insights.get_ai_insights(TENANT, {"tenant_id": TENANT}))

    assert provider["n"] == 0
    assert payload["ai_analysis"] == ""
    assert "metrics" in payload


def test_insights_missing_policy_skips_provider(monkeypatch):
    from backend.routers.analytics import insights

    monkeypatch.setattr(insights, "_get_cached", lambda _key: None)
    monkeypatch.setattr(
        "backend.config.settings.anthropic_api_key", "test-key", raising=False
    )
    monkeypatch.setattr(
        insights,
        "get_service_supabase",
        lambda: db({"tenants": [{"business_name": "Keys Koffee"}]}),
    )
    provider = _patch_provider(monkeypatch, insights)

    def boom(**_kwargs):
        raise AssertionError("reserve must not run without a policy")

    monkeypatch.setattr(insights, "reserve_ai_tokens", boom)
    payload = run(insights.get_ai_insights(TENANT, {"tenant_id": TENANT}))
    assert provider["n"] == 0
    assert payload["ai_analysis"] == ""


def test_insights_success_records_and_failure_releases(monkeypatch):
    from backend.routers.analytics import insights

    monkeypatch.setattr(insights, "_get_cached", lambda _key: None)
    monkeypatch.setattr(
        "backend.config.settings.anthropic_api_key", "test-key", raising=False
    )
    monkeypatch.setattr(
        insights,
        "get_service_supabase",
        lambda: db({"tenants": [_tenant()]}),
    )
    recorded = {}
    released = {"n": 0}
    reservation = _reservation()
    monkeypatch.setattr(insights, "reserve_ai_tokens", lambda **_kwargs: reservation)
    monkeypatch.setattr(
        insights,
        "record_ai_usage",
        lambda **kwargs: recorded.update(kwargs),
    )
    monkeypatch.setattr(
        insights,
        "release_ai_token_reservation",
        lambda _reservation: released.__setitem__("n", released["n"] + 1),
    )
    provider = _patch_provider(monkeypatch, insights, result=_result("Leads are up."))
    payload = run(insights.get_ai_insights(TENANT, {"tenant_id": TENANT}))
    assert provider["n"] == 1
    assert payload["ai_analysis"] == "Leads are up."
    assert recorded["operation"] == "analytics.ai_insights"
    assert released["n"] == 0

    provider_fail = _patch_provider(
        monkeypatch, insights, error=RuntimeError("ada@example.com secret")
    )
    recorded.clear()
    payload = run(insights.get_ai_insights(TENANT, {"tenant_id": TENANT}))
    assert provider_fail["n"] == 1
    assert payload["ai_analysis"] == ""
    assert recorded == {}
    assert released["n"] == 1


def test_lead_summary_denial_and_missing_tenant_skip_provider(monkeypatch):
    from backend.routers import leads

    lead_row = {
        "id": LEAD,
        "conversation_id": "conv-1",
        "name": "Ada",
        "client_id": TENANT,
    }
    messages = [
        {"role": "user", "content": "Need a quote"},
        {"role": "assistant", "content": "Happy to help"},
    ]
    store = {
        "leads": [lead_row],
        "conversations": [{"id": "conv-1", "messages": messages, "client_id": TENANT}],
        "tenants": [_tenant()],
    }
    monkeypatch.setattr(leads, "get_service_supabase", lambda: db(store))
    provider = _patch_provider(monkeypatch, leads)
    monkeypatch.setattr(
        leads,
        "reserve_ai_tokens",
        lambda **_kwargs: _reservation(allowed=False, reason="hard_limit"),
    )
    with pytest.raises(HTTPException) as denied:
        run(leads.generate_lead_summary(TENANT, LEAD, {"tenant_id": TENANT}))
    assert denied.value.status_code == 429
    assert provider["n"] == 0

    monkeypatch.setattr(
        leads,
        "get_service_supabase",
        lambda: db({**store, "tenants": []}),
    )
    with pytest.raises(HTTPException) as missing:
        run(leads.generate_lead_summary(TENANT, LEAD, {"tenant_id": TENANT}))
    assert missing.value.status_code == 503
    assert provider["n"] == 0


def test_lead_summary_records_success_and_releases_on_failure(monkeypatch, caplog):
    from backend.routers import leads

    store = {
        "leads": [{
            "id": LEAD,
            "conversation_id": "conv-1",
            "name": "Ada",
            "client_id": TENANT,
        }],
        "conversations": [{
            "id": "conv-1",
            "client_id": TENANT,
            "messages": [
                {"role": "user", "content": "Need a quote"},
                {"role": "assistant", "content": "Happy to help"},
            ],
        }],
        "tenants": [_tenant()],
    }
    monkeypatch.setattr(leads, "get_service_supabase", lambda: db(store))
    reservation = _reservation()
    recorded = {}
    released = {"n": 0}
    monkeypatch.setattr(leads, "reserve_ai_tokens", lambda **_kwargs: reservation)
    monkeypatch.setattr(leads, "record_ai_usage", lambda **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(
        leads,
        "release_ai_token_reservation",
        lambda _reservation: released.__setitem__("n", released["n"] + 1),
    )
    _patch_provider(monkeypatch, leads, result=_result("Ada wants a quote."))
    payload = run(leads.generate_lead_summary(TENANT, LEAD, {"tenant_id": TENANT}))
    assert payload["summary"] == "Ada wants a quote."
    assert recorded["operation"] == "leads.generate_summary"
    assert released["n"] == 0

    recorded.clear()
    with caplog.at_level(logging.WARNING):
        _patch_provider(
            monkeypatch, leads, error=RuntimeError("ada@example.com leaked")
        )
        with pytest.raises(HTTPException) as failed:
            run(leads.generate_lead_summary(TENANT, LEAD, {"tenant_id": TENANT}))
    assert failed.value.status_code == 502
    assert recorded == {}
    assert released["n"] == 1
    assert "ada@example.com" not in caplog.text
    assert "leaked" not in caplog.text


def test_review_draft_route_blocks_and_records(monkeypatch, caplog):
    from backend.routers import reviews

    review = {
        "id": REVIEW,
        "tenant_id": TENANT,
        "author_name": "Ada",
        "rating": 5,
        "review_text": "Loved it",
    }
    store = {"reviews": [review], "tenants": [_tenant()]}
    monkeypatch.setattr(reviews, "get_service_supabase", lambda: db(store))
    provider = _patch_provider(monkeypatch, reviews)
    monkeypatch.setattr(
        reviews,
        "reserve_ai_tokens",
        lambda **_kwargs: _reservation(reason="guard_unavailable"),
    )
    draft_route = reviews.generate_ai_draft.__wrapped__
    with pytest.raises(HTTPException) as blocked:
        run(
            draft_route(
                object(),
                TENANT,
                REVIEW,
                reviews.AIDraftRequest(),
                {"tenant_id": TENANT},
            )
        )
    assert blocked.value.status_code == 503
    assert provider["n"] == 0

    reservation = _reservation()
    recorded = {}
    released = {"n": 0}
    monkeypatch.setattr(reviews, "reserve_ai_tokens", lambda **_kwargs: reservation)
    monkeypatch.setattr(reviews, "record_ai_usage", lambda **kwargs: recorded.update(kwargs))
    monkeypatch.setattr(
        reviews,
        "release_ai_token_reservation",
        lambda _reservation: released.__setitem__("n", released["n"] + 1),
    )
    _patch_provider(monkeypatch, reviews, result=_result("Thanks Ada."))
    payload = run(
        draft_route(
            object(),
            TENANT,
            REVIEW,
            reviews.AIDraftRequest(),
            {"tenant_id": TENANT},
        )
    )
    assert payload["draft"] == "Thanks Ada."
    assert recorded["operation"] == "reviews.generate_draft"

    recorded.clear()
    with caplog.at_level(logging.ERROR):
        _patch_provider(
            monkeypatch,
            reviews,
            error=RuntimeError("authorization=Bearer secret ada@example.com"),
        )
        with pytest.raises(HTTPException) as failed:
            run(
                draft_route(
                    object(),
                    TENANT,
                    REVIEW,
                    reviews.AIDraftRequest(),
                    {"tenant_id": TENANT},
                )
            )
    assert failed.value.status_code == 500
    assert released["n"] == 1
    assert recorded == {}
    assert "Bearer" not in caplog.text
    assert "ada@example.com" not in caplog.text


def test_review_responder_fail_closed_and_records(monkeypatch):
    from backend.services import review_responder

    review = {"review_text": "Slow service", "review_rating": 2, "review_id": REVIEW}
    provider = _patch_provider(monkeypatch, review_responder)
    missing = run(
        review_responder.draft_response(
            db({"tenants": [{"id": TENANT, "business_name": "Keys"}]}),
            tenant_id=TENANT,
            review=review,
        )
    )
    assert missing is None
    assert provider["n"] == 0

    reservation = _reservation()
    recorded = {}
    monkeypatch.setattr(
        review_responder, "reserve_ai_tokens", lambda **_kwargs: reservation
    )
    monkeypatch.setattr(
        review_responder, "record_ai_usage", lambda **kwargs: recorded.update(kwargs)
    )
    provider = _patch_provider(
        monkeypatch, review_responder, result=_result("Sorry about the wait.")
    )
    created = run(
        review_responder.draft_response(
            db({
                "tenants": [_tenant()],
                "review_responses": [{"id": "rr-1", "status": "draft"}],
            }),
            tenant_id=TENANT,
            review=review,
        )
    )
    assert created["id"] == "rr-1"
    assert recorded["operation"] == "review_responder.draft"
    assert provider["n"] == 1
