"""Tests for the Slack agent team (grok-style mentionable bots).

Covers:
  - Slack v0 signature verification (valid / tampered / replayed / malformed)
  - roster parsing from SLACK_AGENT_TEAM (valid, malformed, partial entries)
  - event filtering (human mentions + DMs in, bot echoes + subtypes out)
  - POST /api/v1/slack/events — 403 unconfigured, 401 bad signature,
    url_verification challenge, accepted mention, retry + bot-event drops
  - reply generation guardrail (secret-shaped reply never posts)
  - chat.postMessage payload (thread_ts threading, bearer auth)
"""

import asyncio
import hashlib
import hmac
import json
import time

import httpx

from backend.config import settings
from backend.main import app
from backend.services import slack_agent_team
from backend.services.llm_runtime import ClaudeCallResult
from backend.tests.conftest import SyncASGITestClient

_FABLE_SECRET = "fable-signing-secret-000000000001"
_CODEX_SECRET = "codex-signing-secret-000000000002"

_ROSTER = json.dumps(
    [
        {
            "agent": "fable5",
            "app_id": "A0FABLE",
            "signing_secret": _FABLE_SECRET,
            "bot_token": "xoxb-fable-token",
            "bot_user_id": "U0FABLEBOT",
        },
        {
            "agent": "codex",
            "app_id": "A0CODEX",
            "signing_secret": _CODEX_SECRET,
            "bot_token": "xoxb-codex-token",
        },
    ]
)


def _sign(secret: str, timestamp: str, body: bytes) -> str:
    base = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def _signed_headers(body: bytes, secret: str = _FABLE_SECRET) -> dict[str, str]:
    ts = str(int(time.time()))
    return {
        "X-Slack-Request-Timestamp": ts,
        "X-Slack-Signature": _sign(secret, ts, body),
        "Content-Type": "application/json",
    }


def _mention_payload(**event_overrides) -> dict:
    event = {
        "type": "app_mention",
        "user": "U0HUMAN",
        "text": "<@U0FABLEBOT> what do you think?",
        "channel": "C0GENERAL",
        "ts": "1700000000.000100",
    }
    event.update(event_overrides)
    return {
        "type": "event_callback",
        "api_app_id": "A0FABLE",
        "event": event,
        "authorizations": [{"is_bot": True, "user_id": "U0FABLEBOT"}],
    }


def _make_client():
    return SyncASGITestClient(app)


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def test_valid_signature_accepted(self):
        ts = str(int(time.time()))
        body = b'{"type":"url_verification"}'
        sig = _sign(_FABLE_SECRET, ts, body)
        assert slack_agent_team.verify_signature(_FABLE_SECRET, ts, body, sig)

    def test_tampered_body_rejected(self):
        ts = str(int(time.time()))
        sig = _sign(_FABLE_SECRET, ts, b"original")
        assert not slack_agent_team.verify_signature(
            _FABLE_SECRET, ts, b"tampered", sig
        )

    def test_replayed_timestamp_rejected(self):
        stale_ts = str(int(time.time()) - 600)
        body = b"{}"
        sig = _sign(_FABLE_SECRET, stale_ts, body)
        assert not slack_agent_team.verify_signature(_FABLE_SECRET, stale_ts, body, sig)

    def test_non_numeric_timestamp_rejected(self):
        assert not slack_agent_team.verify_signature(
            _FABLE_SECRET, "not-a-ts", b"{}", "v0=abc"
        )

    def test_missing_pieces_rejected(self):
        ts = str(int(time.time()))
        assert not slack_agent_team.verify_signature("", ts, b"{}", "v0=abc")
        assert not slack_agent_team.verify_signature(_FABLE_SECRET, ts, b"{}", "")

    def test_resolve_app_picks_matching_secret(self):
        team = [
            slack_agent_team.SlackAgentApp(
                agent="fable5",
                app_id="A0FABLE",
                signing_secret=_FABLE_SECRET,
                bot_token="xoxb-1",
            ),
            slack_agent_team.SlackAgentApp(
                agent="codex",
                app_id="A0CODEX",
                signing_secret=_CODEX_SECRET,
                bot_token="xoxb-2",
            ),
        ]
        ts = str(int(time.time()))
        body = b"{}"
        sig = _sign(_CODEX_SECRET, ts, body)
        resolved = slack_agent_team.resolve_app(team, ts, body, sig)
        assert resolved is not None and resolved.agent == "codex"
        assert (
            slack_agent_team.resolve_app(team, ts, body, "v0=deadbeef") is None
        )


# ---------------------------------------------------------------------------
# Roster parsing
# ---------------------------------------------------------------------------


