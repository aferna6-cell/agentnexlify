"""MCP client v1 (enterprise-audit item 5) — protocol + safety contracts.

Uses httpx.MockTransport so the JSON-RPC framing, SSE fallback parsing, auth
header shaping, and error surfaces are exercised against a real httpx stack
with zero network.
"""

import asyncio
import json
from unittest.mock import patch

import httpx
import pytest

from backend.services import mcp_client
from backend.services.mcp_client import McpError, validate_server_url


def _client_factory(handler):
    """Patch httpx.AsyncClient so mcp_client talks to a MockTransport."""
    transport = httpx.MockTransport(handler)
    real_init = httpx.AsyncClient.__init__

    def _patched(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    return patch.object(httpx.AsyncClient, "__init__", _patched)


class TestValidateServerUrl:
    def test_https_allowed(self):
        assert validate_server_url("https://mcp.example.com/x") == (
            "https://mcp.example.com/x"
        )

    def test_localhost_http_allowed(self):
        assert validate_server_url("http://localhost:3000/mcp")
        assert validate_server_url("http://127.0.0.1:3000/mcp")

    def test_plain_http_rejected(self):
        with pytest.raises(McpError):
            validate_server_url("http://mcp.example.com")

    def test_empty_rejected(self):
        with pytest.raises(McpError):
            validate_server_url("")


class TestListTools:
    def test_parses_tools_and_sends_bearer(self):
        seen = {}

        def handler(request):
            seen["auth"] = request.headers.get("authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"tools": [{"name": "search", "description": "d"}]},
                },
            )

        with _client_factory(handler):
            tools = asyncio.run(
                mcp_client.list_tools(
                    "https://mcp.example.com", "Authorization", "tok123"
                )
            )
        assert tools == [{"name": "search", "description": "d"}]
        assert seen["auth"] == "Bearer tok123"
        assert seen["body"]["method"] == "tools/list"

    def test_sse_framed_response_parsed(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": [{"name": "t"}]},
        }

        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                text=f"event: message\ndata: {json.dumps(payload)}\n\n",
            )

        with _client_factory(handler):
            tools = asyncio.run(mcp_client.list_tools("https://mcp.example.com"))
        assert tools == [{"name": "t"}]

    def test_server_error_object_raises(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32601, "message": "no such method"},
                },
            )

        with _client_factory(handler):
            with pytest.raises(McpError, match="-32601"):
                asyncio.run(mcp_client.list_tools("https://mcp.example.com"))

    def test_http_error_status_raises(self):
        def handler(request):
            return httpx.Response(500, text="boom")

        with _client_factory(handler):
            with pytest.raises(McpError, match="HTTP 500"):
                asyncio.run(mcp_client.list_tools("https://mcp.example.com"))

    def test_missing_tools_array_raises(self):
        def handler(request):
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "result": {}}
            )

        with _client_factory(handler):
            with pytest.raises(McpError, match="tools"):
                asyncio.run(mcp_client.list_tools("https://mcp.example.com"))


class TestCallTool:
    def test_sends_name_and_arguments(self):
        seen = {}

        def handler(request):
            seen["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"content": [{"type": "text", "text": "ok"}]},
                },
            )

        with _client_factory(handler):
            result = asyncio.run(
                mcp_client.call_tool(
                    "https://mcp.example.com", "search", {"q": "hours"}
                )
            )
        assert result["content"][0]["text"] == "ok"
        assert seen["body"]["params"] == {
            "name": "search",
            "arguments": {"q": "hours"},
        }

    def test_empty_tool_name_rejected_before_transport(self):
        with pytest.raises(McpError, match="tool_name"):
            asyncio.run(mcp_client.call_tool("https://mcp.example.com", "  "))

    def test_custom_auth_header_passed_verbatim(self):
        seen = {}

        def handler(request):
            seen["key"] = request.headers.get("x-api-key")
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
            )

        with _client_factory(handler):
            asyncio.run(
                mcp_client.call_tool(
                    "https://mcp.example.com",
                    "t",
                    {},
                    auth_header="X-Api-Key",
                    auth_token="raw-key",
                )
            )
        assert seen["key"] == "raw-key"

    def test_non_json_response_raises(self):
        def handler(request):
            return httpx.Response(200, text="<html>nope</html>")

        with _client_factory(handler):
            with pytest.raises(McpError, match="non-JSON"):
                asyncio.run(mcp_client.call_tool("https://mcp.example.com", "t"))
