"""Subscribe and unsubscribe confirmation emails.

Best-effort Resend sends after checkout activation and after /billing/cancel
schedules cancel_at_period_end. customer.subscription.deleted does not send.
Dedupe keys are written to idempotency_keys only after send_email succeeds.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config import settings
from backend.routers import auth_billing, billing
from backend.routers.stripe_webhooks import stripe_webhook as stripe_path_webhook
from backend.services import billing_confirmation_email as mailer

_TENANT = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
_PORTAL = "https://billing.example.test/billing"
_OWNER = "pii-owner@example.com"
_SECRET = "sk_test_SHOULD_NOT_LOG"


class Result:
    def __init__(self, data):
        self.data = data


class Store:
    """Minimal PostgREST stand-in for tenants and idempotency_keys."""

    def __init__(self):
        self.rows = {
            "tenants": [],
            "idempotency_keys": [],
            "tenant_cancellation_events": [],
        }
        self.updates = []
        self.fail_idempotency_insert = False

    def table(self, name):
        return Query(self, name)

    def keys(self):
        return [row.get("key") for row in self.rows["idempotency_keys"]]


class Query:
    def __init__(self, store, table):
        self.store = store
        self.table = table
        self.op = "select"
        self.payload = None
        self.filters = {}
        self.ignore_dupes = False

    def select(self, *args, **kwargs):
        self.op = "select"
        return self

    def update(self, payload):
        self.op = "update"
        self.payload = dict(payload)
        return self

    def insert(self, payload):
        self.op = "insert"
        self.payload = dict(payload)
        return self

    def upsert(self, payload, on_conflict="key", ignore_duplicates=False):
        self.op = "upsert"
        self.payload = dict(payload)
        self.ignore_dupes = ignore_duplicates
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def limit(self, _count):
        return self

    def execute(self):
        rows = self.store.rows.setdefault(self.table, [])
        if self.op == "select":
            matched = [
                row for row in rows
                if all(row.get(col) == val for col, val in self.filters.items())
            ]
            return Result(matched[:1])
        if self.op == "update":
            self.store.updates.append((self.table, dict(self.payload), dict(self.filters)))
            return Result([{"ok": True}])
        if self.op == "insert":
            if self.table == "idempotency_keys" and self.store.fail_idempotency_insert:
                raise RuntimeError("insert failed")
            row = dict(self.payload)
            if self.table == "idempotency_keys" and any(
                existing.get("key") == row.get("key") for existing in rows
            ):
                raise RuntimeError("duplicate key")
            rows.append(row)
            return Result([row])
        if self.op == "upsert":
            key = self.payload.get("key")
            existing = next((row for row in rows if row.get("key") == key), None)
            if existing is not None:
                if self.ignore_dupes:
                    return Result([])
                existing.update(self.payload)
                return Result([existing])
            rows.append(dict(self.payload))
            return Result([dict(self.payload)])
        if self.op == "delete":
            self.store.rows[self.table] = [
                row for row in rows
                if not all(row.get(col) == val for col, val in self.filters.items())
            ]
            return Result([])
        return Result([])


@pytest.fixture(autouse=True)
def _portal_and_tasks(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://billing.example.test")
    mailer._pending_tasks.set(None)
    yield
    mailer._pending_tasks.set(None)


def _session(**overrides):
    base = {
        "id": "cs_confirm_1",
        "metadata": {"tenant_id": _TENANT, "plan": "agent_os"},
        "customer": "cus_confirm",
        "customer_email": _OWNER,
        "subscription": "sub_confirm",
        "amount_total": 9999,
        "mode": "subscription",
        "status": "complete",
        "payment_status": "no_payment_required",
    }
    base.update(overrides)
    return base


def _event(event_id, event_type, obj):
    return {"id": event_id, "type": event_type, "data": {"object": obj}}


def _request():
    request = MagicMock()

    async def _body():
        return b"{}"

    request.body = _body
    request.headers = {"stripe-signature": "sig"}
    return request


def _our_messages(caplog):
    """Confirmation logs only. Checkout already logs the session email."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.getMessage().startswith("billing confirmation ")
    ]


