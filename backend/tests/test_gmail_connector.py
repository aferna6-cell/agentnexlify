"""Tests for the Gmail connector (Phase 2 — Gmail connector + inbox triage).

Contracts:
  - OAuth URL carries the gmail.readonly/send/modify scopes + signed state
  - tokens are stored encrypted (never plaintext) when a vault key is set
  - Gmail message payloads normalize into the shared ParsedEmail shape
  - send_reply builds RFC-threaded MIME (In-Reply-To/References) + threadId
  - list_history surfaces the HISTORY_EXPIRED sentinel on a 404, paginates,
    and filters to INBOX-labeled additions
  - get_message degrades to None on any API failure (never raises)
"""

import base64
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from backend.services import gmail_connector as gc
from backend.services import integration_key_vault as vault

TENANT_ID = "00000000-0000-0000-0000-000000000001"
KEY = Fernet.generate_key().decode()


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _with_oauth_settings():
    return patch.multiple(
        gc.settings,
        google_client_id="cid",
        google_client_secret="secret",
        gmail_redirect_uri="https://api.example.com/api/v1/integrations/gmail/callback",
    )


def _with_key():
    return patch.object(vault.settings, "integrations_enc_key", KEY)


# ---------------------------------------------------------------------------
# OAuth URL
# ---------------------------------------------------------------------------


class TestAuthUrl:
    def test_url_carries_gmail_scopes_state_and_offline(self):
        with _with_oauth_settings():
            url = gc.get_auth_url(
                "https://api.example.com/api/v1/integrations/gmail/callback", "state123"
            )
        assert "gmail.readonly" in url
        assert "gmail.send" in url
        assert "gmail.modify" in url
        assert "state=state123" in url
        assert "access_type=offline" in url


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


def _fake_db_no_existing_row():
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    chain.insert.return_value = chain
    db = MagicMock()
    db.table.return_value = chain
    return db, chain


class TestSaveIntegration:
    def test_tokens_dual_written_with_decryptable_ciphertext(self):
        """Matches integration_key_vault's documented dual-write contract
        (migration 176 comment): plaintext columns stay until the sunset
        migration; ciphertext columns are added alongside whenever a key is
        configured, and must decrypt back to the original secret."""
        db, chain = _fake_db_no_existing_row()
        with _with_key(), patch.object(gc, "get_service_supabase", return_value=db):
            gc.save_integration(
                TENANT_ID,
                access_token="ya29.secret",
                refresh_token="1//refresh",
                token_expiry="2026-08-01T00:00:00+00:00",
            )
        inserted = chain.insert.call_args.args[0]
        assert inserted["access_token_enc"].startswith("\\x")
        assert inserted["refresh_token_enc"].startswith("\\x")
        assert inserted["provider"] == "gmail"
        with _with_key():
            assert (
                vault.decrypt_key(vault._from_bytea(inserted["access_token_enc"]))
                == "ya29.secret"
            )
            assert (
                vault.decrypt_key(vault._from_bytea(inserted["refresh_token_enc"]))
                == "1//refresh"
            )

    def test_no_encryption_key_falls_back_to_plaintext_columns(self):
        """No key configured -> encrypt_oauth_tokens no-ops; the OAuth flow
        must keep working (matches google_calendar.py's pre-vault behavior)."""
        db, chain = _fake_db_no_existing_row()
        with patch.object(vault.settings, "integrations_enc_key", ""), patch.object(
            vault.settings, "integrations_enc_keys", ""
        ), patch.object(gc, "get_service_supabase", return_value=db):
            gc.save_integration(
                TENANT_ID,
                access_token="ya29.secret",
                refresh_token="1//refresh",
                token_expiry="2026-08-01T00:00:00+00:00",
            )
        inserted = chain.insert.call_args.args[0]
        assert inserted["access_token"] == "ya29.secret"
        assert "access_token_enc" not in inserted


# ---------------------------------------------------------------------------
# Message normalization
# ---------------------------------------------------------------------------


class TestNormalizeMessage:
    def test_extracts_parsed_email_from_plain_text_part(self):
        raw = {
            "id": "msg-1",
            "threadId": "thread-1",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "From", "value": '"Jane Doe" <jane@example.com>'},
                    {"name": "To", "value": "support@tenant.com"},
                    {"name": "Subject", "value": "Question about pricing"},
                    {"name": "Message-Id", "value": "<abc123@mail.gmail.com>"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": _b64url("How much does the pro plan cost?")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": _b64url("<p>How much...</p>")},
                    },
                ],
            },
        }
        parsed = gc._normalize_message(raw)
        assert parsed["provider_message_id"] == "msg-1"
        assert parsed["thread_id"] == "thread-1"
        assert parsed["sender_email"] == "jane@example.com"
        assert parsed["sender_name"] == "Jane Doe"
        assert parsed["subject"] == "Question about pricing"
        assert parsed["body_text"] == "How much does the pro plan cost?"
        assert parsed["headers"]["from"] == '"Jane Doe" <jane@example.com>'

    def test_falls_back_to_html_body_when_no_plain_part(self):
        raw = {
            "id": "msg-2",
            "threadId": "thread-2",
            "payload": {
                "mimeType": "text/html",
                "headers": [{"name": "From", "value": "a@b.com"}],
                "body": {"data": _b64url("<p>hello</p>")},
            },
        }
        parsed = gc._normalize_message(raw)
        assert parsed["body_text"] == "<p>hello</p>"


# ---------------------------------------------------------------------------
# send_reply
# ---------------------------------------------------------------------------


