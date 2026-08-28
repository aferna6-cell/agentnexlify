"""Unit tests for agent_sdk_client shared-secret auth headers.

The X-Agent-Token header is sent only when AGENT_SERVICE_TOKEN is configured,
so agent-service can reject unauthenticated callers without breaking local /
unconfigured runs.
"""

from backend.services import agent_sdk_client as client


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_auth_headers_empty_when_no_token(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "")
    assert client._auth_headers() == {}


def test_auth_headers_present_when_token_set(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "s3cret")
    assert client._auth_headers() == {"X-Agent-Token": "s3cret"}


def test_run_agent_sync_attaches_token_header(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "http://svc.internal:3100")
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "s3cret")
    captured = {}

    def _fake_post(endpoint, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _Resp({"is_error": False, "result": "ok"})

    monkeypatch.setattr(client.httpx, "post", _fake_post)
    out = client.run_agent_sync("widget-support", "hi")
    assert out["result"] == "ok"
    assert captured["headers"] == {"X-Agent-Token": "s3cret"}


def test_orchestrate_sync_attaches_token_header(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "http://svc.internal:3100")
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "s3cret")
    captured = {}

    def _fake_post(endpoint, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _Resp({"result": {}, "record": {}})

    monkeypatch.setattr(client.httpx, "post", _fake_post)
    out = client.orchestrate_sync("acct-1", "summarize", {"kb": []})
    assert "record" in out
    assert captured["headers"] == {"X-Agent-Token": "s3cret"}


def test_no_header_sent_when_token_unset(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "http://svc.internal:3100")
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "")
    captured = {}

    def _fake_post(endpoint, **kwargs):
        captured["headers"] = kwargs.get("headers")
        return _Resp({"is_error": False, "result": "ok"})

    monkeypatch.setattr(client.httpx, "post", _fake_post)
    client.run_agent_sync("widget-support", "hi")
    assert captured["headers"] == {}


# --- approve_action_sync ----------------------------------------------------
#
# Drives an approved engine-plane action. A lost response here must never be
# retried blindly, so the "returns None" cases are part of the contract.


def test_approve_action_sync_posts_the_stored_execution(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "http://svc.internal:3100")
    monkeypatch.setattr(client, "_AGENT_SERVICE_TOKEN", "s3cret")
    captured = {}

    def _fake_post(endpoint, **kwargs):
        captured["endpoint"] = endpoint
        captured["json"] = kwargs.get("json")
        captured["headers"] = kwargs.get("headers")
        return _Resp({"execution": {"id": "exec-1", "status": "succeeded"}, "customerNotes": []})

    monkeypatch.setattr(client.httpx, "post", _fake_post)
    out = client.approve_action_sync(
        "acct-1",
        {"id": "exec-1", "accountId": "acct-1", "toolId": "add_customer_note"},
        {"kb": []},
        approved_by="owner@example.test",
        tool_policy={"approvalThreshold": 1},
    )

    assert out["execution"]["status"] == "succeeded"
    assert captured["endpoint"].endswith("/actions/approve")
    assert captured["json"]["approvedBy"] == "owner@example.test"
    assert captured["json"]["execution"]["id"] == "exec-1"
    assert captured["json"]["toolPolicy"] == {"approvalThreshold": 1}
    assert captured["headers"] == {"X-Agent-Token": "s3cret"}


def test_approve_action_sync_returns_none_when_the_engine_is_unconfigured(monkeypatch):
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "")
    out = client.approve_action_sync(
        "acct-1", {"id": "exec-1"}, {}, approved_by="owner@example.test"
    )
    assert out is None


def test_approve_action_sync_returns_none_on_a_lost_response(monkeypatch):
    """None means UNKNOWN outcome — the caller must not retry on its own."""
    monkeypatch.setattr(client, "_AGENT_SERVICE_URL", "http://svc.internal:3100")

    def _timeout(*_args, **_kwargs):
        raise client.httpx.TimeoutException("read timeout")

    monkeypatch.setattr(client.httpx, "post", _timeout)
    assert (
        client.approve_action_sync(
            "acct-1", {"id": "exec-1"}, {}, approved_by="owner@example.test"
        )
        is None
    )