async def _deliver_billing(store, event):
    with (
        patch.object(billing.stripe.Webhook, "construct_event", return_value=event),
        patch.object(billing, "get_service_supabase", return_value=store),
        patch.object(billing, "log_activity"),
        patch(
            "backend.services.owner_alerts.notify_new_paid_signup",
            new=AsyncMock(),
        ),
        patch(
            "backend.services.referral_reward.grant_referral_reward_for_signup",
            new=AsyncMock(),
        ),
    ):
        return await billing.stripe_webhook(_request())


async def _deliver_stripe_path(store, event):
    with (
        patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event", return_value=event),
        patch("backend.routers.stripe_webhooks.get_service_supabase", return_value=store),
        patch.object(billing, "log_activity"),
        patch(
            "backend.services.owner_alerts.notify_new_paid_signup",
            new=AsyncMock(),
        ),
        patch(
            "backend.services.referral_reward.grant_referral_reward_for_signup",
            new=AsyncMock(),
        ),
    ):
        return await stripe_path_webhook(_request())


def _capture(sent, result=None, error=None):
    async def _send(**kwargs):
        if error is not None:
            raise error
        sent.append(kwargs)
        return result or {"success": True, "detail": "sent"}

    return _send


@pytest.mark.asyncio
async def test_checkout_activation_sends_subscribe_email_once():
    store = Store()
    sent = []
    event = _event("evt_sub_1", "checkout.session.completed", _session())
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        first = await _deliver_billing(store, event)
        second = await _deliver_billing(
            store,
            _event("evt_sub_2", "checkout.session.completed", _session()),
        )

    assert first == {"status": "ok"}
    assert second == {"status": "ok"}
    assert len(sent) == 1
    body = sent[0]["body_html"]
    assert sent[0]["subject"] == "Your AgentNexLiFy subscription is active"
    assert sent[0]["to"] == _OWNER
    assert sent[0]["tenant_id"] == _TENANT
    assert "Agent OS" in body
    assert "active" in body
    assert _PORTAL in body
    assert "billing_sub_confirm:cs_confirm_1" in store.keys()
    activation = [payload for table, payload, _filt in store.updates if table == "tenants"]
    assert activation[-1]["plan"] == "agent_os"
    assert activation[-1]["plan_status"] == "active"


@pytest.mark.asyncio
async def test_stripe_webhook_path_sends_the_same_subscribe_email():
    store = Store()
    sent = []
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        result = await _deliver_stripe_path(
            store,
            _event("evt_path_1", "checkout.session.completed", _session(id="cs_path_1")),
        )

    assert result == {"status": "ok"}
    assert len(sent) == 1
    assert "billing_sub_confirm:cs_path_1" in store.keys()
    assert _PORTAL in sent[0]["body_html"]


@pytest.mark.asyncio
async def test_activation_failure_and_deleted_subscription_send_nothing():
    store = Store()
    sent = []
    unresolved = _session(metadata={"tenant_id": _TENANT}, amount_total=0, customer_email="")
    deleted = {
        "id": "sub_deleted_1",
        "customer": "cus_confirm",
        "metadata": {"tenant_id": _TENANT},
    }
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        failed = await _deliver_billing(
            store,
            _event("evt_fail", "checkout.session.completed", unresolved),
        )
        removed = await _deliver_billing(
            store,
            _event("evt_del", "customer.subscription.deleted", deleted),
        )
        removed_path = await _deliver_stripe_path(
            store,
            _event("evt_del_path", "customer.subscription.deleted", deleted),
        )

    assert failed == {"status": "ok"}
    assert removed == {"status": "ok"}
    assert removed_path == {"status": "ok"}
    assert sent == []
    assert not any(key.startswith("billing_sub_confirm:") for key in store.keys())
    assert not any(key.startswith("billing_unsub_confirm:") for key in store.keys())
    downgrades = [
        payload for table, payload, _filt in store.updates
        if table == "tenants" and payload.get("plan") == "free"
    ]
    assert len(downgrades) == 2
    assert all(row["plan_status"] == "cancelled" for row in downgrades)


@pytest.mark.asyncio
async def test_fraud_pause_does_not_send(caplog):
    store = Store()
    sent = []
    session = _session(payment_status="unpaid", customer_email=_OWNER)
    caplog.set_level(logging.INFO)
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        result = billing._handle_checkout_completed(store, session)
        await mailer.drain_billing_confirmation_tasks()

    assert result is None
    assert sent == []
    assert not any(key.startswith("billing_sub_confirm:") for key in store.keys())
    paused = [payload for table, payload, _filt in store.updates if table == "tenants"]
    assert paused[-1]["plan_status"] == "paused"
    mail_logs = "\n".join(_our_messages(caplog))
    assert _OWNER not in mail_logs
    assert _SECRET not in mail_logs


