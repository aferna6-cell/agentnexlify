"""Provider failure reasons stay sanitized, and /readyz reports ai_live_ok."""

import io
import json
import urllib.error

from backend.services.ai_live import (
    current_ai_live,
    normalize_api_key,
    probe_agent_service,
    probe_anthropic_key,
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


def test_probe_anthropic_key_401_is_invalid_api_key_and_key_stays_out_of_the_url():
    seen = {}

    def opener(req, timeout=0):
        seen["url"] = req.full_url
        seen["header"] = req.get_header("X-api-key")
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            "unauthorized",
            hdrs=None,
            fp=io.BytesIO(
                b'{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}'
            ),
        )

    ok, reason = probe_anthropic_key('"sk-ant-test-key"', opener=opener)
    assert ok is False
    assert reason == "invalid_api_key"
    assert "sk-ant" not in seen["url"]
    assert seen["header"] == "sk-ant-test-key"


def test_probe_agent_service_reads_ai_live_fields_only():
    def opener(req, timeout=0):
        assert req.full_url.endswith("/health")
        return _Body(
            200,
            json.dumps(
                {"status": "ok", "ai_live_ok": False, "ai_live_reason": "invalid_api_key", "api_key": "nope"}
            ).encode(),
        )

    ok, reason = probe_agent_service("http://agent.internal:3100", opener=opener)
    assert ok is False
    assert reason == "invalid_api_key"


def test_current_ai_live_prefers_agent_service_over_a_configured_backend_key():
    reset_ai_live_cache()

    def probe_key(_key):
        return True, "ok"

    def probe_service(_url):
        return False, "invalid_api_key"

    live = current_ai_live(
        _deps={
            "probe_key": probe_key,
            "probe_service": probe_service,
            "model_log": lambda: (True, "ok"),
            "api_key": "sk-ant-present",
            "service_url": "http://agent.internal:3100",
        }
    )
    assert live == {
        "ai_live_ok": False,
        "ai_live_reason": "invalid_api_key",
        "ai_live_scope": "agent_service",
    }
    assert "sk-ant" not in json.dumps(live)


def test_current_ai_live_uses_model_log_when_agent_service_health_is_old():
    live = current_ai_live(
        _deps={
            "probe_key": lambda _key: (True, "ok"),
            "probe_service": lambda _url: (None, "agent_service_status_unknown"),
            "model_log": lambda: (False, "invalid_api_key"),
            "api_key": "sk-ant-present",
            "service_url": "http://agent.internal:3100",
        }
    )
    assert live["ai_live_ok"] is False
    assert live["ai_live_reason"] == "invalid_api_key"
    assert live["ai_live_scope"] == "model_log"


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
