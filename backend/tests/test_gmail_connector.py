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

import httpx
import pytest
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

    def test_non_404_api_error_returns_none_cursor(self):
        with patch.object(gc, "_api_get", side_effect=gc.GmailApiError(500, "server error")):
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


class TestIsConnectedExceptionPath:
    def test_true_when_integration_exists(self):
        with patch.object(gc, "get_integration", return_value={"id": "x"}):
            assert gc.is_connected(TENANT_ID) is True

    def test_false_on_lookup_exception(self):
        with patch.object(gc, "get_integration", side_effect=RuntimeError("db down")):
            assert gc.is_connected(TENANT_ID) is False


# ---------------------------------------------------------------------------
# save_integration — existing row (update path, metadata preserved/merged)
# ---------------------------------------------------------------------------


class TestSaveIntegrationUpdate:
    def test_existing_row_updates_and_writes_metadata(self):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.update.return_value = chain
        select_result = MagicMock(
            data=[{"id": "existing-1", "tenant_id": TENANT_ID, "provider": "gmail"}]
        )
        update_result = MagicMock(data=[{"id": "existing-1"}])
        chain.execute.side_effect = [select_result, update_result]
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(gc, "get_service_supabase", return_value=db):
            result = gc.save_integration(
                TENANT_ID,
                access_token="tok",
                refresh_token="rt",
                token_expiry="2026-01-01T00:00:00+00:00",
                metadata={"email_address": "a@b.com"},
            )
        chain.update.assert_called_once()
        updated_payload = chain.update.call_args.args[0]
        assert updated_payload["metadata"] == {"email_address": "a@b.com"}
        assert result == {"id": "existing-1"}


# ---------------------------------------------------------------------------
# update_metadata — not-found / merge-success / db-failure
# ---------------------------------------------------------------------------


class TestUpdateMetadata:
    def test_no_existing_integration_returns_none(self):
        db, _chain = _fake_db_no_existing_row()
        with patch.object(gc, "get_service_supabase", return_value=db):
            result = gc.update_metadata(TENANT_ID, {"history_id": "5"})
        assert result is None

    def test_merges_and_updates_existing_metadata(self):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.update.return_value = chain
        select_result = MagicMock(data=[{"id": "int-1", "metadata": {"foo": "bar"}}])
        update_result = MagicMock(
            data=[{"id": "int-1", "metadata": {"foo": "bar", "history_id": "5"}}]
        )
        chain.execute.side_effect = [select_result, update_result]
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(gc, "get_service_supabase", return_value=db):
            result = gc.update_metadata(TENANT_ID, {"history_id": "5"})
        merged = chain.update.call_args.args[0]["metadata"]
        assert merged == {"foo": "bar", "history_id": "5"}
        assert result["metadata"]["history_id"] == "5"

    def test_db_failure_returns_none_without_raising(self):
        db = MagicMock()
        db.table.side_effect = RuntimeError("db down")
        with patch.object(gc, "get_service_supabase", return_value=db):
            result = gc.update_metadata(TENANT_ID, {"history_id": "5"})
        assert result is None


# ---------------------------------------------------------------------------
# delete_integration
# ---------------------------------------------------------------------------


class TestDeleteIntegration:
    def test_deletes_by_tenant_and_provider(self):
        chain = MagicMock()
        chain.delete.return_value = chain
        chain.eq.return_value = chain
        db = MagicMock()
        db.table.return_value = chain
        with patch.object(gc, "get_service_supabase", return_value=db):
            gc.delete_integration(TENANT_ID)
        chain.delete.assert_called_once()
        eq_calls = [c.args for c in chain.eq.call_args_list]
        assert ("tenant_id", TENANT_ID) in eq_calls
        assert ("provider", gc.PROVIDER) in eq_calls


# ---------------------------------------------------------------------------
# get_credentials — no integration / not-expired / expired-refresh-ok /
# expired-refresh-fails
# ---------------------------------------------------------------------------


