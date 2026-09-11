"""Regression coverage for #801 known-vs-unknown Gmail send outcomes."""

import asyncio
from unittest.mock import patch

from backend.services import gmail_connector, os_tool_executions as svc, os_tools
from backend.tests.fake_supabase_store import FakeSupabase

CLIENT = "11111111-1111-1111-1111-111111111111"
EXEC_ID = "22222222-2222-2222-2222-222222222222"


def _db() -> FakeSupabase:
    return FakeSupabase(
        {
            "os_tool_executions": [
                {
                    "id": EXEC_ID,
                    "client_id": CLIENT,
                    "agent_id": "sales",
                    "tool_id": "send_email",
                    "status": "pending_approval",
                    "approval_state": "pending",
                    "risk_level": 2,
                    "mutating": True,
                    "requires_approval": True,
                    "input": {
                        "to": "sarah@example.com",
                        "subject": "Following up",
                        "body": "Hi Sarah",
                    },
                    "policy_reason": "level 2 requires approval",
                    "attempts": 0,
                    "created_at": "2026-08-28T10:00:00Z",
                }
            ]
        }
    )


def _ctx(db: FakeSupabase) -> os_tools.ToolContext:
    return os_tools.ToolContext(
        db=db,
        client_id=CLIENT,
        execution_id=EXEC_ID,
        tool_id="send_email",
        input={"to": "sarah@example.com", "subject": "Following up", "body": "Hi Sarah"},
        agent_id="sales",
        approved_by="maya@sunsetauto.test",
        port=os_tools.GmailMailboxPort(CLIENT, db),
    )


def test_known_gmail_api_failure_becomes_terminal_failed(monkeypatch):
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)

    with patch.object(
        gmail_connector, "find_message_id_by_rfc822_msgid", return_value=None
    ), patch.object(
        gmail_connector,
        "send_message",
        return_value={
            "success": False,
            "detail": "gmail api error 503",
            "status_code": 503,
        },
    ):
        outcome = asyncio.run(os_tools.run_tool(_ctx(db)))

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert outcome == {
        "executed": True,
        "adopted": False,
        "unknown": False,
        "failed": True,
        "status_code": 503,
    }
    assert row["status"] == "failed"
    assert row["error"]["code"] == "gmail_api_error"
    assert row["error"]["statusCode"] == 503
    assert row.get("finished_at") not in (None, "")


def test_credential_or_transport_none_remains_unknown_and_nonterminal(monkeypatch):
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)

    with patch.object(
        gmail_connector, "find_message_id_by_rfc822_msgid", return_value=None
    ), patch.object(
        gmail_connector,
        "send_message",
        return_value={"success": False, "detail": "no gmail credentials or send failed"},
    ):
        outcome = asyncio.run(os_tools.run_tool(_ctx(db)))

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert outcome["executed"] is True
    assert outcome["unknown"] is True
    assert row["status"] == "running"
    assert row["error"]["code"] == "engine_unavailable"
    assert row.get("finished_at") in (None, "")
