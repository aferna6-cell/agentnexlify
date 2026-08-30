"""Tests for the Slack agent team.

Four surfaces, in the order a request travels through them:

  1. ``slack_verify``            — signature authenticity + replay window
  2. ``slack_agent_roster``      — command grammar + deterministic routing
  3. ``slack_agent_team``        — Slack API calls, prompt building, dispatch
  4. ``routers/slack_agents``    — webhook gating (config, workspace, loops)

Real ``httpx.Response`` objects and small stub classes stand in for Slack
and Anthropic, so assertions are about what got posted to which channel —
not about which mock was called.
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import ClassVar

import httpx
import pytest

from backend.config import settings
from backend.main import app
from backend.services import slack_agent_roster as roster_mod
from backend.services import slack_agent_team
from backend.services.slack_agent_team import ThreadMessage
from backend.services.slack_verify import verify_slack_signature
from backend.tests.conftest import SyncASGITestClient

_SECRET = "signing-secret-used-only-in-tests"
_BOT_TOKEN = "bot-token-used-only-in-tests"
_TEAM_ID = "T0AGENTTEAM"
_CHANNEL = "C0GENERAL"
_USER = "U0FOUNDER"


def _sign(body: bytes, timestamp: str, secret: str = _SECRET) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        b"v0:" + timestamp.encode("utf-8") + b":" + body,
        hashlib.sha256,
    ).hexdigest()
    return f"v0={digest}"


@pytest.fixture()
def slack_configured(monkeypatch):
    """Minimum viable Slack config: secret + bot token + workspace id."""
    monkeypatch.setattr(settings, "slack_signing_secret", _SECRET)
    monkeypatch.setattr(settings, "slack_bot_token", _BOT_TOKEN)
    monkeypatch.setattr(settings, "slack_team_id", _TEAM_ID)
    monkeypatch.setattr(settings, "slack_allowed_user_ids", "")


class Recorder:
    """Collects every message the team tried to post."""

    def __init__(self):
        self.posts: list[dict] = []

    async def post(self, *, channel, text, agent=None, thread_ts=None):
        self.posts.append(
            {
                "channel": channel,
                "text": text,
                "agent": agent.key if agent else None,
                "thread_ts": thread_ts,
            }
        )
        return {"ok": True}

    @property
    def agents(self) -> list[str | None]:
        return [p["agent"] for p in self.posts]

    @property
    def texts(self) -> list[str]:
        return [p["text"] for p in self.posts]


@pytest.fixture()
def recorder(monkeypatch):
    rec = Recorder()
    monkeypatch.setattr(slack_agent_team, "post_as_agent", rec.post)
    return rec


def _stub_answers(monkeypatch, *, text=None):
    """Replace the model call with a deterministic per-agent reply."""

    async def _answer(*, agent, question, history):
        return text or f"[{agent.key}] on: {question}"

    monkeypatch.setattr(slack_agent_team, "answer", _answer)


# ---------------------------------------------------------------------------
# 1. Signature verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    def test_accepts_a_correctly_signed_body(self):
        body = b'{"type":"event_callback"}'
        ts = "1700000000"
        assert (
            verify_slack_signature(
                raw_body=body,
                timestamp=ts,
                signature=_sign(body, ts),
                signing_secret=_SECRET,
                now=1700000010,
            )
            is True
        )

    def test_rejects_a_tampered_body(self):
        ts = "1700000000"
        signature = _sign(b'{"channel":"C0GENERAL"}', ts)
        assert (
            verify_slack_signature(
                raw_body=b'{"channel":"C0ATTACKER"}',
                timestamp=ts,
                signature=signature,
                signing_secret=_SECRET,
                now=1700000010,
            )
            is False
        )

    def test_rejects_a_replayed_request_outside_the_window(self):
        body = b'{"type":"event_callback"}'
        ts = "1700000000"
        signature = _sign(body, ts)
        assert (
            verify_slack_signature(
                raw_body=body,
                timestamp=ts,
                signature=signature,
                signing_secret=_SECRET,
                now=1700000000 + 301,
            )
            is False
        )

    def test_rejects_when_signing_secret_is_unset(self):
        body = b"{}"
        assert (
            verify_slack_signature(
                raw_body=body,
                timestamp="1700000000",
                signature=_sign(body, "1700000000"),
                signing_secret="",
                now=1700000000,
            )
            is False
        )

    @pytest.mark.parametrize("timestamp", ["", "not-a-number", "1700000000.x"])
    def test_rejects_unparseable_timestamps(self, timestamp):
        assert (
            verify_slack_signature(
                raw_body=b"{}",
                timestamp=timestamp,
                signature="v0=deadbeef",
                signing_secret=_SECRET,
                now=1700000000,
            )
            is False
        )


# ---------------------------------------------------------------------------
# 2. Roster + command grammar
# ---------------------------------------------------------------------------


class TestCommandParsing:
    def test_named_agent_prefix_wins_over_routing(self):
        command = roster_mod.parse_command(
            "<@U0BOT> schema: is there a tenant_id on leads?"
        )
        assert command.kind == "ask"
        assert command.agent_keys == ("schema",)
        assert command.question == "is there a tenant_id on leads?"
        assert command.explicit is True

    def test_alias_resolves_to_the_same_agent(self):
        assert roster_mod.parse_command("db: add an index").agent_keys == ("schema",)
        assert roster_mod.parse_command("infra: restart it").agent_keys == ("ops",)

    def test_display_name_resolves_case_insensitively(self):
        agent = roster_mod.resolve_label("Schema Guardian")
        assert agent is not None and agent.key == "schema"

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("the railway deploy failed with a 502", "ops"),
            ("a customer reports the widget is not answering", "support"),
            ("should we match GoHighLevel pricing?", "growth"),
            ("this endpoint 422s on every request", "engineer"),
            ("do I need a migration to add a column?", "schema"),
            ("what should i work on next", "chief"),
        ],
    )
    def test_auto_routes_to_the_specialist(self, text, expected):
        assert roster_mod.route(text) == expected

    def test_unmatched_text_falls_back_to_the_chief(self):
        assert roster_mod.route("thoughts on the weather in Dublin") == "chief"

    def test_unknown_colon_prefix_is_treated_as_prose_not_an_error(self):
        """'Note: ...' is a question, not a typo'd agent name."""
        command = roster_mod.parse_command("<@U0BOT> Note: the railway deploy failed")
        assert command.kind == "ask"
        assert command.explicit is False
        assert command.question == "Note: the railway deploy failed"
        assert command.agent_keys == ("ops",)

    @pytest.mark.parametrize("text", ["<@U0BOT>", "<@U0BOT> help", "who?", "agents"])
    def test_help_variants_need_no_model_call(self, text):
        command = roster_mod.parse_command(text)
        assert command.kind == "help"
        assert command.agent_keys == ()

    def test_team_prefix_fans_out_to_distinct_agents(self):
        command = roster_mod.parse_command("<@U0BOT> team: should I raise prices?")
        assert command.kind == "team"
        assert len(command.agent_keys) == roster_mod.TEAM_FANOUT
        assert len(set(command.agent_keys)) == roster_mod.TEAM_FANOUT
        assert command.question == "should I raise prices?"

    def test_team_fanout_leads_with_the_best_matched_agent(self):
        keys = roster_mod.route_many("the railway deploy failed and users see 502")
        assert keys[0] == "ops"

    def test_route_many_pads_a_vague_question_to_a_full_team(self):
        keys = roster_mod.route_many("what do you all think")
        assert len(keys) == roster_mod.TEAM_FANOUT
        assert len(set(keys)) == roster_mod.TEAM_FANOUT

    def test_mentions_never_leak_into_the_question(self):
        question = roster_mod.parse_command(
            "<@U0BOT> ask <@U0OTHER> about <!here> the widget"
        ).question
        assert "<@" not in question and "<!" not in question


