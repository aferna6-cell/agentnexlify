"""Minimal MCP (Model Context Protocol) client — Streamable HTTP transport
(enterprise-audit item 5, interop v1).

Speaks the two JSON-RPC methods the v1 integration needs — ``tools/list`` and
``tools/call`` — against MCP servers exposing the Streamable HTTP transport
(single POST endpoint, JSON or SSE-framed responses). This one client buys
the whole MCP tool ecosystem instead of a per-connector build, and positions
the Agent OS for A2A-style interop later.

Scope guardrails:
- Outbound only, HTTPS-or-localhost URLs, bounded timeouts and response size.
- No sessions/notifications/sampling — request/response only.
- Callers catch McpError; nothing here touches the database.
"""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_S = 20.0
_MAX_RESPONSE_BYTES = 512_000
PROTOCOL_VERSION = "2025-06-18"


class McpError(RuntimeError):
    """A transport, protocol, or server-reported MCP failure."""


def validate_server_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("https://"):
        return url
    if url.startswith("http://localhost") or url.startswith("http://127.0.0.1"):
        return url  # local development servers
    raise McpError("MCP server URL must be https:// (or localhost for dev)")


def _parse_body(response: httpx.Response) -> dict:
    """Extract the JSON-RPC payload from a JSON or SSE-framed response."""
    if len(response.content) > _MAX_RESPONSE_BYTES:
        raise McpError("MCP response too large")
    content_type = response.headers.get("content-type", "")
    text = response.text
    if "text/event-stream" in content_type:
        # Streamable HTTP may frame the reply as SSE; the JSON-RPC response
        # is the last `data:` line.
        data_lines = [
            line[5:].strip()
            for line in text.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            raise McpError("MCP SSE response carried no data frames")
        text = data_lines[-1]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as err:
        raise McpError(f"MCP server returned non-JSON response: {err}") from err
    if not isinstance(payload, dict):
        raise McpError("MCP response is not a JSON-RPC object")
    return payload


async def _rpc(
    url: str,
    headers: dict[str, str],
    method: str,
    params: dict | None = None,
) -> Any:
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(url, json=request, headers=headers)
    except httpx.HTTPError as err:
        raise McpError(f"MCP transport error: {str(err)[:200]}") from err
    if response.status_code >= 400:
        raise McpError(
            f"MCP server returned HTTP {response.status_code}: "
            f"{response.text[:200]}"
        )
    payload = _parse_body(response)
    if payload.get("error"):
        error = payload["error"]
        raise McpError(
            f"MCP error {error.get('code')}: {str(error.get('message'))[:200]}"
        )
    return payload.get("result")


def _headers(auth_header: str | None, auth_token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
    }
    if auth_token:
        name = (auth_header or "Authorization").strip() or "Authorization"
        value = auth_token
        if name.lower() == "authorization" and not value.lower().startswith(
            ("bearer ", "basic ")
        ):
            value = f"Bearer {value}"
        headers[name] = value
    return headers


async def list_tools(
    url: str, auth_header: str | None = None, auth_token: str | None = None
) -> list[dict]:
    """Return the server's tool definitions [{name, description, inputSchema}]."""
    result = await _rpc(
        validate_server_url(url), _headers(auth_header, auth_token), "tools/list"
    )
    tools = (result or {}).get("tools")
    if not isinstance(tools, list):
        raise McpError("MCP tools/list result missing 'tools' array")
    return [t for t in tools if isinstance(t, dict)]


async def call_tool(
    url: str,
    tool_name: str,
    arguments: dict | None = None,
    auth_header: str | None = None,
    auth_token: str | None = None,
) -> dict:
    """Invoke one tool; returns the MCP result ({content: [...], isError})."""
    if not tool_name or not tool_name.strip():
        raise McpError("tool_name is required")
    result = await _rpc(
        validate_server_url(url),
        _headers(auth_header, auth_token),
        "tools/call",
        {"name": tool_name.strip(), "arguments": arguments or {}},
    )
    if not isinstance(result, dict):
        raise McpError("MCP tools/call returned no result object")
    return result
