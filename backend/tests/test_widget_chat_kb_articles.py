import asyncio
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from starlette.requests import Request

from backend.models.schemas import WidgetChatRequest
from backend.routers import widget_chat as widget_chat_module


def _run(coro):
    return asyncio.run(coro)


def _make_request():
    return Request({"type": "http", "method": "POST", "path": "/api/v1/widget/chat", "headers": []})


def _make_empty_db():
    mock = MagicMock()
    empty = MagicMock(data=[])
    table = mock.table.return_value
    table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = empty
    return mock


def _cached_widget_value(key, ttl=None):
    if key.startswith("faq:") or key.startswith("corr:"):
        return []
    if key.startswith("bh:") or key.startswith("wsc:"):
        return False
    return None


def test_kb_article_refs_are_added_to_prompt_and_background_tasks():
    refs = [
        {
            "id": "article-1",
            "title": "KB Article",
            "summary": "Helpful summary",
            "source_url": "https://example.com/article",
            "last_validated": "2026-04-01T00:00:00+00:00",
        }
    ]
    captured = {}
    background_tasks = MagicMock()
    req = WidgetChatRequest(
        api_key="widget-key",
        session_id="sess-kb",
        message="Need help with pricing",
    )
    widget = {"tenant_id": "tenant-1", "knowledge_base": "kb", "show_watermark": True}
    tenant = {
        "id": "tenant-1",
        "business_name": "Acme",
        "plan": "growth",
        "business_type": "general",
    }

    def fake_resolve_int_setting(key, default=0):
        if key == "widget_kb_articles_enabled":
            return 1
        return default

    def fake_build_system_prompt(*args, **kwargs):
        captured["kb_article_refs"] = kwargs.get("kb_article_refs")
        return "system prompt"

    async def fake_claude_messages(**kwargs):
        return SimpleNamespace(text="All good", duration_ms=1, input_tokens=1, output_tokens=1)

    with ExitStack() as stack:
        stack.enter_context(patch("backend.routers.widget_chat._get_widget_config", return_value=widget))
        stack.enter_context(patch("backend.routers.widget_chat._get_tenant", return_value=tenant))
        stack.enter_context(patch("backend.routers.widget_chat._check_origin"))
        stack.enter_context(patch("backend.routers.widget_chat._get_or_create_conversation", return_value=("conv-1", False)))
        stack.enter_context(patch("backend.routers.widget_chat.get_service_supabase", return_value=_make_empty_db()))
        stack.enter_context(patch("backend.routers.widget_chat._load_chat_history", return_value=[]))
        stack.enter_context(patch("backend.routers.widget_chat._build_intent_window", return_value="pricing"))
        stack.enter_context(patch("backend.routers.widget_chat._needs_job_context", return_value=False))
        stack.enter_context(patch("backend.routers.widget_chat._needs_bid_context", return_value=False))
        stack.enter_context(patch("backend.routers.widget_chat._compact_messages_for_llm", return_value=[]))
        stack.enter_context(patch("backend.routers.widget_chat._get_cached", side_effect=_cached_widget_value))
        stack.enter_context(patch("backend.routers.widget_chat._build_system_prompt", side_effect=fake_build_system_prompt))
        stack.enter_context(patch("backend.routers.widget_chat.resolve_int_setting", side_effect=fake_resolve_int_setting))
        stack.enter_context(patch("backend.routers.widget_chat.resolve_string_setting", side_effect=lambda key, default=None: default))
        stack.enter_context(patch("backend.routers.widget_chat.estimate_widget_chat_tokens", return_value=12))
        stack.enter_context(patch("backend.routers.widget_chat.reserve_ai_tokens", return_value=SimpleNamespace(allowed=True, reason=None)))
        stack.enter_context(patch("backend.routers.widget_chat.call_claude_messages", side_effect=fake_claude_messages))
        stack.enter_context(patch("backend.routers.widget_chat.record_ai_usage", return_value=None))
        stack.enter_context(patch("backend.routers.widget_chat._extract_order_from_response", return_value=None))
        stack.enter_context(patch("backend.routers.widget_chat._extract_bid_request_from_response", return_value=None))
        stack.enter_context(patch("backend.routers.widget_chat._run_support_fallback", return_value=("All good", False)))
        stack.enter_context(patch("backend.routers.widget_chat._save_chat_messages"))
        stack.enter_context(patch("backend.routers.widget_chat.fire_event_background"))
        stack.enter_context(patch("backend.routers.widget_chat._extract_lead_info", return_value=None))
        stack.enter_context(patch("backend.routers.widget_chat.log_activity"))
        stack.enter_context(patch("backend.routers.widget_chat._query_kb_articles", return_value=refs))
        response = _run(
            widget_chat_module.widget_chat(_make_request(), req, background_tasks)
        )

    assert captured["kb_article_refs"] == refs
    background_tasks.add_task.assert_any_call(
        widget_chat_module._increment_kb_citation_counts,
        ["article-1"],
    )
    assert response.response == "All good"
