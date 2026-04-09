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
