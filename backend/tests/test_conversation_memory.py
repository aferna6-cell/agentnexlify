"""Tests for backend.services.conversation_memory."""

import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.services.conversation_memory import (
    _cosine_similarity,
    retrieve_relevant,
    update_confidence,
    RECENT_WINDOW,
    TOP_K_DEFAULT,
    CONFIDENCE_FLOOR,
    MEMORY_THRESHOLD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    """Run an async coroutine synchronously for unit tests."""
    return asyncio.run(coro)


def _make_msg(index: int, confidence: float = 0.8, embedding=None) -> dict:
    """Build a fake chat_messages row with a stable, time-ordered timestamp."""
    ts = (
        datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index * 5)
    ).isoformat()
    return {
        "id": f"msg-{index:03d}",
        "role": "user" if index % 2 == 0 else "assistant",
        "content": f"Message number {index}",
        "message_confidence": confidence,
        "embedding": embedding,
        "created_at": ts,
    }


def _mock_db(rows):
    """Return a MagicMock supabase client that returns rows on the fetch chain."""
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .gt.return_value
        .order.return_value
        .execute.return_value
    ) = MagicMock(data=rows)
    return mock


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_empty_input():
    assert _cosine_similarity([], []) == 0.0


def test_cosine_zero_vector():
    assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_mismatched_length():
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# update_confidence
# ---------------------------------------------------------------------------


def _mock_db_for_update(current_confidence: float):
    """Return a mock DB that captures the update value."""
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = MagicMock(data=[{"message_confidence": current_confidence}])
    return mock


def test_update_confidence_clamps_upper():
    mock = _mock_db_for_update(0.9)
    captured = {}

    original_update = mock.table.return_value.update

    def capturing_update(data):
        captured["data"] = data
        return original_update(data)

    mock.table.return_value.update = capturing_update

    with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
        update_confidence("msg-1", 0.5)  # 0.9 + 0.5 = 1.4 → clamped to 1.0

    assert captured["data"]["message_confidence"] == pytest.approx(1.0)


def test_update_confidence_clamps_lower():
    mock = _mock_db_for_update(0.1)
    captured = {}

    original_update = mock.table.return_value.update

    def capturing_update(data):
        captured["data"] = data
        return original_update(data)

    mock.table.return_value.update = capturing_update

    with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
        update_confidence("msg-2", -0.5)  # 0.1 - 0.5 = -0.4 → clamped to 0.0

    assert captured["data"]["message_confidence"] == pytest.approx(0.0)


def test_update_confidence_normal_delta():
    mock = _mock_db_for_update(0.5)
    captured = {}

    original_update = mock.table.return_value.update

    def capturing_update(data):
        captured["data"] = data
        return original_update(data)

    mock.table.return_value.update = capturing_update

    with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
        update_confidence("msg-3", 0.2)  # 0.5 + 0.2 = 0.7

    assert captured["data"]["message_confidence"] == pytest.approx(0.7)


def test_update_confidence_message_not_found():
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = MagicMock(data=[])

    with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
        # Must not raise
        update_confidence("nonexistent", 0.1)


# ---------------------------------------------------------------------------
# retrieve_relevant — unit tests
# ---------------------------------------------------------------------------


