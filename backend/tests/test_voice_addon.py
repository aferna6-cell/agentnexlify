"""Voice receptionist add-on (+$49.99/mo, 2026-08-25).

Contract:
  - Checkout requires an active paid plan, refuses plans that already include
    voice (agent_os + grandfathered), refuses double-purchase, 503s until
    STRIPE_PRICE_VOICE_ADDON_MONTHLY is configured.
  - Webhook events tagged metadata.addon='voice' NEVER reach the plan
    handlers; they only flip tenants.voice_addon_active (+ voice_ai_enabled
    on first activation).
  - _ai_voice_mode grants the live AI loop to a chatbot tenant with the
    add-on; without it, chatbot stays voicemail-mode (existing gate tests
    in test_voice_plan_gate.py still hold).

Run: pytest backend/tests/test_voice_addon.py --noconftest
"""

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "1")

from backend.tests.fake_supabase import db as _db, run as _run


# --- gate --------------------------------------------------------------------


class TestAiVoiceModeWithAddon:
    def test_chatbot_with_addon_gets_live_ai(self):
        from backend.services.voice_phone_routing import _ai_voice_mode

        tenant = {
            "plan": "chatbot",
            "voice_ai_enabled": True,
            "voice_addon_active": True,
        }
        assert _ai_voice_mode(tenant) is True

    def test_chatbot_without_addon_stays_voicemail(self):
        from backend.services.voice_phone_routing import _ai_voice_mode

        tenant = {"plan": "chatbot", "voice_ai_enabled": True}
        assert _ai_voice_mode(tenant) is False

    def test_addon_without_voice_ai_enabled_stays_off(self):
        from backend.services.voice_phone_routing import _ai_voice_mode

        tenant = {
            "plan": "chatbot",
            "voice_ai_enabled": False,
            "voice_addon_active": True,
        }
        assert _ai_voice_mode(tenant) is False

    def test_agent_os_unaffected(self):
        from backend.services.voice_phone_routing import _ai_voice_mode

        tenant = {"plan": "agent_os", "voice_ai_enabled": True}
        assert _ai_voice_mode(tenant) is True

    def test_phone_select_includes_addon_column(self):
        from backend.services.voice_phone_routing import _TENANT_PHONE_SELECT

        assert "voice_addon_active" in _TENANT_PHONE_SELECT


# --- checkout endpoint -------------------------------------------------------


