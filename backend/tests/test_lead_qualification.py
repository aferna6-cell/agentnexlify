"""Unit tests for backend.services.lead_qualification.

These tests stub out both the Supabase client and the Managed Agents
client — no network, no database, no API cost.

Focus areas:
  1. Plan gating — free tier must NEVER spend on the agent.
  2. JSON extraction — handles fenced, bare, and wrapped responses.
  3. Normalization — clamps scores, rejects invalid recommendations.
  4. Persistence payload shape — stores json, recommendation, qualified_at.
  5. Background wrapper swallows exceptions so FastAPI's BackgroundTasks
     doesn't blow up the request cycle.
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.lead_qualification import (
    LeadQualificationError,
    _extract_json_from_reply,
    _normalize_qualification,
    qualify_lead,
    qualify_lead_background,
)


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_direct_parse_of_bare_json(self):
        text = '{"intent_score": 8, "recommendation": "hot_call_now"}'
        result = _extract_json_from_reply(text)
        assert result == {"intent_score": 8, "recommendation": "hot_call_now"}

    def test_fenced_json_block(self):
        text = "Here's the result:\n```json\n{\"fit_score\": 5}\n```\nThanks."
        result = _extract_json_from_reply(text)
        assert result == {"fit_score": 5}

    def test_unlabeled_fence(self):
        text = "```\n{\"intent_score\": 3}\n```"
        result = _extract_json_from_reply(text)
        assert result == {"intent_score": 3}

    def test_json_wrapped_in_prose(self):
        text = (
            "After analyzing the lead, my assessment is:\n\n"
            '{"intent_score": 7, "fit_score": 6, "recommendation": "warm_nurture_sequence"}\n\n'
            "Let me know if you need more details."
        )
        result = _extract_json_from_reply(text)
        assert result is not None
        assert result["recommendation"] == "warm_nurture_sequence"

    def test_empty_string_returns_none(self):
        assert _extract_json_from_reply("") is None

    def test_no_json_returns_none(self):
        assert _extract_json_from_reply("Just plain prose, nothing here.") is None

    def test_non_dict_json_returns_none(self):
        # Bare array at top level — not what we want.
        assert _extract_json_from_reply("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_clamps_scores_to_range(self):
        raw = {
            "intent_score": 99,
            "fit_score": -5,
            "recommendation": "hot_call_now",
        }
        result = _normalize_qualification(raw)
        assert result["intent_score"] == 10
        assert result["fit_score"] == 1

    def test_string_scores_coerced(self):
        raw = {"intent_score": "7", "recommendation": "cold_drop"}
        result = _normalize_qualification(raw)
        assert result["intent_score"] == 7
        assert result["recommendation"] == "cold_drop"

    def test_invalid_recommendation_dropped(self):
        raw = {"recommendation": "call_them_asap"}
        result = _normalize_qualification(raw)
        assert "recommendation" not in result

    def test_reasoning_and_reply_preserved(self):
        raw = {
            "recommendation": "hot_call_now",
            "reasoning": "  High intent, good fit. ",
            "suggested_first_reply": "Hi, thanks for reaching out!",
        }
        result = _normalize_qualification(raw)
        assert result["reasoning"] == "High intent, good fit."
        assert result["suggested_first_reply"] == "Hi, thanks for reaching out!"

    def test_empty_strings_dropped(self):
        raw = {"reasoning": "   ", "recommendation": "cold_drop"}
        result = _normalize_qualification(raw)
        assert "reasoning" not in result

    def test_unknown_keys_dropped(self):
        raw = {
            "recommendation": "hot_call_now",
            "chain_of_thought": "should not be persisted",
        }
        result = _normalize_qualification(raw)
        assert "chain_of_thought" not in result


# ---------------------------------------------------------------------------
# Plan gating + orchestration
# ---------------------------------------------------------------------------


def _fake_supabase_for(lead: dict, tenant: dict):
    """Build a MagicMock Supabase client that serves this specific lead + tenant.

    Returns the SAME MagicMock per table name on repeated `.table(name)`
    calls so tests can assert against `.table('leads').update.call_args`.
    """
    db = MagicMock()
    tables: dict[str, MagicMock] = {}

    def _build_leads_tbl():
        tbl = MagicMock()
        select_chain = MagicMock()
        select_chain.data = [lead] if lead else []
        tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = select_chain
        tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[lead] if lead else [])
        return tbl

    def _build_tenants_tbl():
        tbl = MagicMock()
        select_chain = MagicMock()
        select_chain.data = [tenant] if tenant else []
        tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = select_chain
        return tbl

    def _build_activity_tbl():
        tbl = MagicMock()
        tbl.insert.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    def table_side_effect(name):
        if name not in tables:
            if name == "leads":
                tables[name] = _build_leads_tbl()
            elif name == "tenants":
                tables[name] = _build_tenants_tbl()
            elif name == "activity_log":
                tables[name] = _build_activity_tbl()
            else:
                tables[name] = MagicMock()
        return tables[name]

    db.table.side_effect = table_side_effect
    return db


class TestQualifyLead:
    def test_free_plan_skips_agent_entirely(self):
        lead = {"id": "lead_1", "client_id": "tenant_1", "name": "Test"}
        tenant = {"id": "tenant_1", "plan": "free", "business_name": "Coffee Shop"}
        db = _fake_supabase_for(lead, tenant)

        with (
            patch("backend.services.lead_qualification.get_supabase", return_value=db),
            patch("backend.services.lead_qualification.ManagedAgentsClient") as mock_client_cls,
            patch("backend.services.lead_qualification.lead_qualifier"),
        ):
            result = qualify_lead("lead_1")

        assert result is None
        # Plan gate runs BEFORE we construct the client → no instantiation.
        mock_client_cls.assert_not_called()

    def test_growth_plan_runs_agent_and_persists(self):
        lead = {
            "id": "lead_1",
            "client_id": "tenant_1",
            "name": "Alice",
            "email": "alice@example.com",
        }
        tenant = {
            "id": "tenant_1",
            "plan": "growth",
            "business_name": "Alice Auto",
            "business_type": "auto_repair",
        }
        db = _fake_supabase_for(lead, tenant)

        # Agent replies with a clean JSON summary.
        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            '{"intent_score": 8, "fit_score": 7, '
                            '"recommendation": "hot_call_now", '
                            '"reasoning": "Strong signals.", '
                            '"suggested_first_reply": "Hi Alice!"}'
                        ),
                    }
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = events
        mock_client.send_user_message.return_value = None

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_abc"
        mock_handle.environment_id = "env_abc"

        with (
            patch("backend.services.lead_qualification.get_supabase", return_value=db),
            patch("backend.services.lead_qualification.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.lead_qualification.lead_qualifier", return_value=mock_handle),
        ):
            result = qualify_lead("lead_1")

        assert result is not None
        assert result["recommendation"] == "hot_call_now"
        assert result["intent_score"] == 8
        assert result["fit_score"] == 7

        # Persistence: leads.update called with the normalized payload.
        leads_update_call = db.table("leads").update.call_args
        payload = leads_update_call.args[0]
        assert payload["qualification_recommendation"] == "hot_call_now"
        assert payload["qualification_json"]["intent_score"] == 8
        assert "qualified_at" in payload

        # Metadata sanity: flow, tenant_id, lead_id.
        session_kwargs = mock_client.create_session.call_args.kwargs
        assert session_kwargs["metadata"]["flow"] == "lead_qualification"
        assert session_kwargs["metadata"]["tenant_id"] == "tenant_1"
        assert session_kwargs["metadata"]["lead_id"] == "lead_1"

    def test_missing_lead_returns_none(self):
        db = _fake_supabase_for(None, None)
        with (
            patch("backend.services.lead_qualification.get_supabase", return_value=db),
            patch("backend.services.lead_qualification.ManagedAgentsClient") as mock_client_cls,
        ):
            result = qualify_lead("nonexistent")
        assert result is None
        mock_client_cls.assert_not_called()

    def test_unparseable_reply_raises(self):
        lead = {"id": "lead_1", "client_id": "tenant_1", "name": "Bob"}
        tenant = {"id": "tenant_1", "plan": "professional", "business_name": "Bob"}
        db = _fake_supabase_for(lead, tenant)

        events = iter([
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": "Just prose, no JSON."}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ])
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = events

        mock_handle = MagicMock()
        mock_handle.agent_id = "agent_abc"
        mock_handle.environment_id = "env_abc"

        with (
            patch("backend.services.lead_qualification.get_supabase", return_value=db),
            patch("backend.services.lead_qualification.ManagedAgentsClient", return_value=mock_client),
            patch("backend.services.lead_qualification.lead_qualifier", return_value=mock_handle),
        ):
            with pytest.raises(LeadQualificationError):
                qualify_lead("lead_1")

    def test_background_wrapper_swallows_exceptions(self):
        """The _background variant must never raise — BackgroundTasks
        propagates exceptions if it does, which would taint the response."""
        with patch(
            "backend.services.lead_qualification.qualify_lead",
            side_effect=RuntimeError("boom"),
        ):
            # Must not raise.
            qualify_lead_background("lead_1")