class TestLoadTeam:
    def test_parses_roster(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        team = slack_agent_team.load_team()
        assert [a.agent for a in team] == ["fable5", "codex"]
        assert team[0].bot_user_id == "U0FABLEBOT"
        assert team[1].bot_user_id == ""

    def test_empty_and_malformed_return_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", "")
        assert slack_agent_team.load_team() == []
        monkeypatch.setattr(settings, "slack_agent_team", "{not json")
        assert slack_agent_team.load_team() == []
        monkeypatch.setattr(settings, "slack_agent_team", '{"agent": "x"}')
        assert slack_agent_team.load_team() == []

    def test_entry_missing_required_keys_skipped(self, monkeypatch):
        roster = json.dumps(
            [
                {"agent": "fable5", "app_id": "A1"},  # no secrets
                {
                    "agent": "kimi3",
                    "app_id": "A2",
                    "signing_secret": "s",
                    "bot_token": "xoxb-3",
                },
            ]
        )
        monkeypatch.setattr(settings, "slack_agent_team", roster)
        team = slack_agent_team.load_team()
        assert [a.agent for a in team] == ["kimi3"]

    def test_known_agents_get_contract_personas(self):
        app_ = slack_agent_team.SlackAgentApp(
            agent="kimi3", app_id="A", signing_secret="s", bot_token="t"
        )
        assert "challenger and verification" in app_.role_prompt()
        custom = slack_agent_team.SlackAgentApp(
            agent="kimi3",
            app_id="A",
            signing_secret="s",
            bot_token="t",
            persona="You are a pirate.",
        )
        assert custom.role_prompt() == "You are a pirate."


# ---------------------------------------------------------------------------
# Event filtering + mention stripping
# ---------------------------------------------------------------------------


class TestEventFiltering:
    def test_human_mention_handled(self):
        assert slack_agent_team.should_handle_event(
            {"type": "app_mention", "user": "U1", "text": "hi"}
        )

    def test_human_dm_handled(self):
        assert slack_agent_team.should_handle_event(
            {"type": "message", "channel_type": "im", "user": "U1"}
        )

    def test_bot_authored_event_ignored(self):
        """Load-bearing: two agent bots must never reply to each other."""
        assert not slack_agent_team.should_handle_event(
            {"type": "app_mention", "user": "U1", "bot_id": "B123"}
        )

    def test_channel_message_without_mention_ignored(self):
        assert not slack_agent_team.should_handle_event(
            {"type": "message", "channel_type": "channel", "user": "U1"}
        )

    def test_subtype_and_userless_ignored(self):
        assert not slack_agent_team.should_handle_event(
            {"type": "message", "channel_type": "im", "user": "U1", "subtype": "message_changed"}
        )
        assert not slack_agent_team.should_handle_event({"type": "app_mention"})

    def test_strip_self_mention_exact(self):
        assert (
            slack_agent_team.strip_self_mention(
                "hey <@U0FABLEBOT> review <@U0HUMAN>'s plan", "U0FABLEBOT"
            )
            == "hey review <@U0HUMAN>'s plan"
        )

    def test_strip_self_mention_leading_fallback(self):
        assert (
            slack_agent_team.strip_self_mention("<@U0FABLEBOT> ship it?", "")
            == "ship it?"
        )


# ---------------------------------------------------------------------------
# POST /api/v1/slack/events
# ---------------------------------------------------------------------------


class TestSlackEventsRoute:
    def test_unconfigured_returns_403(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", "")
        client = _make_client()
        try:
            resp = client.post("/api/v1/slack/events", content=b"{}")
        finally:
            client.close()
        assert resp.status_code == 403, resp.text

    def test_invalid_signature_returns_401(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        body = json.dumps({"type": "url_verification", "challenge": "x"}).encode()
        headers = _signed_headers(body, secret="wrong-secret-000000000000000000")
        client = _make_client()
        try:
            resp = client.post("/api/v1/slack/events", content=body, headers=headers)
        finally:
            client.close()
        assert resp.status_code == 401, resp.text

    def test_url_verification_echoes_challenge(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        body = json.dumps(
            {"type": "url_verification", "challenge": "challenge-token-123"}
        ).encode()
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/slack/events", content=body, headers=_signed_headers(body)
            )
        finally:
            client.close()
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"challenge": "challenge-token-123"}

    def test_app_mention_accepted_for_resolved_agent(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        body = json.dumps(_mention_payload()).encode()
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/slack/events", content=body, headers=_signed_headers(body)
            )
        finally:
            client.close()
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "accepted", "agent": "fable5"}

    def test_retry_delivery_ignored(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        body = json.dumps(_mention_payload()).encode()
        headers = _signed_headers(body)
        headers["X-Slack-Retry-Num"] = "1"
        client = _make_client()
        try:
            resp = client.post("/api/v1/slack/events", content=body, headers=headers)
        finally:
            client.close()
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "ignored_retry"}

    def test_bot_authored_mention_ignored(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_agent_team", _ROSTER)
        body = json.dumps(_mention_payload(bot_id="B0CODEXBOT")).encode()
        client = _make_client()
        try:
            resp = client.post(
                "/api/v1/slack/events", content=body, headers=_signed_headers(body)
            )
        finally:
            client.close()
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "ignored"}


# ---------------------------------------------------------------------------
# Reply generation + outbound guard
# ---------------------------------------------------------------------------


def _app(agent: str = "fable5", **overrides) -> slack_agent_team.SlackAgentApp:
    kwargs = {
        "agent": agent,
        "app_id": "A0TEST",
        "signing_secret": "s",
        "bot_token": "xoxb-test",
    }
    kwargs.update(overrides)
    return slack_agent_team.SlackAgentApp(**kwargs)


class TestGenerateReply:
    def test_normal_reply_passes_through(self, monkeypatch):
        async def _fake_call(**kwargs):
            return ClaudeCallResult(text="Ship it — the plan is sound.", duration_ms=5)

        monkeypatch.setattr(slack_agent_team, "call_claude_messages", _fake_call)
        reply = asyncio.run(
            slack_agent_team.generate_reply(_app(), [_app()], "thoughts?", [])
        )
        assert reply == "Ship it — the plan is sound."

    def test_secret_shaped_reply_blocked_by_guard(self, monkeypatch):
        leaked = "Use this key: sk-" + "a1b2c3d4e5f6g7h8" * 2

        async def _fake_call(**kwargs):
            return ClaudeCallResult(text=leaked, duration_ms=5)

        monkeypatch.setattr(slack_agent_team, "call_claude_messages", _fake_call)
        reply = asyncio.run(
            slack_agent_team.generate_reply(_app(), [_app()], "key?", [])
        )
        assert "sk-" not in reply
        assert "guardrail" in reply

    def test_thread_context_lands_in_prompt(self, monkeypatch):
        captured: dict = {}

        async def _fake_call(**kwargs):
            captured.update(kwargs)
            return ClaudeCallResult(text="ok", duration_ms=5)

        monkeypatch.setattr(slack_agent_team, "call_claude_messages", _fake_call)
        asyncio.run(
            slack_agent_team.generate_reply(
                _app(),
                [_app(), _app(agent="codex")],
                "and now?",
                ["<@U0HUMAN>: we shipped the widget fix"],
            )
        )
        content = captured["messages"][0]["content"]
        assert "we shipped the widget fix" in content
        assert "and now?" in content
        assert "codex" in captured["system"]


class TestSystemPrompt:
    def test_includes_persona_and_teammates(self):
        team = [_app("fable5"), _app("codex"), _app("kimi3")]
        prompt = slack_agent_team.build_system_prompt(team[0], team)
        assert "product and architecture steward" in prompt
        assert "codex" in prompt and "kimi3" in prompt
        assert "Never output secrets" in prompt


# ---------------------------------------------------------------------------
# Slack Web API calls
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body if body is not None else {"ok": True}
        self.text = text

    def json(self):
        return self._body


class _FakeAsyncClient:
    """Stub for httpx.AsyncClient capturing the last request per method."""

    captured: dict = {}
    post_response = _FakeResponse()
    get_response = _FakeResponse()

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers=None, json=None):
        _FakeAsyncClient.captured["post"] = {
            "url": url,
            "headers": headers,
            "json": json,
        }
        return _FakeAsyncClient.post_response

    async def get(self, url, headers=None, params=None):
        _FakeAsyncClient.captured["get"] = {
            "url": url,
            "headers": headers,
            "params": params,
        }
        return _FakeAsyncClient.get_response