class TestGetCredentials:
    def test_no_integration_returns_none(self):
        with patch.object(gc, "get_integration", return_value=None):
            assert gc.get_credentials(TENANT_ID) is None

    def test_not_expired_returns_credentials_untouched(self):
        integration = {"access_token": "tok", "refresh_token": "rt"}
        fake_creds = MagicMock(expired=False, refresh_token="rt", token="tok")
        with patch.object(gc, "get_integration", return_value=integration), patch.object(
            gc, "Credentials", return_value=fake_creds
        ), patch.object(gc, "save_integration") as save_mock:
            result = gc.get_credentials(TENANT_ID)
        assert result is fake_creds
        save_mock.assert_not_called()

    def test_expired_with_successful_refresh_persists_new_tokens(self):
        import datetime as dt

        integration = {"access_token": "old", "refresh_token": "rt"}
        expiry = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
        fake_creds = MagicMock(
            expired=True, refresh_token="rt", token="new-tok", expiry=expiry
        )
        with patch.object(gc, "get_integration", return_value=integration), patch.object(
            gc, "Credentials", return_value=fake_creds
        ), patch.object(gc, "Request", return_value=MagicMock()), patch.object(
            gc, "save_integration"
        ) as save_mock:
            result = gc.get_credentials(TENANT_ID)
        assert result is fake_creds
        fake_creds.refresh.assert_called_once()
        save_mock.assert_called_once_with(
            tenant_id=TENANT_ID,
            access_token="new-tok",
            refresh_token="rt",
            token_expiry=expiry.isoformat(),
        )

    def test_expired_refresh_failure_returns_none(self):
        integration = {"access_token": "old", "refresh_token": "rt"}
        fake_creds = MagicMock(expired=True, refresh_token="rt")
        fake_creds.refresh.side_effect = RuntimeError("refresh failed")
        with patch.object(gc, "get_integration", return_value=integration), patch.object(
            gc, "Credentials", return_value=fake_creds
        ), patch.object(gc, "Request", return_value=MagicMock()), patch.object(
            gc, "save_integration"
        ) as save_mock:
            result = gc.get_credentials(TENANT_ID)
        assert result is None
        save_mock.assert_not_called()


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------


class TestExchangeCode:
    def test_exchanges_code_for_credentials(self):
        flow = MagicMock()
        flow.credentials = MagicMock(token="tok")
        with patch.object(gc, "build_oauth_flow", return_value=flow) as build_mock:
            creds = gc.exchange_code("auth-code", "https://api.example.com/cb")
        build_mock.assert_called_once_with("https://api.example.com/cb")
        flow.fetch_token.assert_called_once_with(code="auth-code")
        assert creds is flow.credentials


# ---------------------------------------------------------------------------
# _api_get / _api_post — no-creds / success / HTTPStatusError / transport
# failure branches (currently only exercised via patch.object(gc, "_api_get"))
# ---------------------------------------------------------------------------


class TestApiGet:
    def test_no_credentials_returns_none(self):
        with patch.object(gc, "get_credentials", return_value=None):
            assert gc._api_get(TENANT_ID, "/profile") is None

    def test_success_returns_json_with_bearer_header(self):
        creds = MagicMock(token="tok123")
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"emailAddress": "a@b.com"}
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "get", return_value=resp
        ) as http_get:
            data = gc._api_get(TENANT_ID, "/profile", params={"x": 1})
        assert data == {"emailAddress": "a@b.com"}
        assert http_get.call_args.kwargs["headers"]["Authorization"] == "Bearer tok123"

    def test_http_status_error_raises_gmail_api_error(self):
        creds = MagicMock(token="tok123")
        request = httpx.Request("GET", "https://gmail.googleapis.com/x")
        response = httpx.Response(404, request=request, text="not found")
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "get", return_value=response
        ):
            with pytest.raises(gc.GmailApiError) as excinfo:
                gc._api_get(TENANT_ID, "/x")
        assert excinfo.value.status_code == 404

    def test_transport_failure_returns_none(self):
        creds = MagicMock(token="tok123")
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "get", side_effect=RuntimeError("network down")
        ):
            assert gc._api_get(TENANT_ID, "/x") is None


