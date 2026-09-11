"""Regression coverage for #801 send_email approval HTTP semantics."""

import asyncio

import pytest
from fastapi import HTTPException

from backend.routers import os_tool_executions as router_mod

EXECUTION_ID = "22222222-2222-2222-2222-222222222222"
CLIENT_ID = "11111111-1111-1111-1111-111111111111"
CLAIMS = {
    "tenant_id": CLIENT_ID,
    "role": "owner",
    "email": "owner@example.test",
}


def _row(status: str = "pending_approval") -> dict:
    return {
        "id": EXECUTION_ID,
        "client_id": CLIENT_ID,
        "agent_id": "sales",
        "tool_id": "send_email",
        "status": status,
        "approval_state": "pending",
        "risk_level": 2,
        "mutating": True,
        "requires_approval": True,
        "input": {
            "to": "customer@example.test",
            "subject": "Following up",
            "body": "Hello",
        },
        "policy_reason": "level 2 requires approval",
        "attempts": 0,
        "created_at": "2026-09-11T12:00:00Z",
    }


def _wire(monkeypatch, outcome: dict, final_row: dict | None = None) -> None:
    db = object()
    pending = _row()
    claimed = {**pending, "status": "running", "approval_state": "approved"}
    current = final_row or claimed

    monkeypatch.setattr(router_mod, "get_service_supabase", lambda: db)
    monkeypatch.setattr(
        router_mod.os_tool_executions,
        "get_tool_execution",
        lambda _db, _client_id, _execution_id: current,
    )
    monkeypatch.setattr(
        router_mod.os_tool_executions,
        "validate_before_claim",
        lambda _db, _client_id, _execution_id: (pending, None),
    )
    monkeypatch.setattr(
        router_mod.os_tool_executions,
        "claim_for_execution",
        lambda _db, _client_id, _execution_id, _actor: claimed,
    )
    monkeypatch.setattr(router_mod.os_tools, "refuse_send_email", lambda **_kwargs: None)
    monkeypatch.setattr(
        router_mod.os_tools,
        "production_send_email_port",
        lambda _client_id, _db: object(),
    )

    async def _run_tool(_ctx):
        return outcome

    monkeypatch.setattr(router_mod.os_tools, "run_tool", _run_tool)


def test_unknown_send_returns_502_and_never_looks_successful(monkeypatch):
    _wire(
        monkeypatch,
        {
            "executed": True,
            "adopted": False,
            "unknown": True,
            "failed": False,
        },
        final_row={
            **_row("running"),
            "error": {"code": "engine_unavailable"},
            "finished_at": None,
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.approve_tool_execution(EXECUTION_ID, CLAIMS, None))

    assert exc_info.value.status_code == 502
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "send_outcome_unknown"


def test_known_gmail_failure_returns_non_2xx_and_preserves_provider_status(monkeypatch):
    _wire(
        monkeypatch,
        {
            "executed": True,
            "adopted": False,
            "unknown": False,
            "failed": True,
            "status_code": 503,
        },
        final_row={
            **_row("failed"),
            "error": {"code": "gmail_api_error", "statusCode": 503},
            "finished_at": "2026-09-11T12:01:00Z",
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(router_mod.approve_tool_execution(EXECUTION_ID, CLAIMS, None))

    assert exc_info.value.status_code >= 400
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "gmail_api_error"
    assert detail["provider_status_code"] == 503


def test_successful_send_keeps_existing_success_response(monkeypatch):
    outcome = {
        "executed": True,
        "adopted": False,
        "unknown": False,
        "failed": False,
        "result": {"messageId": "gmail-123"},
    }
    succeeded = {
        **_row("succeeded"),
        "result": {"messageId": "gmail-123"},
        "finished_at": "2026-09-11T12:01:00Z",
    }
    _wire(monkeypatch, outcome, final_row=succeeded)

    response = asyncio.run(
        router_mod.approve_tool_execution(EXECUTION_ID, CLAIMS, None)
    )

    assert response["already_decided"] is False
    assert response["execution"]["status"] == "succeeded"
    assert response["outcome"] == outcome
