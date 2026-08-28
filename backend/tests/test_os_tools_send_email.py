"""The first real external action: ``send_email``.

Exercises the actual provider abstraction — ``backend.services.gmail_connector``
— with its functions patched, rather than a parallel fake email stack. The
seam under test is the real one every future integration will use.

What these tests are protecting, in one line: the system must never send an
email the owner did not approve, never send the same one twice, and never
claim it sent something it did not.
"""

import os
from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

import pytest

from backend.dependencies import _get_current_tenant
from backend.main import app
from backend.routers import os_tool_executions as router_mod
from backend.services import gmail_connector, os_tools
from backend.services import os_tool_executions as svc
from backend.services.agent_os_gate import require_agent_os_access
from backend.services.os_tools.send_email import SendEmailInput, rfc822_msgid_for
from backend.tests.conftest import SyncASGITestClient
from backend.tests.fake_supabase_store import FakeSupabase

CLIENT = "11111111-1111-1111-1111-111111111111"
OTHER_CLIENT = "99999999-9999-9999-9999-999999999999"
EXEC_ID = "22222222-2222-2222-2222-222222222222"
OWNER = {"tenant_id": CLIENT, "role": "owner", "email": "maya@sunsetauto.test"}
STAFF = {"tenant_id": CLIENT, "role": "staff", "email": "sam@sunsetauto.test"}
INTRUDER = {"tenant_id": OTHER_CLIENT, "role": "owner", "email": "attacker@example.test"}

SENT_MESSAGE_ID = "gmail-msg-1"


def _pending_row(**overrides):
    row = {
        "id": EXEC_ID,
        "client_id": CLIENT,
        "agent_id": "sales",
        "engine_run_id": "engine_run_1",
        "tool_id": "send_email",
        "risk_level": 2,
        "mutating": True,
        "requires_approval": True,
        "approval_state": "pending",
        "status": "pending_approval",
        "input": {
            "to": "sarah@example.com",
            "subject": "Following up on your brake quote",
            "body": "Hi Sarah,\n\nJust following up on the quote.",
        },
        "policy_reason": "level 2 requires approval",
        "attempts": 0,
        "created_at": "2026-08-28T10:00:00Z",
    }
    row.update(overrides)
    return row


def _db(**overrides):
    return FakeSupabase({"os_tool_executions": [_pending_row(**overrides)]})


def _client(claims=OWNER):
    app.dependency_overrides[_get_current_tenant] = lambda: claims
    app.dependency_overrides[require_agent_os_access] = lambda: claims
    return SyncASGITestClient(app)


def _teardown():
    app.dependency_overrides.pop(_get_current_tenant, None)
    app.dependency_overrides.pop(require_agent_os_access, None)


class _Gmail:
    """Records what the provider was asked to do, and what it answered.

    Stands in for the network, not for the connector: the module functions
    under patch are the real ones the tool calls in production.
    """

    def __init__(self, *, connected=True, send=None, message=None, existing=None, raises=None):
        self.connected = connected
        self.send_result = send or {
            "success": True,
            "detail": "sent",
            "message_id": SENT_MESSAGE_ID,
            "thread_id": "gmail-thread-1",
        }
        self.message = message
        self.existing = existing
        self.raises = raises
        self.sends: list[dict] = []
        self.lookups: list[str] = []

    def is_connected(self, tenant_id):
        return self.connected

    def find_message_id_by_rfc822_msgid(self, tenant_id, msgid):
        self.lookups.append(msgid)
        return self.existing

    def send_message(self, db, tenant_id, **kwargs):
        self.sends.append({"tenant_id": tenant_id, **kwargs})
        if self.raises:
            raise self.raises
        return self.send_result

    def get_message(self, tenant_id, message_id):
        return self.message


def _patched(gmail: _Gmail, db):
    """Patch the real connector functions + the router's db handle."""
    return (
        patch.object(gmail_connector, "is_connected", gmail.is_connected),
        patch.object(
            gmail_connector,
            "find_message_id_by_rfc822_msgid",
            gmail.find_message_id_by_rfc822_msgid,
        ),
        patch.object(gmail_connector, "send_message", gmail.send_message),
        patch.object(gmail_connector, "get_message", gmail.get_message),
        patch.object(router_mod, "get_service_supabase", return_value=db),
    )