class TestApiPost:
    def test_no_credentials_returns_none(self):
        with patch.object(gc, "get_credentials", return_value=None):
            assert gc._api_post(TENANT_ID, "/messages/send", {}) is None

    def test_success_returns_json(self):
        creds = MagicMock(token="tok123")
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"id": "sent-1"}
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "post", return_value=resp
        ) as http_post:
            data = gc._api_post(TENANT_ID, "/messages/send", {"raw": "abc"})
        assert data == {"id": "sent-1"}
        assert http_post.call_args.kwargs["headers"]["Authorization"] == "Bearer tok123"

    def test_http_status_error_raises_gmail_api_error(self):
        creds = MagicMock(token="tok123")
        request = httpx.Request("POST", "https://gmail.googleapis.com/messages/send")
        response = httpx.Response(500, request=request, text="server error")
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "post", return_value=response
        ):
            with pytest.raises(gc.GmailApiError) as excinfo:
                gc._api_post(TENANT_ID, "/messages/send", {})
        assert excinfo.value.status_code == 500

    def test_transport_failure_returns_none(self):
        creds = MagicMock(token="tok123")
        with patch.object(gc, "get_credentials", return_value=creds), patch.object(
            gc.httpx, "post", side_effect=RuntimeError("network down")
        ):
            assert gc._api_post(TENANT_ID, "/messages/send", {}) is None


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    def test_returns_data_from_api_get(self):
        with patch.object(gc, "_api_get", return_value={"emailAddress": "a@b.com"}):
            assert gc.get_profile(TENANT_ID) == {"emailAddress": "a@b.com"}

    def test_returns_empty_dict_on_api_error(self):
        with patch.object(gc, "_api_get", side_effect=gc.GmailApiError(500, "boom")):
            assert gc.get_profile(TENANT_ID) == {}

    def test_returns_empty_dict_when_no_data(self):
        with patch.object(gc, "_api_get", return_value=None):
            assert gc.get_profile(TENANT_ID) == {}


# ---------------------------------------------------------------------------
# list_recent_message_ids
# ---------------------------------------------------------------------------


class TestListRecentMessageIds:
    def test_returns_message_ids_filtering_ones_without_id(self):
        with patch.object(
            gc, "_api_get", return_value={"messages": [{"id": "m1"}, {"id": "m2"}, {}]}
        ):
            assert gc.list_recent_message_ids(TENANT_ID) == ["m1", "m2"]

    def test_returns_empty_list_when_no_data(self):
        with patch.object(gc, "_api_get", return_value=None):
            assert gc.list_recent_message_ids(TENANT_ID) == []

    def test_returns_empty_list_on_api_error(self):
        with patch.object(gc, "_api_get", side_effect=gc.GmailApiError(500, "boom")):
            assert gc.list_recent_message_ids(TENANT_ID) == []


# ---------------------------------------------------------------------------
# _decode_base64url — malformed input
# ---------------------------------------------------------------------------


class TestDecodeBase64Url:
    def test_malformed_data_returns_empty_string(self):
        assert gc._decode_base64url("a") == ""


# ---------------------------------------------------------------------------
# _extract_body_text — empty payload / nested-parts recursion / no-match
# fallthrough
# ---------------------------------------------------------------------------


class TestExtractBodyText:
    def test_empty_payload_returns_empty_string(self):
        assert gc._extract_body_text({}) == ""
        assert gc._extract_body_text(None) == ""

    def test_recurses_into_nested_multipart_parts(self):
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": _b64url("nested text")},
                        }
                    ],
                }
            ],
        }
        assert gc._extract_body_text(payload) == "nested text"

    def test_falls_through_to_empty_string_when_nothing_matches(self):
        payload = {"mimeType": "application/octet-stream", "body": {}}
        assert gc._extract_body_text(payload) == ""
