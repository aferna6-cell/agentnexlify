"""Unit tests for os_actions registry + foundation.

Spec: ``specs/agent-os-connectors-actions_spec.md``.

Focus:
- Registry auto-discovers calendar handler via SPEC import.
- ``run_action`` writes status, payloads, and timestamps tenant-scoped.
- Idempotency: succeeded action cannot be re-inserted for the same
  (deliverable_id, action_type) (enforced by DB partial unique — test
  validates the route preflight that short-circuits before insert).
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


from backend.services.os_actions import all_actions, get_action, run_action
from backend.services.os_actions.base import (
    ActionContext,
    ActionResult,
    ActionSpec,
)

_CLIENT_A = "00000000-0000-0000-0000-00000000000a"
_DELIV = "10000000-0000-0000-0000-00000000abcd"
_ACTION_RUN = "20000000-0000-0000-0000-00000000abcd"


def _stub_supabase(agent_run_row: dict | None = None):
    """Mimic the chained supabase-py builder used by tenant_table()."""
    builder = MagicMock(name="builder")
    builder.select.return_value = builder
    builder.update.return_value = builder
    builder.insert.return_value = builder
    builder.eq.return_value = builder
    builder.limit.return_value = builder
    builder.execute.return_value = SimpleNamespace(
        data=[agent_run_row] if agent_run_row else []
    )
    db = MagicMock(name="db")
    db.table.return_value = builder
    return db, builder


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_discovers_calendar_handler():
    actions = all_actions()
    assert "calendar.event.create" in actions
    spec = actions["calendar.event.create"]
    assert isinstance(spec, ActionSpec)
    assert spec.worker == "booking"
    assert "google_calendar" in spec.required_connectors


def test_get_action_returns_none_for_unknown():
    assert get_action("does.not.exist") is None


def test_get_action_returns_spec_for_known():
    spec = get_action("calendar.event.create")
    assert spec is not None
    assert spec.name == "calendar.event.create"


# ---------------------------------------------------------------------------
# run_action background-task harness
# ---------------------------------------------------------------------------


def test_run_action_marks_unknown_action_failed():
    db, builder = _stub_supabase(agent_run_row={"id": _DELIV, "deliverable": {}})
    with patch("backend.services.os_actions.get_service_supabase", return_value=db):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "not.a.real.action"))
    # The failure path writes status=failed with error_detail.
    update_calls = [c for c in builder.update.call_args_list]
    assert any(
        c.args[0].get("status") == "failed" for c in update_calls
    ), "failed status update not recorded"


def test_run_action_invokes_handler_run():
    db, builder = _stub_supabase(
        agent_run_row={
            "id": _DELIV,
            "deliverable": {"title": "T", "body": "approved body"},
            "client_id": _CLIENT_A,
            "thread_id": "thr-1",
        }
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.name = "calendar.event.create"
    stub_handler.run = AsyncMock(
        return_value=ActionResult(
            status="succeeded",
            request_payload={"summary": "ok"},
            response_payload={"event_id": "abc"},
        )
    )
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    stub_handler.run.assert_awaited_once()
    ctx_arg = stub_handler.run.call_args.args[0]
    assert isinstance(ctx_arg, ActionContext)
    assert ctx_arg.client_id == _CLIENT_A
    assert ctx_arg.deliverable_id == _DELIV
    assert ctx_arg.action_type == "calendar.event.create"
    assert ctx_arg.deliverable == {"title": "T", "body": "approved body"}
    # status=succeeded must be persisted with payloads.
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    final = [u for u in update_calls if u.get("status") == "succeeded"]
    assert final, "succeeded status not persisted"
    assert final[0]["response_payload"] == {"event_id": "abc"}


def test_run_action_propagates_handler_exception_as_failed():
    db, builder = _stub_supabase(
        agent_run_row={"id": _DELIV, "deliverable": {"body": "x"}}
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(side_effect=RuntimeError("boom"))
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    fail = [u for u in update_calls if u.get("status") == "failed"]
    assert fail, "exception did not trigger failed status write"
    assert "boom" in (fail[-1].get("error_detail") or {}).get("message", "")


# ---------------------------------------------------------------------------
# Tenant scoping
# ---------------------------------------------------------------------------


def test_run_action_uses_client_id_for_os_action_runs_scope():
    """tenant_table('os_action_runs', client_id) must scope by client_id."""
    db, builder = _stub_supabase(
        agent_run_row={"id": _DELIV, "deliverable": {"body": "x"}}
    )
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(return_value=ActionResult(status="succeeded"))
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "calendar.event.create"))
    # The scoping filter from tenant_table is added to every chained query
    # — assert the client_id was passed to .eq() at least once.
    eq_args = [c.args for c in builder.eq.call_args_list]
    flat = [a for tpl in eq_args for a in tpl]
    assert _CLIENT_A in flat, "client_id never used in scoping filter"


# ---------------------------------------------------------------------------
# Registry coverage — the 6 new action SPECs from the Agent OS rehaul
# ---------------------------------------------------------------------------


def test_registry_includes_email_send():
    actions = all_actions()
    assert "email.send" in actions
    spec = actions["email.send"]
    assert isinstance(spec, ActionSpec)
    assert spec.worker == "lead_nurture"
    assert spec.required_connectors == []
    assert callable(spec.run)


def test_registry_includes_widget_message():
    actions = all_actions()
    assert "widget.message" in actions
    spec = actions["widget.message"]
    assert spec.worker == "customer_question"
    assert spec.required_connectors == []


def test_registry_includes_crm_contact_upsert():
    actions = all_actions()
    assert "crm.contact_upsert" in actions
    spec = actions["crm.contact_upsert"]
    assert spec.worker == "lead_nurture"
    assert spec.required_connectors == []


def test_registry_includes_social_facebook_post():
    actions = all_actions()
    assert "social.facebook.post" in actions
    spec = actions["social.facebook.post"]
    assert spec.worker == "campaign"
    assert "facebook" in spec.required_connectors


def test_registry_includes_social_instagram_post():
    actions = all_actions()
    assert "social.instagram.post" in actions
    spec = actions["social.instagram.post"]
    assert spec.worker == "campaign"
    assert "instagram" in spec.required_connectors


def test_registry_includes_gbp_post():
    actions = all_actions()
    assert "gbp.post" in actions
    spec = actions["gbp.post"]
    assert spec.worker == "campaign"
    assert "google_business_profile" in spec.required_connectors


# ---------------------------------------------------------------------------
# email.send — handler contract
# ---------------------------------------------------------------------------


def _action_ctx(deliverable: dict, db=None) -> ActionContext:
    return ActionContext(
        db=db or MagicMock(),
        client_id=_CLIENT_A,
        deliverable_id=_DELIV,
        action_run_id=_ACTION_RUN,
        action_type="test",
        deliverable=deliverable,
        agent_run={},
    )


def test_email_send_rejects_empty_body():
    from backend.services.os_actions.email import _run

    result = asyncio.run(_run(_action_ctx({"body": ""})))
    assert result.status == "failed"
    assert "empty body" in (result.error_detail or {}).get("message", "")


def test_email_send_rejects_missing_recipient():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(return_value={"error": "missing recipient"})
    with patch.object(email_action, "_extract_email_payload", extractor):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert "missing recipient" in (result.error_detail or {}).get("message", "")


def test_email_send_rejects_invalid_recipient_format():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={"to": "notanemail", "subject": "x", "body_html": "<p>x</p>"}
    )
    with patch.object(email_action, "_extract_email_payload", extractor):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "validate"


def test_email_send_sends_via_resend_on_valid_payload():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={
            "to": "alice@example.com",
            "subject": "Following up",
            "body_html": "<p>Hello Alice</p>",
        }
    )
    sender = AsyncMock(return_value={"success": True, "resend_id": "re_123"})
    with patch.object(email_action, "_extract_email_payload", extractor), patch.object(
        email_action, "send_email", sender
    ), patch.object(email_action, "m365_is_connected", return_value=False):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload["to"] == "alice@example.com"
    assert result.request_payload.get("provider") == "resend"
    assert result.response_payload["resend_id"] == "re_123"
    assert result.response_payload.get("provider") == "resend"
    sender.assert_awaited_once()


def test_email_send_records_resend_failure_as_failed():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={
            "to": "alice@example.com",
            "subject": "Following up",
            "body_html": "<p>Hello</p>",
        }
    )
    sender = AsyncMock(return_value={"success": False, "detail": "no api key"})
    with patch.object(email_action, "_extract_email_payload", extractor), patch.object(
        email_action, "send_email", sender
    ), patch.object(email_action, "m365_is_connected", return_value=False):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "resend"


def test_email_send_dispatches_to_m365_when_connected():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={
            "to": "alice@example.com",
            "subject": "Following up",
            "body_html": "<p>Hello Alice</p>",
        }
    )
    graph_sender = AsyncMock(
        return_value={"success": True, "detail": "sent", "message_id": "req-abc"}
    )
    resend_sender = AsyncMock(return_value={"success": True, "resend_id": "re_xxx"})
    with patch.object(email_action, "_extract_email_payload", extractor), patch.object(
        email_action, "m365_is_connected", return_value=True
    ), patch.object(
        email_action, "m365_send_email_via_graph", graph_sender
    ), patch.object(
        email_action, "send_email", resend_sender
    ):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload.get("provider") == "m365"
    assert result.response_payload.get("provider") == "m365"
    assert result.response_payload.get("message_id") == "req-abc"
    graph_sender.assert_awaited_once()
    resend_sender.assert_not_awaited()


def test_email_send_records_m365_failure_as_failed():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={
            "to": "alice@example.com",
            "subject": "Following up",
            "body_html": "<p>Hello</p>",
        }
    )
    graph_sender = AsyncMock(
        return_value={"success": False, "detail": "auth error (HTTP 401)"}
    )
    with patch.object(email_action, "_extract_email_payload", extractor), patch.object(
        email_action, "m365_is_connected", return_value=True
    ), patch.object(email_action, "m365_send_email_via_graph", graph_sender):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "m365"
    assert "auth error" in (result.error_detail or {}).get("message", "")


def test_email_send_falls_back_to_resend_when_m365_lookup_raises():
    from backend.services.os_actions import email as email_action

    extractor = AsyncMock(
        return_value={
            "to": "alice@example.com",
            "subject": "Following up",
            "body_html": "<p>Hello</p>",
        }
    )
    bad_lookup = MagicMock(side_effect=RuntimeError("supabase boom"))
    sender = AsyncMock(return_value={"success": True, "resend_id": "re_fb"})
    with patch.object(email_action, "_extract_email_payload", extractor), patch.object(
        email_action, "m365_is_connected", bad_lookup
    ), patch.object(email_action, "send_email", sender):
        result = asyncio.run(email_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload.get("provider") == "resend"
    sender.assert_awaited_once()


# ---------------------------------------------------------------------------
# sms.send — handler contract
# ---------------------------------------------------------------------------


def test_registry_includes_sms_send():
    actions = all_actions()
    assert "sms.send" in actions
    spec = actions["sms.send"]
    assert isinstance(spec, ActionSpec)
    assert spec.worker == "lead_nurture"
    assert spec.required_connectors == []
    assert callable(spec.run)


def test_sms_send_rejects_empty_body():
    from backend.services.os_actions.sms import _run

    result = asyncio.run(_run(_action_ctx({"body": ""})))
    assert result.status == "failed"
    assert "empty body" in (result.error_detail or {}).get("message", "")


def test_sms_send_rejects_missing_recipient():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"error": "missing recipient"})
    with patch.object(sms_action, "_extract_sms_payload", extractor):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert "missing recipient" in (result.error_detail or {}).get("message", "")


def test_sms_send_rejects_invalid_phone_format():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "555-1234", "body": "Hello"})
    with patch.object(sms_action, "_extract_sms_payload", extractor):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Hi there"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "validate"


def test_sms_send_rejects_empty_payload_body():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": ""})
    with patch.object(sms_action, "_extract_sms_payload", extractor):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft"})))
    assert result.status == "failed"
    assert "empty sms body" in (result.error_detail or {}).get("message", "")


def test_sms_send_sends_via_twilio_on_valid_payload():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": "Following up"})
    sender = AsyncMock(return_value=True)
    with patch.object(sms_action, "_extract_sms_payload", extractor), patch.object(
        sms_action, "twilio_is_connected", return_value=False
    ), patch.object(sms_action, "send_sms", sender):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload["to"] == "+15555550123"
    assert result.request_payload["provider"] == "twilio_platform"
    assert result.response_payload["detail"] == "sent"
    assert result.response_payload["provider"] == "twilio_platform"
    sender.assert_awaited_once()


def test_sms_send_records_twilio_failure_as_failed():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": "Following up"})
    sender = AsyncMock(return_value=False)
    with patch.object(sms_action, "_extract_sms_payload", extractor), patch.object(
        sms_action, "twilio_is_connected", return_value=False
    ), patch.object(sms_action, "send_sms", sender):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "twilio"


def test_sms_send_dispatches_to_twilio_byo_when_connected():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": "Following up"})
    byo_sender = AsyncMock(
        return_value={"success": True, "detail": "sent", "message_sid": "SMabc123"}
    )
    with patch.object(sms_action, "_extract_sms_payload", extractor), patch.object(
        sms_action, "twilio_is_connected", return_value=True
    ), patch.object(sms_action, "send_sms_via_tenant", byo_sender):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload["provider"] == "twilio_byo"
    assert result.response_payload["provider"] == "twilio_byo"
    assert result.response_payload["message_sid"] == "SMabc123"
    byo_sender.assert_awaited_once()


def test_sms_send_records_twilio_byo_failure_as_failed():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": "Following up"})
    byo_sender = AsyncMock(
        return_value={"success": False, "detail": "auth error (HTTP 401)"}
    )
    with patch.object(sms_action, "_extract_sms_payload", extractor), patch.object(
        sms_action, "twilio_is_connected", return_value=True
    ), patch.object(sms_action, "send_sms_via_tenant", byo_sender):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "twilio_byo"
    assert "auth error" in (result.error_detail or {}).get("message", "")


def test_sms_send_falls_back_to_platform_when_byo_lookup_raises():
    from backend.services.os_actions import sms as sms_action

    extractor = AsyncMock(return_value={"to": "+15555550123", "body": "Following up"})
    sender = AsyncMock(return_value=True)
    raising_lookup = MagicMock(side_effect=RuntimeError("supabase boom"))
    with patch.object(sms_action, "_extract_sms_payload", extractor), patch.object(
        sms_action, "twilio_is_connected", raising_lookup
    ), patch.object(sms_action, "send_sms", sender):
        result = asyncio.run(sms_action._run(_action_ctx({"body": "Draft body"})))
    assert result.status == "succeeded"
    assert result.request_payload["provider"] == "twilio_platform"
    assert result.response_payload["provider"] == "twilio_platform"
    sender.assert_awaited_once()


# ---------------------------------------------------------------------------
# widget.message — handler contract
# ---------------------------------------------------------------------------


def test_widget_message_rejects_empty_body():
    from backend.services.os_actions.widget import _run

    result = asyncio.run(_run(_action_ctx({"body": ""})))
    assert result.status == "failed"


def test_widget_message_requires_session_id():
    from backend.services.os_actions.widget import _run

    result = asyncio.run(_run(_action_ctx({"body": "hi"})))
    assert result.status == "failed"
    assert "session_id" in (result.error_detail or {}).get("message", "")


def test_widget_message_inserts_assistant_row():
    from backend.services.os_actions import widget as widget_action

    db = MagicMock()
    builder = MagicMock()
    builder.execute.return_value = SimpleNamespace(data=[{"id": "msg-1"}])
    inserter = MagicMock(return_value=builder)
    ctx = _action_ctx({"body": "hello", "session_id": "sess-42"}, db=db)
    with patch.object(widget_action, "tenant_insert", inserter):
        result = asyncio.run(widget_action._run(ctx))
    assert result.status == "succeeded"
    assert result.request_payload["session_id"] == "sess-42"
    assert result.response_payload["message_id"] == "msg-1"
    inserter.assert_called_once()
    insert_call = inserter.call_args
    inserted_row = insert_call.args[3]
    assert inserted_row["role"] == "assistant"
    assert inserted_row["tenant_id"] == _CLIENT_A
    assert inserted_row["session_id"] == "sess-42"


def test_widget_message_falls_back_to_agent_run_thread_metadata():
    from backend.services.os_actions import widget as widget_action

    db = MagicMock()
    builder = MagicMock()
    builder.execute.return_value = SimpleNamespace(data=[{"id": "msg-7"}])
    inserter = MagicMock(return_value=builder)
    ctx = ActionContext(
        db=db,
        client_id=_CLIENT_A,
        deliverable_id=_DELIV,
        action_run_id=_ACTION_RUN,
        action_type="widget.message",
        deliverable={"body": "answer"},
        agent_run={"thread_metadata": {"session_id": "sess-from-thread"}},
    )
    with patch.object(widget_action, "tenant_insert", inserter):
        result = asyncio.run(widget_action._run(ctx))
    assert result.status == "succeeded"
    assert result.request_payload["session_id"] == "sess-from-thread"


# ---------------------------------------------------------------------------
# crm.contact_upsert — handler contract
# ---------------------------------------------------------------------------


def test_crm_upsert_rejects_no_identifier():
    from backend.services.os_actions import crm as crm_action

    extractor = AsyncMock(return_value={"error": "no contact identifier"})
    with patch.object(crm_action, "_extract_contact", extractor):
        result = asyncio.run(crm_action._run(_action_ctx({"body": "no contact info"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "extract"


def test_crm_upsert_inserts_when_no_existing_match():
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": "Bob Customer",
            "email": "bob@example.com",
            "phone": None,
            "notes": "asked about pricing",
            "areas_of_interest": ["pricing"],
        }
    )
    finder = MagicMock(return_value=None)
    insert_builder = MagicMock()
    insert_builder.execute.return_value = SimpleNamespace(data=[{"id": "lead-99"}])
    inserter = MagicMock(return_value=insert_builder)
    ctx = _action_ctx({"body": "approved msg"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_insert", inserter), patch.object(
        crm_action, "hubspot_is_connected", return_value=False
    ):
        result = asyncio.run(crm_action._run(ctx))
    assert result.status == "succeeded"
    assert result.response_payload["operation"] == "inserted"
    assert result.response_payload["lead_id"] == "lead-99"
    assert "hubspot_push" not in result.response_payload


def test_crm_upsert_updates_when_existing_match():
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": None,
            "email": "carol@example.com",
            "phone": None,
            "notes": "asked again about pricing",
            "areas_of_interest": None,
        }
    )
    finder = MagicMock(
        return_value={
            "id": "lead-existing",
            "name": "Carol",
            "email": "carol@example.com",
            "phone": None,
            "notes": "first note",
        }
    )
    update_builder = MagicMock()
    update_builder.eq.return_value = update_builder
    update_builder.execute.return_value = SimpleNamespace(data=[])
    updater = MagicMock(return_value=update_builder)
    ctx = _action_ctx({"body": "approved msg"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_update", updater), patch.object(
        crm_action, "hubspot_is_connected", return_value=False
    ):
        result = asyncio.run(crm_action._run(ctx))
    assert result.status == "succeeded"
    assert result.response_payload["operation"] == "updated"
    assert result.response_payload["lead_id"] == "lead-existing"
    assert "hubspot_push" not in result.response_payload


def test_crm_upsert_rejects_invalid_email_format():
    from backend.services.os_actions import crm as crm_action

    extractor = AsyncMock(
        return_value={
            "name": "Dan",
            "email": "notanemail",
            "phone": None,
            "notes": None,
            "areas_of_interest": None,
        }
    )
    with patch.object(crm_action, "_extract_contact", extractor):
        result = asyncio.run(crm_action._run(_action_ctx({"body": "x"})))
    assert result.status == "failed"
    assert "invalid email" in (result.error_detail or {}).get("message", "")


def test_crm_upsert_pushes_to_hubspot_when_connected():
    """When tenant has HubSpot connected, push contact to HubSpot after internal upsert."""
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": "Eve Customer",
            "email": "eve@example.com",
            "phone": None,
            "notes": "interested in autopilot",
            "areas_of_interest": ["autopilot"],
        }
    )
    finder = MagicMock(return_value=None)
    insert_builder = MagicMock()
    insert_builder.execute.return_value = SimpleNamespace(data=[{"id": "lead-555"}])
    inserter = MagicMock(return_value=insert_builder)
    hubspot_push = AsyncMock(
        return_value={
            "success": True,
            "detail": "created",
            "contact_id": "hs-12345",
            "operation": "created",
        }
    )
    ctx = _action_ctx({"body": "approved"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_insert", inserter), patch.object(
        crm_action, "hubspot_is_connected", return_value=True
    ), patch.object(
        crm_action, "hubspot_upsert_contact", hubspot_push
    ):
        result = asyncio.run(crm_action._run(ctx))
    assert result.status == "succeeded"
    assert result.response_payload["lead_id"] == "lead-555"
    assert result.response_payload["operation"] == "inserted"
    assert result.response_payload["hubspot_contact_id"] == "hs-12345"
    assert result.response_payload["hubspot_push"]["success"] is True
    hubspot_push.assert_awaited_once()


def test_crm_upsert_hard_fails_when_hubspot_push_fails():
    """If HubSpot push fails, whole action fails — but lead_id preserved in response."""
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": "Frank",
            "email": "frank@example.com",
            "phone": None,
            "notes": "wants demo",
            "areas_of_interest": None,
        }
    )
    finder = MagicMock(return_value=None)
    insert_builder = MagicMock()
    insert_builder.execute.return_value = SimpleNamespace(data=[{"id": "lead-666"}])
    inserter = MagicMock(return_value=insert_builder)
    hubspot_push = AsyncMock(
        return_value={"success": False, "detail": "HubSpot auth error: 401"}
    )
    ctx = _action_ctx({"body": "approved"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_insert", inserter), patch.object(
        crm_action, "hubspot_is_connected", return_value=True
    ), patch.object(
        crm_action, "hubspot_upsert_contact", hubspot_push
    ):
        result = asyncio.run(crm_action._run(ctx))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "hubspot_push"
    assert "auth error" in (result.error_detail or {}).get("message", "")
    # Lead was created internally — preserve lead_id for observability.
    assert result.response_payload["lead_id"] == "lead-666"
    assert result.response_payload["operation"] == "inserted"
    assert result.response_payload["hubspot_push"]["success"] is False


def test_crm_upsert_skips_hubspot_when_not_connected():
    """When HubSpot not connected, internal upsert only — no hubspot fields in response."""
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": "Gina",
            "email": "gina@example.com",
            "phone": None,
            "notes": None,
            "areas_of_interest": None,
        }
    )
    finder = MagicMock(return_value=None)
    insert_builder = MagicMock()
    insert_builder.execute.return_value = SimpleNamespace(data=[{"id": "lead-777"}])
    inserter = MagicMock(return_value=insert_builder)
    hubspot_push = AsyncMock(
        return_value={"success": True, "detail": "should not be called"}
    )
    ctx = _action_ctx({"body": "approved"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_insert", inserter), patch.object(
        crm_action, "hubspot_is_connected", return_value=False
    ), patch.object(
        crm_action, "hubspot_upsert_contact", hubspot_push
    ):
        result = asyncio.run(crm_action._run(ctx))
    assert result.status == "succeeded"
    assert result.response_payload["lead_id"] == "lead-777"
    assert "hubspot_push" not in result.response_payload
    assert "hubspot_contact_id" not in result.response_payload
    hubspot_push.assert_not_awaited()


def test_crm_upsert_falls_back_when_hubspot_lookup_raises():
    """If hubspot_is_connected raises, treat as not-connected — internal flow intact."""
    from backend.services.os_actions import crm as crm_action

    db = MagicMock()
    extractor = AsyncMock(
        return_value={
            "name": "Hank",
            "email": "hank@example.com",
            "phone": None,
            "notes": None,
            "areas_of_interest": None,
        }
    )
    finder = MagicMock(return_value=None)
    insert_builder = MagicMock()
    insert_builder.execute.return_value = SimpleNamespace(data=[{"id": "lead-888"}])
    inserter = MagicMock(return_value=insert_builder)
    hubspot_push = AsyncMock(return_value={"success": True})

    def _connected_raises(_tenant_id):
        raise RuntimeError("supabase down")

    ctx = _action_ctx({"body": "approved"}, db=db)
    with patch.object(crm_action, "_extract_contact", extractor), patch.object(
        crm_action, "_find_existing", finder
    ), patch.object(crm_action, "tenant_insert", inserter), patch.object(
        crm_action, "hubspot_is_connected", side_effect=_connected_raises
    ), patch.object(
        crm_action, "hubspot_upsert_contact", hubspot_push
    ):
        result = asyncio.run(crm_action._run(ctx))
    # Safe fallback: internal lead intact, no hubspot push attempted.
    assert result.status == "succeeded"
    assert result.response_payload["lead_id"] == "lead-888"
    assert "hubspot_push" not in result.response_payload
    hubspot_push.assert_not_awaited()


# ---------------------------------------------------------------------------
# social.facebook.post — handler contract
# ---------------------------------------------------------------------------


def test_facebook_post_rejects_when_page_not_connected():
    from backend.services.os_actions import social_facebook as fb_action

    extractor = AsyncMock(return_value={"message": "Sale today!", "link": None})
    page_loader = MagicMock(return_value=None)
    with patch.object(fb_action, "_extract_post", extractor), patch.object(
        fb_action, "_load_fb_page", page_loader
    ):
        result = asyncio.run(fb_action._run(_action_ctx({"body": "Sale today!"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "connector"


def test_facebook_post_succeeds_on_graph_2xx():
    from backend.services.os_actions import social_facebook as fb_action

    extractor = AsyncMock(return_value={"message": "Sale today!", "link": None})
    page_loader = MagicMock(
        return_value={"page_id": "1234", "page_access_token": "tok"}
    )

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = b'{"id":"1234_5678"}'
    fake_resp.json.return_value = {"id": "1234_5678"}

    class _StubClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, data=None):
            return fake_resp

    with patch.object(fb_action, "_extract_post", extractor), patch.object(
        fb_action, "_load_fb_page", page_loader
    ), patch.object(fb_action.httpx, "AsyncClient", _StubClient):
        result = asyncio.run(fb_action._run(_action_ctx({"body": "Sale today!"})))
    assert result.status == "succeeded"
    assert result.response_payload["post_id"] == "1234_5678"


def test_facebook_post_records_graph_4xx_as_failed():
    from backend.services.os_actions import social_facebook as fb_action

    extractor = AsyncMock(return_value={"message": "Sale today!", "link": None})
    page_loader = MagicMock(
        return_value={"page_id": "1234", "page_access_token": "tok"}
    )

    fake_resp = MagicMock()
    fake_resp.status_code = 400
    fake_resp.content = b'{"error":{"message":"bad token"}}'
    fake_resp.text = '{"error":{"message":"bad token"}}'

    class _StubClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, data=None):
            return fake_resp

    with patch.object(fb_action, "_extract_post", extractor), patch.object(
        fb_action, "_load_fb_page", page_loader
    ), patch.object(fb_action.httpx, "AsyncClient", _StubClient):
        result = asyncio.run(fb_action._run(_action_ctx({"body": "Sale today!"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("status_code") == 400


# ---------------------------------------------------------------------------
# social.instagram.post — handler contract
#
# IG publishes in two Graph calls: POST /{ig_user_id}/media (create container)
# then POST /{ig_user_id}/media_publish. ``_IGStubClient`` routes by URL so a
# single stub can return distinct responses for each leg — letting us cover the
# success path AND the two distinct failure points (container vs publish).
# ---------------------------------------------------------------------------


def test_instagram_post_spec_is_well_formed():
    from backend.services.os_actions.social_instagram import SPEC

    assert SPEC.name == "social.instagram.post"
    assert SPEC.worker == "campaign"
    assert "instagram" in SPEC.required_connectors
    assert callable(SPEC.run)


def _ig_resp(status_code: int, payload: dict):
    resp = MagicMock()
    resp.status_code = status_code
    raw = json.dumps(payload).encode()
    resp.content = raw
    resp.text = raw.decode()
    resp.json.return_value = payload
    return resp


class _IGStubClient:
    """httpx.AsyncClient stand-in that routes POSTs by URL leg.

    ``container_resp`` is returned for the ``/media`` create call, ``publish_resp``
    for the ``/media_publish`` call. Either may be None to assert that leg is
    never reached.
    """

    container_resp = None
    publish_resp = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, data=None):
        if url.endswith("/media_publish"):
            assert self.publish_resp is not None, "publish leg should not be reached"
            return self.publish_resp
        return self.container_resp


def test_instagram_post_rejects_non_https_image():
    from backend.services.os_actions import social_instagram as ig_action

    extractor = AsyncMock(
        return_value={"caption": "hi", "image_url": "http://insecure/x.jpg"}
    )
    with patch.object(ig_action, "_extract_post", extractor):
        result = asyncio.run(ig_action._run(_action_ctx({"body": "post draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "validate"


def test_instagram_post_rejects_when_account_not_connected():
    from backend.services.os_actions import social_instagram as ig_action

    extractor = AsyncMock(
        return_value={"caption": "hi", "image_url": "https://cdn/x.jpg"}
    )
    loader = MagicMock(return_value=None)
    with patch.object(ig_action, "_extract_post", extractor), patch.object(
        ig_action, "_load_ig_account", loader
    ):
        result = asyncio.run(ig_action._run(_action_ctx({"body": "post draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "connector"


def test_instagram_post_succeeds_on_two_step_2xx():
    from backend.services.os_actions import social_instagram as ig_action

    extractor = AsyncMock(
        return_value={"caption": "Launch day", "image_url": "https://cdn/x.jpg"}
    )
    loader = MagicMock(return_value={"ig_user_id": "ig-1", "access_token": "tok"})

    stub = type(
        "_Stub",
        (_IGStubClient,),
        {
            "container_resp": _ig_resp(200, {"id": "container-123"}),
            "publish_resp": _ig_resp(200, {"id": "media-456"}),
        },
    )
    with patch.object(ig_action, "_extract_post", extractor), patch.object(
        ig_action, "_load_ig_account", loader
    ), patch.object(ig_action.httpx, "AsyncClient", stub):
        result = asyncio.run(ig_action._run(_action_ctx({"body": "post draft"})))
    assert result.status == "succeeded"
    assert result.response_payload["media_id"] == "media-456"
    assert result.response_payload["creation_id"] == "container-123"


def test_instagram_post_fails_when_container_create_4xx():
    from backend.services.os_actions import social_instagram as ig_action

    extractor = AsyncMock(
        return_value={"caption": "x", "image_url": "https://cdn/x.jpg"}
    )
    loader = MagicMock(return_value={"ig_user_id": "ig-1", "access_token": "tok"})

    stub = type(
        "_Stub",
        (_IGStubClient,),
        {
            "container_resp": _ig_resp(400, {"error": {"message": "bad image"}}),
            "publish_resp": None,  # publish must never be reached
        },
    )
    with patch.object(ig_action, "_extract_post", extractor), patch.object(
        ig_action, "_load_ig_account", loader
    ), patch.object(ig_action.httpx, "AsyncClient", stub):
        result = asyncio.run(ig_action._run(_action_ctx({"body": "post draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "ig_create_container"
    assert (result.error_detail or {}).get("status_code") == 400


def test_instagram_post_fails_when_publish_4xx():
    from backend.services.os_actions import social_instagram as ig_action

    extractor = AsyncMock(
        return_value={"caption": "x", "image_url": "https://cdn/x.jpg"}
    )
    loader = MagicMock(return_value={"ig_user_id": "ig-1", "access_token": "tok"})

    stub = type(
        "_Stub",
        (_IGStubClient,),
        {
            "container_resp": _ig_resp(200, {"id": "container-123"}),
            "publish_resp": _ig_resp(400, {"error": {"message": "rate limited"}}),
        },
    )
    with patch.object(ig_action, "_extract_post", extractor), patch.object(
        ig_action, "_load_ig_account", loader
    ), patch.object(ig_action.httpx, "AsyncClient", stub):
        result = asyncio.run(ig_action._run(_action_ctx({"body": "post draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "ig_publish"


# ---------------------------------------------------------------------------
# gbp.post — handler contract
# ---------------------------------------------------------------------------


def test_gbp_post_spec_is_well_formed():
    from backend.services.os_actions.gbp import SPEC

    assert SPEC.name == "gbp.post"
    assert SPEC.worker == "campaign"
    assert "google_business_profile" in SPEC.required_connectors
    assert callable(SPEC.run)


def _gbp_stub_client(resp):
    class _StubClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            return resp

    return _StubClient


def test_gbp_post_rejects_empty_summary():
    from backend.services.os_actions import gbp as gbp_action

    extractor = AsyncMock(return_value={"summary": "", "topic_type": "STANDARD"})
    with patch.object(gbp_action, "_extract_post", extractor):
        result = asyncio.run(gbp_action._run(_action_ctx({"body": "draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "validate"


def test_gbp_post_rejects_when_not_connected():
    from backend.services.os_actions import gbp as gbp_action

    extractor = AsyncMock(return_value={"summary": "Open late Friday"})
    loader = MagicMock(return_value=None)
    with patch.object(gbp_action, "_extract_post", extractor), patch.object(
        gbp_action, "_load_gbp", loader
    ):
        result = asyncio.run(gbp_action._run(_action_ctx({"body": "draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "connector"


def test_gbp_post_succeeds_on_2xx():
    from backend.services.os_actions import gbp as gbp_action

    extractor = AsyncMock(
        return_value={"summary": "Open late Friday", "topic_type": "STANDARD"}
    )
    loader = MagicMock(
        return_value={
            "access_token": "tok",
            "account_id": "acc-1",
            "location_id": "loc-1",
        }
    )
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.content = b'{"name":"accounts/acc-1/locations/loc-1/localPosts/9"}'
    fake_resp.json.return_value = {
        "name": "accounts/acc-1/locations/loc-1/localPosts/9"
    }
    with patch.object(gbp_action, "_extract_post", extractor), patch.object(
        gbp_action, "_load_gbp", loader
    ), patch.object(gbp_action.httpx, "AsyncClient", _gbp_stub_client(fake_resp)):
        result = asyncio.run(gbp_action._run(_action_ctx({"body": "draft"})))
    assert result.status == "succeeded"
    assert result.response_payload["name"].endswith("/localPosts/9")


def test_gbp_post_records_4xx_as_failed():
    from backend.services.os_actions import gbp as gbp_action

    extractor = AsyncMock(return_value={"summary": "Open late Friday"})
    loader = MagicMock(
        return_value={
            "access_token": "tok",
            "account_id": "acc-1",
            "location_id": "loc-1",
        }
    )
    fake_resp = MagicMock()
    fake_resp.status_code = 403
    fake_resp.content = b'{"error":"insufficient scope"}'
    fake_resp.text = '{"error":"insufficient scope"}'
    with patch.object(gbp_action, "_extract_post", extractor), patch.object(
        gbp_action, "_load_gbp", loader
    ), patch.object(gbp_action.httpx, "AsyncClient", _gbp_stub_client(fake_resp)):
        result = asyncio.run(gbp_action._run(_action_ctx({"body": "draft"})))
    assert result.status == "failed"
    assert (result.error_detail or {}).get("stage") == "gbp_api"
    assert (result.error_detail or {}).get("status_code") == 403


# ---------------------------------------------------------------------------
# End-to-end loop: approve deliverable -> run_action -> handler -> audit row
# ---------------------------------------------------------------------------


def test_e2e_approve_dispatches_action_and_marks_succeeded():
    """Full loop with an arbitrary registered action.

    Simulates a tenant approving an email.send deliverable:
    1. ``run_action`` is invoked (as FastAPI BackgroundTask would invoke it)
       with a fresh action_run_id and the matching deliverable_id.
    2. Stubbed DB returns the agent_run row + deliverable JSONB.
    3. The handler is replaced with a stub that asserts the ActionContext
       carries client_id, deliverable_id, action_run_id, action_type and
       both deliverable + agent_run dicts.
    4. ``run_action`` must write status=running then status=succeeded,
       with request_payload + response_payload populated from the
       handler's ActionResult.
    5. All DB calls must scope by client_id (tenant isolation).
    """
    agent_run_row = {
        "id": _DELIV,
        "client_id": _CLIENT_A,
        "deliverable_status": "pending_approval",
        "action_type": "email.send",
        "deliverable": {
            "title": "Follow-up draft",
            "body": "Hi Alice — confirming Tuesday 3pm.",
            "to": "alice@example.com",
        },
        "context": {"thread_id": "thr-1"},
    }
    db, builder = _stub_supabase(agent_run_row=agent_run_row)

    received_ctx: dict = {}

    async def fake_run(ctx):
        received_ctx["client_id"] = ctx.client_id
        received_ctx["deliverable_id"] = ctx.deliverable_id
        received_ctx["action_run_id"] = ctx.action_run_id
        received_ctx["action_type"] = ctx.action_type
        received_ctx["deliverable"] = ctx.deliverable
        received_ctx["agent_run"] = ctx.agent_run
        return ActionResult(
            status="succeeded",
            request_payload={"to": "alice@example.com"},
            response_payload={"resend_id": "re_abc123"},
        )

    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = fake_run

    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "email.send"))

    # Handler received a fully populated ActionContext
    assert received_ctx["client_id"] == _CLIENT_A
    assert received_ctx["deliverable_id"] == _DELIV
    assert received_ctx["action_run_id"] == _ACTION_RUN
    assert received_ctx["action_type"] == "email.send"
    assert received_ctx["deliverable"]["to"] == "alice@example.com"
    assert received_ctx["agent_run"]["id"] == _DELIV

    # DB audit trail: status moves running -> succeeded with payloads
    update_calls = [c.args[0] for c in builder.update.call_args_list]
    running = [u for u in update_calls if u.get("status") == "running"]
    succeeded = [u for u in update_calls if u.get("status") == "succeeded"]
    assert running, "running status never recorded"
    assert succeeded, "succeeded status never recorded"
    final = succeeded[-1]
    assert final["request_payload"] == {"to": "alice@example.com"}
    assert final["response_payload"] == {"resend_id": "re_abc123"}
    assert final.get("finished_at")
    assert final.get("updated_at")

    # Tenant scoping: every chained query goes through client_id
    eq_args = [c.args for c in builder.eq.call_args_list]
    flat = [a for tpl in eq_args for a in tpl]
    assert _CLIENT_A in flat, "client_id never used in scoping filter"
    # action_run_id is the audit row key used on update
    assert _ACTION_RUN in flat


def test_e2e_handler_failure_records_failed_status_with_error_detail():
    """If the handler raises, the loop must mark the action failed and
    capture the error detail — no silent failure."""
    agent_run_row = {
        "id": _DELIV,
        "client_id": _CLIENT_A,
        "deliverable_status": "pending_approval",
        "action_type": "email.send",
        "deliverable": {"to": "alice@example.com", "body": "hi"},
    }
    db, builder = _stub_supabase(agent_run_row=agent_run_row)

    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(side_effect=RuntimeError("resend rejected"))

    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "email.send"))

    update_calls = [c.args[0] for c in builder.update.call_args_list]
    failed = [u for u in update_calls if u.get("status") == "failed"]
    assert failed, "exception did not mark the action_run failed"
    err = failed[-1].get("error_detail") or {}
    assert "resend rejected" in (err.get("message") or "")


def test_e2e_handler_returns_failed_result_preserves_error_detail():
    """Handler returning ActionResult(status='failed', error_detail=...) must
    persist error_detail to os_action_runs without raising."""
    agent_run_row = {
        "id": _DELIV,
        "client_id": _CLIENT_A,
        "action_type": "email.send",
        "deliverable": {"to": "alice@example.com", "body": "hi"},
    }
    db, builder = _stub_supabase(agent_run_row=agent_run_row)

    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(
        return_value=ActionResult(
            status="failed",
            request_payload={"to": "alice@example.com"},
            response_payload=None,
            error_detail={"reason": "invalid_recipient"},
        )
    )

    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "email.send"))

    update_calls = [c.args[0] for c in builder.update.call_args_list]
    failed = [u for u in update_calls if u.get("status") == "failed"]
    assert failed
    assert failed[-1]["error_detail"] == {"reason": "invalid_recipient"}


def test_e2e_missing_deliverable_records_failed():
    """If the deliverable_id can't be loaded, the loop must still write
    a failed status — never leave the action_run row stuck in 'queued'."""
    db, builder = _stub_supabase(agent_run_row=None)  # empty .data
    stub_handler = MagicMock(spec=ActionSpec)
    stub_handler.run = AsyncMock(return_value=ActionResult(status="succeeded"))
    with patch(
        "backend.services.os_actions.get_service_supabase", return_value=db
    ), patch("backend.services.os_actions.get_action", return_value=stub_handler):
        asyncio.run(run_action(_ACTION_RUN, _CLIENT_A, _DELIV, "email.send"))

    update_calls = [c.args[0] for c in builder.update.call_args_list]
    failed = [u for u in update_calls if u.get("status") == "failed"]
    assert failed, "missing deliverable did not trigger failure write"
    err = failed[-1].get("error_detail") or {}
    assert "not found" in (err.get("message") or "").lower()
    stub_handler.run.assert_not_called()
