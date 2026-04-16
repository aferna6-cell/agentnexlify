"""Unit tests for backend.services.managed_agents (raw-HTTP client)."""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.services.managed_agents import (
    ManagedAgentsClient,
    ManagedAgentsError,
    MANAGED_AGENTS_BETA,
    ANTHROPIC_VERSION,
    SessionTerminalState,
)


def _ok_response(payload: Any) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json=payload,
        request=httpx.Request("POST", "https://api.anthropic.com/v1/test"),
    )


def _make_client() -> ManagedAgentsClient:
    return ManagedAgentsClient(api_key="sk-test-noop")


class TestHeaders:
    def test_required_headers_present(self):
        client = _make_client()
        headers = client._headers()
        assert headers["x-api-key"] == "sk-test-noop"
        assert headers["anthropic-version"] == ANTHROPIC_VERSION
        assert headers["anthropic-beta"] == MANAGED_AGENTS_BETA
        assert headers["content-type"] == "application/json"

    def test_extra_beta_appended(self):
        client = _make_client()
        headers = client._headers(extra_beta="files-api-2025-04-14")
        assert headers["anthropic-beta"] == (
            f"{MANAGED_AGENTS_BETA},files-api-2025-04-14"
        )

    def test_extra_beta_same_as_managed_agents_not_duplicated(self):
        client = _make_client()
        headers = client._headers(extra_beta=MANAGED_AGENTS_BETA)
        assert headers["anthropic-beta"] == MANAGED_AGENTS_BETA


class TestCreateEnvironment:
    def test_create_environment_body_shape(self):
        client = _make_client()

        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = _ok_response(
            {"id": "env_abc", "name": "my-env"}
        )

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            result = client.create_environment(name="my-env")

        assert result == {"id": "env_abc", "name": "my-env"}
        call = mock_http.request.call_args
        assert call.args[0] == "POST"
        assert call.args[1].endswith("/v1/environments")
        assert call.kwargs["json"] == {
            "name": "my-env",
            "config": {
                "type": "cloud",
                "networking": {"type": "unrestricted"},
            },
        }


class TestCreateAgentBody:
    def test_minimal_agent_body(self):
        client = _make_client()
        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = _ok_response(
            {"id": "agent_abc", "name": "Bot", "version": 1}
        )

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            client.create_agent(name="Bot", model="claude-opus-4-6")

        body = mock_http.request.call_args.kwargs["json"]
        assert body == {"name": "Bot", "model": "claude-opus-4-6"}
        # Optional fields must be omitted, not sent as None/empty
        assert "system" not in body
        assert "tools" not in body
        assert "skills" not in body

    def test_full_agent_body(self):
        client = _make_client()
        tools = [{"type": "agent_toolset_20260401"}]
        skills = [{"type": "anthropic", "skill_id": "xlsx"}]

        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = _ok_response({"id": "agent_abc"})

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            client.create_agent(
                name="Bot",
                model="claude-opus-4-6",
                system="You are a bot.",
                tools=tools,
                skills=skills,
                description="Test bot.",
            )

        body = mock_http.request.call_args.kwargs["json"]
        assert body["system"] == "You are a bot."
        assert body["tools"] == tools
        assert body["skills"] == skills
        assert body["description"] == "Test bot."


class TestCreateSessionAgentRef:
    def test_string_shorthand_when_no_version(self):
        client = _make_client()
        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = _ok_response({"id": "sess_1"})

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            client.create_session(agent_id="agent_abc", environment_id="env_abc")

        body = mock_http.request.call_args.kwargs["json"]
        assert body["agent"] == "agent_abc"  # string shorthand
        assert body["environment_id"] == "env_abc"

    def test_version_object_when_pinning(self):
        client = _make_client()
        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = _ok_response({"id": "sess_1"})

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            client.create_session(
                agent_id="agent_abc",
                environment_id="env_abc",
                agent_version=42,
            )

        body = mock_http.request.call_args.kwargs["json"]
        assert body["agent"] == {
            "type": "agent",
            "id": "agent_abc",
            "version": 42,
        }


