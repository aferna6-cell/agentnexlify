"""POST /api/v1/admin/voice-test-call: automated voice-stack E2E trigger.

Contract:

  1. Admin secret required (401 without).
  2. Numbers validated as E.164 and must differ (422 otherwise).
  3. On success Twilio's Calls API is hit with From/To/Twiml and the call
     sid comes back to the caller.
  4. Twilio rejection surfaces as 502, never a silent success.
"""

from unittest.mock import AsyncMock, MagicMock, patch

_ADMIN_SECRET = "test-admin-secret"
URL = "/api/v1/admin/voice-test-call"


def _patch_admin_secret(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.admin_health._admin_secret",
        lambda: _ADMIN_SECRET,
    )


def _payload(**over):
    body = {"from_number": "+19148032547", "to_number": "+12012947124"}
    body.update(over)
    return body


def _twilio_ok(sid="CA123"):
    resp = MagicMock()
    resp.status_code = 201
    resp.json.return_value = {"sid": sid, "status": "queued"}
    return resp


def _patch_httpx(resp):
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.return_value = resp
    return patch("backend.routers.admin_voice_test.httpx.AsyncClient", return_value=client), client


def _patch_twilio_settings():
    return patch.multiple(
        "backend.routers.admin_voice_test.settings",
        twilio_account_sid="ACtest",
        twilio_auth_token="tok",
    )


class TestVoiceTestCall:
    def test_requires_admin_secret(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        resp = client.post(URL, json=_payload())
        assert resp.status_code == 401

    def test_rejects_non_e164_numbers(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        with _patch_twilio_settings():
            resp = client.post(
                URL,
                json=_payload(from_number="9148032547"),
                headers={"x-api-secret": _ADMIN_SECRET},
            )
        assert resp.status_code == 422
        assert "E.164" in resp.text

    def test_rejects_same_from_and_to(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        with _patch_twilio_settings():
            resp = client.post(
                URL,
                json=_payload(to_number="+19148032547"),
                headers={"x-api-secret": _ADMIN_SECRET},
            )
        assert resp.status_code == 422
        assert "differ" in resp.text

    def test_places_call_and_returns_sid(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        httpx_patch, fake_client = _patch_httpx(_twilio_ok("CA999"))
        with _patch_twilio_settings(), httpx_patch:
            resp = client.post(
                URL, json=_payload(), headers={"x-api-secret": _ADMIN_SECRET}
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["call_sid"] == "CA999"
        assert body["from_number"] == "+19148032547"
        sent = fake_client.post.call_args
        assert "Calls.json" in sent.args[0]
        assert sent.kwargs["data"]["From"] == "+19148032547"
        assert sent.kwargs["data"]["To"] == "+12012947124"
        assert "<Say>" in sent.kwargs["data"]["Twiml"]

    def test_twilio_rejection_surfaces_as_502(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        bad = MagicMock()
        bad.status_code = 400
        bad.text = "invalid number"
        httpx_patch, _ = _patch_httpx(bad)
        with _patch_twilio_settings(), httpx_patch:
            resp = client.post(
                URL, json=_payload(), headers={"x-api-secret": _ADMIN_SECRET}
            )
        assert resp.status_code == 502
        assert "Twilio rejected" in resp.text

    def test_say_content_is_tag_escaped(self, client, monkeypatch):
        _patch_admin_secret(monkeypatch)
        httpx_patch, fake_client = _patch_httpx(_twilio_ok())
        with _patch_twilio_settings(), httpx_patch:
            resp = client.post(
                URL,
                json=_payload(say="<Dial>+15551234567</Dial>"),
                headers={"x-api-secret": _ADMIN_SECRET},
            )
        assert resp.status_code == 200
        twiml = fake_client.post.call_args.kwargs["data"]["Twiml"]
        assert "<Dial>" not in twiml
        assert "Dial" in twiml