class TestSlackWebApi:
    def test_post_message_threads_and_authenticates(self, monkeypatch):
        _FakeAsyncClient.captured = {}
        _FakeAsyncClient.post_response = _FakeResponse(body={"ok": True})
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

        ok = asyncio.run(
            slack_agent_team.post_message(
                _app(), "C0GENERAL", "reply text", "1700000000.000100"
            )
        )
        assert ok is True
        sent = _FakeAsyncClient.captured["post"]
        assert sent["url"].endswith("/chat.postMessage")
        assert sent["headers"]["Authorization"] == "Bearer xoxb-test"
        assert sent["json"] == {
            "channel": "C0GENERAL",
            "text": "reply text",
            "thread_ts": "1700000000.000100",
        }

    def test_post_message_reports_slack_level_error(self, monkeypatch):
        _FakeAsyncClient.captured = {}
        _FakeAsyncClient.post_response = _FakeResponse(
            body={"ok": False, "error": "channel_not_found"}
        )
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

        ok = asyncio.run(
            slack_agent_team.post_message(_app(), "C0GENERAL", "reply", None)
        )
        assert ok is False

    def test_fetch_thread_context_maps_authors(self, monkeypatch):
        _FakeAsyncClient.captured = {}
        _FakeAsyncClient.get_response = _FakeResponse(
            body={
                "ok": True,
                "messages": [
                    {"user": "U0HUMAN", "text": "plan is in the doc"},
                    {"bot_id": "B0OTHER", "text": "earlier bot answer"},
                    {"user": "U0HUMAN", "text": ""},
                ],
            }
        )
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

        lines = asyncio.run(
            slack_agent_team.fetch_thread_context(
                _app(), "C0GENERAL", "1700000000.000100"
            )
        )
        assert lines == [
            "<@U0HUMAN>: plan is in the doc",
            "bot: earlier bot answer",
        ]

    def test_fetch_thread_context_degrades_on_error(self, monkeypatch):
        _FakeAsyncClient.get_response = _FakeResponse(
            body={"ok": False, "error": "missing_scope"}
        )
        monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
        lines = asyncio.run(
            slack_agent_team.fetch_thread_context(_app(), "C0", "1.0")
        )
        assert lines == []