class TestErrorMapping:
    def test_4xx_raises_with_envelope_fields(self):
        client = _make_client()
        bad = httpx.Response(
            status_code=400,
            json={
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": "Invalid tool config",
                },
                "request_id": "req_abc",
            },
            headers={"request-id": "req_abc"},
            request=httpx.Request("POST", "https://api.anthropic.com/v1/agents"),
        )

        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = bad

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            with pytest.raises(ManagedAgentsError) as exc_info:
                client.create_agent(name="Bot", model="claude-opus-4-6")

        err = exc_info.value
        assert err.status == 400
        assert err.error_type == "invalid_request_error"
        assert err.request_id == "req_abc"
        assert "Invalid tool config" in str(err)

    def test_5xx_retries_then_raises(self):
        client = _make_client()
        fail = httpx.Response(
            status_code=500,
            json={"type": "error", "error": {"type": "api_error", "message": "boom"}},
            request=httpx.Request("POST", "https://api.anthropic.com/v1/agents"),
        )

        mock_http = MagicMock()
        mock_http.__enter__.return_value = mock_http
        mock_http.__exit__.return_value = False
        mock_http.request.return_value = fail

        # Stub sleep so retries don't actually wait.
        with (
            patch("backend.services.managed_agents.httpx.Client", return_value=mock_http),
            patch("backend.services.managed_agents.time.sleep"),
        ):
            with pytest.raises(ManagedAgentsError) as exc_info:
                client.create_agent(name="Bot", model="claude-opus-4-6")

        # retries=2 default → 3 total attempts
        assert mock_http.request.call_count == 3
        assert exc_info.value.status == 500


class TestStreamEvents:
    def _make_sse_client(self, body: bytes) -> MagicMock:
        """Build a fake httpx.Client whose .stream() returns canned SSE bytes."""
        stream_ctx = MagicMock()
        stream_resp = MagicMock()
        stream_resp.status_code = 200
        stream_resp.iter_lines.return_value = iter(
            body.decode("utf-8").splitlines()
        )
        stream_ctx.__enter__.return_value = stream_resp
        stream_ctx.__exit__.return_value = False

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.stream.return_value = stream_ctx
        return mock_client

    def test_parses_data_frames(self):
        client = _make_client()
        body = (
            b": heartbeat\n"
            b"event: agent.message\n"
            b'data: {"type":"agent.message","id":"sevt_1","content":[{"type":"text","text":"hello"}]}\n'
            b"\n"
            b"event: session.status_idle\n"
            b'data: {"type":"session.status_idle","id":"sevt_2","stop_reason":{"type":"end_turn"}}\n'
            b"\n"
        )
        mock_http = self._make_sse_client(body)

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            events = list(client.stream_events("sess_1"))

        assert len(events) == 2
        assert events[0]["type"] == "agent.message"
        assert events[0]["content"][0]["text"] == "hello"
        assert events[1]["type"] == "session.status_idle"


class TestRunUntilIdle:
    def _make_sse_client(self, body: bytes) -> MagicMock:
        stream_ctx = MagicMock()
        stream_resp = MagicMock()
        stream_resp.status_code = 200
        stream_resp.iter_lines.return_value = iter(body.decode("utf-8").splitlines())
        stream_ctx.__enter__.return_value = stream_resp
        stream_ctx.__exit__.return_value = False

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.stream.return_value = stream_ctx
        mock_client.request.return_value = _ok_response({"ok": True})
        return mock_client

    def test_terminal_state_preserves_session_id(self):
        client = _make_client()
        body = (
            b'event: session.status_idle\n'
            b'data: {"type":"session.status_idle","id":"sevt_2","stop_reason":{"type":"end_turn"}}\n'
            b"\n"
        )
        mock_http = self._make_sse_client(body)

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            terminal = client.run_until_idle("sess_123")

        assert terminal.session_id == "sess_123"
        assert terminal.last_event_id == "sevt_2"
        assert terminal.stop_reason_type == "end_turn"

    def test_skips_malformed_json(self):
        client = _make_client()
        body = (
            b"data: {not-json}\n\n"
            b'data: {"type":"agent.message","id":"sevt_1"}\n\n'
        )
        mock_http = self._make_sse_client(body)
        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_http):
            events = list(client.stream_events("sess_1"))
        # The malformed frame is logged and skipped, the good one yields.
        assert len(events) == 1
        assert events[0]["id"] == "sevt_1"

    def test_stream_http_error_raises(self):
        client = _make_client()
        stream_resp = MagicMock()
        stream_resp.status_code = 401
        stream_resp.read.return_value = (
            b'{"type":"error","error":{"type":"authentication_error","message":"bad key"}}'
        )

        stream_ctx = MagicMock()
        stream_ctx.__enter__.return_value = stream_resp
        stream_ctx.__exit__.return_value = False

        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.stream.return_value = stream_ctx

        with patch("backend.services.managed_agents.httpx.Client", return_value=mock_client):
            with pytest.raises(ManagedAgentsError) as exc_info:
                # stream_events is a generator — must iterate to trigger
                list(client.stream_events("sess_1"))

        assert exc_info.value.status == 401