class TestRoster:
    def test_help_text_lists_every_agent_with_its_key(self):
        text = roster_mod.help_text("@nexus")
        for agent in roster_mod.roster():
            assert agent.display_name in text
            assert f"`{agent.key}`" in text

    def test_every_agent_prompt_carries_the_schema_invariant(self):
        """A wrong client_id answer is the most expensive mistake here."""
        for agent in roster_mod.roster():
            prompt = agent.system_prompt()
            assert "client_id" in prompt
            assert agent.display_name in prompt
            assert agent.mandate in prompt

    def test_keys_and_aliases_are_unique_across_the_roster(self):
        labels = [
            label
            for agent in roster_mod.roster()
            for label in (agent.key, *agent.aliases)
        ]
        assert len(labels) == len(set(labels))

    def test_default_agent_exists(self):
        assert roster_mod.get_agent(roster_mod.DEFAULT_AGENT_KEY) is not None
        assert roster_mod.get_agent("no-such-agent") is None


# ---------------------------------------------------------------------------
# 3. Prompt building + thread continuation
# ---------------------------------------------------------------------------


class TestPromptBuilding:
    def test_bare_question_when_thread_has_no_history(self):
        assert slack_agent_team.build_prompt("why is it slow?", []) == "why is it slow?"

    def test_transcript_precedes_the_current_question(self):
        history = [
            ThreadMessage(speaker="Founder", text="deploy failed", is_agent=False),
            ThreadMessage(speaker="Ops", text="check the build log", is_agent=True),
        ]
        prompt = slack_agent_team.build_prompt("which log?", history)
        assert prompt.index("deploy failed") < prompt.index("check the build log")
        assert prompt.index("check the build log") < prompt.index("which log?")
        assert "Ops: check the build log" in prompt

    def test_oldest_context_is_dropped_first_when_over_budget(self):
        history = [
            ThreadMessage(speaker=f"S{i}", text="y" * 700, is_agent=False)
            for i in range(20)
        ]
        prompt = slack_agent_team.build_prompt("now what?", history)
        assert "S19: " in prompt
        assert "S0: " not in prompt
        assert prompt.endswith("now what?")


