"""Sales-only send_email behind SEND_EMAIL_ENABLED (default off).

Proves: the flag is off by default; an off flag cannot send; a non-Sales
department cannot send even when the flag is on in tests. Production Gmail
is reached only through the existing approve → claim → run_tool path.
"""

import asyncio
import base64
import os
from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import os_tool_executions as router_mod
from backend.services import gmail_connector, os_tool_executions as svc
from backend.services import os_tools
from backend.services.agent_os_gate import require_agent_os_access
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase_store import FakeSupabase
from backend.tests.test_gmail_send_message import FakeGmailPort, rfc822_msgid_for

CLIENT = "11111111-1111-1111-1111-111111111111"
EXEC_ID = "22222222-2222-2222-2222-222222222222"
OWNER = {"tenant_id": CLIENT, "role": "owner", "email": "maya@sunsetauto.test"}


def _pending_row(**overrides):
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
            "to": "sarah@example.com",
            "subject": "Following up",
            "body": "Hi Sarah",
        },
        "policy_reason": "level 2 requires approval",
        "attempts": 0,
        "created_at": "2026-08-28T10:00:00Z",
    }
    row.update(overrides)
    return row


def _pending_db(**overrides):
    return FakeSupabase({"os_tool_executions": [_pending_row(**overrides)]})


def _ctx(db, gmail=None, **overrides):
    kwargs = {
        "db": db,
        "client_id": CLIENT,
        "execution_id": EXEC_ID,
        "tool_id": "send_email",
        "input": {"to": "sarah@example.com", "subject": "Hi", "body": "Hello"},
        "agent_id": "sales",
        "approved_by": "maya@sunsetauto.test",
        "port": gmail,
    }
    kwargs.update(overrides)
    return os_tools.ToolContext(**kwargs)


def _client():
    app.dependency_overrides[_get_current_tenant] = lambda: OWNER
    app.dependency_overrides[require_agent_os_access] = lambda: OWNER
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


# --- flag defaults off -------------------------------------------------------


def test_send_email_enabled_defaults_off(monkeypatch):
    monkeypatch.delenv("SEND_EMAIL_ENABLED", raising=False)
    assert os_tools.send_email_enabled() is False
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "0")
    assert os_tools.send_email_enabled() is False
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "false")
    assert os_tools.send_email_enabled() is False
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    assert os_tools.send_email_enabled() is True


def test_flag_off_run_tool_does_not_call_gmail(monkeypatch):
    monkeypatch.delenv("SEND_EMAIL_ENABLED", raising=False)
    db = _pending_db()
    gmail = FakeGmailPort()
    sends = []

    def _should_not_send(*args, **kwargs):
        sends.append(kwargs)
        raise AssertionError("gmail_connector.send_message must not run when the flag is off")

    svc.claim_for_execution(db, CLIENT, EXEC_ID)
    with patch.object(gmail_connector, "send_message", _should_not_send), patch.object(
        gmail_connector, "find_message_id_by_rfc822_msgid", return_value=None
    ):
        outcome = asyncio.run(os_tools.run_tool(_ctx(db, gmail)))

    assert outcome["refused"] is True
    assert "defaults off" in outcome["reason"]
    assert outcome["executed"] is False
    assert gmail.sends == []
    assert sends == []
    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert row["status"] == "running"
    assert row.get("finished_at") in (None, "")