class TestQualifyLeadBlocking:
    """Unit tests for the router's `_qualify_lead_blocking` event loop.

    The real loop wires `ManagedAgentsClient` to the Managed Agents API, but
    the interesting logic is the break-gate state machine: we must break on
    `status_terminated`, break on `status_idle` with a non-`requires_action`
    stop, keep looping on `status_idle` with `requires_action`, and fail loudly
    on an unexpected `agent.custom_tool_use` (lead_qualifier has no custom
    tools — any sighting is a config drift).
    """

    def _make_mock_client(self, events: list[dict[str, Any]]) -> MagicMock:
        mock_client = MagicMock()
        mock_client.create_session.return_value = {"id": "sess_1"}
        mock_client.stream_events.return_value = iter(events)
        mock_client.send_user_message.return_value = None
        return mock_client

    def test_happy_path_captures_transcript_and_breaks_on_end_turn(self):
        from backend.routers.managed_agent_runs import _qualify_lead_blocking

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": "ok"}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_client = self._make_mock_client(events)

        terminal, transcript = _qualify_lead_blocking(
            mock_client,
            agent_id="agent_abc",
            environment_id="env_abc",
            prompt="qualify",
            tenant_id="tenant_xyz",
        )
        # Regression: terminal state must carry the real session_id, not the
        # last event id. Previously the router returned last_event_id as the
        # API response's `session_id`, which confused downstream consumers.
        assert terminal.session_id == "sess_1"
        assert terminal.session_id != terminal.last_event_id

        # Session was created with the right metadata.
        mock_client.create_session.assert_called_once()
        kwargs = mock_client.create_session.call_args.kwargs
        assert kwargs["agent_id"] == "agent_abc"
        assert kwargs["environment_id"] == "env_abc"
        assert kwargs["metadata"]["tenant_id"] == "tenant_xyz"
        assert kwargs["metadata"]["flow"] == "lead_qualify"

        # Stream was opened BEFORE the first user message was sent.
        call_order = [c[0] for c in mock_client.method_calls]
        stream_idx = call_order.index("stream_events")
        send_idx = call_order.index("send_user_message")
        assert stream_idx < send_idx, (
            "stream_events must be opened before send_user_message — "
            "the SSE API drops events published before a subscriber attaches"
        )

        # Assistant message captured, terminal state reflects end_turn.
        assert len(transcript) == 1
        assert transcript[0]["role"] == "assistant"
        assert transcript[0]["content"] == [{"type": "text", "text": "ok"}]
        assert terminal.terminated is False
        assert terminal.stop_reason_type == "end_turn"
        assert terminal.last_event_id == "sevt_2"

    def test_break_on_session_terminated(self):
        from backend.routers.managed_agent_runs import _qualify_lead_blocking

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": "partial"}],
            },
            {"type": "session.status_terminated", "id": "sevt_2"},
            # Sentinel event — loop must have broken before reaching this.
            {
                "type": "agent.message",
                "id": "sevt_3",
                "content": [{"type": "text", "text": "should-not-capture"}],
            },
        ]
        mock_client = self._make_mock_client(events)

        terminal, transcript = _qualify_lead_blocking(
            mock_client,
            agent_id="agent_abc",
            environment_id="env_abc",
            prompt="qualify",
            tenant_id="tenant_xyz",
        )

        assert terminal.terminated is True
        assert terminal.last_event_id == "sevt_2"
        # Only the first message — the sentinel after the break should NOT be
        # appended.
        assert len(transcript) == 1
        assert transcript[0]["content"][0]["text"] == "partial"

    def test_idle_requires_action_does_not_break(self):
        from backend.routers.managed_agent_runs import _qualify_lead_blocking

        # requires_action idle is transient — the loop MUST keep going.
        # This test would hang forever if the loop broke incorrectly on the
        # first idle, because the next event is a real end_turn.
        events = [
            {
                "type": "session.status_idle",
                "id": "sevt_1",
                "stop_reason": {"type": "requires_action"},
            },
            {
                "type": "agent.message",
                "id": "sevt_2",
                "content": [{"type": "text", "text": "after tool"}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_3",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_client = self._make_mock_client(events)

        terminal, transcript = _qualify_lead_blocking(
            mock_client,
            agent_id="agent_abc",
            environment_id="env_abc",
            prompt="qualify",
            tenant_id="tenant_xyz",
        )

        assert terminal.stop_reason_type == "end_turn"
        assert terminal.last_event_id == "sevt_3"
        assert len(transcript) == 1
        assert transcript[0]["content"][0]["text"] == "after tool"

    def test_custom_tool_use_breaks_early_as_config_drift_signal(self):
        from backend.routers.managed_agent_runs import _qualify_lead_blocking

        events = [
            {
                "type": "agent.custom_tool_use",
                "id": "sevt_1",
                "tool_name": "unexpected_tool",
            },
            # Sentinel — should NOT be reached.
            {
                "type": "agent.message",
                "id": "sevt_2",
                "content": [{"type": "text", "text": "unreachable"}],
            },
        ]
        mock_client = self._make_mock_client(events)

        terminal, transcript = _qualify_lead_blocking(
            mock_client,
            agent_id="agent_abc",
            environment_id="env_abc",
            prompt="qualify",
            tenant_id="tenant_xyz",
        )

        # The loop broke on the custom tool request — no transcript,
        # terminal state still at its initial non-terminated value.
        assert transcript == []
        assert terminal.terminated is False
        assert terminal.last_event_id is None


class TestSafeContentDisposition:
    """Regression tests for Content-Disposition header injection via filenames."""

    def test_crlf_stripped(self):
        from backend.routers.managed_agent_runs import _safe_content_disposition

        header = _safe_content_disposition("evil\r\nX-Injected: yes.docx")
        # CR/LF must not survive — otherwise an attacker could inject a new
        # response header and split the response.
        assert "\r" not in header
        assert "\n" not in header
        assert "X-Injected" in header  # the literal chars are fine, just not as a new header line

    def test_embedded_quote_escaped(self):
        from backend.routers.managed_agent_runs import _safe_content_disposition

        header = _safe_content_disposition('hack".docx')
        # Raw double-quote would close the filename parameter early.
        assert 'filename="hack_.docx"' in header

    def test_unicode_filename_uses_rfc6266_star(self):
        from backend.routers.managed_agent_runs import _safe_content_disposition

        header = _safe_content_disposition("résumé.pdf")
        # ASCII fallback must be present, and RFC 6266 filename* must encode
        # the UTF-8 bytes.
        assert "filename=" in header
        assert "filename*=UTF-8''" in header
        assert "r%C3%A9sum%C3%A9.pdf" in header

    def test_empty_filename_defaults_to_download(self):
        from backend.routers.managed_agent_runs import _safe_content_disposition

        header = _safe_content_disposition("")
        assert 'filename="download"' in header


class TestRegistry:
    def test_missing_env_vars_raises_actionable_error(self):
        from backend.services.managed_agents_registry import (
            ManagedAgentNotConfigured,
            lead_qualifier,
        )
        from backend.config import settings

        with (
            patch.object(settings, "managed_agents_environment_id", ""),
            patch.object(settings, "lead_qualifier_agent_id", ""),
        ):
            with pytest.raises(ManagedAgentNotConfigured) as exc_info:
                lead_qualifier()

        assert "LEAD_QUALIFIER_AGENT_ID" in str(exc_info.value) or \
               "MANAGED_AGENTS_ENVIRONMENT_ID" in str(exc_info.value)

    def test_handle_returned_when_configured(self):
        from backend.services.managed_agents_registry import lead_qualifier
        from backend.config import settings

        with (
            patch.object(settings, "managed_agents_environment_id", "env_abc"),
            patch.object(settings, "lead_qualifier_agent_id", "agent_abc"),
        ):
            handle = lead_qualifier()

        assert handle.agent_id == "agent_abc"
        assert handle.environment_id == "env_abc"


# ----------------------------------------------------------------------
# New agents (2026-04-10): support_agent, structured_extractor
# ----------------------------------------------------------------------
#
# These mirror TestQualifyLeadBlocking but cover the service-level
# wrappers rather than the router helper. Both services use the
# `_CapturingManagedAgentClient` pattern which wraps a real
# ManagedAgentsClient instance AND calls back into
# `ManagedAgentsClient.run_until_idle(self, ...)` as an unbound class
# method. That means we cannot just replace the whole class with a
# MagicMock — the wrapper's delegation would resolve the class method
# to a sub-mock and return a MagicMock instead of a SessionTerminalState.
#
# `_patch_managed_agents_class(mod, mock_inner)` is the helper that
# does the right thing: it replaces the constructor so `ManagedAgentsClient()`
# returns `mock_inner`, but keeps `ManagedAgentsClient.run_until_idle`
# pointing at the real function so the capturing wrapper still works.
# ----------------------------------------------------------------------


def _mock_inner_client(events: list[dict[str, Any]]) -> MagicMock:
    inner = MagicMock()
    inner.create_session.return_value = {"id": "sess_1"}
    inner.stream_events.return_value = iter(events)
    inner.send_user_message.return_value = None
    return inner


def _patch_managed_agents_class(mod: Any, mock_inner: MagicMock):
    """Patch `mod.ManagedAgentsClient` so the constructor returns `mock_inner`
    while preserving the real unbound `run_until_idle` classmethod for the
    capturing wrapper to delegate into.
    """
    from backend.services.managed_agents import ManagedAgentsClient as _Real

    replacement = MagicMock(name="ManagedAgentsClient")
    replacement.return_value = mock_inner
    # The capturing wrapper resolves `ManagedAgentsClient.run_until_idle`
    # at call time via the module globals — keep it pointing at the real
    # function so it actually drains the stream.
    replacement.run_until_idle = _Real.run_until_idle
    return patch.object(mod, "ManagedAgentsClient", replacement)


def _capture_terminal_state(mod: Any, captured: dict[str, SessionTerminalState]):
    """Patch the capturing wrapper to expose the terminal state to tests."""
    original = mod._CapturingManagedAgentClient.run_until_idle

    def capture(
        self,
        session_id: str,
        *,
        kickoff_text: str | None = None,
    ) -> SessionTerminalState:
        terminal = original(self, session_id, kickoff_text=kickoff_text)
        captured["terminal"] = terminal
        return terminal

    return patch.object(mod._CapturingManagedAgentClient, "run_until_idle", capture)


class TestStructuredExtractor:
    """Tests for backend.services.structured_extractor.extract_structured."""

    def test_unsupported_schema_raises(self):
        from backend.services.structured_extractor import extract_structured

        with pytest.raises(ValueError, match="unsupported target_schema"):
            extract_structured("tenant_abc", "any text", "nope")

    def test_happy_path_parses_json_and_enforces_session_id_contract(self):
        from backend.services import structured_extractor as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "name": "Maria Lopez",
                                "email": "maria.lopez@example.com",
                                "phone": "973-555-0134",
                                "interest": "pressure wash + deck sealing",
                                "timeline": "2 weeks",
                                "budget": 500,
                                "source": "google ad",
                            }
                        ),
                    },
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_extract", environment_id="env_abc",
        )
        captured_terminal: dict[str, SessionTerminalState] = {}

        with (
            _patch_managed_agents_class(mod, mock_inner),
            _capture_terminal_state(mod, captured_terminal),
            patch.object(mod, "structured_extractor", return_value=fake_handle),
        ):
            parsed = mod.extract_structured(
                "tenant_abc", "Hi I am Maria...", "lead",
            )

        assert parsed == {
            "name": "Maria Lopez",
            "email": "maria.lopez@example.com",
            "phone": "973-555-0134",
            "interest": "pressure wash + deck sealing",
            "timeline": "2 weeks",
            "budget": 500,
            "source": "google ad",
        }

        # Prompt embeds schema + raw text in labeled blocks.
        send_call = mock_inner.send_user_message.call_args
        assert send_call is not None, "send_user_message was never called"
        prompt = send_call.args[1]
        assert "[SCHEMA]" in prompt
        assert "target_schema: lead" in prompt
        assert "[RAW_TEXT]" in prompt
        assert "Maria" in prompt

        # Stream was opened before the kickoff message was sent.
        call_order = [c[0] for c in mock_inner.method_calls]
        stream_idx = call_order.index("stream_events")
        send_idx = call_order.index("send_user_message")
        assert stream_idx < send_idx

        # Session metadata carries tenant_id + flow.
        create_kwargs = mock_inner.create_session.call_args.kwargs
        assert create_kwargs["agent_id"] == "agent_extract"
        assert create_kwargs["environment_id"] == "env_abc"
        assert create_kwargs["metadata"]["tenant_id"] == "tenant_abc"
        assert create_kwargs["metadata"]["flow"] == "structured_extractor"
        assert create_kwargs["metadata"]["target_schema"] == "lead"

        terminal = captured_terminal["terminal"]
        assert terminal.session_id == "sess_1"
        assert terminal.session_id != terminal.last_event_id

    def test_invalid_json_raises_value_error(self):
        from backend.services import structured_extractor as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {"type": "text", "text": "sorry, I can't do JSON today"},
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_extract", environment_id="env_abc",
        )

        with (
            _patch_managed_agents_class(mod, mock_inner),
            patch.object(mod, "structured_extractor", return_value=fake_handle),
        ):
            with pytest.raises(ValueError, match="invalid JSON"):
                mod.extract_structured("tenant_abc", "garbage", "lead")

    def test_empty_reply_raises_value_error(self):
        from backend.services import structured_extractor as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "session.status_idle",
                "id": "sevt_1",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_extract", environment_id="env_abc",
        )

        with (
            _patch_managed_agents_class(mod, mock_inner),
            patch.object(mod, "structured_extractor", return_value=fake_handle),
        ):
            with pytest.raises(ValueError, match="no assistant text"):
                mod.extract_structured("tenant_abc", "anything", "lead")

    def test_fenced_markdown_reply_parses(self):
        """Regression: Haiku sometimes wraps the JSON in ```json fences even
        when told not to. Live smoke on 2026-04-10 caught this — strict
        json.loads raised ValueError in production. Extractor must tolerate
        fenced replies."""
        from backend.services import structured_extractor as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        fenced_reply = (
            "```json\n"
            "{\n"
            '  "name": "Maria Lopez",\n'
            '  "email": "maria.lopez@example.com",\n'
            '  "phone": "973-555-0134",\n'
            '  "interest": "driveway pressure wash",\n'
            '  "timeline": "two weeks",\n'
            '  "budget": "around 500 dollars",\n'
            '  "source": "Google ad"\n'
            "}\n"
            "```"
        )
        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [{"type": "text", "text": fenced_reply}],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_extract", environment_id="env_abc",
        )

        with (
            _patch_managed_agents_class(mod, mock_inner),
            patch.object(mod, "structured_extractor", return_value=fake_handle),
        ):
            parsed = mod.extract_structured(
                "tenant_abc", "Hi I am Maria...", "lead",
            )

        assert parsed["name"] == "Maria Lopez"
        assert parsed["email"] == "maria.lopez@example.com"
        assert parsed["phone"] == "973-555-0134"
        assert parsed["source"] == "Google ad"


