"""Tenant MCP server management + owner-invoked tool calls
(enterprise-audit item 5, interop v1).

Platform-gated by ``os_mcp_enabled`` (off by default). Tool calls are
owner-initiated from the dashboard — a human is in the loop on every
side-effecting call, preserving the propose-only trust model. auth_token is
write-only: accepted on create/update, never returned.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.dependencies import _get_current_tenant
from backend.models.database import get_service_supabase
from backend.services import mcp_client
from backend.services.platform_flags import flag_enabled
from backend.services.tenant_scope import tenant_select, tenant_table

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/os/mcp", tags=["agent-os"])

_SERVER_CAP = 10
_PUBLIC_COLUMNS = "id, name, url, auth_header, enabled, created_at, updated_at"


class ServerIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=8, max_length=500)
    auth_header: str = Field(default="Authorization", max_length=100)
    auth_token: str | None = Field(default=None, max_length=2000)
    enabled: bool = True


class ToolCallIn(BaseModel):
    tool: str = Field(min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_flag() -> None:
    if not flag_enabled("os_mcp_enabled"):
        raise HTTPException(
            status_code=403, detail="MCP integration is not enabled on this platform"
        )


def _load_server(db, tenant_id: str, server_id: str) -> dict:
    rows = (
        tenant_select(db, "tenant_mcp_servers", tenant_id, "*")
        .eq("id", server_id)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return rows[0]


@router.get("/servers")
async def list_servers(claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    rows = (
        tenant_select(db, "tenant_mcp_servers", claims["tenant_id"], _PUBLIC_COLUMNS)
        .order("created_at", desc=False)
        .limit(_SERVER_CAP)
        .execute()
    ).data or []
    return {"servers": rows}


@router.post("/servers")
async def create_server(body: ServerIn, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    try:
        mcp_client.validate_server_url(body.url)
    except mcp_client.McpError as err:
        raise HTTPException(status_code=422, detail=str(err))
    db = get_service_supabase()
    existing = (
        tenant_select(db, "tenant_mcp_servers", claims["tenant_id"], "id")
        .limit(_SERVER_CAP)
        .execute()
    ).data or []
    if len(existing) >= _SERVER_CAP:
        raise HTTPException(status_code=422, detail="MCP server limit reached")
    created = (
        tenant_table(db, "tenant_mcp_servers", claims["tenant_id"])
        .insert(
            {
                "name": body.name.strip(),
                "url": body.url.strip(),
                "auth_header": body.auth_header.strip() or "Authorization",
                "auth_token": body.auth_token,
                "enabled": body.enabled,
            }
        )
        .execute()
    )
    row = dict(created.data[0])
    row.pop("auth_token", None)
    return row


@router.delete("/servers/{server_id}")
async def delete_server(server_id: str, claims: dict = Depends(_get_current_tenant)):
    _require_flag()
    db = get_service_supabase()
    deleted = (
        tenant_table(db, "tenant_mcp_servers", claims["tenant_id"])
        .delete()
        .eq("id", server_id)
        .execute()
    )
    if not deleted.data:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"deleted": True}


@router.get("/servers/{server_id}/tools")
async def list_server_tools(
    server_id: str, claims: dict = Depends(_get_current_tenant)
):
    _require_flag()
    db = get_service_supabase()
    server = _load_server(db, claims["tenant_id"], server_id)
    if not server.get("enabled"):
        raise HTTPException(status_code=422, detail="MCP server is disabled")
    try:
        tools = await mcp_client.list_tools(
            server["url"], server.get("auth_header"), server.get("auth_token")
        )
    except mcp_client.McpError as err:
        raise HTTPException(status_code=502, detail=str(err))
    return {"server_id": server_id, "tools": tools}


@router.post("/servers/{server_id}/call")
async def call_server_tool(
    server_id: str, body: ToolCallIn, claims: dict = Depends(_get_current_tenant)
):
    """Owner-invoked tool call — the human IS the approval gate here."""
    _require_flag()
    db = get_service_supabase()
    server = _load_server(db, claims["tenant_id"], server_id)
    if not server.get("enabled"):
        raise HTTPException(status_code=422, detail="MCP server is disabled")
    try:
        result = await mcp_client.call_tool(
            server["url"],
            body.tool,
            body.arguments,
            server.get("auth_header"),
            server.get("auth_token"),
        )
    except mcp_client.McpError as err:
        raise HTTPException(status_code=502, detail=str(err))
    tenant_table(db, "tenant_mcp_servers", claims["tenant_id"]).update(
        {"updated_at": _now()}
    ).eq("id", server_id).execute()
    return {"server_id": server_id, "tool": body.tool, "result": result}
