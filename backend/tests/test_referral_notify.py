"""Tests for referral_notify — notify_referrer_of_signup.

Three contracts:
(a) A referred signup triggers an email to the referrer's owner_email.
(b) An unresolvable / missing widget_key silently skips — no email, no raise.
(c) A send failure is swallowed — caller unaffected.

Patching strategy: notify_referrer_of_signup imports send_platform_email
lazily inside the function body, so we patch at the module where it lives:
backend.services.platform_mailer.send_platform_email.
"""

import os

os.environ.setdefault("TESTING", "1")

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch target: the function object in its defining module.
_PATCH_TARGET = "backend.services.platform_mailer.send_platform_email"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REFERRER_TENANT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
VALID_API_KEY = "anx_test_key_abc123"
REFERRER_EMAIL = "referrer@example.com"


def _make_db(
    *,
    widget_key_found: bool = True,
    tenant_found: bool = True,
    owner_email: str = REFERRER_EMAIL,
) -> MagicMock:
    """Build a Supabase mock that routes widget_configs and tenants queries."""
    db = MagicMock()

    # --- widget_configs chain ---
    wc_execute = MagicMock()
    wc_execute.data = (
        [{"tenant_id": REFERRER_TENANT_ID}] if widget_key_found else []
    )
    wc_chain = MagicMock()
    (
        wc_chain.select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = wc_execute

    # --- tenants chain ---
    tenant_execute = MagicMock()
    tenant_execute.data = (
        [{"owner_email": owner_email}] if tenant_found else []
    )
    tenant_chain = MagicMock()
    (
        tenant_chain.select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = tenant_execute

    def _route(table_name: str):
        if table_name == "widget_configs":
            return wc_chain
        if table_name == "tenants":
            return tenant_chain
        raise AssertionError(f"unexpected table: {table_name}")

    db.table.side_effect = _route
    return db


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# (a) Happy path — email is sent to the referrer's owner_email
# ---------------------------------------------------------------------------

class TestNotifyReferrerHappyPath:
    def test_sends_email_to_referrer_owner_email(self):
        db = _make_db()

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["recipient"] == REFERRER_EMAIL

    def test_email_subject_mentions_referral(self):
        db = _make_db()

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

        subject = mock_send.call_args.kwargs["subject"]
        assert "referral" in subject.lower()

    def test_email_body_contains_dashboard_link(self):
        db = _make_db()

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

        body_html = mock_send.call_args.kwargs["body_html"]
        assert "/dashboard/referral" in body_html


# ---------------------------------------------------------------------------
# (b) Unresolvable ref — silently skips, no email, no raise
# ---------------------------------------------------------------------------

class TestNotifyReferrerUnresolvable:
    def test_unknown_widget_key_skips_email(self):
        db = _make_db(widget_key_found=False)

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key="nonexistent_key"))

        mock_send.assert_not_awaited()

    def test_unknown_widget_key_does_not_raise(self):
        db = _make_db(widget_key_found=False)

        with patch(_PATCH_TARGET, new_callable=AsyncMock):
            from backend.services.referral import notify_referrer_of_signup

            # Must not raise
            _run(notify_referrer_of_signup(db, widget_key="nonexistent_key"))

    def test_empty_widget_key_skips_and_does_not_raise(self):
        db = _make_db()

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=""))

        mock_send.assert_not_awaited()

    def test_missing_tenant_row_skips_email(self):
        """widget_key resolves to tenant_id but that tenant has no DB row."""
        db = _make_db(widget_key_found=True, tenant_found=False)

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

        mock_send.assert_not_awaited()

    def test_empty_owner_email_skips_send(self):
        """Tenant exists but owner_email is blank — no email, no raise."""
        db = _make_db(widget_key_found=True, tenant_found=True, owner_email="")

        with patch(_PATCH_TARGET, new_callable=AsyncMock) as mock_send:
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

        mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# (c) Send failure is swallowed — caller unaffected
# ---------------------------------------------------------------------------

class TestNotifyReferrerSendFailure:
    def test_send_failure_does_not_raise(self):
        db = _make_db()

        with patch(
            _PATCH_TARGET,
            new_callable=AsyncMock,
            side_effect=Exception("Resend connection refused"),
        ):
            from backend.services.referral import notify_referrer_of_signup

            # Must complete without raising
            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))

    def test_db_error_does_not_raise(self):
        """If the DB call itself blows up, the function must swallow the error."""
        db = MagicMock()
        db.table.side_effect = RuntimeError("DB offline")

        with patch(_PATCH_TARGET, new_callable=AsyncMock):
            from backend.services.referral import notify_referrer_of_signup

            _run(notify_referrer_of_signup(db, widget_key=VALID_API_KEY))