class TestThreadContinuation:
    def test_last_speaking_agent_is_resolved_from_its_display_name(self):
        history = [
            ThreadMessage(speaker="Founder", text="deploy failed", is_agent=False),
            ThreadMessage(speaker="Ops", text="rolled back", is_agent=True),
            ThreadMessage(speaker="Founder", text="and the second one?", is_agent=False),
        ]
        assert slack_agent_team.last_agent_in_thread(history) == "ops"

    def test_no_agent_in_thread_yields_none(self):
        history = [ThreadMessage(speaker="Founder", text="hi", is_agent=False)]
        assert slack_agent_team.last_agent_in_thread(history) is None

    def test_unknown_bot_name_is_ignored(self):
        history = [ThreadMessage(speaker="Zapier", text="ran a zap", is_agent=True)]
        assert slack_agent_team.last_agent_in_thread(history) is None


# ---------------------------------------------------------------------------
# 3b. Slack Web API calls
# ---------------------------------------------------------------------------


class StubAsyncClient:
    """Stands in for httpx.AsyncClient, recording POSTs and replaying bodies."""

    requests: ClassVar[list[dict]] = []
    responses: ClassVar[list[httpx.Response]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, headers=None, json=None):
        StubAsyncClient.requests.append(
            {"url": url, "headers": headers or {}, "json": json or {}}
        )
        if StubAsyncClient.responses:
            return StubAsyncClient.responses.pop(0)
        return httpx.Response(200, json={"ok": True})


@pytest.fixture()
def stub_http(monkeypatch):
    StubAsyncClient.requests = []
    StubAsyncClient.responses = []
    monkeypatch.setattr(slack_agent_team.httpx, "AsyncClient", StubAsyncClient)
    return StubAsyncClient


