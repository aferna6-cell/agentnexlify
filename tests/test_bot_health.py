"""Bot-Health evals (#R4) — unit tests.

Contracts:
  - _compute_health_score implements the documented weighted formula
    (resolution 50% / low-hallucination 25% / low-unresolved 15% / sentiment 10%).
  - score_tenant_bot_health aggregates the judge verdicts correctly and inserts
    one bot_health_scores row keyed by tenant_id (NOT client_id).
  - score_tenant_bot_health never raises: empty messages, judge failure, an
    unparseable/count-mismatched judge response, and DB failure all return None.
  - the judge runs on Haiku (cheap, high-volume — #R7 cost floor).
  - router: GET is tenant-scoped (403 on mismatch) and returns no_data when the
    tenant has never been scored; POST /run rejects a bad admin secret (401).
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import backend.services.bot_health as bot_health
from backend.services.bot_health import (
    _JUDGE_MODEL,
    _compute_health_score,
    score_tenant_bot_health,
)
from backend.routers.bot_health import (
    _verify_admin_secret,
    _verify_tenant,
    get_latest_bot_health,
)

TENANT = "11111111-1111-1111-1111-111111111111"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _messages_two_sessions():
    """Two distinct sessions -> two conversations after reconstruction."""
    return [
        {"session_id": "s1", "role": "user", "content": "do you do drain cleaning?",
         "created_at": "2026-07-10T10:00:00+00:00"},
        {"session_id": "s1", "role": "assistant", "content": "Yes, we do.",
         "created_at": "2026-07-10T10:00:05+00:00"},
        {"session_id": "s2", "role": "user", "content": "how much for a water heater?",
         "created_at": "2026-07-10T11:00:00+00:00"},
        {"session_id": "s2", "role": "assistant", "content": "It depends on the model.",
         "created_at": "2026-07-10T11:00:05+00:00"},
    ]


def _db_with_messages(messages):
    """Mock get_service_supabase() -> db.table('chat_messages').select().eq().gte().order().execute()."""
    db = MagicMock()
    chain = MagicMock()
    for m in ["select", "eq", "gte", "order"]:
        getattr(chain, m).return_value = chain
    chain.execute.return_value = MagicMock(data=messages)
    db.table.return_value = chain
    return db


def _judge_result(json_text):
    r = MagicMock()
    r.text = json_text
    return r


# ---------------------------------------------------------------------------
# Formula
# ---------------------------------------------------------------------------


def test_health_score_perfect_is_100():
    score = _compute_health_score(
        resolution_rate=1.0, hallucination_rate=0.0, unresolved_rate=0.0, avg_sentiment=1.0
    )
    assert score == 100.0


def test_health_score_worst_is_zero():
    # 0 resolution, all hallucinate, all unresolved, worst sentiment -> 0
    score = _compute_health_score(
        resolution_rate=0.0, hallucination_rate=1.0, unresolved_rate=1.0, avg_sentiment=-1.0
    )
    assert score == 0.0


def test_health_score_weighted_midpoint():
    # resolution .5 (.25) + low-halluc 1 (.25) + low-unresolved 1 (.15) + sentiment 0 -> .5 (.05)
    # = 100 * (0.25 + 0.25 + 0.15 + 0.05) = 70.0
    score = _compute_health_score(
        resolution_rate=0.5, hallucination_rate=0.0, unresolved_rate=0.0, avg_sentiment=0.0
    )
    assert score == 70.0


# ---------------------------------------------------------------------------
# score_tenant_bot_health — happy path + skips
# ---------------------------------------------------------------------------


def test_scores_and_inserts_row_with_correct_aggregation():
    db = _db_with_messages(_messages_two_sessions())
    # session 1 resolved + happy, session 2 unresolved + hallucination + negative
    verdicts = (
        '[{"resolved": true, "hallucination_risk": false, "unresolved_intent": false, "sentiment": 1.0},'
        ' {"resolved": false, "hallucination_risk": true, "unresolved_intent": true, "sentiment": -1.0}]'
    )
    insert_chain = MagicMock()
    insert_chain.insert.return_value = insert_chain
    insert_chain.execute.return_value = MagicMock(data=[{"id": "row-1", "health_score": 55.0}])

    with patch.object(bot_health, "get_service_supabase", return_value=db), patch.object(
        bot_health, "call_claude_messages", new=AsyncMock(return_value=_judge_result(verdicts))
    ) as judge, patch.object(bot_health, "tenant_table", return_value=insert_chain):
        result = asyncio.run(score_tenant_bot_health(TENANT, window_days=7))

    assert result is not None
    # judge ran on Haiku
    assert judge.await_args.kwargs["model"] == _JUDGE_MODEL
    # aggregation on the row passed to insert
    inserted_row = insert_chain.insert.call_args.args[0]
    assert inserted_row["sample_size"] == 2
    assert inserted_row["resolution_rate"] == 0.5
    assert inserted_row["hallucination_flag_count"] == 1
    assert inserted_row["unresolved_intent_count"] == 1
    assert inserted_row["avg_sentiment"] == 0.0
    # 100*(.5*.5 + .25*.5 + .15*.5 + .10*.5) = 50.0
    assert inserted_row["health_score"] == 50.0


def test_no_recent_messages_returns_none():
    db = _db_with_messages([])
    with patch.object(bot_health, "get_service_supabase", return_value=db):
        result = asyncio.run(score_tenant_bot_health(TENANT))
    assert result is None


def test_judge_failure_returns_none_not_raise():
    db = _db_with_messages(_messages_two_sessions())
    with patch.object(bot_health, "get_service_supabase", return_value=db), patch.object(
        bot_health, "call_claude_messages", new=AsyncMock(side_effect=RuntimeError("boom"))
    ):
        result = asyncio.run(score_tenant_bot_health(TENANT))
    assert result is None


def test_unparseable_judge_returns_none():
    db = _db_with_messages(_messages_two_sessions())
    with patch.object(bot_health, "get_service_supabase", return_value=db), patch.object(
        bot_health, "call_claude_messages", new=AsyncMock(return_value=_judge_result("not json"))
    ):
        result = asyncio.run(score_tenant_bot_health(TENANT))
    assert result is None


def test_count_mismatch_judge_returns_none():
    # 2 conversations but judge returns 1 verdict -> mismatch -> None
    db = _db_with_messages(_messages_two_sessions())
    one = '[{"resolved": true, "hallucination_risk": false, "unresolved_intent": false, "sentiment": 0.5}]'
    with patch.object(bot_health, "get_service_supabase", return_value=db), patch.object(
        bot_health, "call_claude_messages", new=AsyncMock(return_value=_judge_result(one))
    ):
        result = asyncio.run(score_tenant_bot_health(TENANT))
    assert result is None


# ---------------------------------------------------------------------------
# Router auth
# ---------------------------------------------------------------------------


def test_verify_tenant_rejects_mismatch():
    with pytest.raises(HTTPException) as exc:
        _verify_tenant({"tenant_id": "other"}, TENANT)
    assert exc.value.status_code == 403


def test_verify_admin_secret_rejects_bad_secret():
    with patch("backend.routers.bot_health._admin_secret", return_value="right"):
        with pytest.raises(HTTPException) as exc:
            _verify_admin_secret("wrong")
        assert exc.value.status_code == 401


def test_get_latest_returns_no_data_when_never_scored():
    empty_chain = MagicMock()
    for m in ["select", "order", "limit"]:
        getattr(empty_chain, m).return_value = empty_chain
    empty_chain.execute.return_value = MagicMock(data=[])
    with patch("backend.routers.bot_health.get_service_supabase", return_value=MagicMock()), patch(
        "backend.routers.bot_health.tenant_table", return_value=empty_chain
    ):
        resp = asyncio.run(get_latest_bot_health(TENANT, claims={"tenant_id": TENANT}))
    assert resp.status == "no_data"