def _approve(gmail: _Gmail, db, claims=OWNER, times=1):
    client = _client(claims)
    patches = _patched(gmail, db)
    responses = []
    try:
        for p in patches:
            p.start()
        for _ in range(times):
            responses.append(client.post(f"/api/v1/os/tool-executions/{EXEC_ID}/approve"))
    finally:
        for p in patches:
            p.stop()
        _teardown()
    return responses


def _delivered(to="sarah@example.com", subject="Following up on your brake quote"):
    """What get_message returns for a message that really is in the mailbox."""
    return {"recipient": to, "subject": subject, "provider_message_id": SENT_MESSAGE_ID}


# --- classification + schema ------------------------------------------------


def test_send_email_is_classified_as_external_communication():
    spec = os_tools.get_tool("send_email")
    assert spec is not None
    assert spec.risk_level == 2
    assert spec.mutating is True
    assert spec.requires_approval is True
    assert spec.required_connectors == ["gmail"]
    assert spec.verify is not None, "an external send must be independently verifiable"


def test_the_engine_and_the_data_plane_agree_on_what_this_tool_is():
    """Parity guard.

    The engine classifies the action; this plane holds the credentials. If the
    two ever disagree about the risk level or the approval requirement, the
    gate could be applied in one place and not the other — so the declarations
    are compared directly.
    """
    declaration = open(
        "agent-service/src/agent-os/actions/tools/send_email.ts", encoding="utf-8"
    ).read()
    spec = os_tools.get_tool("send_email")

    assert 'id: "send_email"' in declaration
    assert "riskLevel: RISK_EXTERNAL_COMMUNICATION" in declaration
    assert "requiresApproval: true" in declaration
    assert "mutating: true" in declaration
    assert 'implementation: "data_plane"' in declaration
    assert 'requiredConnectors: ["gmail"]' in declaration
    assert spec.risk_level == 2 and spec.requires_approval and spec.mutating
    assert spec.required_connectors == ["gmail"]


def test_a_malformed_recipient_is_rejected_by_the_schema():
    with pytest.raises(Exception):
        SendEmailInput(to="not-an-email", subject="hi", body="hi")
    with pytest.raises(Exception):
        SendEmailInput(to="sarah@example.com", subject="", body="hi")
    ok = SendEmailInput(to="  sarah@example.com ", subject=" Hi ", body=" Hello ")
    assert ok.to == "sarah@example.com"
    assert ok.subject == "Hi"


def test_the_message_id_fingerprint_is_stable_and_unique():
    """The duplicate check is only meaningful if this is a function of the id."""
    fingerprint = rfc822_msgid_for(EXEC_ID)

    assert EXEC_ID in fingerprint, "it is derived from the execution, not random"
    assert fingerprint.startswith("aos-")
    assert fingerprint != rfc822_msgid_for("other-execution")
    # Anything that could break the RFC 5322 header is stripped.
    assert rfc822_msgid_for("weird/id with spaces") == "aos-weirdidwithspaces@actions.agentnexlify"


# --- the approval gate ------------------------------------------------------


def test_the_owner_sees_exactly_what_will_be_sent_before_approving():
    """An approval prompt that hides the recipient or the text is not an approval."""
    db = _db()
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db):
            queue = client.get("/api/v1/os/tool-executions?status=pending_approval")
            one = client.get(f"/api/v1/os/tool-executions/{EXEC_ID}")
    finally:
        _teardown()

    assert queue.json()["count"] == 1
    waiting = one.json()
    assert waiting["status"] == "pending_approval"
    assert waiting["tool_id"] == "send_email"
    assert waiting["agent_id"] == "sales", "the owner can see which agent asked"
    assert waiting["input"]["to"] == "sarah@example.com"
    assert waiting["input"]["subject"] == "Following up on your brake quote"
    assert "Just following up" in waiting["input"]["body"]
    assert waiting["risk_level"] == 2


