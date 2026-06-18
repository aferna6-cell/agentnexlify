"""Tests for the new-signup founder alert.

Contract:
- send_signup_alert emails settings.signup_alert_email (founder inbox, NOT the
  support inbox), with the business details, via send_platform_email's recipient
  override.
- It never raises (best-effort) and no-ops when signup_alert_email is unset.
- The signup side-effects path invokes it.
"""

import asyncio
from unittest.mock import AsyncMock, patch

from backend.services import signup_alert
from backend.config import settings


def _run(coro):
    return asyncio.run(coro)


def test_send_signup_alert_targets_founder_inbox():
    with patch.object(settings, "signup_alert_email", "founder@example.com"), patch.object(
        signup_alert, "send_platform_email", new=AsyncMock(return_value={"success": True})
    ) as mock_send:
        result = _run(
            signup_alert.send_signup_alert(
                business_name="Acme Roofing",
                owner_name="Jane Doe",
                email="jane@acme.com",
                industry="roofing",
                city="Austin, TX",
            )
        )
    assert result == {"success": True}
    mock_send.assert_awaited_once()
    kwargs = mock_send.await_args.kwargs
    args = mock_send.await_args.args
    # recipient override points at the founder inbox, not support@
    assert kwargs.get("recipient") == "founder@example.com"
    subject = args[0]
    body = args[1]
    assert "Acme Roofing" in subject
    assert "Acme Roofing" in body and "jane@acme.com" in body and "roofing" in body


def test_send_signup_alert_noops_without_recipient():
    with patch.object(settings, "signup_alert_email", ""), patch.object(
        signup_alert, "send_platform_email", new=AsyncMock()
    ) as mock_send:
        result = _run(
            signup_alert.send_signup_alert(
                business_name="X", owner_name="Y", email="z@x.com",
                industry="i", city="c",
            )
        )
    assert result["success"] is False
    mock_send.assert_not_awaited()


def test_send_signup_alert_never_raises_on_send_failure():
    with patch.object(settings, "signup_alert_email", "founder@example.com"), patch.object(
        signup_alert, "send_platform_email",
        new=AsyncMock(side_effect=RuntimeError("resend boom")),
    ):
        result = _run(
            signup_alert.send_signup_alert(
                business_name="X", owner_name="Y", email="z@x.com",
                industry="i", city="c",
            )
        )
    assert result["success"] is False


def test_escapes_html_in_business_fields():
    with patch.object(settings, "signup_alert_email", "founder@example.com"), patch.object(
        signup_alert, "send_platform_email", new=AsyncMock(return_value={"success": True})
    ) as mock_send:
        _run(
            signup_alert.send_signup_alert(
                business_name="<script>x</script>", owner_name="O",
                email="e@x.com", industry="i", city="c",
            )
        )
    body = mock_send.await_args.args[1]
    assert "<script>" not in body
    assert "&lt;script&gt;" in body


def test_signup_side_effects_fires_alert():
    """_run_signup_side_effects invokes send_signup_alert (covers the hook)."""
    from backend.routers import auth

    alert_mock = AsyncMock()
    with patch.object(auth, "send_email", new=AsyncMock()), patch(
        "backend.services.signup_alert.send_signup_alert", new=alert_mock
    ):
        _run(
            auth._run_signup_side_effects(
                email="jane@acme.com",
                owner_name="Jane",
                tenant_id="t-1",
                business_name="Acme Roofing",
                industry="roofing",
                city="Austin, TX",
                website_url=None,
            )
        )
    alert_mock.assert_awaited_once()
    assert alert_mock.await_args.kwargs["business_name"] == "Acme Roofing"
