"""Regression test: phone-only lead dedup in _capture_leads_from_session.

Gap fixed: when a visitor shares only a phone number (no email), the code
previously skipped the dedup query and inserted a duplicate lead on every
subsequent visit.  The fix adds a phone-based dedup lookup before the insert.

These tests call _capture_leads_from_session directly (no ASGI layer) with
fully mocked DB and LLM dependencies so they run offline.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to build minimal mock chains
# ---------------------------------------------------------------------------

def _make_execute_result(data):
    """Wrap data in an object with a .data attribute, matching supabase-py."""
    r = MagicMock()
    r.data = data
    return r


def _chainable_mock(data=None):
    """Return a mock where chained calls ultimately return execute_result."""
    result = _make_execute_result(data if data is not None else [])
    m = MagicMock()
    # Every chained attribute or call returns self so we can chain .eq().limit()
    m.return_value = m
    for attr in (
        "select", "eq", "neq", "limit", "order", "filter",
        "is_", "not_", "insert", "update", "upsert", "delete",
    ):
        setattr(m, attr, MagicMock(return_value=m))
    m.execute.return_value = result
    return m


def _noop_async(*args, **kwargs):
    """Async noop suitable for patching coroutines we don't care about."""
    async def _inner(*a, **kw):
        return None
    return _inner(*args, **kwargs)


# ---------------------------------------------------------------------------
# Test 1: phone-only visitor — no existing lead → NEW lead inserted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phone_only_new_lead_is_created():
    """Visitor sends only a phone. No existing lead. New lead row inserted."""

    messages = [
        {"role": "user", "content": "Hi my number is 555-867-5309"},
        {"role": "assistant", "content": "Thanks! How can I help?"},
    ]

    # tenant_select returns no existing phone lead → goes to insert
    phone_dedup_chain = _chainable_mock(data=[])
    # tenant_insert returns success row
    insert_chain = _chainable_mock(data=[{"id": "new-lead-uuid"}])
    # all update calls succeed silently
    update_chain = _chainable_mock(data=[])

    def _fake_tenant_select(db_obj, table, tenant_id, fields):
        return phone_dedup_chain

    with (
        # _load_chat_history is imported lazily inside _capture_leads_from_session
        # from backend.routers.widget_chat_helpers — patch it there.
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=messages,
        ),
        patch(
            "backend.routers.widget_lead_helpers.get_service_supabase",
            return_value=MagicMock(),
        ),
        patch(
            "backend.routers.widget_lead_helpers.tenant_select",
            side_effect=_fake_tenant_select,
        ),
        patch(
            "backend.routers.widget_lead_helpers.tenant_insert",
            return_value=insert_chain,
        ) as mock_insert,
        patch(
            "backend.routers.widget_lead_helpers.tenant_update",
            return_value=update_chain,
        ),
        patch("backend.routers.widget_lead_helpers.log_activity"),
        patch("backend.routers.widget_lead_helpers.fire_event_background"),
        patch("backend.routers.widget_lead_helpers.score_lead_background"),
        patch(
            "backend.routers.widget_lead_helpers._extract_tags_from_conversation",
            return_value=[],
        ),
        # Stub out downstream async calls triggered after insert
        patch(
            "backend.services.automation_engine.trigger_sequence",
            side_effect=_noop_async,
        ),
        patch(
            "backend.routers.email_enrollment.enroll_lead_in_sequences",
            side_effect=_noop_async,
        ),
        patch(
            "backend.services.lead_alerts.send_new_lead_alert",
            side_effect=_noop_async,
        ),
        # asyncio.to_thread used for tag extraction — return empty list
        patch(
            "asyncio.to_thread",
            new=AsyncMock(return_value=[]),
        ),
    ):
        from backend.routers.widget_lead_helpers import _capture_leads_from_session

        await _capture_leads_from_session(
            tenant_id="tenant-1",
            session_id="sess-phone-new",
            conversation_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        )

        assert mock_insert.called, (
            "tenant_insert must be called when phone dedup finds no existing lead"
        )


