"""``gmail_connector.send_message`` + the Message-ID duplicate lookup.

These are the two functions the ``send_email`` tool's guarantees rest on, so
they are tested directly rather than only through the tool: the MIME the
provider actually receives, and the search that decides whether a send already
happened.
"""

import base64
import email
import os

from unittest.mock import patch

os.environ.setdefault("TESTING", "1")

from backend.services import gmail_connector

TENANT = "11111111-1111-1111-1111-111111111111"


def _decode(body: dict) -> email.message.Message:
    """The MIME message Gmail would receive, decoded back."""
    raw = base64.urlsafe_b64decode(body["raw"].encode("ascii"))
    return email.message_from_bytes(raw)


def test_send_message_builds_the_mime_gmail_receives():
    captured = {}

    def fake_post(tenant_id, path, json_body):
        captured["tenant_id"] = tenant_id
        captured["path"] = path
        captured["body"] = json_body
        return {"id": "msg-1", "threadId": "thread-1"}

    with patch.object(gmail_connector, "_api_post", fake_post):
        result = gmail_connector.send_message(
            None,
            TENANT,
            to="sarah@example.com",
            subject="Following up",
            body_html="<p>Hi Sarah</p>",
            rfc822_msgid="aos-exec-1@actions.agentnexlify",
        )

    assert result == {
        "success": True,
        "detail": "sent",
        "message_id": "msg-1",
        "thread_id": "thread-1",
    }
    assert captured["tenant_id"] == TENANT, "the send is scoped to one tenant's mailbox"
    assert captured["path"] == "/messages/send"

    message = _decode(captured["body"])
    assert message["to"] == "sarah@example.com"
    assert message["subject"] == "Following up"
    # The fingerprint that makes the duplicate check possible.
    assert message["Message-ID"] == "<aos-exec-1@actions.agentnexlify>"
    assert "Hi Sarah" in message.get_payload(decode=True).decode()


def test_send_message_threads_a_reply_when_asked():
    captured = {}

    def fake_post(tenant_id, path, json_body):
        captured["body"] = json_body
        return {"id": "msg-2", "threadId": "thread-9"}

    with patch.object(gmail_connector, "_api_post", fake_post):
        gmail_connector.send_message(
            None,
            TENANT,
            to="sarah@example.com",
            subject="Re: quote",
            body_html="<p>Following up</p>",
            rfc822_msgid="aos-exec-2@actions.agentnexlify",
            thread_id="thread-9",
            in_reply_to="original-id@mail.example",
        )

    assert captured["body"]["threadId"] == "thread-9"
    message = _decode(captured["body"])
    assert message["In-Reply-To"] == "<original-id@mail.example>"
    assert message["References"] == "<original-id@mail.example>"


def test_send_message_reports_a_provider_error_without_raising():
    error = gmail_connector.GmailApiError(401, "invalid credentials")

    def fake_post(*_args, **_kwargs):
        raise error

    with patch.object(gmail_connector, "_api_post", fake_post):
        result = gmail_connector.send_message(
            None, TENANT, to="s@example.com", subject="Hi", body_html="<p>Hi</p>"
        )

    assert result["success"] is False
    assert result["status_code"] == 401, "the caller needs this to tell 4xx from unknown"


def test_send_message_reports_an_unknown_outcome_when_the_transport_gave_nothing():
    with patch.object(gmail_connector, "_api_post", lambda *a, **k: None):
        result = gmail_connector.send_message(
            None, TENANT, to="s@example.com", subject="Hi", body_html="<p>Hi</p>"
        )

    assert result["success"] is False
    assert "status_code" not in result, "no status code means the outcome is not definite"


def test_finding_a_message_by_its_fingerprint():
    captured = {}

    def fake_get(tenant_id, path, params=None):
        captured["params"] = params
        return {"messages": [{"id": "already-sent"}]}

    with patch.object(gmail_connector, "_api_get", fake_get):
        found = gmail_connector.find_message_id_by_rfc822_msgid(
            TENANT, "<aos-exec-1@actions.agentnexlify>"
        )

    assert found == "already-sent"
    # Angle brackets are stripped: Gmail's operator matches the bare id.
    assert captured["params"]["q"] == "rfc822msgid:aos-exec-1@actions.agentnexlify"


def test_no_match_and_a_failed_lookup_both_read_as_unknown():
    with patch.object(gmail_connector, "_api_get", lambda *a, **k: {"messages": []}):
        assert gmail_connector.find_message_id_by_rfc822_msgid(TENANT, "aos-x@y") is None

    def raises(*_args, **_kwargs):
        raise gmail_connector.GmailApiError(500, "boom")

    with patch.object(gmail_connector, "_api_get", raises):
        assert gmail_connector.find_message_id_by_rfc822_msgid(TENANT, "aos-x@y") is None

    assert gmail_connector.find_message_id_by_rfc822_msgid(TENANT, "") is None
