"""Tests for the embed-instructions email escape hatch (onboarding wizard).

Non-technical owners often can't edit their own website. The wizard's embed
step lets them email the widget snippet + install steps to whoever manages
their site. Contract:

  - POST /api/v1/onboarding/{tenant_id}/email-embed {recipient_email}
  - JWT required, tenant must match (403 cross-tenant)
  - Invalid recipient -> 422
  - Sends one email via email_sender.send_email with the snippet inside
  - Recipient/business values are HTML-escaped (snippet itself is pre-built)
"""

from unittest.mock import AsyncMock, MagicMock

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _seed_widget_key(mock_supabase, api_key="anx_test_key_123"):
    chain = (
        mock_supabase.table.return_value.select.return_value.eq.return_value
        .limit.return_value.execute
    )
    chain.return_value = MagicMock(data=[{"api_key": api_key, "bot_name": "Helper"}])


class TestEmailEmbedInstructions:
    def test_requires_auth(self, client):
        resp = client.post(
            f"/api/v1/onboarding/{TENANT_ID}/email-embed",
            json={"recipient_email": "dev@example.com"},
        )
        assert resp.status_code in (401, 422)

    def test_cross_tenant_forbidden(self, client, auth_headers):
        other = "00000000-0000-0000-0000-000000000099"
        resp = client.post(
            f"/api/v1/onboarding/{other}/email-embed",
            json={"recipient_email": "dev@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_invalid_email_422(self, client, auth_headers):
        resp = client.post(
            f"/api/v1/onboarding/{TENANT_ID}/email-embed",
            json={"recipient_email": "not-an-email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_sends_snippet_email(self, client, auth_headers, mock_supabase, monkeypatch):
        from backend.routers import embed_instructions

        _seed_widget_key(mock_supabase)
        sent = AsyncMock(return_value=True)
        monkeypatch.setattr(embed_instructions, "send_email", sent)

        resp = client.post(
            f"/api/v1/onboarding/{TENANT_ID}/email-embed",
            json={"recipient_email": "webdev@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        sent.assert_awaited_once()
        kwargs = sent.await_args.kwargs
        assert kwargs["to"] == "webdev@example.com"
        assert "anx_test_key_123" in kwargs["body_html"]
        assert "</body>" in kwargs["body_html"] or "&lt;/body&gt;" in kwargs["body_html"]

    def test_html_escapes_business_name(
        self, client, auth_headers, mock_supabase, monkeypatch
    ):
        from backend.routers import embed_instructions

        _seed_widget_key(mock_supabase)
        sent = AsyncMock(return_value=True)
        monkeypatch.setattr(embed_instructions, "send_email", sent)

        # business_name comes from the JWT claims ("Test Business") — inject a
        # hostile note instead via the optional message field.
        resp = client.post(
            f"/api/v1/onboarding/{TENANT_ID}/email-embed",
            json={
                "recipient_email": "webdev@example.com",
                "note": '<img src=x onerror=alert(1)>',
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body_html = sent.await_args.kwargs["body_html"]
        assert "<img src=x" not in body_html
        assert "&lt;img" in body_html

    def test_widget_key_missing_404(self, client, auth_headers, mock_supabase, monkeypatch):
        from backend.routers import embed_instructions

        chain = (
            mock_supabase.table.return_value.select.return_value.eq.return_value
            .limit.return_value.execute
        )
        chain.return_value = MagicMock(data=[])
        monkeypatch.setattr(embed_instructions, "send_email", AsyncMock())

        resp = client.post(
            f"/api/v1/onboarding/{TENANT_ID}/email-embed",
            json={"recipient_email": "webdev@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