class TestSlackApiCalls:
    def test_post_as_agent_sends_the_persona_identity(self, slack_configured, stub_http):
        agent = roster_mod.get_agent("schema")

        async def _run():
            return await slack_agent_team.post_as_agent(
                channel=_CHANNEL, text="use client_id", agent=agent, thread_ts="111.1"
            )

        body = asyncio.run(_run())

        sent = stub_http.requests[0]
        assert sent["url"].endswith("/chat.postMessage")
        assert sent["json"]["username"] == agent.display_name
        assert sent["json"]["icon_emoji"] == agent.emoji
        assert sent["json"]["thread_ts"] == "111.1"
        assert sent["json"]["text"] == "use client_id"
        assert sent["headers"]["Authorization"] == f"Bearer {_BOT_TOKEN}"
        assert body["ok"] is True

    def test_slack_application_error_is_reported_not_swallowed(
        self, slack_configured, stub_http
    ):
        """Slack returns ok:false with HTTP 200 — status alone proves nothing."""
        stub_http.responses = [
            httpx.Response(200, json={"ok": False, "error": "missing_scope"})
        ]

        body = asyncio.run(
            slack_agent_team.post_as_agent(channel=_CHANNEL, text="hello")
        )
        assert body["ok"] is False
        assert body["error"] == "missing_scope"

    def test_thread_fetch_normalizes_speakers_and_drops_the_trigger(
        self, slack_configured, stub_http
    ):
        stub_http.responses = [
            httpx.Response(
                200,
                json={
                    "ok": True,
                    "messages": [
                        {"ts": "1.0", "user": _USER, "text": "<@U0BOT> deploy failed"},
                        {
                            "ts": "2.0",
                            "bot_id": "B1",
                            "username": "Ops",
                            "text": "rolled back",
                        },
                        {"ts": "3.0", "user": _USER, "text": ""},
                        {"ts": "4.0", "user": _USER, "text": "<@U0BOT> and now?"},
                    ],
                },
            )
        ]

        history = asyncio.run(
            slack_agent_team.fetch_thread(
                channel=_CHANNEL, thread_ts="1.0", exclude_ts="4.0"
            )
        )

        assert [m.speaker for m in history] == ["Founder", "Ops"]
        assert history[0].text == "deploy failed"
        assert history[1].is_agent is True

    def test_thread_fetch_degrades_to_no_context_on_slack_error(
        self, slack_configured, stub_http
    ):
        stub_http.responses = [
            httpx.Response(200, json={"ok": False, "error": "channel_not_found"})
        ]

        assert (
            asyncio.run(
                slack_agent_team.fetch_thread(channel=_CHANNEL, thread_ts="1.0")
            )
            == []
        )

    def test_non_json_slack_response_is_treated_as_failure(
        self, slack_configured, stub_http
    ):
        stub_http.responses = [httpx.Response(200, content=b"<html>gateway</html>")]

        body = asyncio.run(slack_agent_team.post_as_agent(channel=_CHANNEL, text="hi"))
        assert not body.get("ok")

    def test_transport_failure_never_raises_and_hides_no_token(
        self, slack_configured, monkeypatch
    ):
        class ExplodingClient(StubAsyncClient):
            async def post(self, url, headers=None, json=None):
                raise httpx.ConnectError("boom")

        monkeypatch.setattr(slack_agent_team.httpx, "AsyncClient", ExplodingClient)

        body = asyncio.run(
            slack_agent_team.post_as_agent(channel=_CHANNEL, text="hi")
        )
        assert body["ok"] is False
        assert body["error"] == "http_error:ConnectError"


# ---------------------------------------------------------------------------
# 3c. Dispatch
# ---------------------------------------------------------------------------