class TestSupportAgentBlocking:
    """Tests for backend.services.support_agent.run_support_query."""

    def _fake_tenant_ctx(self):
        tenant = {
            "id": "tenant_abc",
            "business_name": "Smoke Salon",
            "business_type": "hair salon",
        }
        widget = {
            "knowledge_base": "Walk-ins Monday-Friday before 4pm.",
            "custom_instructions": "Warm and concise tone.",
        }
        faq_entries = [
            {"question": "Do you take walk-ins?", "answer": "Yes, M-F before 4pm."},
        ]
        hours_row = {
            "timezone": "America/New_York",
            "hours": {
                "monday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "sunday": {"enabled": False},
            },
        }
        return tenant, widget, faq_entries, hours_row

    def test_happy_path_parses_json_reply(self):
        from backend.services import support_agent as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "answer": "We're open Monday to Friday 9-6.",
                                "confidence": "high",
                                "escalate_reason": None,
                            }
                        ),
                    },
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_support", environment_id="env_abc",
        )
        captured_terminal: dict[str, SessionTerminalState] = {}

        with (
            _patch_managed_agents_class(mod, mock_inner),
            _capture_terminal_state(mod, captured_terminal),
            patch.object(mod, "support_agent", return_value=fake_handle),
            patch.object(
                mod, "_load_tenant_context", return_value=self._fake_tenant_ctx(),
            ),
            patch.object(mod, "_load_conversation_history", return_value=[]),
        ):
            parsed = mod.run_support_query("tenant_abc", "What are your hours?")

        assert parsed == {
            "answer": "We're open Monday to Friday 9-6.",
            "confidence": "high",
            "escalate_reason": None,
        }

        # Prompt contains all four labeled blocks.
        send_call = mock_inner.send_user_message.call_args
        assert send_call is not None
        prompt = send_call.args[1]
        for block in (
            "[TENANT_CONTEXT]",
            "[KB_SNIPPET]",
            "[CONVERSATION_HISTORY]",
            "[QUESTION]",
        ):
            assert block in prompt, f"prompt missing {block}"
        assert "Smoke Salon" in prompt
        assert "What are your hours?" in prompt

        # Stream was opened before the kickoff message was sent.
        call_order = [c[0] for c in mock_inner.method_calls]
        stream_idx = call_order.index("stream_events")
        send_idx = call_order.index("send_user_message")
        assert stream_idx < send_idx

        # Session metadata carries tenant_id + flow.
        create_kwargs = mock_inner.create_session.call_args.kwargs
        assert create_kwargs["agent_id"] == "agent_support"
        assert create_kwargs["metadata"]["tenant_id"] == "tenant_abc"
        assert create_kwargs["metadata"]["flow"] == "support_agent"

        terminal = captured_terminal["terminal"]
        assert terminal.session_id == "sess_1"
        assert terminal.session_id != terminal.last_event_id

    def test_plain_text_reply_falls_back_to_string(self):
        from backend.services import support_agent as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "agent.message",
                "id": "sevt_1",
                "content": [
                    {"type": "text", "text": "We're open Mon-Fri 9 to 6."},
                ],
            },
            {
                "type": "session.status_idle",
                "id": "sevt_2",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_support", environment_id="env_abc",
        )

        with (
            _patch_managed_agents_class(mod, mock_inner),
            patch.object(mod, "support_agent", return_value=fake_handle),
            patch.object(
                mod, "_load_tenant_context", return_value=self._fake_tenant_ctx(),
            ),
            patch.object(mod, "_load_conversation_history", return_value=[]),
        ):
            parsed = mod.run_support_query("tenant_abc", "Hours?")

        assert parsed["answer"] == "We're open Mon-Fri 9 to 6."
        # Confidence heuristic: plain-text non-escalating reply defaults to medium.
        assert parsed["confidence"] == "medium"
        assert parsed["escalate_reason"] is None

    def test_empty_reply_raises_value_error(self):
        from backend.services import support_agent as mod
        from backend.services.managed_agents_registry import ManagedAgentHandle

        events = [
            {
                "type": "session.status_idle",
                "id": "sevt_1",
                "stop_reason": {"type": "end_turn"},
            },
        ]
        mock_inner = _mock_inner_client(events)
        fake_handle = ManagedAgentHandle(
            agent_id="agent_support", environment_id="env_abc",
        )

        with (
            _patch_managed_agents_class(mod, mock_inner),
            patch.object(mod, "support_agent", return_value=fake_handle),
            patch.object(
                mod, "_load_tenant_context", return_value=self._fake_tenant_ctx(),
            ),
            patch.object(mod, "_load_conversation_history", return_value=[]),
        ):
            with pytest.raises(ValueError, match="no assistant text"):
                mod.run_support_query("tenant_abc", "Hours?")