class TestVoiceAddonCheckout:
    def _tenant_db(self, **overrides):
        tenant = {
            "id": "t1",
            "owner_email": "owner@example.com",
            "business_name": "Biz",
            "plan": "chatbot",
            "plan_status": "active",
            "voice_addon_active": False,
        }
        tenant.update(overrides)
        return _db({"tenants": [tenant]})

    def _checkout(self, db, price_id="price_live_voice"):
        from backend.routers import billing_addons

        session = MagicMock()
        session.url = "https://stripe.example/voice"
        session.id = "cs_voice"
        stripe_mock = MagicMock()
        stripe_mock.checkout.Session.create.return_value = session
        customer = MagicMock()
        customer.id = "cus_1"
        with patch.object(billing_addons, "stripe", stripe_mock), patch.object(
            billing_addons, "VOICE_ADDON_PRICE_ID", price_id
        ), patch.object(billing_addons, "ensure_stripe_configured"), patch.object(
            billing_addons, "get_service_supabase", return_value=db
        ), patch.object(
            billing_addons, "get_or_create_customer", return_value=customer
        ):
            out = _run(
                billing_addons.voice_addon_checkout(claims={"tenant_id": "t1"})
            )
        return out, stripe_mock

    def test_chatbot_tenant_gets_checkout_with_addon_metadata(self):
        out, stripe_mock = self._checkout(self._tenant_db())
        assert out["checkout_url"] == "https://stripe.example/voice"
        params = stripe_mock.checkout.Session.create.call_args.kwargs
        assert params["metadata"] == {"tenant_id": "t1", "addon": "voice"}
        assert params["subscription_data"]["metadata"]["addon"] == "voice"
        assert params["line_items"] == [{"price": "price_live_voice", "quantity": 1}]
        assert params["mode"] == "subscription"

    def _expect_400(self, db, match):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as err:
            self._checkout(db)
        assert err.value.status_code == 400
        assert match in str(err.value.detail)

    def test_free_plan_refused(self):
        self._expect_400(self._tenant_db(plan="free"), "paid plan")

    def test_paused_plan_refused(self):
        self._expect_400(self._tenant_db(plan_status="paused"), "paid plan")

    def test_agent_os_refused_already_included(self):
        self._expect_400(self._tenant_db(plan="agent_os"), "already includes")

    def test_enterprise_refused_already_included(self):
        self._expect_400(self._tenant_db(plan="enterprise"), "already includes")

    def test_double_purchase_refused(self):
        self._expect_400(self._tenant_db(voice_addon_active=True), "already active")

    def test_unconfigured_price_503s(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as err:
            self._checkout(self._tenant_db(), price_id="price_voice_addon_monthly")
        assert err.value.status_code == 503
        assert "STRIPE_PRICE_VOICE_ADDON_MONTHLY" in str(err.value.detail)


# --- webhook routing ---------------------------------------------------------


class _Recorder:
    """Fake supabase client recording table().update() payloads."""

    def __init__(self, rows_by_table=None):
        self.updates = []
        self._rows = rows_by_table or {}

    def table(self, name):
        rec = self

        class _Q:
            def __init__(self):
                self._pending = None

            def update(self, payload):
                self._pending = ("update", name, payload)
                return self

            def select(self, *a, **k):
                return self

            def insert(self, payload):
                self._pending = ("insert", name, payload)
                return self

            def eq(self, *a):
                return self

            def limit(self, *a):
                return self

            def execute(self):
                if self._pending:
                    rec.updates.append(self._pending)
                result = MagicMock()
                result.data = rec._rows.get(name, [])
                return result

        return _Q()


class TestVoiceAddonWebhook:
    def test_is_voice_addon_detects_metadata(self):
        from backend.routers.billing import _is_voice_addon

        assert _is_voice_addon({"metadata": {"addon": "voice"}}) is True
        assert _is_voice_addon(
            {"subscription_data": {"metadata": {"addon": "voice"}}}
        ) is True
        assert _is_voice_addon({"metadata": {"addon": "marketing"}}) is False
        assert _is_voice_addon({}) is False

    def test_completed_sets_both_flags_and_never_touches_plan(self):
        from backend.routers.billing import _handle_voice_addon_completed

        db = _Recorder()
        _handle_voice_addon_completed(
            db, {"id": "cs_1", "metadata": {"addon": "voice", "tenant_id": "t1"}}
        )
        tenant_updates = [u for u in db.updates if u[1] == "tenants"]
        assert len(tenant_updates) == 1
        payload = tenant_updates[0][2]
        assert payload == {"voice_addon_active": True, "voice_ai_enabled": True}
        assert "plan" not in payload and "plan_status" not in payload

    def test_subscription_deleted_clears_addon_only(self):
        from backend.routers.billing import _handle_voice_addon_deleted

        db = _Recorder()
        _handle_voice_addon_deleted(
            db, {"metadata": {"addon": "voice", "tenant_id": "t1"}}
        )
        payload = db.updates[0][2]
        assert payload == {"voice_addon_active": False}

    def test_subscription_updated_tracks_status(self):
        from backend.routers.billing import _handle_voice_addon_subscription_updated

        db = _Recorder()
        _handle_voice_addon_subscription_updated(
            db,
            {"metadata": {"addon": "voice", "tenant_id": "t1"}, "status": "past_due"},
        )
        assert db.updates[0][2] == {"voice_addon_active": False}

        db2 = _Recorder()
        _handle_voice_addon_subscription_updated(
            db2,
            {"metadata": {"addon": "voice", "tenant_id": "t1"}, "status": "active"},
        )
        assert db2.updates[0][2] == {"voice_addon_active": True}

    def test_unresolvable_tenant_is_noop(self):
        from backend.routers.billing import _handle_voice_addon_completed

        db = _Recorder()  # no tenants rows -> customer lookup misses
        _handle_voice_addon_completed(db, {"id": "cs_1", "metadata": {"addon": "voice"}})
        assert [u for u in db.updates if u[0] == "update"] == []