# ---------------------------------------------------------------------------
# handle_event orchestration
# ---------------------------------------------------------------------------


class TestHandleEvent:
    def test_top_level_mention_replies_in_new_thread(self, monkeypatch):
        calls: dict = {}

        async def _fake_fetch(app_, channel, thread_ts):
            calls["fetched"] = True
            return []

        async def _fake_generate(app_, team, question, thread_lines):
            calls["question"] = question
            calls["thread_lines"] = thread_lines
            return "here's my take"

        async def _fake_post(app_, channel, text, thread_ts):
            calls["posted"] = {"channel": channel, "text": text, "thread_ts": thread_ts}
            return True

        monkeypatch.setattr(slack_agent_team, "fetch_thread_context", _fake_fetch)
        monkeypatch.setattr(slack_agent_team, "generate_reply", _fake_generate)
        monkeypatch.setattr(slack_agent_team, "post_message", _fake_post)

        event = {
            "type": "app_mention",
            "user": "U0HUMAN",
            "text": "<@U0FABLEBOT> status of the widget fix?",
            "channel": "C0GENERAL",
            "ts": "1700000000.000100",
        }
        asyncio.run(
            slack_agent_team.handle_event(_app(), [_app()], event, "U0FABLEBOT")
        )

        # Fresh top-level mention: no thread fetch, reply threads on the
        # mention itself (grok-style).
        assert "fetched" not in calls
        assert calls["question"] == "status of the widget fix?"
        assert calls["posted"] == {
            "channel": "C0GENERAL",
            "text": "here's my take",
            "thread_ts": "1700000000.000100",
        }

    def test_in_thread_mention_fetches_context(self, monkeypatch):
        calls: dict = {}

        async def _fake_fetch(app_, channel, thread_ts):
            calls["fetch_ts"] = thread_ts
            return ["<@U0HUMAN>: earlier message"]

        async def _fake_generate(app_, team, question, thread_lines):
            calls["thread_lines"] = thread_lines
            return "reply"

        async def _fake_post(app_, channel, text, thread_ts):
            calls["post_ts"] = thread_ts
            return True

        monkeypatch.setattr(slack_agent_team, "fetch_thread_context", _fake_fetch)
        monkeypatch.setattr(slack_agent_team, "generate_reply", _fake_generate)
        monkeypatch.setattr(slack_agent_team, "post_message", _fake_post)

        event = {
            "type": "app_mention",
            "user": "U0HUMAN",
            "text": "<@U0FABLEBOT> and your view?",
            "channel": "C0GENERAL",
            "ts": "1700000099.000500",
            "thread_ts": "1700000000.000100",
        }
        asyncio.run(
            slack_agent_team.handle_event(_app(), [_app()], event, "U0FABLEBOT")
        )

        assert calls["fetch_ts"] == "1700000000.000100"
        assert calls["post_ts"] == "1700000000.000100"
        assert calls["thread_lines"] == ["<@U0HUMAN>: earlier message"]

    def test_never_raises_on_downstream_failure(self, monkeypatch):
        async def _boom(app_, team, question, thread_lines):
            raise RuntimeError("model down")

        monkeypatch.setattr(slack_agent_team, "generate_reply", _boom)
        event = {
            "type": "app_mention",
            "user": "U0HUMAN",
            "text": "hi",
            "channel": "C0GENERAL",
            "ts": "1.0",
        }
        # Must not raise — this runs as a BackgroundTask.
        asyncio.run(slack_agent_team.handle_event(_app(), [_app()], event, ""))