class TestSendReply:
    def test_builds_threaded_mime_and_returns_success(self):
        captured = {}

        def fake_api_post(tenant_id, path, json_body):
            captured["tenant_id"] = tenant_id
            captured["path"] = path
            captured["body"] = json_body
            return {"id": "sent-1", "threadId": "thread-1"}

        with patch.object(gc, "_api_post", side_effect=fake_api_post):
            result = gc.send_reply(
                db=object(),
                tenant_id=TENANT_ID,
                thread_id="thread-1",
                to="jane@example.com",
                subject="Re: Question about pricing",
                body_html="<p>The pro plan is $49/mo.</p>",
                in_reply_to="abc123@mail.gmail.com",
                references="",
            )

        assert result["success"] is True
        assert result["message_id"] == "sent-1"
        assert result["thread_id"] == "thread-1"
        assert captured["path"] == "/messages/send"
        assert captured["body"]["threadId"] == "thread-1"

        raw_bytes = base64.urlsafe_b64decode(captured["body"]["raw"] + "===")
        raw_text = raw_bytes.decode()
        assert "In-Reply-To: <abc123@mail.gmail.com>" in raw_text
        assert "References: <abc123@mail.gmail.com>" in raw_text
        assert "jane@example.com" in raw_text

    def test_no_credentials_returns_failure_without_raising(self):
        with patch.object(gc, "_api_post", return_value=None):
            result = gc.send_reply(
                db=object(),
                tenant_id=TENANT_ID,
                thread_id="t1",
                to="a@b.com",
                subject="hi",
                body_html="<p>hi</p>",
            )
        assert result["success"] is False

    def test_gmail_api_error_returns_failure_without_raising(self):
        with patch.object(
            gc, "_api_post", side_effect=gc.GmailApiError(500, "boom")
        ):
            result = gc.send_reply(
                db=object(),
                tenant_id=TENANT_ID,
                thread_id="t1",
                to="a@b.com",
                subject="hi",
                body_html="<p>hi</p>",
            )
        assert result["success"] is False
        assert "500" in result["detail"]


# ---------------------------------------------------------------------------
# list_history
# ---------------------------------------------------------------------------


class TestListHistory:
    def test_expired_cursor_returns_sentinel(self):
        with patch.object(gc, "_api_get", side_effect=gc.GmailApiError(404, "not found")):
            message_ids, latest = gc.list_history(TENANT_ID, "12345")
        assert message_ids == []
        assert latest == gc.HISTORY_EXPIRED

    def test_no_since_history_id_short_circuits(self):
        with patch.object(gc, "_api_get") as mock_get:
            message_ids, latest = gc.list_history(TENANT_ID, "")
        assert message_ids == []
        assert latest is None
        mock_get.assert_not_called()

    def test_filters_to_inbox_labeled_messages_and_dedupes(self):
        page = {
            "history": [
                {
                    "messagesAdded": [
                        {"message": {"id": "m1", "labelIds": ["INBOX"]}},
                        {"message": {"id": "m2", "labelIds": ["SENT"]}},
                        {"message": {"id": "m1", "labelIds": ["INBOX"]}},
                    ]
                }
            ],
            "historyId": "999",
        }
        with patch.object(gc, "_api_get", return_value=page):
            message_ids, latest = gc.list_history(TENANT_ID, "100")
        assert message_ids == ["m1"]
        assert latest == "999"

    def test_paginates_across_pages(self):
        page1 = {
            "history": [{"messagesAdded": [{"message": {"id": "m1", "labelIds": ["INBOX"]}}]}],
            "historyId": "200",
            "nextPageToken": "tok2",
        }
        page2 = {
            "history": [{"messagesAdded": [{"message": {"id": "m2", "labelIds": ["INBOX"]}}]}],
            "historyId": "300",
        }
        with patch.object(gc, "_api_get", side_effect=[page1, page2]):
            message_ids, latest = gc.list_history(TENANT_ID, "100")
        assert message_ids == ["m1", "m2"]
        assert latest == "300"

    def test_transport_failure_returns_none_cursor(self):
        with patch.object(gc, "_api_get", return_value=None):
            message_ids, latest = gc.list_history(TENANT_ID, "100")
        assert message_ids == []
        assert latest is None


# ---------------------------------------------------------------------------
# get_message
# ---------------------------------------------------------------------------


class TestGetMessage:
    def test_returns_none_on_api_error(self):
        with patch.object(gc, "_api_get", side_effect=gc.GmailApiError(500, "boom")):
            assert gc.get_message(TENANT_ID, "m1") is None

    def test_returns_none_when_no_data(self):
        with patch.object(gc, "_api_get", return_value=None):
            assert gc.get_message(TENANT_ID, "m1") is None

    def test_returns_parsed_email_on_success(self):
        raw = {
            "id": "m1",
            "threadId": "t1",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "From", "value": "a@b.com"}],
                "body": {"data": _b64url("hi there")},
            },
        }
        with patch.object(gc, "_api_get", return_value=raw):
            parsed = gc.get_message(TENANT_ID, "m1")
        assert parsed["provider_message_id"] == "m1"
        assert parsed["body_text"] == "hi there"


# ---------------------------------------------------------------------------
# get_integration / is_connected
# ---------------------------------------------------------------------------


class TestGetIntegration:
    def test_returns_none_when_no_row(self):
        db = MagicMock()
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db.table.return_value = chain
        with patch.object(gc, "get_service_supabase", return_value=db):
            assert gc.get_integration(TENANT_ID) is None
            assert gc.is_connected(TENANT_ID) is False