class TestConfigGates:
    def test_partial_configuration_counts_as_off(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_signing_secret", _SECRET)
        monkeypatch.setattr(settings, "slack_bot_token", _BOT_TOKEN)
        monkeypatch.setattr(settings, "slack_team_id", "")
        assert slack_agent_team.is_configured() is False

    def test_fully_configured_is_on(self, slack_configured):
        assert slack_agent_team.is_configured() is True

    def test_empty_user_allow_list_admits_the_whole_workspace(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_allowed_user_ids", "")
        assert slack_agent_team.is_allowed_user("U0ANYONE") is True

    def test_user_allow_list_is_honored(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_allowed_user_ids", " U0FOUNDER , U0COFOUND ")
        assert slack_agent_team.is_allowed_user("U0FOUNDER") is True
        assert slack_agent_team.is_allowed_user("U0GUEST") is False


class TestHandleMessage:
    def test_help_reply_is_posted_by_the_chief_without_a_model_call(
        self, slack_configured, recorder, monkeypatch
    ):
        def _explode(**kwargs):
            raise AssertionError("help must not call the model")

        monkeypatch.setattr(slack_agent_team, "answer", _explode)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL, text="<@U0BOT> help", thread_ts=None, message_ts="9.1"
            )
        )

        assert recorder.agents == ["chief"]
        assert "Schema Guardian" in recorder.texts[0]

    def test_reply_starts_a_thread_on_the_triggering_message(
        self, slack_configured, recorder, monkeypatch
    ):
        _stub_answers(monkeypatch)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL,
                text="<@U0BOT> the railway deploy failed",
                thread_ts=None,
                message_ts="9.2",
            )
        )

        assert recorder.posts[0]["thread_ts"] == "9.2"
        assert recorder.posts[0]["agent"] == "ops"
        assert recorder.posts[0]["channel"] == _CHANNEL

    def test_follow_up_stays_with_the_agent_already_in_the_thread(
        self, slack_configured, recorder, monkeypatch
    ):
        """'and the second one?' routes nowhere — continuity has to carry it."""
        _stub_answers(monkeypatch)

        async def _history(*, channel, thread_ts, exclude_ts=None):
            return [
                ThreadMessage(speaker="Ops", text="rolled back", is_agent=True),
            ]

        monkeypatch.setattr(slack_agent_team, "fetch_thread", _history)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL,
                text="<@U0BOT> and the second one?",
                thread_ts="9.3",
                message_ts="9.4",
            )
        )

        assert recorder.agents == ["ops"]
        assert recorder.posts[0]["thread_ts"] == "9.3"

    def test_named_agent_overrides_thread_continuity(
        self, slack_configured, recorder, monkeypatch
    ):
        _stub_answers(monkeypatch)

        async def _history(*, channel, thread_ts, exclude_ts=None):
            return [ThreadMessage(speaker="Ops", text="rolled back", is_agent=True)]

        monkeypatch.setattr(slack_agent_team, "fetch_thread", _history)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL,
                text="<@U0BOT> growth: does this change pricing?",
                thread_ts="9.5",
                message_ts="9.6",
            )
        )

        assert recorder.agents == ["growth"]

    def test_team_question_posts_every_agent_then_one_synthesis(
        self, slack_configured, recorder, monkeypatch
    ):
        _stub_answers(monkeypatch)

        async def _synthesize(*, question, answers):
            return f"decision after {len(answers)} answers"

        monkeypatch.setattr(slack_agent_team, "synthesize", _synthesize)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL,
                text="<@U0BOT> team: should I raise the chatbot price?",
                thread_ts=None,
                message_ts="9.7",
            )
        )

        assert len(recorder.posts) == roster_mod.TEAM_FANOUT + 1
        assert recorder.agents[-1] == "chief"
        assert recorder.texts[-1] == f"decision after {roster_mod.TEAM_FANOUT} answers"
        assert {p["thread_ts"] for p in recorder.posts} == {"9.7"}

    def test_team_skips_synthesis_when_only_one_agent_answered(
        self, slack_configured, recorder, monkeypatch
    ):
        """A lone surviving answer needs no chief restating it."""
        failures = {"count": 0}

        async def _mostly_failing(*, agent, question, history):
            failures["count"] += 1
            if failures["count"] == 1:
                return "the one real answer"
            return slack_agent_team._FAILURE_NOTICE

        monkeypatch.setattr(slack_agent_team, "answer", _mostly_failing)

        async def _synthesize(*, question, answers):
            raise AssertionError("synthesis must be skipped")

        monkeypatch.setattr(slack_agent_team, "synthesize", _synthesize)

        asyncio.run(
            slack_agent_team.handle_message(
                channel=_CHANNEL,
                text="<@U0BOT> team: what now?",
                thread_ts=None,
                message_ts="9.8",
            )
        )

        assert len(recorder.posts) == roster_mod.TEAM_FANOUT
        assert "the one real answer" in recorder.texts