@pytest.mark.asyncio
async def test_send_failure_does_not_break_webhook_or_record_key(caplog):
    store = Store()
    caplog.set_level(logging.INFO)
    boom = RuntimeError(f"{_SECRET} {_OWNER} " + str({"customer": "cus_full_payload"}))
    with patch.object(mailer, "send_email", side_effect=_capture([], error=boom)):
        result = await _deliver_billing(
            store,
            _event("evt_boom", "checkout.session.completed", _session()),
        )

    assert result == {"status": "ok"}
    assert "billing_sub_confirm:cs_confirm_1" not in store.keys()
    messages = "\n".join(_our_messages(caplog))
    assert "billing_sub_confirm:cs_confirm_1" in messages
    assert "RuntimeError" in messages
    assert _OWNER not in messages
    assert _SECRET not in messages
    assert "cus_full_payload" not in messages


@pytest.mark.asyncio
async def test_cancel_sends_unsub_email_once_and_rerun_does_not(caplog):
    store = Store()
    store.rows["tenants"].append({
        "id": _TENANT,
        "stripe_customer_id": "cus_confirm",
        "plan": "agent_os",
        "owner_email": _OWNER,
    })
    period_end = int(datetime(2030, 1, 15, tzinfo=timezone.utc).timestamp())
    sub = MagicMock()
    sub.id = "sub_cancel_1"
    sub.current_period_end = period_end
    sent = []
    request = MagicMock()

    async def _json():
        return {"reason": "too_expensive", "reason_detail": "budget"}

    request.json = _json
    caplog.set_level(logging.INFO)

    with (
        patch.object(auth_billing, "get_service_supabase", return_value=store),
        patch.object(auth_billing, "ensure_stripe_configured"),
        patch.object(auth_billing.stripe.Subscription, "list", return_value=MagicMock(data=[sub])),
        patch.object(auth_billing.stripe.Subscription, "modify", return_value=MagicMock()),
        patch.object(auth_billing, "log_activity"),
        patch.object(mailer, "send_email", side_effect=_capture(sent)),
    ):
        first = await auth_billing.billing_cancel(
            request, claims={"tenant_id": _TENANT, "role": "owner"},
        )
        second = await auth_billing.billing_cancel(
            request, claims={"tenant_id": _TENANT, "role": "owner"},
        )

    assert first["status"] == "cancellation_scheduled"
    assert second["status"] == "cancellation_scheduled"
    assert first["current_period_end"] == period_end
    assert len(sent) == 1
    body = sent[0]["body_html"]
    assert sent[0]["subject"] == "Your AgentNexLiFy cancellation is scheduled"
    assert "Agent OS" in body
    assert "January 15, 2030" in body
    assert "keep access until" in body
    assert _PORTAL in body
    assert "resubscribe" in body
    assert "billing_unsub_confirm:sub_cancel_1" in store.keys()
    assert len(store.rows["tenant_cancellation_events"]) == 2
    rerun_logs = "\n".join(_our_messages(caplog))
    assert "AlreadyRecorded" in rerun_logs
    assert _OWNER not in rerun_logs


@pytest.mark.asyncio
async def test_cancel_send_failure_keeps_response_and_skips_key(caplog):
    store = Store()
    store.rows["tenants"].append({
        "id": _TENANT,
        "stripe_customer_id": "cus_confirm",
        "plan": "chatbot",
        "owner_email": _OWNER,
    })
    sub = MagicMock()
    sub.id = "sub_cancel_fail"
    sub.current_period_end = None
    request = MagicMock()

    async def _json():
        return {"reason": "other"}

    request.json = _json
    caplog.set_level(logging.WARNING)
    boom = RuntimeError(f"{_SECRET} {_OWNER}")
    with (
        patch.object(auth_billing, "get_service_supabase", return_value=store),
        patch.object(auth_billing, "ensure_stripe_configured"),
        patch.object(auth_billing.stripe.Subscription, "list", return_value=MagicMock(data=[sub])),
        patch.object(auth_billing.stripe.Subscription, "modify", return_value=MagicMock()),
        patch.object(auth_billing, "log_activity"),
        patch.object(mailer, "send_email", side_effect=_capture([], error=boom)),
    ):
        result = await auth_billing.billing_cancel(
            request, claims={"tenant_id": _TENANT, "role": "owner"},
        )

    assert result["status"] == "cancellation_scheduled"
    assert result["current_period_end"] is None
    assert "billing_unsub_confirm:sub_cancel_fail" not in store.keys()
    messages = "\n".join(_our_messages(caplog))
    assert "billing_unsub_confirm:sub_cancel_fail" in messages
    assert "RuntimeError" in messages
    assert _OWNER not in messages
    assert _SECRET not in messages
    assert "keep access until the end of the current billing period" not in messages


