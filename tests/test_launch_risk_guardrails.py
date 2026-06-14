from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class Chain:
    def __init__(self, data=None):
        self.data = data or []
        self.updated = None
        self.inserted = None

    def select(self, *args, **kwargs):
        return self

    def update(self, data):
        self.updated = data
        return self

    def insert(self, data):
        self.inserted = data
        return self

    def eq(self, *args):
        return self

    def limit(self, *args):
        return self

    def execute(self):
        return MagicMock(data=self.data)


class FailingChain(Chain):
    def execute(self):
        raise RuntimeError("db write failed")


def test_ai_usage_policy_uses_plan_baseline():
    from backend.services.ai_usage_guard import resolve_ai_usage_policy

    policy = resolve_ai_usage_policy({"id": "tenant-1", "plan": "growth"})

    assert policy.alert_threshold_tokens == 3_000_000
    assert policy.hard_limit_tokens == 5_000_000


def test_ai_usage_policy_honors_tenant_overrides():
    from backend.services.ai_usage_guard import resolve_ai_usage_policy

    policy = resolve_ai_usage_policy({
        "id": "tenant-1",
        "plan": "growth",
        "ai_monthly_token_alert_threshold": 12_000,
        "ai_monthly_token_hard_limit": 20_000,
    })

    assert policy.alert_threshold_tokens == 12_000
    assert policy.hard_limit_tokens == 20_000


def test_estimate_widget_chat_tokens_counts_prompt_history_and_completion_budget():
    from backend.services.ai_usage_guard import estimate_widget_chat_tokens

    estimate = estimate_widget_chat_tokens(
        system_prompt="a" * 400,
        messages=[{"role": "user", "content": "b" * 200}],
        max_tokens=320,
    )

    assert estimate == 500


