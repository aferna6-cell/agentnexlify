"""MCP router (enterprise-audit item 5) — gating, token hygiene, proxying."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.routers import os_mcp
from backend.routers.os_mcp import ServerIn, ToolCallIn
from backend.services.mcp_client import McpError

_CLAIMS = {"tenant_id": "t1"}


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows, sink=None):
        self._rows = rows
        self._sink = sink if sink is not None else []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self._sink.append((name, args))
            if name == "execute":
                return _Result(self._rows)
            return self

        return _method


def _db(rows, sink=None):
    db = MagicMock()
    db.table.side_effect = lambda name: _Query(rows, sink)
    return db


def _flag(value: bool):
    return patch.object(os_mcp, "flag_enabled", return_value=value)


class TestFlagGate:
    def test_disabled_flag_403s_everything(self):
        with _flag(False):
            with pytest.raises(HTTPException) as err:
                asyncio.run(os_mcp.list_servers(claims=_CLAIMS))
        assert err.value.status_code == 403


class TestServerCrud:
    def test_create_returns_row_without_token(self):
        row = {
            "id": "s1",
            "name": "crm",
            "url": "https://mcp.example.com",
            "auth_token": "secret",
        }
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([row])
        ):
            out = asyncio.run(
                os_mcp.create_server(
                    ServerIn(
                        name="crm",
                        url="https://mcp.example.com",
                        auth_token="secret",
                    ),
                    claims=_CLAIMS,
                )
            )
        assert "auth_token" not in out

    def test_create_rejects_plain_http(self):
        with _flag(True):
            with pytest.raises(HTTPException) as err:
                asyncio.run(
                    os_mcp.create_server(
                        ServerIn(name="x", url="http://mcp.example.com"),
                        claims=_CLAIMS,
                    )
                )
        assert err.value.status_code == 422

    def test_list_servers_returns_rows(self):
        with _flag(True), patch.object(
            os_mcp,
            "get_service_supabase",
            return_value=_db([{"id": "s1", "name": "crm"}]),
        ):
            out = asyncio.run(os_mcp.list_servers(claims=_CLAIMS))
        assert out["servers"][0]["id"] == "s1"

    def test_delete_missing_404s(self):
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([])
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(os_mcp.delete_server("nope", claims=_CLAIMS))
        assert err.value.status_code == 404


class TestToolProxy:
    _server = {
        "id": "s1",
        "url": "https://mcp.example.com",
        "auth_header": "Authorization",
        "auth_token": "tok",
        "enabled": True,
    }

    def test_tools_proxied(self):
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([self._server])
        ), patch.object(
            os_mcp.mcp_client,
            "list_tools",
            new=AsyncMock(return_value=[{"name": "search"}]),
        ) as listed:
            out = asyncio.run(os_mcp.list_server_tools("s1", claims=_CLAIMS))
        assert out["tools"] == [{"name": "search"}]
        listed.assert_awaited_once_with("https://mcp.example.com", "Authorization", "tok")

    def test_disabled_server_422s(self):
        row = {**self._server, "enabled": False}
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([row])
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(os_mcp.list_server_tools("s1", claims=_CLAIMS))
        assert err.value.status_code == 422

    def test_transport_failure_502s(self):
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([self._server])
        ), patch.object(
            os_mcp.mcp_client,
            "list_tools",
            new=AsyncMock(side_effect=McpError("down")),
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(os_mcp.list_server_tools("s1", claims=_CLAIMS))
        assert err.value.status_code == 502

    def test_call_proxies_tool_and_arguments(self):
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([self._server])
        ), patch.object(
            os_mcp.mcp_client,
            "call_tool",
            new=AsyncMock(return_value={"content": []}),
        ) as called:
            out = asyncio.run(
                os_mcp.call_server_tool(
                    "s1", ToolCallIn(tool="search", arguments={"q": "x"}),
                    claims=_CLAIMS,
                )
            )
        assert out["result"] == {"content": []}
        called.assert_awaited_once_with(
            "https://mcp.example.com", "search", {"q": "x"}, "Authorization", "tok"
        )

    def test_call_transport_failure_502s(self):
        with _flag(True), patch.object(
            os_mcp, "get_service_supabase", return_value=_db([self._server])
        ), patch.object(
            os_mcp.mcp_client,
            "call_tool",
            new=AsyncMock(side_effect=McpError("nope")),
        ):
            with pytest.raises(HTTPException) as err:
                asyncio.run(
                    os_mcp.call_server_tool(
                        "s1", ToolCallIn(tool="t"), claims=_CLAIMS
                    )
                )
        assert err.value.status_code == 502
