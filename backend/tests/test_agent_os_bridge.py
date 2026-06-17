"""Unit tests for the agent_os_bridge pure mappers (no database needed)."""

from backend.services import agent_os_bridge as bridge


def test_map_business_profile_omits_missing_and_maps_names():
    row = {
        "business_name": "Acme Auto",
        "owner_name": "Sam",
        "business_type": "auto_shop",
        "city": "Austin",
        "phone": None,
        "owner_email": "sam@acme.test",
        "google_review_link": None,
    }
    out = bridge.map_business_profile(row)
    assert out["businessName"] == "Acme Auto"
    assert out["ownerName"] == "Sam"
    assert out["businessType"] == "auto_shop"
    assert out["industry"] == "auto_shop"
    assert out["email"] == "sam@acme.test"
    # None values are omitted, never sent as null
    assert "phone" not in out
    assert "reviewLinkGoogle" not in out


def test_map_business_profile_handles_none_row():
    assert bridge.map_business_profile(None) == {}


def test_map_widget_history_groups_by_session_and_summarizes():
    msgs = [
        {"session_id": "s1", "role": "user", "content": "Do you do brakes?", "created_at": "2026-06-01T10:00:00Z"},
        {"session_id": "s1", "role": "assistant", "content": "Yes we do.", "created_at": "2026-06-01T10:00:05Z"},
        {"session_id": "s2", "role": "user", "content": "Hours?", "created_at": "2026-06-02T09:00:00Z"},
    ]
    convos = bridge.map_widget_history(msgs)
    assert len(convos) == 2
    # most-recent session first
    assert convos[0]["id"] == "s2"
    # summary comes from the first USER message of the session
    s1 = next(c for c in convos if c["id"] == "s1")
    assert s1["summary"] == "Do you do brakes?"
    assert s1["closedAt"] == "2026-06-01T10:00:05Z"
    assert s1["topics"] == []


def test_map_lead_maps_canonical_columns_and_omits_missing():
    out = bridge.map_lead({"id": "L1", "name": "Jane", "status": "contacted", "deal_value": 1200})
    assert out == {"id": "L1", "name": "Jane", "status": "contacted", "quoteAmount": 1200}


def test_reply_text_prefers_answer_then_draft_then_notes():
    assert bridge.reply_text({"answer": "Here is the summary."}) == "Here is the summary."

    draft = bridge.reply_text(
        {"orchestratorNotes": ["Routed to Sales."], "draft": {"title": "Quote for Jane"}}
    )
    assert "Routed to Sales." in draft
    assert "Draft ready for review: Quote for Jane" in draft

    assert bridge.reply_text({"orchestratorNotes": ["Saved to wishlist."]}) == "Saved to wishlist."
    assert bridge.reply_text({"noDraftReason": "Nothing to draft."}) == "Nothing to draft."
    assert bridge.reply_text({}) == "Done."


def test_status_map_collapses_demo_statuses():
    assert bridge._STATUS_MAP["completed"] == "succeeded"
    assert bridge._STATUS_MAP["no_draft"] == "succeeded"
    assert bridge._STATUS_MAP["failed"] == "failed"


def test_map_routing_decision_row_snake_cases_and_links_run():
    row = bridge.map_routing_decision_row(
        {
            "ask": "draft a quote",
            "classifier": "heuristic",
            "decision": "routed",
            "chosenAgent": "sales",
            "confidence": 0.82,
            "alternates": [{"agentId": "marketing", "confidence": 0.3}],
            "accepted": None,
        },
        run_id="run-1",
    )
    assert row == {
        "run_id": "run-1",
        "ask": "draft a quote",
        "classifier": "heuristic",
        "decision": "routed",
        "chosen_agent": "sales",
        "confidence": 0.82,
        "alternates": [{"agentId": "marketing", "confidence": 0.3}],
        "accepted": None,
        "changed_to": None,
    }


def test_map_model_call_row_snake_cases_tokens_and_cost():
    row = bridge.map_model_call_row(
        {
            "purpose": "draft",
            "model": "claude-sonnet-4-6",
            "inputTokens": 120,
            "outputTokens": 340,
            "costUsd": 0.0051,
            "ok": True,
        },
        run_id=None,
    )
    assert row == {
        "run_id": None,
        "purpose": "draft",
        "model": "claude-sonnet-4-6",
        "input_tokens": 120,
        "output_tokens": 340,
        "cost_usd": 0.0051,
        "ok": True,
        "error": None,
    }


def test_map_widget_history_merges_stored_sentiment_and_intent():
    msgs = [
        {"session_id": "s1", "role": "user", "content": "Hi", "created_at": "2026-06-01T10:00:00Z"},
        {"session_id": "s2", "role": "user", "content": "Hours?", "created_at": "2026-06-02T09:00:00Z"},
    ]
    sentiment_by_session = {
        "s1": {"sentiment": "negative", "intent": "complaint"},
        "s2": {"sentiment": "positive"},
    }
    convos = bridge.map_widget_history(msgs, sentiment_by_session)
    by_id = {c["id"]: c for c in convos}
    assert by_id["s1"]["sentiment"] == "negative"
    assert by_id["s1"]["intent"] == "complaint"
    assert by_id["s2"]["sentiment"] == "positive"
    # s2 had no stored intent -> key omitted, never fabricated
    assert "intent" not in by_id["s2"]


def test_map_widget_history_omits_sentiment_when_unclassified():
    msgs = [
        {"session_id": "s1", "role": "user", "content": "Hi", "created_at": "2026-06-01T10:00:00Z"},
    ]
    convos = bridge.map_widget_history(msgs)
    assert "sentiment" not in convos[0]
    assert "intent" not in convos[0]


class _FakeChain:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        from types import SimpleNamespace

        return SimpleNamespace(data=self._rows)


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _FakeChain(self._rows)


def test_load_conversation_sentiment_builds_session_map():
    db = _FakeDB(
        [
            {"session_id": "s1", "sentiment": "positive", "intent": "booking request"},
            {"session_id": "s2", "sentiment": None, "intent": None},
            {"session_id": None, "sentiment": "negative", "intent": "complaint"},
        ]
    )
    out = bridge._load_conversation_sentiment(db, "client-1")
    assert out == {"s1": {"sentiment": "positive", "intent": "booking request"}}


def test_load_conversation_sentiment_degrades_on_query_failure():
    class _BoomDB:
        def table(self, name):
            raise RuntimeError("no such column: sentiment")

    assert bridge._load_conversation_sentiment(_BoomDB(), "client-1") == {}
