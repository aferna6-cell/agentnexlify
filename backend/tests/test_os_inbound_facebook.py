"""Tests for the Agent OS Facebook bridge plug-in (Phase 6).

The Facebook webhook itself is unchanged from the existing
``backend.routers.channels_facebook`` flow — Phase 6 only adds a
fail-open bridge call AFTER ``channel_manager.ingest_channel_message``
succeeds. Tests cover three contracts:

  - Bridge enabled + ingest returns tenant -> ``bridge_facebook`` called
  - Bridge disabled (``facebook_enabled=False``) -> no bridge call
  - Bridge raises -> exception is swallowed, webhook processing continues

Direct exercise of ``_process_fb_webhook_event`` keeps the test fast and
avoids re-testing the FB sig-verify path (covered by FB's own libs and
the existing webhook contract).
"""

import asyncio


from backend.routers import channels_facebook


def _make_fb_payload(*, page_id: str, sender_id: str, text: str, mid: str) -> dict:
    return {
        "entry": [
            {
                "id": page_id,
                "messaging": [
                    {
                        "sender": {"id": sender_id},
                        "recipient": {"id": page_id},
                        "timestamp": 1700000000000,
                        "message": {"mid": mid, "text": text},
                    }
                ],
            }
        ]
    }


def _install_bridge_capture(monkeypatch, *, enabled: bool = True):
    """Replace channel_manager + bridge helpers with capture stubs."""
    bridge_calls: list = []

    def _fake_ingest(
        *, provider, page_id, sender_id, sender_name, text, timestamp_ms=None
    ):
        return {"tenant_id": "client-abc-123", "conversation_id": "conv-xyz"}

    def _fake_is_enabled(db, client_id, source):
        bridge_calls.append(
            {"kind": "is_enabled", "client_id": client_id, "source": source}
        )
        return enabled

    async def _fake_bridge_facebook(**kwargs):
        bridge_calls.append({"kind": "bridge", "kwargs": kwargs})
        return {"thread_id": "thr-1"}

    def _fake_db():
        return object()

    monkeypatch.setattr(channels_facebook, "ingest_channel_message", _fake_ingest)
    monkeypatch.setattr(channels_facebook, "get_service_supabase", _fake_db)
    monkeypatch.setattr(
        channels_facebook.os_inbound_bridge, "is_bridge_enabled", _fake_is_enabled
    )
    monkeypatch.setattr(
        channels_facebook.os_inbound_bridge,
        "bridge_facebook",
        _fake_bridge_facebook,
    )
    return bridge_calls


class TestFacebookBridgePlugin:
    def test_bridge_fires_when_enabled(self, monkeypatch):
        calls = _install_bridge_capture(monkeypatch, enabled=True)

        payload = _make_fb_payload(
            page_id="PAGE-1",
            sender_id="PSID-1",
            text="Hi, do you do same-day appointments?",
            mid="m_test_123",
        )
        asyncio.run(channels_facebook._process_fb_webhook_event(payload))

        kinds = [c["kind"] for c in calls]
        assert "is_enabled" in kinds, "bridge gate must be checked"
        assert "bridge" in kinds, "bridge_facebook must run when enabled"

        bridge_call = next(c for c in calls if c["kind"] == "bridge")
        kwargs = bridge_call["kwargs"]
        assert kwargs["client_id"] == "client-abc-123"
        assert kwargs["fb_thread_id"] == "PAGE-1:PSID-1"
        assert kwargs["provider_message_id"] == "m_test_123"
        assert kwargs["user_content"].startswith("Hi, do you do")
        assert kwargs["sender_metadata"]["sender_id"] == "PSID-1"
        assert kwargs["sender_metadata"]["page_id"] == "PAGE-1"
        assert kwargs["sender_metadata"]["provider"] == "facebook"

    def test_bridge_skipped_when_disabled(self, monkeypatch):
        calls = _install_bridge_capture(monkeypatch, enabled=False)

        payload = _make_fb_payload(
            page_id="PAGE-2",
            sender_id="PSID-2",
            text="ping",
            mid="m_test_disabled",
        )
        asyncio.run(channels_facebook._process_fb_webhook_event(payload))

        kinds = [c["kind"] for c in calls]
        assert "is_enabled" in kinds, "gate must still be checked"
        assert "bridge" not in kinds, "bridge_facebook must NOT run when disabled"

    def test_bridge_exception_does_not_break_webhook(self, monkeypatch):
        # If the bridge fails (DB blip, etc.) the FB webhook must still complete.
        # Existing behavior already returned 200 before this background task runs,
        # but a raised exception in the BackgroundTasks callback would surface in
        # worker logs as unhandled and might be misread as a "down" webhook.
        async def _boom(**_kwargs):
            raise RuntimeError("simulated bridge crash")

        def _fake_ingest(**_kwargs):
            return {"tenant_id": "client-boom", "conversation_id": "conv-boom"}

        def _fake_is_enabled(db, client_id, source):
            return True

        monkeypatch.setattr(channels_facebook, "ingest_channel_message", _fake_ingest)
        monkeypatch.setattr(channels_facebook, "get_service_supabase", lambda: object())
        monkeypatch.setattr(
            channels_facebook.os_inbound_bridge, "is_bridge_enabled", _fake_is_enabled
        )
        monkeypatch.setattr(
            channels_facebook.os_inbound_bridge, "bridge_facebook", _boom
        )

        payload = _make_fb_payload(
            page_id="PAGE-3",
            sender_id="PSID-3",
            text="raises",
            mid="m_test_boom",
        )
        # Must not raise — exception is swallowed by _bridge_facebook_safe.
        asyncio.run(channels_facebook._process_fb_webhook_event(payload))

    def test_echo_messages_are_skipped(self, monkeypatch):
        # Sanity check — page-authored echo messages bypass ingest, so bridge
        # never runs either. Mirrors existing FB router contract.
        calls = _install_bridge_capture(monkeypatch, enabled=True)

        payload = {
            "entry": [
                {
                    "id": "PAGE-4",
                    "messaging": [
                        {
                            "sender": {"id": "PSID-4"},
                            "recipient": {"id": "PAGE-4"},
                            "timestamp": 1700000000000,
                            "message": {
                                "mid": "m_test_echo",
                                "text": "page-side message",
                                "is_echo": True,
                            },
                        }
                    ],
                }
            ]
        }
        asyncio.run(channels_facebook._process_fb_webhook_event(payload))

        assert calls == [], "echo events must not trigger ingest or bridge"

    def test_missing_mid_skips_bridge(self, monkeypatch):
        # Defensive: if FB ever omits ``mid`` (shouldn't happen, but be safe),
        # we still ingest but skip the bridge so we don't insert a row with
        # a blank source_ref that would collide on idempotency.
        calls = _install_bridge_capture(monkeypatch, enabled=True)

        payload = {
            "entry": [
                {
                    "id": "PAGE-5",
                    "messaging": [
                        {
                            "sender": {"id": "PSID-5"},
                            "recipient": {"id": "PAGE-5"},
                            "timestamp": 1700000000000,
                            "message": {"text": "no mid here"},
                        }
                    ],
                }
            ]
        }
        asyncio.run(channels_facebook._process_fb_webhook_event(payload))

        kinds = [c["kind"] for c in calls]
        assert "bridge" not in kinds, "bridge must not run without provider_message_id"
