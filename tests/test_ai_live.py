"""Provider failure reasons stay sanitized. Public health exposes only ai_live."""

import io
import json
import urllib.error

from backend.services.ai_live import (
    AI_LIVE_TTL_S,
    current_ai_live,
    fetch_agent_service_status,
    normalize_api_key,
    probe_models_list,
    reset_ai_live_cache,
    sanitize_exception,
    sanitize_provider_reason,
)
from backend.services.llm_runtime import _log_error


class _Body:
    def __init__(self, status, payload=b""):
        self.status = status
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_sanitize_provider_reason_hides_key_and_request_id():
    secret = "sk-ant-api03-supersecretkeyvalue"
    reason = sanitize_provider_reason(
        401,
        f'401 {{"type":"error","error":{{"type":"authentication_error","message":"invalid x-api-key"}},"request_id":"req_abc"}} {secret}',
    )
    assert reason == "invalid_api_key"
    assert "sk-ant" not in reason
    assert "req_abc" not in reason


def test_sanitize_exception_uses_status_not_message():
    exc = RuntimeError("boom sk-ant-api03-leakedkey customer@example.com")
    exc.status_code = 404  # type: ignore[attr-defined]
    reason = sanitize_exception(exc)
    assert reason == "invalid_model"
    assert "sk-ant" not in reason
    assert "customer@" not in reason


def test_invalid_model_and_rate_limit_codes():
    assert sanitize_provider_reason(404, "not_found_error model: claude-retired") == "invalid_model"
    assert sanitize_provider_reason(429, "rate_limit_error") == "rate_limited"
    assert sanitize_provider_reason(None, "") == "provider_unreachable"


def test_normalize_api_key_strips_quotes():
    assert normalize_api_key('  "sk-ant-example" ') == "sk-ant-example"
    assert normalize_api_key("   ") == ""


def test_models_list_401_is_invalid_api_key_and_key_stays_out_of_the_url():
    seen = {}

    def opener(req, timeout=0):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["header"] = req.get_header("X-api-key")
        assert req.data is None
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            "unauthorized",
            hdrs=None,
            fp=io.BytesIO(
                b'{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}'
            ),
        )

    ok, reason = probe_models_list('"sk-ant-test-key"', opener=opener)
    assert ok is False
    assert reason == "invalid_api_key"
    assert seen["method"] == "GET"
    assert seen["url"] == "https://api.anthropic.com/v1/models?limit=1"
    assert "sk-ant" not in seen["url"]
    assert seen["header"] == "sk-ant-test-key"


def test_present_key_is_not_live_until_models_list_succeeds():
    reset_ai_live_cache()

    def opener(req, timeout=0):
        return _Body(200, b'{"data":[]}')

    ok, reason = probe_models_list("sk-ant-present", opener=opener)
    assert (ok, reason) == (True, "ok")


def test_empty_key_does_not_call_models_list():
    def opener(req, timeout=0):
        raise AssertionError("should not call")

    assert probe_models_list("  ", opener=opener) == (False, "no_api_key")


def test_models_probe_is_cached_for_a_few_minutes():
    reset_ai_live_cache()
    calls = {"n": 0}

    def probe(api_key):
        calls["n"] += 1
        assert api_key == "sk-ant-test"
        return False, "invalid_api_key"

    deps = {"probe": probe, "api_key": '"sk-ant-test"', "service_url": ""}
    first = current_ai_live(force=True, _deps=deps)
    second = current_ai_live(_deps=deps)
    assert calls["n"] == 1
    assert first == {"ai_live": False, "ai_live_reason": "invalid_api_key"}
    assert second == first
    assert "sk-ant" not in json.dumps(first)
    assert AI_LIVE_TTL_S >= 180


def test_agent_service_public_health_boolean_and_authed_reason():
    seen = []

    def opener(req, timeout=0):
        seen.append(req.full_url)
        if req.full_url.endswith("/health"):
            assert req.get_header("X-agent-token") is None
            return _Body(200, json.dumps({"status": "ok", "ai_live": False}).encode())
        assert req.full_url.endswith("/ai-live")
        assert req.get_header("X-agent-token") == "s3cret"
        return _Body(
            200,
            json.dumps({"ai_live": False, "ai_live_reason": "invalid_api_key"}).encode(),
        )

    ok, reason = fetch_agent_service_status(
        "http://agent.internal:3100",
        opener=opener,
        token="s3cret",
    )
    assert (ok, reason) == (False, "invalid_api_key")
    assert seen == [
        "http://agent.internal:3100/health",
        "http://agent.internal:3100/ai-live",
    ]


def test_llm_error_log_records_reason_not_secret(caplog):
    import logging

    exc = RuntimeError("invalid x-api-key sk-ant-api03-shouldnotappear")
    exc.status_code = 401  # type: ignore[attr-defined]
    with caplog.at_level(logging.WARNING):
        _log_error(
            "call1",
            "unit.error",
            "claude-sonnet-4-6",
            12,
            [{"role": "user", "content": "hello"}],
            None,
            {"tenant_id": "tenant-123"},
            exc,
        )
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "llm.call.error" in joined
    assert "reason=invalid_api_key" in joined
    assert "sk-ant" not in joined
    assert "shouldnotappear" not in joined
