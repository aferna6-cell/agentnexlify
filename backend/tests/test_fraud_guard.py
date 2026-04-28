"""Tests for fraud_guard service."""

import pytest
from fastapi import HTTPException, Request
from unittest.mock import MagicMock, patch

from backend.services.fraud_guard import (
    guard_checkout_for_fraud,
    is_disposable_email,
    check_registration_velocity,
    MAX_SIGNUPS_PER_IP_PER_HOUR,
    MAX_SIGNUPS_PER_EMAIL_PER_HOUR,
)


class TestDisposableEmail:
    def test_allows_real_email(self):
        assert is_disposable_email("aidan@example.com") is False
        assert is_disposable_email("user@gmail.com") is False

    def test_blocks_disposable_domain(self):
        assert is_disposable_email("user@mailinator.com") is True
        assert is_disposable_email("user@yopmail.com") is True
        assert is_disposable_email("user@10minutemail.com") is True

    def test_case_insensitive(self):
        assert is_disposable_email("user@YOPMAIL.COM") is True
        assert is_disposable_email("user@Mailinator.Com") is True

    def test_malformed_email_safe(self):
        assert is_disposable_email("not-an-email") is False
        assert is_disposable_email("") is False


class TestCheckoutFraud:
    @patch("backend.services.fraud_guard.stripe.PaymentIntent.retrieve")
    def test_allows_clean_payment(self, mock_retrieve):
        mock_retrieve.return_value = {
            "charges": {
                "data": [{
                    "outcome": {"type": "authorized"},
                    "payment_method_details": {"card": {"country": "US"}},
                    "billing_details": {"address": {"country": "US"}},
                }]
            }
        }
        result = guard_checkout_for_fraud({
            "payment_status": "paid",
            "payment_intent": "pi_test",
        })
        assert result is None

    def test_blocks_unpaid(self):
        result = guard_checkout_for_fraud({
            "payment_status": "unpaid",
            "payment_intent": "pi_test",
        })
        assert result == "payment_status=unpaid"

    def test_blocks_no_payment_intent(self):
        result = guard_checkout_for_fraud({
            "payment_status": "paid",
            "payment_intent": None,
        })
        assert result == "no_payment_intent"

    @patch("backend.services.fraud_guard.stripe.PaymentIntent.retrieve")
    def test_blocks_radar_blocked(self, mock_retrieve):
        mock_retrieve.return_value = {
            "charges": {
                "data": [{
                    "outcome": {"type": "blocked"},
                    "payment_method_details": {"card": {"country": "US"}},
                    "billing_details": {"address": {"country": "US"}},
                }]
            }
        }
        result = guard_checkout_for_fraud({
            "payment_status": "paid",
            "payment_intent": "pi_test",
        })
        assert result == "radar_blocked"

    @patch("backend.services.fraud_guard.stripe.PaymentIntent.retrieve")
    def test_flags_cc_mismatch(self, mock_retrieve):
        mock_retrieve.return_value = {
            "charges": {
                "data": [{
                    "outcome": {"type": "authorized"},
                    "payment_method_details": {"card": {"country": "RU"}},
                    "billing_details": {"address": {"country": "US"}},
                }]
            }
        }
        result = guard_checkout_for_fraud({
            "payment_status": "paid",
            "payment_intent": "pi_test",
        })
        assert result == "cc_country_mismatch"

    @patch("backend.services.fraud_guard.stripe.PaymentIntent.retrieve")
    def test_permissive_on_stripe_error(self, mock_retrieve):
        mock_retrieve.side_effect = Exception("stripe down")
        result = guard_checkout_for_fraud({
            "payment_status": "paid",
            "payment_intent": "pi_test",
        })
        assert result is None


class TestVelocityLimits:
    def _make_request(self, ip="1.2.3.4"):
        req = MagicMock(spec=Request)
        req.headers = {"x-forwarded-for": ip}
        req.client = MagicMock()
        req.client.host = ip
        return req

    @patch("backend.services.fraud_guard.get_service_supabase")
    def test_allows_first_signup(self, mock_get_supabase):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[], count=0)
        mock_get_supabase.return_value = db

        req = self._make_request()
        check_registration_velocity(req, "new@example.com")  # should not raise

    @patch("backend.services.fraud_guard.get_service_supabase")
    def test_blocks_ip_velocity(self, mock_get_supabase):
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[{"id": "1"}] * MAX_SIGNUPS_PER_IP_PER_HOUR,
            count=MAX_SIGNUPS_PER_IP_PER_HOUR,
        )
        mock_get_supabase.return_value = db

        req = self._make_request()
        with pytest.raises(HTTPException) as exc_info:
            check_registration_velocity(req, "new@example.com")
        assert exc_info.value.status_code == 429

    @patch("backend.services.fraud_guard.get_service_supabase")
    def test_blocks_email_velocity(self, mock_get_supabase):
        db = MagicMock()

        def ip_side_effect(*args, **kwargs):
            resp = MagicMock()
            resp.data = []
            resp.count = 0
            return resp

        def email_side_effect(*args, **kwargs):
            resp = MagicMock()
            resp.data = [{"id": "1"}] * MAX_SIGNUPS_PER_EMAIL_PER_HOUR
            resp.count = MAX_SIGNUPS_PER_EMAIL_PER_HOUR
            return resp

        db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = [
            ip_side_effect(),
            email_side_effect(),
        ]
        mock_get_supabase.return_value = db

        req = self._make_request()
        with pytest.raises(HTTPException) as exc_info:
            check_registration_velocity(req, "repeat@example.com")
        assert exc_info.value.status_code == 429