@pytest.mark.asyncio
@patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
async def test_payment_failed_records_dunning_event(mock_send_email):
    from backend.routers.billing import _handle_payment_failed

    mock_send_email.return_value = {"success": True, "detail": "sent"}
    tenant_select = Chain(data=[{
        "id": "tenant-1",
        "owner_email": "owner@example.com",
        "business_name": "Aidan Plumbing",
    }])
    tenant_update = Chain(data=[{"id": "tenant-1"}])
    dunning_insert = Chain(data=[{"id": "dun-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, tenant_update, dunning_insert]

    await _handle_payment_failed(db, {
        "id": "in_123",
        "customer": "cus_123",
        "subscription": "sub_123",
        "attempt_count": 2,
        "next_payment_attempt": 1_800_000_000,
        "amount_due": 24900,
        "currency": "usd",
        "hosted_invoice_url": "https://invoice.stripe.test/pay",
    })

    assert tenant_update.updated["plan_status"] == "paused"
    assert tenant_update.updated["billing_dunning_attempt_count"] == 2
    assert dunning_insert.inserted["tenant_id"] == "tenant-1"
    assert dunning_insert.inserted["stripe_invoice_id"] == "in_123"
    assert dunning_insert.inserted["email_sent"] is True
    mock_send_email.assert_awaited_once()


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_admin_refund_creates_stripe_refund_and_audit_row(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[])
    refund_insert = Chain(data=[{"id": "refund-row"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select, refund_insert]
    mock_db_factory.return_value = db
    mock_refund_create.return_value = {
        "id": "re_123",
        "amount": 24900,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_123",
        "reason": "requested_by_customer",
    }

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-req-123",
            payment_intent="pi_123",
            amount_cents=24900,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested refund before filing dispute.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_called_once()
    assert mock_refund_create.call_args.kwargs["idempotency_key"] == (
        "agentnexlify-refund:tenant-1:refund-req-123"
    )
    assert mock_refund_create.call_args.kwargs["metadata"]["refund_request_id"] == "refund-req-123"
    assert refund_insert.inserted["refund_request_id"] == "refund-req-123"
    assert refund_insert.inserted["stripe_refund_id"] == "re_123"
    assert refund_insert.inserted["tenant_id"] == "tenant-1"
    assert result["status"] == "refunded"
    assert result["idempotent_replay"] is False
    mock_log_activity.assert_called_once()


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_admin_refund_replay_returns_existing_audit_without_creating_refund(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    existing_refund_select = Chain(data=[{
        "stripe_refund_id": "re_existing",
        "amount_cents": 24900,
        "currency": "usd",
        "status": "succeeded",
        "refund_request_id": "refund-req-123",
    }])
    db = MagicMock()
    db.table.side_effect = [tenant_select, existing_refund_select]
    mock_db_factory.return_value = db

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-req-123",
            payment_intent="pi_123",
            amount_cents=24900,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested refund before filing dispute.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_not_called()
    mock_log_activity.assert_not_called()
    assert result["status"] == "refunded"
    assert result["stripe_refund_id"] == "re_existing"
    assert result["idempotent_replay"] is True


@pytest.mark.asyncio
@patch("backend.routers.billing.log_activity")
@patch("backend.routers.billing.stripe.Refund.create")
@patch("backend.routers.billing.ensure_stripe_configured")
@patch("backend.routers.billing._verify_admin_secret")
@patch("backend.routers.billing.get_service_supabase")
async def test_admin_refund_audit_insert_failure_returns_existing_refund_audit(
    mock_db_factory,
    _mock_verify,
    _mock_ensure,
    mock_refund_create,
    mock_log_activity,
):
    from backend.routers.billing import AdminRefundRequest, admin_create_refund

    tenant_select = Chain(data=[{"id": "tenant-1", "owner_email": "owner@example.com"}])
    no_existing_request = Chain(data=[])
    failing_insert = FailingChain()
    existing_refund_select = Chain(data=[{
        "stripe_refund_id": "re_123",
        "amount_cents": 24900,
        "currency": "usd",
        "status": "succeeded",
        "refund_request_id": "refund-req-123",
    }])
    db = MagicMock()
    db.table.side_effect = [
        tenant_select,
        no_existing_request,
        failing_insert,
        existing_refund_select,
    ]
    mock_db_factory.return_value = db
    mock_refund_create.return_value = {
        "id": "re_123",
        "amount": 24900,
        "currency": "usd",
        "status": "succeeded",
        "payment_intent": "pi_123",
        "reason": "requested_by_customer",
    }

    result = await admin_create_refund(
        AdminRefundRequest(
            tenant_id="tenant-1",
            refund_request_id="refund-req-123",
            payment_intent="pi_123",
            amount_cents=24900,
            stripe_reason="requested_by_customer",
            internal_reason="Customer requested refund before filing dispute.",
            requested_by="aidan",
        ),
        x_api_secret="secret",
    )

    mock_refund_create.assert_called_once()
    mock_log_activity.assert_not_called()
    assert result["status"] == "refunded"
    assert result["stripe_refund_id"] == "re_123"
    assert result["idempotent_replay"] is True


@pytest.mark.asyncio
@patch("backend.routers.auth_billing.log_activity")
@patch("backend.routers.auth_billing.stripe.Subscription.modify")
@patch("backend.routers.auth_billing.stripe.Subscription.list")
@patch("backend.routers.auth_billing.ensure_stripe_configured")
@patch("backend.routers.auth_billing.get_service_supabase")
async def test_billing_cancel_requires_and_persists_reason(
    mock_db_factory,
    _mock_ensure,
    mock_subscription_list,
    mock_subscription_modify,
    mock_log_activity,
):
    from backend.routers.auth_billing import billing_cancel

    tenant_select = Chain(data=[{
        "stripe_customer_id": "cus_123",
        "plan": "growth",
    }])
    tenant_update = Chain(data=[{"id": "tenant-1"}])
    cancellation_insert = Chain(data=[{"id": "cancel-1"}])
    db = MagicMock()
    db.table.side_effect = [tenant_select, tenant_update, cancellation_insert]
    mock_db_factory.return_value = db
    mock_subscription_list.return_value = MagicMock(
        data=[MagicMock(id="sub_123", current_period_end=1_800_000_000)]
    )
    request = MagicMock()

    async def json_body():
        return {
            "reason": "not_enough_leads",
            "reason_detail": "Need to pause until traffic improves.",
        }

    request.json = json_body

    result = await billing_cancel(
        request,
        claims={"tenant_id": "tenant-1", "role": "owner"},
    )

    mock_subscription_modify.assert_called_once()
    assert tenant_update.updated["cancellation_reason"] == "not_enough_leads"
    assert cancellation_insert.inserted["reason"] == "not_enough_leads"
    assert result["status"] == "cancellation_scheduled"
    mock_log_activity.assert_called_once()
