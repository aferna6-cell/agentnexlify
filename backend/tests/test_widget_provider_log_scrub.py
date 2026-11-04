"""Widget chat logs omit session ids and provider exception text.

Provider failures still release the reservation once and return the safe
fallback. These tests cover the widget loggers only. Runtime traces are
covered with the usage-accounting change.
"""

import logging
from unittest.mock import AsyncMock, patch

import anthropic
import httpx
import pytest

from backend.tests.test_widget_chat_pipeline import _Chain, _patch_llm, _post_chat, _result, _seed

_PROVIDER_CANARY = "visitor@example.com\r\nINJECTED authorization=Bearer sentinel-token"
_SAFE_FALLBACK = (
    "I'm sorry, I'm having trouble right now. "
    "Please try again in a moment or contact us directly."
)
_RAW_SESSION = _PROVIDER_CANARY


class _WidgetProviderError(Exception):
    def __init__(self):
        super().__init__(_PROVIDER_CANARY + " response body")
        self.status_code = 503


class _BadProviderStatus:
    def __str__(self):
        return _PROVIDER_CANARY + " response body"


class _FakeMessages:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raise self.outcome


class _FakeAnthropic:
    def __init__(self, outcome):
        self.messages = _FakeMessages(outcome)

    def __call__(self, *_args, **_kwargs):
        return self


def _concrete_provider_error(family, status):
    message = _PROVIDER_CANARY + " response body"
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    proved = type(status) is int and 100 <= status <= 599
    if family == "generic":
        exc = _WidgetProviderError()
        exc.status_code = status
        return exc, "_WidgetProviderError"
    if family == "api":
        exc = anthropic.APIError(message, request, body=message)
        exc.status_code = status
        return exc, "APIError"
    response = httpx.Response(status if proved else 400, request=request)
    cls = anthropic.AuthenticationError if family == "auth" else anthropic.RateLimitError
    exc = cls(message, response=response, body=message)
    if not proved:
        exc.status_code = status
    return exc, cls.__name__


def _widget_log_blob(caplog) -> str:
    pieces = []
    for record in caplog.records:
        if not record.name.startswith("backend.routers.widget_chat"):
            continue
        message = record.getMessage()
        pieces.append(message)
        assert "\r" not in message
        assert "\n" not in message
        assert record.exc_info is None
        if record.exc_text:
            pieces.append(record.exc_text)
    return "\n".join(pieces)


def _assert_canaries_absent(blob: str) -> None:
    for piece in (
        "visitor@example.com",
        "INJECTED",
        "authorization=Bearer",
        "sentinel-token",
        "Traceback",
        "response body",
        "\r",
    ):
        assert piece not in blob


def test_widget_logs_omit_raw_session_id(client, mock_supabase, caplog):
    caplog.set_level(logging.DEBUG)
    _seed(
        mock_supabase,
        tenant_id="p9270000-0000-4000-8000-000000000021",
        api_key="anx_widget_session_scrub",
    )
    llm_patch, kb_patch, _llm = _patch_llm("Still here.")

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        llm_patch,
        kb_patch,
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
        patch(
            "backend.routers.widget_chat.record_ai_usage",
            return_value=None,
        ),
    ):
        response = _post_chat(
            client,
            "anx_widget_session_scrub",
            "How fast can you fix a pipeline?",
            _RAW_SESSION,
        )

    assert response.status_code == 200
    assert response.json()["response"] == "Still here."
    _assert_canaries_absent(_widget_log_blob(caplog))


def test_widget_provider_failure_omits_exception_text(client, mock_supabase, caplog):
    caplog.set_level(logging.DEBUG)
    _seed(
        mock_supabase,
        tenant_id="p9270000-0000-4000-8000-000000000020",
        api_key="anx_acct_provider_privacy",
    )
    calls: list[str] = []

    def routed(name, params=None, **_kwargs):
        calls.append(name)
        if name == "reserve_ai_token_budget":
            return _Chain(_result(True))
        raise AssertionError(name)

    mock_supabase.rpc.side_effect = routed
    fake = _FakeAnthropic(_WidgetProviderError())

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        patch("backend.services.llm_runtime.anthropic.Anthropic", fake),
        patch("backend.routers.widget_chat._query_kb_articles", new=AsyncMock(return_value=[])),
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
    ):
        response = _post_chat(
            client,
            "anx_acct_provider_privacy",
            "How fast can you fix a pipeline?",
            "sess-provider-privacy",
        )

    assert response.status_code == 200
    assert response.json()["response"] == _SAFE_FALLBACK
    assert calls.count("record_ai_token_usage") == 0
    assert calls.count("release_ai_token_reservation") == 1
    assert len(fake.messages.calls) == 1
    blob = _widget_log_blob(caplog)
    _assert_canaries_absent(blob)
    assert "error_type=_WidgetProviderError" in blob
    assert "status=503" in blob


@pytest.mark.parametrize(
    ("case_id", "family", "status", "proved"),
    (
        (30, "auth", 401, True),
        (31, "rate", 429, True),
        (32, "api", 500, True),
        (33, "api", True, False),
        (34, "api", "401", False),
        (35, "api", 1.5, False),
        (36, "api", -1, False),
        (37, "api", 99, False),
        (38, "api", 600, False),
        (39, "auth", True, False),
        (40, "rate", "429", False),
        (41, "generic", 503, True),
        (42, "generic", _BadProviderStatus(), False),
    ),
)
def test_widget_concrete_provider_errors_omit_exception_text(
    client, mock_supabase, caplog, case_id, family, status, proved
):
    caplog.set_level(logging.DEBUG)
    api_key = f"anx_acct_priv_{case_id}"
    _seed(
        mock_supabase,
        tenant_id=f"p9270000-0000-4000-8000-{case_id:012d}",
        api_key=api_key,
    )
    calls: list[str] = []

    def routed(name, params=None, **_kwargs):
        calls.append(name)
        if name in {"reserve_ai_token_budget", "release_ai_token_reservation"}:
            return _Chain(_result(True))
        raise AssertionError(name)

    mock_supabase.rpc.side_effect = routed
    exc, error_type = _concrete_provider_error(family, status)
    fake = _FakeAnthropic(exc)

    async def _allow_screen(*_args, **_kwargs):
        return None

    with (
        patch("backend.services.llm_runtime.anthropic.Anthropic", fake),
        patch("backend.services.llm_runtime.time.sleep", return_value=None),
        patch("backend.routers.widget_chat._query_kb_articles", new=AsyncMock(return_value=[])),
        patch(
            "backend.routers.widget_chat_guards.input_screen_guard",
            side_effect=_allow_screen,
        ),
    ):
        response = _post_chat(
            client,
            api_key,
            "How fast can you fix a pipeline?",
            f"sess-provider-privacy-{case_id}",
        )

    assert response.status_code == 200
    assert response.json()["response"] == _SAFE_FALLBACK
    assert calls.count("record_ai_token_usage") == 0
    assert calls.count("release_ai_token_reservation") == 1
    assert len(fake.messages.calls) == (3 if family == "rate" else 1)
    blob = _widget_log_blob(caplog)
    _assert_canaries_absent(blob)
    assert f"error_type={error_type}" in blob
    if proved:
        assert f"status={status}" in blob
    else:
        assert "status=" not in blob
