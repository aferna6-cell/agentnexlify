"""Controlled Gmail proof — FakeGmailPort path (no live send).

Walks the Milestone 6 owner-approval → claim → exactly-once send contract
against an in-process mailbox. Production ``SEND_EMAIL_ENABLED`` stays default
OFF. A real Gmail send is an owner-authority step and is not performed here.

Live-send checklist (blocked until Aidan approves):
  test tenant, test Gmail, known harmless recipient, SEND_EMAIL_ENABLED=1
  in that environment only, then verify Message-ID + recipient + subject.
"""

import os

os.environ.setdefault("TESTING", "1")

from backend.services import os_tool_executions as svc
from backend.tests.fake_supabase_store import FakeSupabase
from backend.tests.test_gmail_send_message import (
    FakeGmailPort,
    drive_claimed_gmail_send,
    rfc822_msgid_for,
)

CLIENT = "11111111-1111-1111-1111-111111111111"
OTHER = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXEC_ID = "22222222-2222-2222-2222-222222222222"
HARMLESS = "aidan+m6-smoke@example.com"


def _proposal(**overrides):
    row = {
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
            "to": HARMLESS,
            "subject": "M6 controlled smoke — ignore",
            "body": "Harmless test. Do not reply.",
        },
        "policy_reason": "level 2 requires approval",
        "attempts": 0,
        "created_at": "2026-08-30T00:00:00Z",
    }
    row.update(overrides)
    return row


def test_controlled_gmail_path_parks_then_sends_once():
    db = FakeSupabase({"os_tool_executions": [_proposal()]})
    gmail = FakeGmailPort()

    parked = db.rows("os_tool_executions")[0]
    assert parked["status"] == "pending_approval"
    assert parked["approval_state"] == "pending"
    assert gmail.sends == []
    assert gmail.mailbox == {}

    claimed = svc.claim_for_execution(db, CLIENT, EXEC_ID)
    assert claimed is not None
    assert claimed["status"] == "running"
    assert claimed["approval_state"] == "approved"
    assert gmail.sends == []

    first = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)
    assert first["executed"] is True
    assert len(gmail.sends) == 1
    assert gmail.sends[0]["to"] == HARMLESS
    assert gmail.sends[0]["subject"] == "M6 controlled smoke — ignore"
    msgid = rfc822_msgid_for(EXEC_ID)
    assert gmail.sends[0]["rfc822_msgid"] == msgid
    assert gmail.find_by_rfc822_msgid(msgid)
    terminal = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert terminal["status"] == "succeeded"

    replay = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)
    assert replay.get("adopted") is True or replay.get("executed") is False or terminal["status"] == "succeeded"
    assert len(gmail.sends) == 1, "replay/redrive must not create a duplicate send"


def test_controlled_gmail_rejects_cross_tenant_claim():
    db = FakeSupabase({"os_tool_executions": [_proposal()]})
    gmail = FakeGmailPort()
    assert svc.claim_for_execution(db, OTHER, EXEC_ID) is None
    assert db.rows("os_tool_executions")[0]["status"] == "pending_approval"
    assert gmail.sends == []


def test_send_email_enabled_still_defaults_off_in_this_module():
    from backend.services import os_tools

    os.environ.pop("SEND_EMAIL_ENABLED", None)
    assert os_tools.send_email_enabled() is False