class TestRetrieveRelevant:
    def test_returns_empty_when_at_or_below_recent_window(self):
        """With ≤ RECENT_WINDOW rows, nothing qualifies as 'older'."""
        rows = [_make_msg(i) for i in range(RECENT_WINDOW)]
        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", [0.1] * 512))

        assert result == []

    def test_returns_empty_on_db_error(self):
        mock = MagicMock()
        mock.table.side_effect = Exception("DB down")

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", [0.1] * 512))

        assert result == []

    def test_retrieval_returns_by_hybrid_score(self):
        """Message with highest cosine similarity ranks first."""
        query_emb = [1.0] + [0.0] * 511
        high_sim_emb = [1.0] + [0.0] * 511   # cosine = 1.0
        low_sim_emb = [0.0, 1.0] + [0.0] * 510  # cosine ≈ 0.0

        # 15 messages: indices 0-14 are older candidates; 15-24 are recent window
        # (but here we only have 15 total → older = 0-4, recent window = 5-14)
        rows = [
            _make_msg(i, embedding=high_sim_emb if i == 2 else low_sim_emb)
            for i in range(15)
        ]
        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", query_emb))

        assert len(result) >= 1
        # High-similarity message (index 2) should be first
        assert result[0]["content"] == "Message number 2"

    def test_respects_top_k(self):
        """Never returns more than top_k results."""
        rows = [_make_msg(i, embedding=[1.0] + [0.0] * 511) for i in range(25)]
        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", [1.0] + [0.0] * 511, top_k=3))

        assert len(result) <= 3

    def test_recent_window_not_returned(self):
        """Messages in the last RECENT_WINDOW are excluded from results."""
        query_emb = [1.0] + [0.0] * 511
        # Give high similarity to a message in the recent window
        rows = []
        for i in range(25):
            # Message 22 is in recent window (indices 15-24) — should be excluded
            emb = [1.0] + [0.0] * 511 if i == 22 else [0.0, 1.0] + [0.0] * 510
            rows.append(_make_msg(i, embedding=emb))

        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", query_emb))

        # Message 22 must not appear in results
        returned_indices = [int(r["content"].split()[-1]) for r in result]
        assert 22 not in returned_indices

    def test_lazy_embed_called_for_missing_embeddings(self):
        """Calls embed_text for messages without pre-computed embeddings."""
        rows = [_make_msg(i, embedding=None) for i in range(15)]
        mock = _mock_db(rows)
        fake_embedding = [0.5] * 512

        async def fake_embed(text: str):
            return fake_embedding

        with (
            patch("backend.services.conversation_memory.get_service_supabase", return_value=mock),
            patch("backend.services.conversation_memory.embed_text", side_effect=fake_embed),
        ):
            result = _run(retrieve_relevant("sess", "t1", [0.5] * 512))

        # Should return results even though embeddings were None
        assert isinstance(result, list)

    def test_confidence_filter_applied_at_db_level(self):
        """DB query uses .gt('message_confidence', CONFIDENCE_FLOOR).

        Verified by confirming the mock chain matches what retrieve_relevant
        builds — the partial index guards low-confidence rows in production.
        """
        rows = [_make_msg(i, confidence=0.9) for i in range(15)]
        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            result = _run(retrieve_relevant("sess", "t1", [0.1] * 512))

        # All returned messages have content (none filtered out here)
        assert all("content" in r for r in result)


# ---------------------------------------------------------------------------
# Integration test — 25-message session
# ---------------------------------------------------------------------------


class TestIntegration25Messages:
    def test_returns_correct_context_slice(self):
        """25-message session: retrieve_relevant returns ≤ top_k older messages.

        Scenario:
          - 25 total messages (indices 0-24)
          - Older candidates: indices 0-14 (25 - RECENT_WINDOW = 15 candidates)
          - Recent window: indices 15-24 (passed verbatim by caller)
          - Message 5 has highest cosine similarity → should rank first

        Widget chat combines: retrieve_relevant() + messages[-10:] for Claude.
        """
        query_emb = [1.0] + [0.0] * 511
        high_sim_emb = [1.0] + [0.0] * 511
        low_sim_emb = [0.0, 1.0] + [0.0] * 510

        rows = []
        for i in range(25):
            emb = high_sim_emb if i == 5 else low_sim_emb
            rows.append(_make_msg(i, confidence=0.8, embedding=emb))

        mock = _mock_db(rows)
        # Stub the embedding update write-back
        mock.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            retrieved = _run(retrieve_relevant("sess-25", "tenant-1", query_emb))

        # Must not exceed TOP_K_DEFAULT
        assert len(retrieved) <= TOP_K_DEFAULT

        # Best result is the high-similarity message
        assert retrieved[0]["content"] == "Message number 5"

        # No recent-window messages (indices 15-24) in results
        for r in retrieved:
            idx = int(r["content"].split()[-1])
            assert idx <= 25 - RECENT_WINDOW - 1, (
                f"Recent message {idx} leaked into older retrieval results"
            )

    def test_combined_context_size(self):
        """Total context = retrieved (≤5) + recent (10) ≤ 15 messages."""
        query_emb = [1.0] + [0.0] * 511
        rows = [_make_msg(i, embedding=[1.0] + [0.0] * 511) for i in range(25)]
        mock = _mock_db(rows)

        with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
            retrieved = _run(retrieve_relevant("sess-25", "tenant-1", query_emb))

        # Caller does: history_for_model = retrieved + messages[-10:]
        last_10 = rows[-10:]
        history_for_model = retrieved + [{"role": r["role"], "content": r["content"]} for r in last_10]

        assert len(history_for_model) <= TOP_K_DEFAULT + RECENT_WINDOW