# ---------------------------------------------------------------------------
# 4. Webhook gating
# ---------------------------------------------------------------------------


def _post_events(payload, *, secret=_SECRET, timestamp=None, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode("utf-8")
    ts = timestamp or str(int(time.time()))
    client = SyncASGITestClient(app)
    try:
        return client.post(
            "/api/v1/slack/events",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Slack-Request-Timestamp": ts,
                "X-Slack-Signature": _sign(body, ts, secret),
            },
        )
    finally:
        client.close()


def _mention_event(**overrides):
    event = {
        "type": "app_mention",
        "user": _USER,
        "channel": _CHANNEL,
        "ts": "1700000000.000100",
        "text": "<@U0BOT> the railway deploy failed",
    }
    event.update(overrides)
    return {
        "type": "event_callback",
        "team_id": _TEAM_ID,
        "event_id": "Ev0TEST0001",
        "event": event,
    }


class TestEventsEndpoint:
    def test_unconfigured_app_returns_503(self, monkeypatch):
        monkeypatch.setattr(settings, "slack_signing_secret", "")
        monkeypatch.setattr(settings, "slack_bot_token", "")
        monkeypatch.setattr(settings, "slack_team_id", "")

        resp = _post_events(_mention_event())
        assert resp.status_code == 503, resp.text

    def test_bad_signature_is_rejected(self, slack_configured):
        resp = _post_events(_mention_event(), secret="the-wrong-secret")
        assert resp.status_code == 401, resp.text

    def test_stale_timestamp_is_rejected(self, slack_configured):
        old = str(int(time.time()) - 3600)
        resp = _post_events(_mention_event(), timestamp=old)
        assert resp.status_code == 401, resp.text

    def test_url_verification_echoes_the_challenge(self, slack_configured):
        resp = _post_events({"type": "url_verification", "challenge": "abc123"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["challenge"] == "abc123"

    def test_event_from_another_workspace_is_refused(self, slack_configured):
        payload = _mention_event()
        payload["team_id"] = "T0SOMEONEELSE"
        resp = _post_events(payload)
        assert resp.status_code == 403, resp.text

    def test_malformed_json_is_a_400(self, slack_configured):
        resp = _post_events(None, raw=b"not json at all")
        assert resp.status_code == 400, resp.text

    def test_accepted_mention_is_acked(self, slack_configured, monkeypatch):
        async def _new(db, provider, event_id):
            return True, None

        from backend.routers import slack_agents as slack_router

        monkeypatch.setattr(slack_router.idempotency, "check_and_record", _new)

        resp = _post_events(_mention_event())
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ok": True}

    def test_redelivered_event_is_skipped(self, slack_configured, monkeypatch):
        async def _duplicate(db, provider, event_id):
            return False, {"response_status": 200, "response_body": {"ok": True}}

        from backend.routers import slack_agents as slack_router

        monkeypatch.setattr(slack_router.idempotency, "check_and_record", _duplicate)

        resp = _post_events(_mention_event())
        assert resp.status_code == 200, resp.text
        assert resp.json()["skipped"] == "duplicate"

    @pytest.mark.parametrize(
        "overrides,reason",
        [
            ({"bot_id": "B0SELF"}, "bot_message"),
            ({"app_id": "A0SELF"}, "bot_message"),
            ({"subtype": "channel_join"}, "subtype:channel_join"),
            ({"type": "reaction_added"}, "event_type:reaction_added"),
            ({"type": "message"}, "not_a_dm"),
            ({"text": "   "}, "empty_text"),
            ({"channel": ""}, "missing_channel_or_ts"),
        ],
    )
    def test_events_that_need_no_reply_are_skipped(
        self, slack_configured, overrides, reason
    ):
        resp = _post_events(_mention_event(**overrides))
        assert resp.status_code == 200, resp.text
        assert resp.json()["skipped"] == reason

    def test_direct_message_without_a_mention_is_handled(self, slack_configured):
        payload = _mention_event(
            type="message", channel_type="im", text="the deploy failed"
        )
        resp = _post_events(payload)
        assert resp.status_code == 200, resp.text
        assert "skipped" not in resp.json()

    def test_user_outside_the_allow_list_is_ignored(self, slack_configured, monkeypatch):
        monkeypatch.setattr(settings, "slack_allowed_user_ids", "U0SOMEONEELSE")
        resp = _post_events(_mention_event())
        assert resp.json()["skipped"] == "user_not_allowed"

    def test_non_event_payloads_are_acked_and_ignored(self, slack_configured):
        resp = _post_events({"type": "app_rate_limited", "team_id": _TEAM_ID})
        assert resp.status_code == 200, resp.text
        assert resp.json()["ignored"] == "app_rate_limited"


class StubClaudeResult:
    def __init__(self, text):
        self.text = text


class TestModelCalls:
    """Covers the real ``answer``/``synthesize`` bodies, not a stubbed-out one."""

    def _capture(self, monkeypatch, text):
        captured: dict = {}

        async def _call(**kwargs):
            captured.update(kwargs)
            return StubClaudeResult(text)

        monkeypatch.setattr(slack_agent_team, "call_claude_messages", _call)
        return captured

    def test_answer_sends_the_agents_own_system_prompt(self, monkeypatch):
        captured = self._capture(monkeypatch, "  use client_id  ")
        agent = roster_mod.get_agent("schema")

        reply = asyncio.run(
            slack_agent_team.answer(agent=agent, question="tenant_id?", history=[])
        )

        assert reply == "use client_id"
        assert captured["system"] == agent.system_prompt()
        assert captured["operation"] == "slack_agent.schema"
        assert captured["messages"] == [{"role": "user", "content": "tenant_id?"}]

    def test_empty_model_output_becomes_a_visible_failure_line(self, monkeypatch):
        self._capture(monkeypatch, "   ")
        reply = asyncio.run(
            slack_agent_team.answer(
                agent=roster_mod.get_agent("ops"), question="status?", history=[]
            )
        )
        assert reply == slack_agent_team._FAILURE_NOTICE

    def test_synthesis_prompt_carries_every_teammate_answer(self, monkeypatch):
        captured = self._capture(monkeypatch, "raise the price")
        answers = [
            (roster_mod.get_agent("growth"), "pricing is too low"),
            (roster_mod.get_agent("support"), "churn risk on the small accounts"),
        ]

        verdict = asyncio.run(
            slack_agent_team.synthesize(question="raise prices?", answers=answers)
        )

        assert verdict == "raise the price"
        prompt = captured["messages"][0]["content"]
        assert "pricing is too low" in prompt
        assert "churn risk on the small accounts" in prompt
        assert "raise prices?" in prompt

    def test_synthesis_of_nothing_is_empty(self, monkeypatch):
        def _explode(**kwargs):
            raise AssertionError("no answers means no model call")

        monkeypatch.setattr(slack_agent_team, "call_claude_messages", _explode)
        assert asyncio.run(slack_agent_team.synthesize(question="x", answers=[])) == ""


class TestBackgroundFailureIsVisible:
    def test_handler_crash_posts_a_notice_in_thread(
        self, slack_configured, recorder, monkeypatch
    ):
        """The webhook already returned 200 — silence would look like a hang."""
        from backend.routers import slack_agents as slack_router

        async def _boom(**kwargs):
            raise RuntimeError("model exploded")

        monkeypatch.setattr(slack_agent_team, "handle_message", _boom)
        monkeypatch.setattr(slack_router.slack_agent_team, "post_as_agent", recorder.post)

        asyncio.run(
            slack_router._handle_safe(
                channel=_CHANNEL, text="hi", thread_ts=None, message_ts="9.9"
            )
        )

        assert len(recorder.posts) == 1
        assert recorder.posts[0]["thread_ts"] == "9.9"
        assert "logs" in recorder.posts[0]["text"]