def test_approving_sends_the_email_and_verifies_it():
    gmail = _Gmail(message=_delivered())
    db = _db()

    resp = _approve(gmail, db)[0]

    assert resp.status_code == 200
    execution = resp.json()["execution"]
    assert execution["status"] == "succeeded"
    assert execution["verification_state"] == "passed"
    assert execution["approval_state"] == "approved"
    assert execution["approved_by"] == "maya@sunsetauto.test"
    assert execution["result"]["messageId"] == SENT_MESSAGE_ID
    assert execution["effect"] == {"port": "gmail", "durable": True}
    assert execution["attempts"] == 1

    assert len(gmail.sends) == 1
    sent = gmail.sends[0]
    assert sent["tenant_id"] == CLIENT
    assert sent["to"] == "sarah@example.com"
    assert sent["subject"] == "Following up on your brake quote"
    assert "Just following up" in sent["body_html"]
    assert sent["rfc822_msgid"] == rfc822_msgid_for(EXEC_ID)


def test_rejecting_guarantees_it_is_never_sent():
    gmail = _Gmail()
    db = _db()
    client = _client()
    try:
        with patch.object(router_mod, "get_service_supabase", return_value=db):
            rejected = client.post(
                f"/api/v1/os/tool-executions/{EXEC_ID}/reject",
                json={"reason": "wrong customer"},
            )
    finally:
        _teardown()
    assert rejected.json()["status"] == "denied"

    # A later approval cannot resurrect it.
    resp = _approve(gmail, db)[0]
    assert resp.json()["execution"]["status"] == "denied"
    assert gmail.sends == [], "a rejected action must never reach the provider"


def test_only_an_owner_can_approve_a_send():
    gmail = _Gmail()
    db = _db()
    resp = _approve(gmail, db, claims=STAFF)[0]
    assert resp.status_code == 403
    assert gmail.sends == []


def test_another_tenant_cannot_approve_this_send():
    gmail = _Gmail()
    db = _db()
    resp = _approve(gmail, db, claims=INTRUDER)[0]
    assert resp.status_code == 404, "another tenant's action must not even be visible"
    assert gmail.sends == []
    assert svc.get_tool_execution(db, CLIENT, EXEC_ID)["status"] == "pending_approval"


# --- idempotency ------------------------------------------------------------


def test_approving_twice_sends_exactly_one_email():
    gmail = _Gmail(message=_delivered())
    db = _db()

    first, second = _approve(gmail, db, times=2)

    assert first.json()["already_decided"] is False
    assert second.json()["already_decided"] is True
    assert len(gmail.sends) == 1, "the second approval must not send again"


def test_an_already_completed_action_is_not_sent_again():
    gmail = _Gmail(message=_delivered())
    db = _db(status="succeeded", approval_state="approved", attempts=1)

    resp = _approve(gmail, db)[0]

    assert resp.json()["already_decided"] is True
    assert gmail.sends == []


def test_a_message_already_in_the_mailbox_is_adopted_not_resent():
    """The pre-send fingerprint check: same execution, message already there."""
    gmail = _Gmail(existing="already-sent-id", message=_delivered())
    db = _db()

    resp = _approve(gmail, db)[0]

    execution = resp.json()["execution"]
    assert execution["status"] in ("succeeded", "verification_failed")
    assert execution["result"]["deduplicated"] is True
    assert execution["result"]["messageId"] == "already-sent-id"
    assert gmail.sends == [], "a duplicate must never be sent"
    assert gmail.lookups == [rfc822_msgid_for(EXEC_ID)]


# --- provider failures ------------------------------------------------------


def test_no_connected_mailbox_fails_closed_with_an_actionable_reason():
    gmail = _Gmail(connected=False)
    db = _db()

    resp = _approve(gmail, db)[0]

    execution = resp.json()["execution"]
    assert execution["status"] == "failed"
    assert execution["error"]["code"] == "connector_unavailable"
    assert "Gmail is not connected" in execution["error"]["message"]
    assert execution["verification_state"] == "not_applicable"
    assert gmail.sends == []