@pytest.mark.asyncio
async def test_cancel_endpoint_survives_confirmation_helper_raising():
    store = Store()
    store.rows["tenants"].append({
        "id": _TENANT,
        "stripe_customer_id": "cus_confirm",
        "plan": "chatbot",
        "owner_email": _OWNER,
    })
    sub = MagicMock()
    sub.id = "sub_helper_raise"
    sub.current_period_end = 1893456000
    request = MagicMock()

    async def _json():
        return {"reason": "temporary_pause"}

    request.json = _json

    async def _raise(**_kwargs):
        raise RuntimeError("helper blew up")

    with (
        patch.object(auth_billing, "get_service_supabase", return_value=store),
        patch.object(auth_billing, "ensure_stripe_configured"),
        patch.object(auth_billing.stripe.Subscription, "list", return_value=MagicMock(data=[sub])),
        patch.object(auth_billing.stripe.Subscription, "modify", return_value=MagicMock()),
        patch.object(auth_billing, "log_activity"),
        patch.object(auth_billing, "send_unsubscribe_confirmation", side_effect=_raise),
    ):
        result = await auth_billing.billing_cancel(
            request, claims={"tenant_id": _TENANT, "role": "owner"},
        )

    assert result["status"] == "cancellation_scheduled"
    assert result["current_period_end"] == 1893456000


def test_enqueue_failure_still_returns_activation():
    store = Store()
    session = _session()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("queue failed")

    with (
        patch.object(billing, "guard_checkout_for_fraud", return_value=None),
        patch.object(billing, "enqueue_subscription_confirmation", side_effect=_boom),
        patch.object(billing, "log_activity"),
    ):
        result = billing._handle_checkout_completed(store, session)

    assert result["event"] == "activated"
    assert result["plan"] == "agent_os"
    assert result["tenant_id"] == _TENANT


def test_subscribe_copy_escapes_plan_and_includes_portal():
    subject, body = mailer.build_subscribe_confirmation(
        plan='agent_os<script>',
        plan_status='active"<img>',
    )
    assert subject == "Your AgentNexLiFy subscription is active"
    assert "<script>" not in body
    assert "<img>" not in body
    assert "agent_os&lt;script&gt;" in body
    assert "active&quot;&lt;img&gt;" in body
    assert _PORTAL in body


@pytest.mark.asyncio
async def test_rejected_send_and_record_failure_do_not_keep_a_key(caplog):
    store = Store()
    caplog.set_level(logging.WARNING)
    rejected = []

    async def _reject(**kwargs):
        rejected.append(kwargs["subject"])
        return {"success": False, "detail": f"{_SECRET} {_OWNER}"}

    with patch.object(mailer, "send_email", side_effect=_reject):
        await mailer.send_subscription_confirmation(
            store,
            checkout_session_id="cs_reject",
            tenant_id=_TENANT,
            plan="chatbot",
            plan_status="active",
            recipient=_OWNER,
        )

    store.fail_idempotency_insert = True
    sent = []
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        await mailer.send_unsubscribe_confirmation(
            store,
            subscription_id="sub_record_fail",
            tenant_id=_TENANT,
            plan="chatbot",
            recipient=_OWNER,
            period_end_iso="not-a-date",
        )

    assert rejected == ["Your AgentNexLiFy subscription is active"]
    assert len(sent) == 1
    assert "Chatbot" in sent[0]["body_html"]
    assert "end of the current billing period" in sent[0]["body_html"]
    assert "billing_sub_confirm:cs_reject" not in store.keys()
    assert "billing_unsub_confirm:sub_record_fail" not in store.keys()
    messages = "\n".join(_our_messages(caplog))
    assert "SendFailed" in messages
    assert "RuntimeError" in messages
    assert _OWNER not in messages
    assert _SECRET not in messages


