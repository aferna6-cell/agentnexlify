import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from backend.services.conversation_memory import retrieve_relevant, update_confidence


def _run(coro):
    return asyncio.run(coro)


def _make_msg(index: int, embedding=None) -> dict:
    ts = (
        datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index * 5)
    ).isoformat()
    return {
        "id": f"msg-{index:03d}",
        "role": "user" if index % 2 == 0 else "assistant",
        "content": f"Message number {index}",
        "message_confidence": 0.8,
        "embedding": embedding,
        "created_at": ts,
    }


def _mock_db(rows):
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


def test_update_confidence_db_failure_does_not_raise():
    mock = MagicMock()
    mock.table.side_effect = RuntimeError("DB down")

    with patch("backend.services.conversation_memory.get_service_supabase", return_value=mock):
        update_confidence("msg-4", 0.1)


def test_embedding_store_failure_does_not_block_results():
    rows = [_make_msg(i, embedding=None) for i in range(15)]
    mock = _mock_db(rows)
    mock.table.return_value.update.return_value.eq.return_value.execute.side_effect = RuntimeError(
        "write failed"
    )
    fake_embedding = [0.5] * 512

    async def fake_embed(text: str):
        return fake_embedding

    with (
        patch("backend.services.conversation_memory.get_service_supabase", return_value=mock),
        patch("backend.services.conversation_memory.embed_text", side_effect=fake_embed),
    ):
        result = _run(retrieve_relevant("sess", "t1", [0.5] * 512))

    assert isinstance(result, list)
    assert result