def test_expired_provider_auth_is_a_definite_non_send():
    """A 401 from Gmail means the message did not leave. Say exactly that."""
    gmail = _Gmail(send={"success": False, "detail": "gmail api error 401", "status_code": 401})
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "failed"
    assert execution["error"]["code"] == "send_rejected"
    assert execution["verification_state"] == "not_applicable"


def test_an_unknown_send_outcome_is_never_reported_as_sent_or_as_not_sent():
    """A transport failure could have been accepted before the response was lost."""
    gmail = _Gmail(send={"success": False, "detail": "no gmail credentials or send failed"})
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "failed"
    assert execution["error"]["code"] == "send_outcome_unknown"
    assert "unknown" in execution["error"]["message"]


def test_a_raising_provider_is_recorded_as_an_unknown_outcome():
    gmail = _Gmail(raises=TimeoutError("read timed out"))
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "failed"
    assert execution["error"]["code"] == "send_outcome_unknown"
    assert "unknown" in execution["error"]["message"]


# --- verification -----------------------------------------------------------


def test_a_send_that_cannot_be_read_back_is_not_reported_as_verified():
    gmail = _Gmail(message=None)
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "verification_failed"
    assert execution["verification_state"] == "failed"
    assert "unconfirmed" in execution["verification_detail"]
    # Execution and verification stay independently representable: the send
    # did happen, and we say we could not confirm it.
    assert execution["result"]["messageId"] == SENT_MESSAGE_ID


def test_a_message_delivered_to_the_wrong_recipient_fails_verification():
    gmail = _Gmail(message=_delivered(to="someone-else@example.com"))
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "verification_failed"
    assert "other than the approved recipient" in execution["verification_detail"]


def test_a_message_with_the_wrong_subject_fails_verification():
    gmail = _Gmail(message=_delivered(subject="Something else entirely"))
    db = _db()

    execution = _approve(gmail, db)[0].json()["execution"]

    assert execution["status"] == "verification_failed"
    assert "approved subject" in execution["verification_detail"]


# --- audit ------------------------------------------------------------------


def test_the_whole_lifecycle_is_readable_from_the_database():
    gmail = _Gmail(message=_delivered())
    db = _db()
    _approve(gmail, db)

    row = db.rows("os_tool_executions")[0]
    assert row["tool_id"] == "send_email"
    assert row["risk_level"] == 2
    assert row["agent_id"] == "sales"
    assert row["approval_state"] == "approved"
    assert row["approved_by"] == "maya@sunsetauto.test"
    assert row["status"] == "succeeded"
    assert row["verification_state"] == "passed"
    assert row["finished_at"]
    assert row["input"]["to"] == "sarah@example.com"


def test_no_oauth_token_is_ever_written_to_the_execution_record():
    gmail = _Gmail(message=_delivered())
    db = _db()
    _approve(gmail, db)

    serialized = repr(db.rows("os_tool_executions")[0]).lower()
    for secret in ("access_token", "refresh_token", "bearer ", "authorization"):
        assert secret not in serialized


def test_a_level_two_action_that_cannot_be_recorded_is_never_queued():
    """Fail closed: no audit row, no approvable action, nothing sent."""

    class Unwritable(FakeSupabase):
        def table(self, name):
            if name == "os_tool_executions":
                raise RuntimeError("audit table unavailable")
            return super().table(name)

    db = Unwritable({"os_tool_executions": []})
    record = {
        "toolExecutions": [
            {
                "id": EXEC_ID,
                "accountId": CLIENT,
                "toolId": "send_email",
                "riskLevel": 2,
                "mutating": True,
                "requiresApproval": True,
                "status": "pending_approval",
                "input": {"to": "sarah@example.com", "subject": "Hi", "body": "Hello"},
            }
        ]
    }

    with pytest.raises(svc.AuditUnavailableError):
        svc.persist_tool_executions(db, CLIENT, None, record)


