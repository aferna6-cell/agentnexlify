"""Regression: Calendar/Gmail OAuth must not emit PKCE on auth URLs.

Auth and callback use separate google_auth_oauthlib Flow instances, so an
auto-generated code_verifier cannot round-trip and breaks fetch_token.
"""

from unittest.mock import patch

from backend.services import google_calendar, gmail_connector


def test_calendar_auth_url_has_no_code_challenge():
    with patch.object(google_calendar.settings, "google_client_id", "cid.apps.googleusercontent.com"), patch.object(
        google_calendar.settings, "google_client_secret", "sec"
    ):
        url = google_calendar.get_auth_url("https://example.com/cb", state="signed-state")
    assert "code_challenge" not in url
    assert "state=signed-state" in url


def test_gmail_auth_url_has_no_code_challenge():
    with patch.object(gmail_connector.settings, "google_client_id", "cid.apps.googleusercontent.com"), patch.object(
        gmail_connector.settings, "google_client_secret", "sec"
    ):
        url = gmail_connector.get_auth_url("https://example.com/cb", state="signed-state")
    assert "code_challenge" not in url
    assert "state=signed-state" in url
