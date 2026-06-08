"""Unit tests for the ``research`` Agent OS worker.

Covers the two behaviors that matter for routing and side effects:
  - channel routing via ``_choose_action_type`` (email default + overrides)
  - ``_run`` passes the server-side web_search tool, returns the Claude draft as
    an approval-gated deliverable with the chosen action_type, and falls back
    deterministically when the Claude call raises.

The Claude call is monkeypatched — these tests never hit the network.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock


from backend.services.os_workers import research
from backend.services.os_workers.base import WorkerContext, WorkerResult

_CLIENT = "00000000-0000-0000-0000-0000000000c3"


def _ctx(user_message: str, *, tools=None) -> WorkerContext:
    return WorkerContext(
        db=MagicMock(name="db"),
        client_id=_CLIENT,
        thread_id="thread-1",
        run_id="run-1",
        user_message=user_message,
        deliverable_title="Competitor Brief",
        tools=tools,
    )


class _StubTools:
    """Minimal async stand-in for WorkerTools — only what the worker calls."""

    def __init__(self, profile: dict | None = None):
        self._profile = profile or {}

    async def tenant_profile(self) -> dict:
        return self._profile


# ---------------------------------------------------------------------------
# _choose_action_type
# ---------------------------------------------------------------------------


def test_action_type_defaults_to_email():
    assert (
        research._choose_action_type("research Acme Co and write me a note")
        == "email.send"
    )


def test_action_type_explicit_email_wins():
    assert research._choose_action_type("look them up then email them") == "email.send"


def test_action_type_routes_sms():
    assert research._choose_action_type("research it and send a text") == "sms.send"


def test_action_type_routes_crm():
    assert (
        research._choose_action_type("research and log a note in the crm")
        == "crm.contact_upsert"
    )


def test_action_type_empty_message_is_email():
    assert research._choose_action_type("") == "email.send"


# ---------------------------------------------------------------------------
# _run — happy path
# ---------------------------------------------------------------------------


def test_run_uses_web_search_and_returns_deliverable(monkeypatch):
    captured: dict = {}

    async def _fake_call(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            text="## Research summary\n- finding\n\n## Outreach draft\n\nHi there"
        )

    monkeypatch.setattr(research, "call_claude_messages", _fake_call)

    tools = _StubTools({"business_name": "Bob's Plumbing", "ignored": "x"})
    ctx = _ctx("research the competitor and email them", tools=tools)

    result = asyncio.run(research._run(ctx))

    assert isinstance(result, WorkerResult)
    assert result.action_type == "email.send"
    assert result.deliverable["title"] == "Competitor Brief"
    assert result.deliverable["format"] == "markdown"
    assert "Outreach draft" in result.deliverable["body"]

    # The server-side web_search tool must be passed through.
    assert captured["tools"] == [research._WEB_SEARCH_TOOL]
    assert captured["model"] == "claude-sonnet-4-6"
    # Business profile is fed to the prompt (filtered to known keys).
    assert "Bob's Plumbing" in captured["messages"][0]["content"]
    assert "ignored" not in captured["messages"][0]["content"]


def test_run_records_progress_steps(monkeypatch):
    async def _fake_call(**kwargs):
        return SimpleNamespace(
            text="## Research summary\n- x\n\n## Outreach draft\n\nHi"
        )

    monkeypatch.setattr(research, "call_claude_messages", _fake_call)

    ctx = _ctx("research solar incentives", tools=_StubTools())
    asyncio.run(research._run(ctx))

    labels = [step["label"] for step in ctx.thought]
    assert "Searching the web" in labels
    assert "Draft prepared" in labels


# ---------------------------------------------------------------------------
# _run — fallback
# ---------------------------------------------------------------------------


def test_run_falls_back_when_claude_raises(monkeypatch):
    async def _boom(**kwargs):
        raise RuntimeError("web search unavailable")

    monkeypatch.setattr(research, "call_claude_messages", _boom)

    ctx = _ctx("research the market and text them", tools=_StubTools())
    result = asyncio.run(research._run(ctx))

    # Still an approval-gated deliverable, routed to the requested channel.
    assert result.action_type == "sms.send"
    assert "research the market" in result.deliverable["body"]
    assert "## Outreach draft" in result.deliverable["body"]
    labels = [step["label"] for step in ctx.thought]
    assert "Draft prepared (fallback)" in labels


def test_run_works_without_tools(monkeypatch):
    async def _fake_call(**kwargs):
        return SimpleNamespace(
            text="## Research summary\n- y\n\n## Outreach draft\n\nHello"
        )

    monkeypatch.setattr(research, "call_claude_messages", _fake_call)

    ctx = _ctx("research X", tools=None)
    result = asyncio.run(research._run(ctx))
    assert result.action_type == "email.send"
    assert result.deliverable["body"].startswith("## Research summary")


# ---------------------------------------------------------------------------
# SPEC registration
# ---------------------------------------------------------------------------


def test_spec_is_registered_as_research():
    assert research.SPEC.name == "research"
    assert research.SPEC.description.strip()
    assert research.SPEC.run is research._run
