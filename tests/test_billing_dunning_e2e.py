"""End-to-end dunning flow via the real stripe_webhook route handler.

Drives ``POST /api/v1/webhooks/stripe`` with signed/mocked events the same way
``test_stripe_webhook.py`` does, exercising the full:

    Stripe event → webhook route → idempotency check
              → _handle_payment_failed → DB writes + email

Dunning policy found in backend/routers/billing.py::_handle_payment_failed
(no explicit max-attempt cap — Stripe controls retry schedule):

    invoice.payment_failed attempt N
        → tenants.plan_status = "paused"
        → tenants.billing_dunning_attempt_count = N  (set to invoice.attempt_count)
        → tenants.billing_dunning_last_sent_at = now()
        → billing_dunning_events row inserted (email_sent flag reflects send outcome)
        → email sent to owner

    invoice.payment_succeeded  → NOT handled (contract gap — see xfail test below)
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_invoice_failed_event(event_id: str, attempt_count: int) -> dict:
    """Minimal Stripe invoice.payment_failed event payload."""
    return {
        "id": event_id,
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": f"in_{event_id}",
                "customer": "cus_dunning_test",
                "subscription": "sub_dunning_test",
                "attempt_count": attempt_count,
                "next_payment_attempt": 1_800_000_000,
                "amount_due": 9900,
                "currency": "usd",
                "hosted_invoice_url": "https://invoice.stripe.test/pay",
                "invoice_pdf": "https://invoice.stripe.test/pdf",
            }
        },
    }


class _TableTracker:
    """Tracks the most recent update/insert for a single table call chain."""

    def __init__(self, data=None):
        self.data = data or []
        self.last_update: dict | None = None
        self.last_insert: dict | None = None

    def select(self, *_):
        return self

    def update(self, payload: dict):
        self.last_update = payload
        return self

    def insert(self, payload: dict):
        self.last_insert = payload
        return self

    def upsert(self, payload, **_):
        self.last_insert = payload
        return self

    def eq(self, *_):
        return self

    def limit(self, *_):
        return self

    def execute(self):
        return MagicMock(data=self.data)


def _build_dunning_db(
    *,
    tenant_id: str = "tenant-dunning-1",
    owner_email: str = "owner@dunning.test",
    business_name: str = "Dunning Plumbing Co",
):
    """Return (db_mock, tenants_tracker, tenant_update_tracker, dunning_tracker, idempotency_tracker).

    The idempotency tables are shared via db.table side_effect ordering.
    stripe_webhooks calls db.table() in this order per fresh event:
        1. idempotency_keys (upsert — returns inserted row so event is "new")
        2. tenants (select by stripe_customer_id)
        3. tenants (update plan_status / dunning counters)
        4. billing_dunning_events (insert)
    And after the handlers:
        5. idempotency_keys (update to record_response)
    """
    idempotency_upsert = _TableTracker(data=[{"key": "stripe:evt_new"}])
    tenant_select = _TableTracker(data=[{
        "id": tenant_id,
        "owner_email": owner_email,
        "business_name": business_name,
    }])
    tenant_update = _TableTracker(data=[{"id": tenant_id}])
    dunning_insert = _TableTracker(data=[{"id": "dun-new"}])
    idempotency_record = _TableTracker(data=[])

    db = MagicMock()
    db.table.side_effect = [
        idempotency_upsert,
        tenant_select,
        tenant_update,
        dunning_insert,
        idempotency_record,
    ]
    return db, tenant_select, tenant_update, dunning_insert, idempotency_upsert


async def _post_webhook(event: dict):
    """Call the stripe_webhook handler directly with a mocked Request."""
    from backend.routers.stripe_webhooks import stripe_webhook

    payload_bytes = json.dumps(event).encode()

    request = MagicMock()
    request.headers = {"stripe-signature": "test_sig"}

    async def _body():
        return payload_bytes

    request.body = _body
    return await stripe_webhook(request)


# ── attempt 1 ────────────────────────────────────────────────────────────────


class TestDunningAttemptOne:
    """First invoice.payment_failed drives the full handler."""

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_attempt_1_pauses_plan_and_sets_count_1(
        self, mock_construct, mock_db_factory, mock_email
    ):
        mock_email.return_value = {"success": True, "detail": "sent"}
        event = _make_invoice_failed_event("evt_attempt1", attempt_count=1)
        mock_construct.return_value = event

        db, _, tenant_update, dunning_insert, _ = _build_dunning_db()
        mock_db_factory.return_value = db

        result = await _post_webhook(event)

        assert result == {"status": "ok"}
        assert tenant_update.last_update["plan_status"] == "paused"
        assert tenant_update.last_update["billing_dunning_attempt_count"] == 1
        assert dunning_insert.last_insert["attempt_count"] == 1
        assert dunning_insert.last_insert["email_sent"] is True
        mock_email.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_attempt_1_dunning_event_has_correct_tenant_and_invoice(
        self, mock_construct, mock_db_factory, mock_email
    ):
        mock_email.return_value = {"success": True, "detail": "sent"}
        event = _make_invoice_failed_event("evt_attempt1b", attempt_count=1)
        mock_construct.return_value = event

        db, _, _, dunning_insert, _ = _build_dunning_db(tenant_id="t-abc")
        mock_db_factory.return_value = db

        await _post_webhook(event)

        assert dunning_insert.last_insert["tenant_id"] == "t-abc"
        assert dunning_insert.last_insert["stripe_invoice_id"] == "in_evt_attempt1b"
        assert dunning_insert.last_insert["stripe_customer_id"] == "cus_dunning_test"


# ── attempt 2 ────────────────────────────────────────────────────────────────


class TestDunningAttemptTwo:
    """Second invoice.payment_failed escalates count to 2, still paused."""

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_attempt_2_sets_count_2_still_paused(
        self, mock_construct, mock_db_factory, mock_email
    ):
        mock_email.return_value = {"success": True, "detail": "sent"}
        event = _make_invoice_failed_event("evt_attempt2", attempt_count=2)
        mock_construct.return_value = event

        db, _, tenant_update, dunning_insert, _ = _build_dunning_db()
        mock_db_factory.return_value = db

        result = await _post_webhook(event)

        assert result == {"status": "ok"}
        assert tenant_update.last_update["plan_status"] == "paused"
        assert tenant_update.last_update["billing_dunning_attempt_count"] == 2
        assert dunning_insert.last_insert["attempt_count"] == 2
        mock_email.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_attempt_2_email_sent_flag_matches_send_outcome(
        self, mock_construct, mock_db_factory, mock_email
    ):
        """email_sent in dunning event reflects actual send result."""
        mock_email.return_value = {"success": False, "detail": "send_failed"}
        event = _make_invoice_failed_event("evt_attempt2_fail_email", attempt_count=2)
        mock_construct.return_value = event

        db, _, _, dunning_insert, _ = _build_dunning_db()
        mock_db_factory.return_value = db

        await _post_webhook(event)

        assert dunning_insert.last_insert["email_sent"] is False


# ── no-tenant guard ───────────────────────────────────────────────────────────


class TestDunningUnknownCustomer:
    """Unknown Stripe customer must not raise — silent warning, no DB writes."""

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_unknown_customer_returns_ok_no_update(
        self, mock_construct, mock_db_factory, mock_email
    ):
        event = _make_invoice_failed_event("evt_unknown_cus", attempt_count=1)
        mock_construct.return_value = event

        # tenant select returns nothing
        idempotency_upsert = _TableTracker(data=[{"key": "x"}])
        tenant_select_empty = _TableTracker(data=[])
        idempotency_record = _TableTracker(data=[])

        db = MagicMock()
        db.table.side_effect = [idempotency_upsert, tenant_select_empty, idempotency_record]
        mock_db_factory.return_value = db

        result = await _post_webhook(event)

        assert result == {"status": "ok"}
        mock_email.assert_not_awaited()


# ── idempotency guard ─────────────────────────────────────────────────────────


class TestDunningIdempotency:
    """Duplicate event ID is skipped (idempotency layer)."""

    @pytest.mark.asyncio
    @patch("backend.services.email_sender.send_email", new_callable=AsyncMock)
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_duplicate_event_skips_handler(
        self, mock_construct, mock_db_factory, mock_email
    ):
        event = _make_invoice_failed_event("evt_dup", attempt_count=1)
        mock_construct.return_value = event

        # idempotency upsert returns empty (row already existed → duplicate)
        idempotency_upsert = _TableTracker(data=[])  # empty = already seen
        idempotency_select = _TableTracker(data=[{
            "key": "stripe:evt_dup",
            "response_status": 200,
            "response_body": {"status": "ok"},
        }])

        db = MagicMock()
        db.table.side_effect = [idempotency_upsert, idempotency_select]
        mock_db_factory.return_value = db

        result = await _post_webhook(event)

        assert result == {"status": "ok"}
        mock_email.assert_not_awaited()


# ── recovery (implemented 2026-06-10) ────────────────────────────────────────


class TestDunningRecoveryGap:
    """invoice.payment_succeeded clears dunning state — with a fraud guard.

    Originally an xfail documenting the gap; the handler now exists
    (billing._handle_payment_succeeded). Refinement over the drafted contract:
    recovery only fires when billing_dunning_attempt_count > 0, because a
    fraud-flagged checkout ALSO sets plan_status='paused' (with zero dunning
    count) and that pause must survive payment events — it clears only via
    manual review. Both sides of the guard are tested below.
    """

    @pytest.mark.asyncio
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_payment_succeeded_resets_dunning_counter(
        self, mock_construct, mock_db_factory
    ):
        """After payment_failed x2, a payment_succeeded must reset counter to 0."""
        succeeded_event = {
            "id": "evt_succeeded",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_succeeded",
                    "customer": "cus_dunning_test",
                    "subscription": "sub_dunning_test",
                    "amount_paid": 9900,
                    "currency": "usd",
                    "status": "paid",
                }
            },
        }
        mock_construct.return_value = succeeded_event

        idempotency_upsert = _TableTracker(data=[{"key": "x"}])
        tenant_select = _TableTracker(data=[{
            "id": "tenant-dunning-1",
            "plan_status": "paused",
            "billing_dunning_attempt_count": 2,
        }])
        tenant_update = _TableTracker(data=[{"id": "tenant-dunning-1"}])
        idempotency_record = _TableTracker(data=[])

        db = MagicMock()
        db.table.side_effect = [
            idempotency_upsert,
            tenant_select,
            tenant_update,
            idempotency_record,
        ]
        mock_db_factory.return_value = db

        result = await _post_webhook(succeeded_event)

        assert result == {"status": "ok"}
        assert tenant_update.last_update is not None, (
            "Expected a tenants.update() resetting dunning state"
        )
        assert tenant_update.last_update.get("billing_dunning_attempt_count") == 0
        assert tenant_update.last_update.get("plan_status") == "active"

    @pytest.mark.asyncio
    @patch("backend.routers.stripe_webhooks.get_service_supabase")
    @patch("backend.routers.stripe_webhooks.stripe.Webhook.construct_event")
    async def test_payment_succeeded_leaves_fraud_pause_untouched(
        self, mock_construct, mock_db_factory
    ):
        """A fraud pause (paused with zero dunning count) must NOT auto-clear."""
        succeeded_event = {
            "id": "evt_succeeded_fraud",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_fraud",
                    "customer": "cus_fraud_paused",
                    "subscription": "sub_fraud",
                    "amount_paid": 9900,
                    "currency": "usd",
                    "status": "paid",
                }
            },
        }
        mock_construct.return_value = succeeded_event

        idempotency_upsert = _TableTracker(data=[{"key": "x"}])
        tenant_select = _TableTracker(data=[{
            "id": "tenant-fraud-1",
            "plan_status": "paused",
            "billing_dunning_attempt_count": 0,
        }])
        idempotency_record = _TableTracker(data=[])

        # The guard returns early, so exactly THREE table() calls happen:
        # idempotency upsert, tenants select, idempotency response record.
        # A buggy handler that updates tenants would make a 4th call and
        # blow up on StopIteration — failing this test loudly.
        db = MagicMock()
        db.table.side_effect = [
            idempotency_upsert,
            tenant_select,
            idempotency_record,
        ]
        mock_db_factory.return_value = db

        result = await _post_webhook(succeeded_event)

        assert result == {"status": "ok"}
        assert tenant_select.last_update is None, (
            "Fraud-paused tenant must not be reactivated by a payment event"
        )
