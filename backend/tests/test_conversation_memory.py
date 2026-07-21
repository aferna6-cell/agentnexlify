"""Tests for the conversation memory tier (issue #69).

App-free: exercises the deterministic scoring core + build_tiered_history with
injected loader/embed_fn, so no live Voyage/Supabase is required.
"""

import asyncio

from backend.services.conversation_memory import (
    CONFIDENCE_FLOOR,
    build_tiered_history,
    cosine_similarity,
    hybrid_score,
    rank_messages,
    update_confidence,
)


def test_hybrid_score_weights_sum_to_one_at_max():
    assert hybrid_score(1.0, 1.0, 1.0) == 1.0
    assert hybrid_score(0.0, 0.0, 0.0) == 0.0
    # Cosine is the heaviest term (0.4).
    assert hybrid_score(1.0, 0.0, 0.0) > hybrid_score(0.0, 1.0, 0.0)


def test_cosine_similarity_bounds():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity(None, [1.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0  # length mismatch


def test_rank_messages_filters_low_confidence():
    q = [1.0, 0.0]
    candidates = [
        {"content": "a", "message_confidence": 0.2, "embedding": [1.0, 0.0]},  # dropped
        {"content": "b", "message_confidence": 0.9, "embedding": [0.0, 1.0]},
    ]
    ranked = rank_messages(q, candidates, top_k=5)
    contents = [m["content"] for m in ranked]
    assert "a" not in contents  # confidence 0.2 <= floor
    assert "b" in contents
    assert all(m["message_confidence"] > CONFIDENCE_FLOOR for m in ranked)


def test_rank_messages_orders_by_score_and_caps_top_k():
    q = [1.0, 0.0]
    # Ordered oldest->newest; the exact match is also the newest so it wins on
    # both cosine AND recency (recency is weighted, so a newer good-enough match
    # can outrank an older exact one — this test avoids that ambiguity).
    candidates = [
        {"content": "orth", "message_confidence": 0.8, "embedding": [0.0, 1.0]},
        {"content": "mid", "message_confidence": 0.8, "embedding": [0.7, 0.7]},
        {"content": "match", "message_confidence": 0.8, "embedding": [1.0, 0.0]},
    ]
    ranked = rank_messages(q, candidates, top_k=2)
    assert len(ranked) == 2
    assert ranked[0]["content"] == "match"  # best combined cosine + recency
    assert ranked[0]["memory_score"] >= ranked[1]["memory_score"]
    assert "orth" not in [m["content"] for m in ranked]  # cosine 0 + old ranks out


class _CapturingDB:
    """Captures the chat_messages update so we assert observable state."""

    def __init__(self, current):
        self._current = current
        self.written = None
        self._mode = None

    def table(self, name):
        return self

    def select(self, cols):
        self._mode = "select"
        return self

    def update(self, payload):
        self.written = payload
        self._mode = "update"
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self._mode == "select":
            data = [] if self._current is None else [{"message_confidence": self._current}]
            return type("R", (), {"data": data})()
        return type("R", (), {"data": []})()


def test_update_confidence_clamps_to_unit_interval():
    db = _CapturingDB(current=0.95)
    new = update_confidence(db, "tenant-1", "msg-1", 0.2)
    assert new == 1.0
    assert db.written == {"message_confidence": 1.0}

    db2 = _CapturingDB(current=0.1)
    assert update_confidence(db2, "tenant-1", "msg-1", -0.5) == 0.0

    db3 = _CapturingDB(current=None)  # message not found
    assert update_confidence(db3, "tenant-1", "missing", 0.1) is None


def _fake_embed_factory():
    # Deterministic 2D "embedding": align vector toward whichever axis a keyword hits.
    async def embed(texts):
        out = []
        for t in texts:
            out.append([1.0, 0.0] if "pricing" in t else [0.0, 1.0])
        return out
    return embed


def test_build_tiered_history_returns_none_below_threshold():
    def loader(db, tid, sid, limit):
        return [{"id": str(i), "role": "user", "content": f"m{i}", "message_confidence": 0.8} for i in range(5)]

    result = asyncio.run(
        build_tiered_history(None, "t", "s", "pricing?", loader=loader, embed_fn=_fake_embed_factory())
    )
    assert result is None  # 5 <= threshold(20)


def test_build_tiered_history_long_conversation_slice():
    # 25 messages oldest->newest. Message 2 is the only "pricing" older message.
    msgs = []
    for i in range(25):
        content = "pricing details" if i == 2 else f"chit chat {i}"
        msgs.append({"id": str(i), "role": "user", "content": content, "message_confidence": 0.8})

    def loader(db, tid, sid, limit):
        return list(msgs)

    result = asyncio.run(
        build_tiered_history(
            None, "t", "s", "what about pricing",
            loader=loader, embed_fn=_fake_embed_factory(),
            recent_window=10, top_k=5, threshold=20,
        )
    )
    assert result is not None
    # 10 recent + up to 5 older = 15 items, each a {role, content} dict.
    assert len(result) == 15
    assert all(set(m.keys()) == {"role", "content"} for m in result)
    # Recent window preserved verbatim as the tail (messages 15..24).
    assert [m["content"] for m in result[-10:]] == [msgs[i]["content"] for i in range(15, 25)]
    # The relevant older "pricing" message (index 2) is pulled into the slice.
    assert "pricing details" in [m["content"] for m in result]
