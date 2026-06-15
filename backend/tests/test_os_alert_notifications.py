"""Tests for Agent OS fail/abstain admin alerts (os_alert_notifications).

Hermetic: the Resend send is monkeypatched, so no network or real key is
touched. Verifies the email-unset no-op, fail/abstain passthrough, transcript
contents, and that a send failure is swallowed (never propagates).
"""

import backend.services.os_alert_notifications as al


def _conv():
    return [
        {"role": "user", "content": "help me", "created_at": "2026-06-15T00:00:00Z"},
        {"role": "assistant", "content": "I cannot help", "created_at": "2026-06-15T00:01:00Z"},
    ]


def test_no_op_when_alert_email_unset(monkeypatch):
    monkeypatch.setattr(al.settings, "agent_os_alert_email", "")
    calls = []
    monkeypatch.setattr(al, "_send_alert_via_resend", lambda **kw: calls.append(kw))
    al.notify_agent_os_event("ten1", _conv(), reason="r", kind="fail")
    assert calls == []


def test_fail_sends_with_transcript(monkeypatch):
    monkeypatch.setattr(al.settings, "agent_os_alert_email", "admin@example.com")
    captured = {}
    monkeypatch.setattr(al, "_send_alert_via_resend", lambda **kw: captured.update(kw))
    al.notify_agent_os_event("ten1", _conv(), reason="boom", kind="fail", error="ValueError: x")
    assert captured["to"] == "admin@example.com"
    assert "fail" in captured["subject"]
    assert "ten1" in captured["subject"]
    assert "help me" in captured["transcript_text"]
    assert "I cannot help" in captured["transcript_text"]


def test_abstain_sends(monkeypatch):
    monkeypatch.setattr(al.settings, "agent_os_alert_email", "admin@example.com")
    captured = {}
    monkeypatch.setattr(al, "_send_alert_via_resend", lambda **kw: captured.update(kw))
    al.notify_agent_os_event("ten1", _conv(), reason="no deliverable", kind="abstain")
    assert "abstain" in captured["subject"]


def test_send_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(al.settings, "agent_os_alert_email", "admin@example.com")

    def _boom(**kw):
        raise RuntimeError("resend down")

    monkeypatch.setattr(al, "_send_alert_via_resend", _boom)
    # Must not raise — best-effort alert never breaks the caller.
    al.notify_agent_os_event("ten1", _conv(), reason="r", kind="fail")


def test_transcript_contains_all_messages():
    t = al._build_transcript(_conv())
    assert "USER" in t
    assert "ASSISTANT" in t
    assert "help me" in t
    assert "I cannot help" in t
