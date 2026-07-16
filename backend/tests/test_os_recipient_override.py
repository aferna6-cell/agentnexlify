"""Explicit recipient on Agent OS deliverable sends.

Contract:
  1. ``normalize_phone`` / ``normalize_email`` are strict, deterministic
     normalizers — no guessing beyond the documented US 10-digit default.
  2. When a deliverable carries ``recipient``, sms.send / email.send use it
     directly and send the approved body verbatim — the Haiku extraction
     step is never called (deterministic-first, no LLM in the path).
  3. An invalid explicit recipient fails at the validate stage with a
     message the owner can act on (extraction is NOT used as a fallback —
     the owner's input wins or the send stops).
  4. Compliance gates still apply on the explicit path (SMS opt-out).
  5. PATCH /os/deliverables/{id} persists ``recipient``; the retry endpoint
     accepts a recipient override and writes it to the deliverable before
     requeueing.

Why: the only real send ever attempted in prod failed with
{"stage": "extract", "message": "missing recipient"} — normal drafts do not
contain the recipient's phone/email, and the owner had no way to supply one.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
os.environ.setdefault("TESTING", "1")

from backend.services.os_actions.base import ActionContext
from backend.services.os_actions.recipients import normalize_email, normalize_phone

_TENANT = "aaaaaaaa-0000-0000-0000-000000000001"


# --- normalizers -------------------------------------------------------------
def test_normalize_phone_e164_passthrough():
    assert normalize_phone("+15555550123") == "+15555550123"


def test_normalize_phone_strips_formatting():
    assert normalize_phone("(555) 555-0123") == "+15555550123"
    assert normalize_phone("555-555-0123") == "+15555550123"
    assert normalize_phone("+44 20 7946 0958") == "+442079460958"


def test_normalize_phone_us_defaults():
    assert normalize_phone("5555550123") == "+15555550123"
    assert normalize_phone("15555550123") == "+15555550123"


def test_normalize_phone_rejects_garbage():
    assert normalize_phone("hello") is None
    assert normalize_phone("123") is None
    assert normalize_phone("") is None
    assert normalize_phone(None) is None
    assert normalize_phone("+0123456789") is None


def test_normalize_email_accepts_and_rejects():
    assert normalize_email("sam@example.com") == "sam@example.com"
    assert normalize_email("  Sam.Lee+x@sub.example.co  ") == "Sam.Lee+x@sub.example.co"
    assert normalize_email("not-an-email") is None
    assert normalize_email("a@b") is None
    assert normalize_email(None) is None


# --- action-path helpers ------------------------------------------------------
def _ctx(deliverable: dict) -> ActionContext:
    return ActionContext(
        db=MagicMock(),
        client_id=_TENANT,
        deliverable_id="run-1",
        action_run_id="ar-1",
        action_type="sms.send",
        deliverable=deliverable,
        agent_run={"id": "run-1", "agent_name": "sales"},
    )


_NO_EXTRACT = AsyncMock(side_effect=AssertionError("extraction must not run"))


# --- sms.send explicit path ---------------------------------------------------
def test_sms_explicit_recipient_skips_extraction_and_sends_body_verbatim():
    from backend.services.os_actions import sms as sms_action

    send = AsyncMock(return_value=True)
    with (
        patch.object(sms_action, "_extract_sms_payload", _NO_EXTRACT),
        patch.object(sms_action.sms_compliance, "is_suppressed", return_value=False),
        patch.object(sms_action, "_pick_provider", return_value="twilio_platform"),
        patch.object(sms_action, "send_sms", send),
    ):
        result = asyncio.run(
            sms_action._run(
                _ctx({"body": "Hi Sarah, following up!", "recipient": "555-555-0123"})
            )
        )
    assert result.status == "succeeded"
    assert result.request_payload["to"] == "+15555550123"
    assert result.request_payload["body"] == "Hi Sarah, following up!"
    send.assert_awaited_once()


def test_sms_invalid_explicit_recipient_fails_validate_without_llm():
    from backend.services.os_actions import sms as sms_action

    with patch.object(sms_action, "_extract_sms_payload", _NO_EXTRACT):
        result = asyncio.run(
            sms_action._run(_ctx({"body": "Hi!", "recipient": "not a phone"}))
        )
    assert result.status == "failed"
    assert result.error_detail["stage"] == "validate"
    assert "phone" in result.error_detail["message"]


def test_sms_explicit_recipient_still_respects_opt_out():
    from backend.services.os_actions import sms as sms_action

    with (
        patch.object(sms_action, "_extract_sms_payload", _NO_EXTRACT),
        patch.object(sms_action.sms_compliance, "is_suppressed", return_value=True),
    ):
        result = asyncio.run(
            sms_action._run(_ctx({"body": "Hi!", "recipient": "+15555550123"}))
        )
    assert result.status == "failed"
    assert result.error_detail["stage"] == "compliance"


def test_sms_without_recipient_keeps_extraction_path():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"error": "missing recipient"})
    with patch.object(sms_action, "_extract_sms_payload", extractor):
        result = asyncio.run(sms_action._run(_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert result.error_detail["stage"] == "extract"
    extractor.assert_awaited_once()


def test_sms_explicit_recipient_trims_long_body():
    from backend.services.os_actions import sms as sms_action

    send = AsyncMock(return_value=True)
    with (
        patch.object(sms_action, "_extract_sms_payload", _NO_EXTRACT),
        patch.object(sms_action.sms_compliance, "is_suppressed", return_value=False),
        patch.object(sms_action, "_pick_provider", return_value="twilio_platform"),
        patch.object(sms_action, "send_sms", send),
    ):
        result = asyncio.run(
            sms_action._run(
                _ctx({"body": "x" * 2000, "recipient": "+15555550123"})
            )
        )
    assert result.status == "succeeded"
    assert len(result.request_payload["body"]) == 1600


# --- email.send explicit path ---------------------------------------------------
def test_email_explicit_recipient_skips_extraction_and_wraps_body():
    from backend.services.os_actions import email as email_action

    send = AsyncMock(return_value={"success": True, "resend_id": "r1"})
    with (
        patch.object(email_action, "_extract_email_payload", _NO_EXTRACT),
        patch.object(email_action, "_pick_provider", return_value="resend"),
        patch.object(email_action, "send_email", send),
    ):
        result = asyncio.run(
            email_action._run(
                _ctx(
                    {
                        "title": "Quick follow-up",
                        "body": "Hi Sam,\n\nGreat to meet you & the team.",
                        "recipient": "sam@example.com",
                    }
                )
            )
        )
    assert result.status == "succeeded"
    assert result.request_payload["to"] == "sam@example.com"
    assert result.request_payload["subject"] == "Quick follow-up"
    html_body = result.request_payload["body_html"]
    assert "<p>Hi Sam,</p>" in html_body
    assert "&amp;" in html_body  # user text is escaped, not injected as HTML
    send.assert_awaited_once()


def test_email_invalid_explicit_recipient_fails_validate_without_llm():
    from backend.services.os_actions import email as email_action

    with patch.object(email_action, "_extract_email_payload", _NO_EXTRACT):
        result = asyncio.run(
            email_action._run(_ctx({"body": "Hi!", "recipient": "nope"}))
        )
    assert result.status == "failed"
    assert result.error_detail["stage"] == "validate"
    assert "email" in result.error_detail["message"]


def test_email_without_recipient_keeps_extraction_path():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(return_value={"error": "missing recipient"})
    with patch.object(email_action, "_extract_email_payload", extractor):
        result = asyncio.run(email_action._run(_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert result.error_detail["stage"] == "extract"
    extractor.assert_awaited_once()


# --- router: PATCH recipient + retry override ---------------------------------
def _chain(rows):
    """MagicMock supabase chain whose execute() returns the given rows."""
    m = MagicMock()
    for attr in ("select", "eq", "update", "insert", "limit", "order"):
        getattr(m, attr).return_value = m
    m.execute.return_value = MagicMock(data=rows)
    return m


def test_patch_deliverable_persists_recipient():
    from backend.routers import os_deliverables as router_mod

    run_row = {
        "id": "run-1",
        "deliverable": {"title": "T", "body": "B"},
        "deliverable_status": "pending_approval",
    }
    load_chain = _chain([run_row])
    update_chain = _chain([{"id": "run-1"}])
    tables = MagicMock(side_effect=[load_chain, update_chain])

    with (
        patch.object(router_mod, "get_service_supabase", return_value=MagicMock()),
        patch.object(router_mod, "tenant_table", tables),
    ):
        asyncio.run(
            router_mod.edit_deliverable(
                "run-1",
                router_mod.DeliverableEditRequest(recipient=" +1 555-555-0123 "),
                claims={"tenant_id": _TENANT},
            )
        )

    saved = update_chain.update.call_args[0][0]["deliverable"]
    assert saved["recipient"] == "+1 555-555-0123"
    assert saved["body"] == "B"  # untouched fields survive


def test_retry_with_recipient_writes_deliverable_before_requeue():
    from fastapi import BackgroundTasks

    from backend.routers import os_deliverables as router_mod

    action_row = {
        "id": "ar-1",
        "status": "failed",
        "action_type": "sms.send",
        "deliverable_id": "run-1",
    }
    run_row = {
        "id": "run-1",
        "deliverable": {"title": "T", "body": "B"},
        "deliverable_status": "approved",
    }
    load_action = _chain([action_row])
    load_run = _chain([run_row])
    write_recipient = _chain([{"id": "run-1"}])
    insert_new = _chain([{"id": "ar-2", "status": "queued"}])
    link_back = _chain([{"id": "run-1"}])
    tables = MagicMock(
        side_effect=[load_action, load_run, write_recipient, insert_new, link_back]
    )

    with (
        patch.object(router_mod, "get_service_supabase", return_value=MagicMock()),
        patch.object(router_mod, "tenant_table", tables),
        patch.object(router_mod, "get_action", return_value=object()),
    ):
        created = asyncio.run(
            router_mod.retry_action_run(
                "ar-1",
                BackgroundTasks(),
                req=router_mod.RetryActionRunRequest(recipient="555-555-0123"),
                claims={"tenant_id": _TENANT, "role": "owner"},
            )
        )

    assert created["id"] == "ar-2"
    saved = write_recipient.update.call_args[0][0]["deliverable"]
    assert saved["recipient"] == "555-555-0123"


def test_retry_without_recipient_does_not_touch_deliverable():
    from fastapi import BackgroundTasks

    from backend.routers import os_deliverables as router_mod

    action_row = {
        "id": "ar-1",
        "status": "failed",
        "action_type": "sms.send",
        "deliverable_id": "run-1",
    }
    load_action = _chain([action_row])
    insert_new = _chain([{"id": "ar-2", "status": "queued"}])
    link_back = _chain([{"id": "run-1"}])
    tables = MagicMock(side_effect=[load_action, insert_new, link_back])

    with (
        patch.object(router_mod, "get_service_supabase", return_value=MagicMock()),
        patch.object(router_mod, "tenant_table", tables),
        patch.object(router_mod, "get_action", return_value=object()),
    ):
        created = asyncio.run(
            router_mod.retry_action_run(
                "ar-1",
                BackgroundTasks(),
                req=None,
                claims={"tenant_id": _TENANT, "role": "owner"},
            )
        )

    assert created["id"] == "ar-2"
    assert tables.call_count == 3  # no extra deliverable write
