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
        captured["json"] = kwargs.get("json")
        return _Resp({"result": {}, "record": {}})

    monkeypatch.setattr(client.httpx, "post", _fake_post)
    out = client.orchestrate_sync(
        "acct-1", "summarize", {"kb": []}, request_origin="owner"
    )
    assert "record" in out
    assert captured["headers"] == {"X-Agent-Token": "s3cret"}
    assert captured["json"]["requestOrigin"] == "owner"

    client.orchestrate_sync(
        "acct-1", "customer message", {"kb": []}, request_origin="inbound"
    )
    assert captured["json"]["requestOrigin"] == "inbound"

    client.orchestrate_sync("acct-1", "missing provenance", {"kb": []})
    assert captured["json"]["requestOrigin"] == "system"


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