def test_flag_off_approve_does_not_claim_or_send(monkeypatch):
    monkeypatch.delenv("SEND_EMAIL_ENABLED", raising=False)
    db = _pending_db()
    client = _client()
    sends = []

    def _should_not_send(*args, **kwargs):
        sends.append(kwargs)
        raise AssertionError("approve must not send when the flag is off")

    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            gmail_connector, "send_message", _should_not_send
        ), patch.object(
            router_mod.agent_sdk_client, "approve_action_sync", side_effect=AssertionError("engine")
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 403
    assert "defaults off" in resp.json()["detail"]
    assert sends == []
    row = db.rows("os_tool_executions")[0]
    assert row["status"] == "pending_approval"
    assert row.get("finished_at") in (None, "")


# --- Sales-only --------------------------------------------------------------


def test_flag_on_non_sales_cannot_send(monkeypatch):
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _pending_db(agent_id="marketing")
    gmail = FakeGmailPort()
    sends = []

    def _should_not_send(*args, **kwargs):
        sends.append(kwargs)
        raise AssertionError("non-Sales must not reach Gmail")

    svc.claim_for_execution(db, CLIENT, EXEC_ID)
    with patch.object(gmail_connector, "send_message", _should_not_send):
        outcome = asyncio.run(os_tools.run_tool(_ctx(db, gmail, agent_id="marketing")))

    assert outcome["refused"] is True
    assert "Sales department" in outcome["reason"]
    assert gmail.sends == []
    assert sends == []


def test_flag_on_sales_approve_claim_execute_uses_gmail(monkeypatch):
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _pending_db(agent_id="sales")
    client = _client()
    sends = []

    def fake_find(tenant_id, msgid):
        return None

    def fake_send(db_arg, tenant_id, **kwargs):
        sends.append({"tenant_id": tenant_id, **kwargs})
        return {"success": True, "detail": "sent", "message_id": "gmail-1", "thread_id": "t1"}

    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            gmail_connector, "find_message_id_by_rfc822_msgid", fake_find
        ), patch.object(gmail_connector, "send_message", fake_send), patch.object(
            router_mod.agent_sdk_client, "approve_action_sync", side_effect=AssertionError("engine")
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_decided"] is False
    assert body["execution"]["status"] == "succeeded"
    assert len(sends) == 1
    assert sends[0]["to"] == "sarah@example.com"
    assert sends[0]["rfc822_msgid"] == rfc822_msgid_for(EXEC_ID)
    assert sends[0]["tenant_id"] == CLIENT


def test_successful_sales_send_records_approved_state_and_owner(monkeypatch):
    """A flag-on Sales send must persist the approval axis, not leave pending/null."""
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _pending_db(agent_id="sales")
    client = _client()

    def fake_send(db_arg, tenant_id, **kwargs):
        return {"success": True, "detail": "sent", "message_id": "gmail-1"}

    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db), patch.object(
            gmail_connector, "find_message_id_by_rfc822_msgid", return_value=None
        ), patch.object(gmail_connector, "send_message", fake_send), patch.object(
            router_mod.agent_sdk_client, "approve_action_sync", side_effect=AssertionError("engine")
        ):
            resp = client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve")
    finally:
        _teardown()

    assert resp.status_code == 200
    row = resp.json()["execution"]
    assert row["status"] == "succeeded"
    assert row["approval_state"] == "approved"
    assert row["approved_by"] == OWNER["email"]
    assert row["approved_by"] not in (None, "")
    assert row["approval_state"] not in {"pending", "not_required"}
    stored = db.rows("os_tool_executions")[0]
    assert stored["status"] == "succeeded"
    assert stored["approval_state"] == "approved"
    assert stored["approved_by"] == OWNER["email"]
    assert stored["approval_state"] not in {"pending", "not_required"}


# --- connector send + rfc822 adopt -------------------------------------------


def test_gmail_send_message_stamps_rfc822_msgid():
    captured = {}

    def fake_api_post(tenant_id, path, json_body):
        captured["path"] = path
        captured["body"] = json_body
        return {"id": "gmail-9", "threadId": "thread-9"}

    result = None
    with patch.object(gmail_connector, "_api_post", side_effect=fake_api_post):
        result = gmail_connector.send_message(
            db=object(),
            tenant_id=CLIENT,
            to="sarah@example.com",
            subject="Hi",
            body_html="<p>Hello</p>",
            rfc822_msgid="aos-abc@actions.agentnexlify",
        )

    assert result["success"] is True
    assert result["message_id"] == "gmail-9"
    assert captured["path"] == "/messages/send"
    raw_text = base64.urlsafe_b64decode(captured["body"]["raw"] + "===").decode()
    assert "Message-ID: <aos-abc@actions.agentnexlify>" in raw_text
    assert "sarah@example.com" in raw_text


def test_find_message_id_by_rfc822_msgid_queries_gmail():
    with patch.object(
        gmail_connector,
        "_api_get",
        return_value={"messages": [{"id": "gmail-adopted"}]},
    ) as mock_get:
        found = gmail_connector.find_message_id_by_rfc822_msgid(
            CLIENT, "<aos-abc@actions.agentnexlify>"
        )
    assert found == "gmail-adopted"
    assert mock_get.call_args.kwargs["params"]["q"] == "rfc822msgid:aos-abc@actions.agentnexlify"


def test_gmail_mailbox_port_adopts_instead_of_sending(monkeypatch):
    monkeypatch.setenv("SEND_EMAIL_ENABLED", "1")
    db = _pending_db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)
    sends = []

    def fake_find(tenant_id, msgid):
        return "gmail-existing"

    def fake_send(*args, **kwargs):
        sends.append(kwargs)
        raise AssertionError("adopt path must not send")

    port = os_tools.GmailMailboxPort(CLIENT, db)
    with patch.object(gmail_connector, "find_message_id_by_rfc822_msgid", fake_find), patch.object(
        gmail_connector, "send_message", fake_send
    ):
        outcome = asyncio.run(os_tools.run_tool(_ctx(db, port)))

    assert outcome["adopted"] is True
    assert outcome["executed"] is False
    assert sends == []
    assert svc.get_tool_execution(db, CLIENT, EXEC_ID)["status"] == "succeeded"