@pytest.mark.asyncio
async def test_missing_recipient_uses_owner_email_then_skips_without_logging_it(caplog):
    store = Store()
    store.rows["tenants"].append({"id": _TENANT, "owner_email": _OWNER})
    sent = []
    caplog.set_level(logging.INFO)
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        await mailer.send_subscription_confirmation(
            store,
            checkout_session_id="cs_lookup",
            tenant_id=_TENANT,
            plan="agent_os",
            plan_status="active",
            recipient="",
        )
        await mailer.send_subscription_confirmation(
            store,
            checkout_session_id="",
            tenant_id=_TENANT,
            plan="agent_os",
            plan_status="active",
            recipient="",
        )
        await mailer.send_unsubscribe_confirmation(
            store,
            subscription_id="sub_no_recipient",
            tenant_id=_TENANT,
            plan="agent_os",
            recipient="",
            period_end_iso=None,
        )
        await mailer.send_subscription_confirmation(
            store,
            checkout_session_id="cs_blank_owner",
            tenant_id="tenant-without-email",
            plan="chatbot",
            plan_status="active",
            recipient="",
        )

    assert len(sent) == 1
    assert sent[0]["to"] == _OWNER
    assert "billing_sub_confirm:cs_lookup" in store.keys()
    assert "billing_sub_confirm:cs_blank_owner" not in store.keys()
    messages = "\n".join(_our_messages(caplog))
    assert "MissingId" in messages
    assert "MissingRecipient" in messages
    assert _OWNER not in messages


@pytest.mark.asyncio
async def test_customer_details_email_and_lookup_error(caplog):
    store = Store()
    sent = []
    caplog.set_level(logging.WARNING)

    class BoomTenants:
        def table(self, name):
            if name == "tenants":
                raise RuntimeError(f"{_SECRET} {_OWNER}")
            return store.table(name)

    session = {
        "id": "cs_details",
        "customer_details": {"email": _OWNER},
    }
    with patch.object(mailer, "send_email", side_effect=_capture(sent)):
        mailer.enqueue_subscription_confirmation(
            store, session, tenant_id=_TENANT, plan="chatbot",
        )
        await mailer.drain_billing_confirmation_tasks()
        await mailer.send_subscription_confirmation(
            BoomTenants(),
            checkout_session_id="cs_lookup_fail",
            tenant_id=_TENANT,
            plan="chatbot",
            plan_status="active",
            recipient="",
        )

    assert len(sent) == 1
    assert sent[0]["to"] == _OWNER
    assert "Chatbot" in sent[0]["body_html"]
    assert "billing_sub_confirm:cs_details" in store.keys()
    assert "billing_sub_confirm:cs_lookup_fail" not in store.keys()
    messages = "\n".join(_our_messages(caplog))
    assert "RuntimeError" in messages
    assert _OWNER not in messages
    assert _SECRET not in messages


@pytest.mark.asyncio
async def test_idempotency_lookup_shape_and_drain_failure_log_type_only(caplog):
    caplog.set_level(logging.WARNING)

    class ShapeDB:
        def table(self, _name):
            query = MagicMock()
            query.select.return_value = query
            query.eq.return_value = query
            query.limit.return_value = query
            query.execute.return_value = MagicMock(data=object())
            return query

    await mailer.send_unsubscribe_confirmation(
        ShapeDB(),
        subscription_id="sub_shape",
        tenant_id=_TENANT,
        plan="chatbot",
        recipient=_OWNER,
        period_end_iso="2030-01-15T00:00:00+00:00",
    )

    async def _boom():
        raise RuntimeError(f"{_SECRET} {_OWNER}")

    mailer._pending_tasks.set([__import__("asyncio").create_task(_boom())])
    await mailer.drain_billing_confirmation_tasks()

    messages = "\n".join(_our_messages(caplog))
    assert "TypeError" in messages
    assert "billing_unsub_confirm:sub_shape" in messages
    assert "billing_confirm:drain" in messages
    assert "RuntimeError" in messages
    assert _OWNER not in messages
    assert _SECRET not in messages


def test_enqueue_outside_a_running_loop_does_not_schedule():
    store = Store()
    mailer.enqueue_subscription_confirmation(
        store,
        _session(),
        tenant_id=_TENANT,
        plan="agent_os",
    )
    assert mailer._pending_tasks.get() is None
    assert store.keys() == []