def test_a_level_one_action_that_cannot_be_recorded_does_not_break_the_turn():
    """The other half of the contract: internal work stays resilient."""

    class Unwritable(FakeSupabase):
        def table(self, name):
            if name == "os_tool_executions":
                raise RuntimeError("audit table unavailable")
            return super().table(name)

    db = Unwritable({"os_tool_executions": []})
    record = {
        "toolExecutions": [
            {
                "id": EXEC_ID,
                "accountId": CLIENT,
                "toolId": "add_customer_note",
                "riskLevel": 1,
                "mutating": True,
                "requiresApproval": False,
                "status": "succeeded",
                "input": {"customer_id": "lead_1", "note": "hi"},
            }
        ]
    }

    with pytest.raises(RuntimeError) as err:
        svc.persist_tool_executions(db, CLIENT, None, record)
    assert not isinstance(err.value, svc.AuditUnavailableError)


def test_an_unknown_tool_id_cannot_reach_any_provider():
    """An LLM emitting a plausible tool id gets nothing but an audit row."""
    assert os_tools.get_tool("send_sms") is None
    assert os_tools.get_tool("send_email_v2") is None
    assert not os_tools.has_tool("../../etc/passwd")


# --- the data-plane executor's own contract ---------------------------------


def _ctx(tool_id="send_email", payload=None):
    return os_tools.ToolContext(
        db=FakeSupabase({}),
        client_id=CLIENT,
        execution_id=EXEC_ID,
        tool_id=tool_id,
        input=payload
        if payload is not None
        else {"to": "sarah@example.com", "subject": "Hi", "body": "Hello"},
        agent_id="sales",
        approved_by="maya@sunsetauto.test",
    )


@pytest.mark.asyncio
async def test_run_tool_refuses_a_tool_that_is_not_registered():
    outcome, verification = await os_tools.run_tool(_ctx(tool_id="send_carrier_pigeon"))

    assert outcome.status == "failed"
    assert outcome.error["code"] == "unknown_tool"
    assert verification.state == "not_applicable"


@pytest.mark.asyncio
async def test_run_tool_revalidates_the_stored_input_before_touching_a_provider():
    """The stored input crossed a database and possibly a deploy. Never trust it."""
    gmail = _Gmail()
    with patch.object(gmail_connector, "send_message", gmail.send_message):
        outcome, verification = await os_tools.run_tool(
            _ctx(payload={"to": "not-an-email", "subject": "Hi", "body": "Hello"})
        )

    assert outcome.status == "failed"
    assert outcome.error["code"] == "invalid_input"
    assert verification.state == "not_applicable"
    assert gmail.sends == []


@pytest.mark.asyncio
async def test_a_verifier_that_raises_never_upgrades_to_verified():
    gmail = _Gmail()
    patches = [
        patch.object(gmail_connector, "is_connected", gmail.is_connected),
        patch.object(
            gmail_connector,
            "find_message_id_by_rfc822_msgid",
            gmail.find_message_id_by_rfc822_msgid,
        ),
        patch.object(gmail_connector, "send_message", gmail.send_message),
        patch.object(
            gmail_connector,
            "get_message",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("gmail unreachable")),
        ),
    ]
    try:
        for p in patches:
            p.start()
        outcome, verification = await os_tools.run_tool(_ctx())
    finally:
        for p in patches:
            p.stop()

    assert outcome.status == "succeeded"
    assert verification.state == "failed"
    assert "could not be read back" in verification.detail


@pytest.mark.asyncio
async def test_a_failed_send_is_never_reported_as_verified():
    gmail = _Gmail(connected=False)
    patches = [
        patch.object(gmail_connector, "is_connected", gmail.is_connected),
        patch.object(gmail_connector, "send_message", gmail.send_message),
    ]
    try:
        for p in patches:
            p.start()
        outcome, verification = await os_tools.run_tool(_ctx())
    finally:
        for p in patches:
            p.stop()

    assert outcome.status == "failed"
    assert verification.state == "not_applicable"
    assert "nothing to verify" in verification.detail