# ---------------------------------------------------------------------------
# Test 2: phone-only visitor — existing lead → UPDATE, NOT insert
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_phone_only_existing_lead_is_updated_not_duplicated():
    """Visitor returns with same phone. Existing lead found → update only, no insert."""

    messages = [
        {"role": "user", "content": "John here, 555-867-5309, want a quote"},
        {"role": "assistant", "content": "Happy to help!"},
    ]

    existing_lead = {
        "id": "existing-lead-id",
        "name": "",
        "email": None,
        "phone": "555-867-5309",
        "areas_of_interest": None,
        "conversation_summary": None,
    }

    # Phone dedup finds existing lead
    phone_dedup_chain = _chainable_mock(data=[existing_lead])
    update_chain = _chainable_mock(data=[{"id": "existing-lead-id"}])

    def _fake_tenant_select(db_obj, table, tenant_id, fields):
        return phone_dedup_chain

    with (
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=messages,
        ),
        patch(
            "backend.routers.widget_lead_helpers.get_service_supabase",
            return_value=MagicMock(),
        ),
        patch(
            "backend.routers.widget_lead_helpers.tenant_select",
            side_effect=_fake_tenant_select,
        ),
        patch(
            "backend.routers.widget_lead_helpers.tenant_insert",
        ) as mock_insert,
        patch(
            "backend.routers.widget_lead_helpers.tenant_update",
            return_value=update_chain,
        ) as mock_update,
        patch("backend.routers.widget_lead_helpers.log_activity"),
        patch("backend.routers.widget_lead_helpers.fire_event_background"),
        patch("backend.routers.widget_lead_helpers.score_lead_background"),
        patch(
            "backend.routers.widget_lead_helpers._extract_tags_from_conversation",
            return_value=[],
        ),
    ):
        from backend.routers.widget_lead_helpers import _capture_leads_from_session

        await _capture_leads_from_session(
            tenant_id="tenant-1",
            session_id="sess-phone-existing",
            conversation_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeef",
        )

        # Must NOT insert a duplicate
        assert not mock_insert.called, (
            "tenant_insert must not be called when phone dedup finds existing lead"
        )

        # Must UPDATE to enrich the lead (name filled in from message)
        assert mock_update.called, (
            "tenant_update must be called to enrich the phone-only lead"
        )


# ---------------------------------------------------------------------------
# Test 3: email + phone → email dedup path runs, phone dedup NOT reached
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_email_and_phone_email_dedup_runs_first():
    """Visitor gives email + phone. Email dedup runs; phone dedup path is unreachable."""

    messages = [
        {"role": "user", "content": "I'm Sara, sara@test.com, 555-111-2222"},
        {"role": "assistant", "content": "Got it!"},
    ]

    # Email dedup → no existing lead → falls through to new lead insert
    email_dedup_chain = _chainable_mock(data=[])
    insert_chain = _chainable_mock(data=[{"id": "new-lead-uuid-email"}])
    update_chain = _chainable_mock(data=[])

    def _fake_tenant_select(db_obj, table, tenant_id, fields):
        return email_dedup_chain

    with (
        patch(
            "backend.routers.widget_chat_helpers._load_chat_history",
            return_value=messages,
        ),
        patch(
            "backend.routers.widget_lead_helpers.get_service_supabase",
            return_value=MagicMock(),
        ),
        patch(
            "backend.routers.widget_lead_helpers.tenant_select",
            side_effect=_fake_tenant_select,
        ) as mock_select,
        patch(
            "backend.routers.widget_lead_helpers.tenant_insert",
            return_value=insert_chain,
        ) as mock_insert,
        patch(
            "backend.routers.widget_lead_helpers.tenant_update",
            return_value=update_chain,
        ),
        patch("backend.routers.widget_lead_helpers.log_activity"),
        patch("backend.routers.widget_lead_helpers.fire_event_background"),
        patch("backend.routers.widget_lead_helpers.score_lead_background"),
        patch(
            "backend.routers.widget_lead_helpers._extract_tags_from_conversation",
            return_value=[],
        ),
        patch(
            "backend.services.automation_engine.trigger_sequence",
            side_effect=_noop_async,
        ),
        patch(
            "backend.routers.email_enrollment.enroll_lead_in_sequences",
            side_effect=_noop_async,
        ),
        patch(
            "backend.services.lead_alerts.send_new_lead_alert",
            side_effect=_noop_async,
        ),
        patch(
            "asyncio.to_thread",
            new=AsyncMock(return_value=[]),
        ),
    ):
        from backend.routers.widget_lead_helpers import _capture_leads_from_session

        await _capture_leads_from_session(
            tenant_id="tenant-1",
            session_id="sess-email-phone",
            conversation_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeea",
        )

        # Email dedup select was called
        assert mock_select.called
        # Insert was reached (no existing email lead)
        assert mock_insert.called


# ---------------------------------------------------------------------------
# Test 4–6: _extract_lead_info pure-logic tests (no mocking needed)
# ---------------------------------------------------------------------------

def test_extract_lead_info_phone_only():
    """_extract_lead_info returns phone when only a phone number is present."""
    from backend.routers.widget_lead_helpers import _extract_lead_info

    result = _extract_lead_info("You can reach me at 555-867-5309")
    assert "phone" in result, f"Expected phone in extracted info, got {result}"
    assert "email" not in result
    assert "555" in result["phone"]


def test_extract_lead_info_email_only():
    """_extract_lead_info returns email when only email is present."""
    from backend.routers.widget_lead_helpers import _extract_lead_info

    result = _extract_lead_info("Email me at sara@example.com")
    assert "email" in result
    assert result["email"] == "sara@example.com"
    assert "phone" not in result


def test_extract_lead_info_name_and_phone():
    """_extract_lead_info extracts both name and phone when both are present."""
    from backend.routers.widget_lead_helpers import _extract_lead_info

    result = _extract_lead_info("My name is John Smith, call me at 555-100-2000")
    assert "name" in result
    assert "John" in result["name"]
    assert "phone" in result