# ----------------------------------------------------------------------
# HTTP-level tests for the new router endpoints (2026-04-10)
# ----------------------------------------------------------------------
#
# TestSupportAgentBlocking + TestStructuredExtractor cover the service
# layer. These cover the router wiring — auth via `_get_current_tenant`,
# tenant-mismatch 403, service exception → HTTP status mapping, rate
# limit decorator presence, and happy-path response shape. Services are
# patched at the router module level so no network / no agent invocation.
# ----------------------------------------------------------------------


class TestSupportQueryEndpoint:
    """HTTP tests for POST /api/v1/managed-agents/{tenant_id}/support-query."""

    TENANT = "00000000-0000-0000-0000-000000000001"
    PATH = f"/api/v1/managed-agents/{TENANT}/support-query"

    def test_happy_path(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        fake_result = {
            "answer": "We're open Mon-Fri 9-6.",
            "confidence": "high",
            "escalate_reason": None,
        }
        with patch.object(mod, "run_support_query", return_value=fake_result) as mock_service:
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"question": "What are your hours?"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["answer"] == "We're open Mon-Fri 9-6."
        assert body["confidence"] == "high"
        assert body["escalate_reason"] is None

        mock_service.assert_called_once()
        call_args = mock_service.call_args
        assert call_args.args[0] == self.TENANT
        assert call_args.args[1] == "What are your hours?"

    def test_tenant_mismatch_returns_403(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        wrong_path = "/api/v1/managed-agents/ffffffff-ffff-ffff-ffff-ffffffffffff/support-query"
        with patch.object(mod, "run_support_query") as mock_service:
            resp = client.post(
                wrong_path,
                headers=auth_headers,
                json={"question": "hello"},
            )

        assert resp.status_code == 403
        mock_service.assert_not_called()

    def test_missing_auth_returns_401(self, client):
        resp = client.post(self.PATH, json={"question": "hello"})
        # FastAPI's Header() dependency returns 422 for missing Authorization,
        # not 401 — it's a request-validation error at the framework layer.
        assert resp.status_code in (401, 403, 422)

    def test_not_configured_returns_503(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod
        from backend.services.managed_agents_registry import ManagedAgentNotConfigured

        with patch.object(
            mod,
            "run_support_query",
            side_effect=ManagedAgentNotConfigured("SUPPORT_AGENT_ID"),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"question": "hello"},
            )

        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["error"] == "managed_agents_unavailable"
        assert detail["missing_config"] == "SUPPORT_AGENT_ID"

    def test_upstream_error_maps_to_502(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod
        from backend.services.managed_agents import ManagedAgentsError

        with patch.object(
            mod,
            "run_support_query",
            side_effect=ManagedAgentsError(
                "upstream boom", status=500, request_id="req_1",
            ),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"question": "hello"},
            )

        assert resp.status_code == 502

    def test_invalid_reply_value_error_maps_to_502(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        with patch.object(
            mod,
            "run_support_query",
            side_effect=ValueError("support_agent returned no assistant text"),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"question": "hello"},
            )

        assert resp.status_code == 502

    def test_empty_question_rejected(self, client, auth_headers):
        resp = client.post(
            self.PATH,
            headers=auth_headers,
            json={"question": ""},
        )
        assert resp.status_code == 422


class TestExtractEndpoint:
    """HTTP tests for POST /api/v1/managed-agents/{tenant_id}/extract."""

    TENANT = "00000000-0000-0000-0000-000000000001"
    PATH = f"/api/v1/managed-agents/{TENANT}/extract"

    def test_happy_path(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        fake_result = {
            "name": "Maria Lopez",
            "email": "maria@example.com",
            "phone": "555-0100",
            "interest": "pressure wash",
            "timeline": "two weeks",
            "budget": "500",
            "source": "google ad",
        }
        with patch.object(
            mod, "extract_structured", return_value=fake_result,
        ) as mock_service:
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={
                    "raw_text": "Hi I am Maria Lopez, email maria@example.com",
                    "target_schema": "lead",
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["data"]["name"] == "Maria Lopez"
        mock_service.assert_called_once()
        call_args = mock_service.call_args
        assert call_args.args[0] == self.TENANT
        assert call_args.args[2] == "lead"

    def test_tenant_mismatch_returns_403(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        wrong_path = "/api/v1/managed-agents/ffffffff-ffff-ffff-ffff-ffffffffffff/extract"
        with patch.object(mod, "extract_structured") as mock_service:
            resp = client.post(
                wrong_path,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "lead"},
            )

        assert resp.status_code == 403
        mock_service.assert_not_called()

    def test_missing_auth_returns_401(self, client):
        resp = client.post(
            self.PATH,
            json={"raw_text": "hi", "target_schema": "lead"},
        )
        # FastAPI's Header() dependency returns 422 for missing Authorization,
        # not 401 — it's a request-validation error at the framework layer.
        assert resp.status_code in (401, 403, 422)

    def test_invalid_target_schema_rejected_by_pydantic(
        self, client, auth_headers,
    ):
        """Literal enforcement in the Pydantic model catches bad schemas
        before the service is ever called."""
        from backend.routers import managed_agent_runs as mod

        with patch.object(mod, "extract_structured") as mock_service:
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "invoice_line_item"},
            )

        assert resp.status_code == 422
        mock_service.assert_not_called()

    def test_empty_raw_text_rejected(self, client, auth_headers):
        resp = client.post(
            self.PATH,
            headers=auth_headers,
            json={"raw_text": "", "target_schema": "lead"},
        )
        assert resp.status_code == 422

    def test_not_configured_returns_503(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod
        from backend.services.managed_agents_registry import ManagedAgentNotConfigured

        with patch.object(
            mod,
            "extract_structured",
            side_effect=ManagedAgentNotConfigured("STRUCTURED_EXTRACTOR_AGENT_ID"),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "lead"},
            )

        assert resp.status_code == 503

    def test_unsupported_schema_from_service_maps_to_400(
        self, client, auth_headers,
    ):
        """If the Pydantic Literal accepted the value but the service
        raised `unsupported target_schema` (config drift), the router
        maps it to 400 rather than 502."""
        from backend.routers import managed_agent_runs as mod

        with patch.object(
            mod,
            "extract_structured",
            side_effect=ValueError("unsupported target_schema 'lead'"),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "lead"},
            )

        assert resp.status_code == 400

    def test_invalid_json_value_error_maps_to_502(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod

        with patch.object(
            mod,
            "extract_structured",
            side_effect=ValueError("invalid JSON: garbage"),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "lead"},
            )

        assert resp.status_code == 502

    def test_upstream_error_maps_to_502(self, client, auth_headers):
        from backend.routers import managed_agent_runs as mod
        from backend.services.managed_agents import ManagedAgentsError

        with patch.object(
            mod,
            "extract_structured",
            side_effect=ManagedAgentsError(
                "upstream boom", status=500, request_id="req_1",
            ),
        ):
            resp = client.post(
                self.PATH,
                headers=auth_headers,
                json={"raw_text": "hi", "target_schema": "lead"},
            )

        assert resp.status_code == 502


class TestHealthEndpointLists8Agents:
    """Regression test: GET /health should surface all 8 agent IDs now that
    support_agent, structured_extractor, deep_researcher, field_monitor,
    and data_analyst have been added to the registry.
    """

    TENANT = "00000000-0000-0000-0000-000000000001"
    PATH = f"/api/v1/managed-agents/{TENANT}/health"

    def test_lists_all_eight_agents(self, client, auth_headers):
        from backend.config import settings

        with (
            patch.object(settings, "managed_agents_environment_id", "env_abc"),
            patch.object(settings, "lead_qualifier_agent_id", "agent_lq"),
            patch.object(settings, "document_drafter_agent_id", "agent_dd"),
            patch.object(settings, "codebase_reviewer_agent_id", "agent_cr"),
            patch.object(settings, "support_agent_id", "agent_sa"),
            patch.object(settings, "structured_extractor_agent_id", "agent_se"),
            patch.object(settings, "deep_researcher_agent_id", "agent_dr"),
            patch.object(settings, "field_monitor_agent_id", "agent_fm"),
            patch.object(settings, "data_analyst_agent_id", "agent_da"),
        ):
            resp = client.get(self.PATH, headers=auth_headers)

        assert resp.status_code == 200, resp.text
        body = resp.json()
        for expected in (
            "lead_qualifier",
            "document_drafter",
            "codebase_reviewer",
            "support_agent",
            "structured_extractor",
            "deep_researcher",
            "field_monitor",
            "data_analyst",
        ):
            assert expected in body, f"health payload missing {expected}: {body}"
