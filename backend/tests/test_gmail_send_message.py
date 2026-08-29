"""B-prep contracts that block Slice B (Gmail send).

Test-only. No ``send_email`` production path, no ``gmail_connector.send_message``,
no ``communication_actions``. The harness here is the spec B must satisfy:

1. After ``claim_for_execution``, a transport timeout / lost Gmail response
   stays non-terminal (no ``finished_at``, not failed-as-sent). A later
   re-drive rfc822msgid-adopts and must not send a second message.
2. Engine Zod ``.email()`` vs Python ``normalize_email``: a Zod-pass /
   Python-fail must not burn the only approval claim.
3. ``os_tools.run_tool`` (or the claim-gated stand-in) is unreachable
   without a prior claim — the provider must not execute.

``_run_data_plane_tool`` is not on main after #694. When B adds it, it must
not always write terminal ``failed`` / ``succeeded`` / ``verification_failed``
plus ``finished_at`` for an unknown send outcome.
"""

import importlib
import importlib.util
import os
import re
from pathlib import Path

os.environ.setdefault("TESTING", "1")

import pytest

from backend.services import os_tool_executions as svc
from backend.tests.fake_supabase_store import FakeSupabase


def _load_normalize_email():
    """Load recipients.py without importing ``os_actions`` (package init pulls Supabase)."""
    path = Path(__file__).resolve().parents[1] / "services" / "os_actions" / "recipients.py"
    spec = importlib.util.spec_from_file_location("bprep_os_actions_recipients", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.normalize_email


normalize_email = _load_normalize_email()

CLIENT = "11111111-1111-1111-1111-111111111111"
EXEC_ID = "22222222-2222-2222-2222-222222222222"

# Zod 3/4 default ``z.string().email()`` / ``z.email()`` regex. Mirrors the
# engine schema #693 declared on ``send_email`` (`to: z.string().email()`).
# Kept test-local until that file exists on main.
_ENGINE_ZOD_EMAIL_RE = re.compile(
    r"^(?!\.)(?!.*\.\.)([A-Z0-9_'+\-\.]*)[A-Z0-9_+-]"
    r"@([A-Z0-9][A-Z0-9\-]*\.)+[A-Z]{2,}$",
    re.IGNORECASE,
)

# Zod accepts the apostrophe; Python ``normalize_email`` does not.
ZOD_PASS_PYTHON_FAIL = "o'reilly@example.com"

TERMINAL = set(svc.TERMINAL_STATUSES)


def engine_zod_email_accepts(raw) -> bool:
    """Engine-side email gate: Zod ``.email()``, no trim."""
    if not isinstance(raw, str):
        return False
    return _ENGINE_ZOD_EMAIL_RE.fullmatch(raw) is not None


def rfc822_msgid_for(execution_id: str) -> str:
    """Test-local copy of the #693 fingerprint. Not a production helper."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "", str(execution_id))
    return f"aos-{safe}@actions.agentnexlify"


class FakeGmailPort:
    """In-process mailbox. Stands in for a future Gmail port — not the connector."""

    def __init__(self):
        self.sends: list[dict] = []
        self.mailbox: dict[str, str] = {}
        self.mode = "ok"

    def find_by_rfc822_msgid(self, msgid: str) -> str | None:
        return self.mailbox.get(msgid)

    def send(self, **kwargs) -> dict | None:
        msgid = kwargs["rfc822_msgid"]
        if self.mode == "timeout":
            raise TimeoutError("gmail transport timed out")
        self.sends.append(dict(kwargs))
        provider_id = f"gmail-{len(self.sends)}"
        self.mailbox[msgid] = provider_id
        if self.mode == "accept_then_lose":
            return None
        return {"success": True, "message_id": provider_id}


def _pending_send_row(**overrides):
    row = {
        "id": EXEC_ID,
        "client_id": CLIENT,
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
    return FakeSupabase({"os_tool_executions": [_pending_send_row(**overrides)]})


def _optional_os_tools():
    if importlib.util.find_spec("backend.services.os_tools") is None:
        return None
    return importlib.import_module("backend.services.os_tools")


def apply_unknown_send_outcome(db, client_id: str, execution_id: str, detail: str):
    """Correct write for a lost/timeout send: stay non-terminal.

    B's ``_run_data_plane_tool`` must take this path for ``send_outcome_unknown``
    instead of always writing a terminal status + ``finished_at``.
    """
    svc.mark_engine_unavailable(db, client_id, execution_id, detail)
    return svc.get_tool_execution(db, client_id, execution_id)


def drive_claimed_gmail_send(db, client_id: str, execution_id: str, gmail: FakeGmailPort):
    """One post-claim send attempt. Lookup first; unknown stays non-terminal.

    Until ``os_tools.run_tool`` exists this *is* the contract. When it lands,
    it must preserve these outcomes.
    """
    row = svc.get_tool_execution(db, client_id, execution_id)
    if row is None or row.get("status") != "running":
        return {"executed": False, "adopted": False, "unknown": False}

    msgid = rfc822_msgid_for(execution_id)
    existing = gmail.find_by_rfc822_msgid(msgid)
    if existing:
        svc.record_execution_outcome(
            db,
            client_id,
            {
                "id": execution_id,
                "status": "succeeded",
                "result": {
                    "messageId": existing,
                    "deduplicated": True,
                    "rfc822MsgId": msgid,
                },
                "verificationState": "pending",
            },
        )
        return {"executed": False, "adopted": True, "unknown": False, "message_id": existing}

    payload = row.get("input") or {}
    try:
        sent = gmail.send(
            to=payload.get("to"),
            subject=payload.get("subject"),
            body=payload.get("body"),
            rfc822_msgid=msgid,
        )
    except TimeoutError:
        apply_unknown_send_outcome(
            db, client_id, execution_id, "gmail transport timed out; outcome unknown"
        )
        return {"executed": True, "adopted": False, "unknown": True}

    if sent is None:
        apply_unknown_send_outcome(
            db,
            client_id,
            execution_id,
            "gmail accepted the message but the response was lost; outcome unknown",
        )
        return {"executed": True, "adopted": False, "unknown": True}

    svc.record_execution_outcome(
        db,
        client_id,
        {
            "id": execution_id,
            "status": "succeeded",
            "result": {
                "messageId": sent["message_id"],
                "deduplicated": False,
                "rfc822MsgId": msgid,
            },
        },
    )
    return {"executed": True, "adopted": False, "unknown": False, "message_id": sent["message_id"]}


def claim_only_if_python_email_valid(db, client_id: str, execution_id: str):
    """Pre-claim Python email check. A Zod-pass / Python-fail must stop here."""
    row = svc.get_tool_execution(db, client_id, execution_id)
    if row is None:
        return None
    if normalize_email((row.get("input") or {}).get("to")) is None:
        return None
    return svc.claim_for_execution(db, client_id, execution_id)


# --- 1. accept + lost response / rfc822 adopt --------------------------------


def test_claimed_gmail_timeout_stays_non_terminal():
    db = _pending_db()
    gmail = FakeGmailPort()
    gmail.mode = "timeout"

    claimed = svc.claim_for_execution(db, CLIENT, EXEC_ID)
    assert claimed is not None and claimed["status"] == "running"

    outcome = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert outcome["unknown"] is True
    assert outcome["adopted"] is False
    assert gmail.sends == []
    assert row["status"] == "running"
    assert row.get("finished_at") in (None, "")
    assert row["status"] not in TERMINAL
    assert row["error"]["code"] == "engine_unavailable"
    assert "unknown" in row["error"]["message"]


def test_accept_then_lost_response_is_adopted_on_redrive_and_does_not_send_twice():
    """Gmail accepted; our response was lost. Re-drive must adopt, not resend."""
    db = _pending_db()
    gmail = FakeGmailPort()
    gmail.mode = "accept_then_lose"

    assert svc.claim_for_execution(db, CLIENT, EXEC_ID)["status"] == "running"
    first = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert first["unknown"] is True
    assert first["executed"] is True
    assert len(gmail.sends) == 1
    assert row["status"] == "running"
    assert row.get("finished_at") in (None, "")
    assert row["status"] not in TERMINAL
    assert rfc822_msgid_for(EXEC_ID) in gmail.mailbox

    gmail.mode = "ok"
    second = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert second["adopted"] is True
    assert second["executed"] is False
    assert second["message_id"] == gmail.mailbox[rfc822_msgid_for(EXEC_ID)]
    assert len(gmail.sends) == 1, "a later re-drive must not send a second message"
    assert row["status"] == "succeeded"
    assert row["result"]["deduplicated"] is True


def test_unknown_send_must_not_be_written_terminal_with_finished_at():
    """QA contradiction: #693 ``_run_data_plane_tool`` always wrote a terminal
    status + ``finished_at``. An unknown outcome must not take that write.
    """
    db = _pending_db()
    svc.claim_for_execution(db, CLIENT, EXEC_ID)

    row = apply_unknown_send_outcome(
        db, CLIENT, EXEC_ID, "lost response; whether the message left is unknown"
    )

    assert row["status"] == "running"
    assert row.get("finished_at") in (None, "")
    assert row["status"] not in {"failed", "succeeded", "verification_failed"}
    assert row.get("finished_at") not in row or not row.get("finished_at")


# --- 2. Zod .email() vs normalize_email --------------------------------------


EMAIL_PARITY_MATRIX = (
    # email, zod, python — python is after normalize_email (None => reject)
    ("sarah@example.com", True, True),
    ("user+tag@example.com", True, True),
    ("user_name@example.com", True, True),
    ("first.last@example.com", True, True),
    ("A@B.COM", True, True),
    ("user@sub.example.co.uk", True, True),
    (ZOD_PASS_PYTHON_FAIL, True, False),
    ("  sarah@example.com  ", False, True),
    ("user..name@example.com", False, True),
    (".user@example.com", False, True),
    ("user.@example.com", False, True),
    ("not-an-email", False, False),
    ("a@b", False, False),
    ("user@localhost", False, False),
    ("user@example", False, False),
)


def test_engine_zod_email_and_python_normalize_email_parity_matrix():
    disagreements = []
    for raw, expect_zod, expect_python in EMAIL_PARITY_MATRIX:
        zod_ok = engine_zod_email_accepts(raw)
        python_ok = normalize_email(raw) is not None
        assert zod_ok is expect_zod, f"zod gate mismatch for {raw!r}"
        assert python_ok is expect_python, f"python gate mismatch for {raw!r}"
        if zod_ok != python_ok:
            disagreements.append((raw, zod_ok, python_ok))

    assert (ZOD_PASS_PYTHON_FAIL, True, False) in disagreements
    assert any(zod and not python for _, zod, python in disagreements), (
        "the matrix must include at least one Zod-pass / Python-fail"
    )


def test_zod_pass_python_fail_must_not_burn_the_only_approval_claim():
    assert engine_zod_email_accepts(ZOD_PASS_PYTHON_FAIL)
    assert normalize_email(ZOD_PASS_PYTHON_FAIL) is None

    db = _pending_db(input={"to": ZOD_PASS_PYTHON_FAIL, "subject": "Hi", "body": "Hello"})
    gmail = FakeGmailPort()

    claimed = claim_only_if_python_email_valid(db, CLIENT, EXEC_ID)

    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert claimed is None
    assert row["status"] == "pending_approval"
    assert row.get("finished_at") in (None, "")
    assert drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)["executed"] is False
    assert gmail.sends == []

    # The only approval is still unused. After the owner corrects the address,
    # the same row can still be claimed.
    db.table("os_tool_executions").update(
        {"input": {"to": "sarah@example.com", "subject": "Hi", "body": "Hello"}}
    ).eq("id", EXEC_ID).execute()
    still = claim_only_if_python_email_valid(db, CLIENT, EXEC_ID)
    assert still is not None and still["status"] == "running"


# --- 3. run_tool is unreachable without a claim ------------------------------


def test_run_tool_without_a_prior_claim_does_not_execute_a_provider():
    db = _pending_db()
    gmail = FakeGmailPort()

    os_tools = _optional_os_tools()
    if os_tools is not None and hasattr(os_tools, "run_tool"):
        ctx = os_tools.ToolContext(
            db=db,
            client_id=CLIENT,
            execution_id=EXEC_ID,
            tool_id="send_email",
            input={"to": "sarah@example.com", "subject": "Hi", "body": "Hello"},
            agent_id="sales",
            approved_by="maya@sunsetauto.test",
        )
        import asyncio

        asyncio.run(os_tools.run_tool(ctx))
        assert gmail.sends == []
        row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
        assert row["status"] == "pending_approval"
        return

    outcome = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)
    row = svc.get_tool_execution(db, CLIENT, EXEC_ID)
    assert outcome["executed"] is False
    assert outcome["adopted"] is False
    assert gmail.sends == []
    assert row["status"] == "pending_approval"
    assert row.get("finished_at") in (None, "")


# --- 4. L1 add_customer_note durable-row vs best-effort ----------------------


def test_a_level_one_action_that_cannot_be_recorded_does_not_break_the_turn():
    """L1 add_customer_note: durable-row vs best-effort when audit persist fails.

    L1 mutating with no approval is allowed in A. If the audit row cannot be
    written, the turn still completes (best-effort — no
    ``ToolExecutionAuditError``). The note is not applied without a row.
    Contrast ``test_l2_persist_fails_closed_when_the_audit_row_cannot_be_written``
    in ``test_os_tool_executions.py``.
    """

    class Unwritable(FakeSupabase):
        def table(self, name):
            if name == "os_tool_executions":
                raise RuntimeError("audit table unavailable")
            return super().table(name)

    db = Unwritable(
        {
            "os_tool_executions": [],
            "leads": [
                {"id": "lead_1", "client_id": CLIENT, "name": "Sarah Chen", "notes": None}
            ],
        }
    )
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
                "input": {"customer_id": "lead_1", "note": "Prefers texts after 5pm."},
                "result": {"noteId": "note_1", "customerId": "lead_1"},
                "effect": {"port": "in_memory", "durable": False},
            }
        ],
        "customerNotes": [
            {
                "id": "note_1",
                "customerId": "lead_1",
                "customerName": "Sarah Chen",
                "note": "Prefers texts after 5pm.",
                "source": "agent:admin_records",
                "createdAt": "2026-08-28T10:00:00Z",
            }
        ],
    }

    written = svc.persist_tool_executions(db, CLIENT, None, record)

    assert written == []
    assert db.rows("os_tool_executions") == []
    assert db.rows("leads")[0]["notes"] is None, (
        "no silent write: a note must not land without an audit row"
    )
    assert record["toolExecutions"][0]["riskLevel"] < svc.RISK_FAIL_CLOSED
    assert record["toolExecutions"][0]["effect"]["durable"] is False


def test_l2_audit_persist_still_fails_closed_next_to_l1_best_effort():
    class Unwritable(FakeSupabase):
        def table(self, name):
            if name == "os_tool_executions":
                raise RuntimeError("audit table unavailable")
            return super().table(name)

    db = Unwritable({"os_tool_executions": [], "leads": []})
    record = {
        "toolExecutions": [
            {
                "id": EXEC_ID,
                "toolId": "send_email",
                "riskLevel": 2,
                "mutating": True,
                "requiresApproval": True,
                "status": "pending_approval",
                "idempotencyKey": "l2-audit-write-gmail-1",
                "input": {"to": "sarah@example.com", "subject": "Hi", "body": "Hello"},
            }
        ]
    }

    with pytest.raises(svc.ToolExecutionAuditError, match="refusing to queue"):
        svc.persist_tool_executions(db, CLIENT, None, record)
    assert db.rows("os_tool_executions") == []


def test_claim_then_run_is_the_only_path_that_reaches_the_provider():
    db = _pending_db()
    gmail = FakeGmailPort()

    drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)
    assert gmail.sends == []

    claimed = svc.claim_for_execution(db, CLIENT, EXEC_ID)
    assert claimed["status"] == "running"
    outcome = drive_claimed_gmail_send(db, CLIENT, EXEC_ID, gmail)
    assert outcome["executed"] is True
    assert len(gmail.sends) == 1
    assert gmail.sends[0]["rfc822_msgid"] == rfc822_msgid_for(EXEC_ID)
