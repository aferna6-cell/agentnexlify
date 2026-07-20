"""Outbound guardrail (enterprise-audit item 6) — pattern + wiring contracts.

The guard's job: an auto-approved draft containing a secret, SSN, Luhn-valid
card number, or payment-redirection language parks at pending_approval
instead of auto-sending. Clean drafts and human-gated drafts pass untouched.
"""

from unittest.mock import patch

from backend.services.os_outbound_guard import (
    apply_outbound_guard,
    scan_deliverable,
    scan_text,
)


class TestScanText:
    def test_clean_marketing_copy_passes(self):
        text = (
            "Hi Sam! Your quote for the brake job is ready — $420 parts and "
            "labor. Call us at (555) 010-7788 or reply to book. Order #4111."
        )
        assert scan_text(text) == []

    def test_contact_details_are_not_flagged(self):
        assert scan_text("Reach me at aidan@example.com or +1 555 010 2233") == []

    def test_api_key_flagged(self):
        assert "api_key" in scan_text("here is the key sk-abc123DEF456ghi789jkl")

    def test_aws_key_flagged(self):
        assert "aws_access_key" in scan_text("creds: AKIAIOSFODNN7EXAMPLE")

    def test_github_token_flagged(self):
        assert "github_token" in scan_text("ghp_abcdefghijklmnopqrstuv0123456789")

    def test_private_key_flagged(self):
        assert "private_key" in scan_text("-----BEGIN RSA PRIVATE KEY-----")

    def test_jwt_flagged(self):
        token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig"
        assert "jwt" in scan_text(f"token: {token}")

    def test_ssn_flagged(self):
        assert "ssn" in scan_text("SSN on file: 123-45-6789")

    def test_luhn_valid_card_flagged(self):
        assert "card_number" in scan_text("card 4111 1111 1111 1111 exp 12/28")

    def test_luhn_invalid_digit_run_passes(self):
        # 16 digits, fails Luhn — an order/tracking number, not a card.
        assert scan_text("tracking 1234 5678 9012 3456") == []

    def test_payment_redirect_flagged(self):
        flags = scan_text("Please wire the money to our new bank account today")
        assert "payment_redirect" in flags

    def test_gift_card_redirect_flagged(self):
        assert "payment_redirect" in scan_text("You can pay with gift cards")

    def test_empty_text_passes(self):
        assert scan_text("") == []


class TestScanDeliverable:
    def test_title_and_body_both_scanned(self):
        assert scan_deliverable({"title": "SSN 123-45-6789", "body": "hi"}) == ["ssn"]
        assert scan_deliverable({"title": "hi", "body": "SSN 123-45-6789"}) == ["ssn"]

    def test_non_dict_passes(self):
        assert scan_deliverable(None) == []
        assert scan_deliverable("nope") == []


class TestApplyOutboundGuard:
    def test_clean_approved_draft_stays_approved(self):
        status, flags = apply_outbound_guard(
            "t1", "sales", {"title": "Quote", "body": "See attached."}, "approved"
        )
        assert status == "approved"
        assert flags == []

    def test_flagged_approved_draft_downgrades_and_logs(self):
        with patch(
            "backend.services.os_outbound_guard.log_activity"
        ) as activity:
            status, flags = apply_outbound_guard(
                "t1",
                "sales",
                {"title": "Update", "body": "wire the money to our new bank account"},
                "approved",
            )
        assert status == "pending_approval"
        assert flags == ["payment_redirect"]
        activity.assert_called_once()
        assert activity.call_args.kwargs["tenant_id"] == "t1"
        assert (
            activity.call_args.kwargs["activity_type"] == "outbound_guard_flagged"
        )

    def test_pending_draft_not_scanned(self):
        status, flags = apply_outbound_guard(
            "t1", "sales", {"body": "SSN 123-45-6789"}, "pending_approval"
        )
        assert status == "pending_approval"
        assert flags == []

    def test_none_status_passes_through(self):
        assert apply_outbound_guard("t1", "sales", None, None) == (None, [])
