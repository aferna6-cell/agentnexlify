"""Tests for Drive KB sync (goal item 2) — service + router.

Contracts (specs/drive-kb-onboarding_spec.md):
  - connect is refused (503) until platform OAuth AND the encryption key
    exist — refresh tokens are never stored plaintext
  - the auth URL carries drive.readonly + offline access + signed state
  - sync pulls only files modified since last_synced_at, routes mimes
    (GDoc export / pdf-docx-txt-md download / skip others), writes a sync-log
    row, updates last_synced_at, compiles once — and NEVER raises
  - the daily pass self-gates on the 22h cutoff
  - router endpoints are tenant-auth'd; status reflects connection state
"""

from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet

from backend.services import drive_kb_sync as dks
from backend.services import integration_key_vault as vault
from backend.tests.conftest import _make_auth_token

TENANT_ID = "00000000-0000-0000-0000-000000000001"
KEY = Fernet.generate_key().decode()
DRIVE_BASE = "/api/v1/kb/integrations/drive"


def _auth_headers():
    return {"Authorization": f"Bearer {_make_auth_token(TENANT_ID)}"}


def _with_oauth_settings():
    return patch.multiple(
        dks.settings,
        google_client_id="cid",
        google_client_secret="secret",
        google_drive_redirect_uri="https://api.example.com/api/v1/kb/integrations/drive/callback",
    )


def _with_key():
    return patch.object(vault.settings, "integrations_enc_key", KEY)


# ---------------------------------------------------------------------------
# Auth URL / configuration gates
# ---------------------------------------------------------------------------


class TestAuthUrl:
    def test_refused_when_oauth_unconfigured(self):
        with patch.multiple(
            dks.settings, google_client_id="", google_client_secret="",
            google_drive_redirect_uri="",
        ):
            try:
                dks.build_auth_url("state123")
                assert False, "should have raised"
            except dks.DriveNotConfigured:
                pass

    def test_refused_when_encryption_key_missing(self):
        with _with_oauth_settings(), patch.object(
            vault.settings, "integrations_enc_key", ""
        ), patch.object(vault.settings, "integrations_enc_keys", ""):
            try:
                dks.build_auth_url("state123")
                assert False, "should have raised"
            except dks.EncryptionRequired:
                pass

    def test_url_carries_scope_state_and_offline(self):
        with _with_oauth_settings(), _with_key():
            url = dks.build_auth_url("state123")
        assert "drive.readonly" in url
        assert "state=state123" in url
        assert "access_type=offline" in url


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


class TestSaveTokens:
    def test_tokens_stored_encrypted_never_plaintext(self):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.limit.return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        chain.insert.return_value = chain
        db = MagicMock()
        db.table.return_value = chain
        with _with_key(), patch.object(dks, "get_service_supabase", return_value=db):
            dks.save_tokens(
                TENANT_ID,
                {"access_token": "ya29.secret", "refresh_token": "1//refresh", "expires_in": 3600},
            )
        inserted = chain.insert.call_args.args[0]
        assert "ya29.secret" not in str(inserted)
        assert "1//refresh" not in str(inserted)
        assert inserted["oauth_token_enc"].startswith("\\x")
        # Round-trips through the vault
        with _with_key():
            assert vault.decrypt_key(vault._from_bytea(inserted["oauth_token_enc"])) == "ya29.secret"

    def test_refused_without_encryption_key(self):
        with patch.object(vault.settings, "integrations_enc_key", ""), patch.object(
            vault.settings, "integrations_enc_keys", ""
        ):
            try:
                dks.save_tokens(TENANT_ID, {"access_token": "x"})
                assert False, "should have raised"
            except dks.EncryptionRequired:
                pass


# ---------------------------------------------------------------------------
# Mime routing
# ---------------------------------------------------------------------------


class TestFetchFile:
    def _resp(self, content=b"data"):
        r = MagicMock()
        r.content = content
        r.raise_for_status.return_value = None
        return r

    def test_gdoc_exports_as_text(self):
        with patch.object(dks.httpx, "get", return_value=self._resp(b"doc text")) as get:
            out = dks._fetch_file("tok", {"id": "f1", "name": "Playbook",
                                          "mimeType": "application/vnd.google-apps.document"})
        assert out == ("Playbook.txt", b"doc text")
        assert "/export" in get.call_args.args[0]

    def test_pdf_downloads_media(self):
        with patch.object(dks.httpx, "get", return_value=self._resp(b"%PDF")) as get:
            out = dks._fetch_file("tok", {"id": "f2", "name": "pricing.pdf",
                                          "mimeType": "application/pdf"})
        assert out == ("pricing.pdf", b"%PDF")
        assert get.call_args.kwargs["params"] == {"alt": "media"}

    def test_unsupported_mime_skipped(self):
        assert dks._fetch_file("tok", {"id": "f3", "name": "img.png",
                                       "mimeType": "image/png"}) is None


# ---------------------------------------------------------------------------
# Sync pass
# ---------------------------------------------------------------------------


def _integration(folder="folder-1", last_synced=None):
    return {
        "id": "int-1",
        "client_id": TENANT_ID,
        "provider": "drive",
        "enabled": True,
        "config": {"folder_id": folder, "folder_name": "KB Docs"},
        "last_synced_at": last_synced,
        "oauth_token_enc": None,
        "oauth_refresh_token_enc": None,
        "oauth_expires_at": None,
    }


class TestSyncTenantDrive:
    def _db(self):
        chain = MagicMock()
        for m in ("select", "eq", "limit", "insert", "update", "delete"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[])
        db = MagicMock()
        db.table.return_value = chain
        return db, chain

    def test_not_connected_reports_error(self):
        db, _ = self._db()
        with patch.object(dks, "get_service_supabase", return_value=db), patch.object(
            dks, "get_integration", return_value=None
        ):
            summary = dks.sync_tenant_drive(TENANT_ID)
        assert summary["error"] == "drive not connected or disabled"

    def test_no_folder_reports_error(self):
        db, _ = self._db()
        integration = _integration(folder=None)
        integration["config"] = {}
        with patch.object(dks, "get_service_supabase", return_value=db), patch.object(
            dks, "get_integration", return_value=integration
        ):
            summary = dks.sync_tenant_drive(TENANT_ID)
        assert summary["error"] == "no folder selected"

    def test_happy_path_ingests_logs_and_compiles(self):
        db, chain = self._db()
        files = [
            {"id": "f1", "name": "pricing.pdf", "mimeType": "application/pdf",
             "modifiedTime": "2026-07-13T09:00:00Z"},
            {"id": "f2", "name": "old.md", "mimeType": "text/markdown",
             "modifiedTime": "2026-07-01T00:00:00Z"},  # older than last sync
        ]
        with patch.object(dks, "get_service_supabase", return_value=db), patch.object(
            dks, "get_integration", return_value=_integration(last_synced="2026-07-12T00:00:00Z")
        ), patch.object(dks, "_access_token", return_value="tok"), patch.object(
            dks, "_list_folder_files", return_value=files
        ), patch.object(
            dks, "_fetch_file", return_value=("pricing.md", b"Balayage $180")
        ), patch.object(
            dks, "ingest_file", return_value={"filename": "pricing.md", "status": "added"}
        ) as ingest, patch.object(dks, "compile_tenant_kb", return_value={"documents": 1}) as compile_:
            summary = dks.sync_tenant_drive(TENANT_ID)
        assert summary == {"added": 1, "updated": 0, "skipped": 0, "pii_flagged": 0, "error": None}
        ingest.assert_called_once()
        compile_.assert_called_once_with(TENANT_ID)
        # sync log row written
        logged = [c.args[0] for c in chain.insert.call_args_list][0]
        assert logged["files_added"] == 1
        assert logged["provider"] == "drive"

    def test_api_failure_recorded_never_raises(self):
        db, chain = self._db()
        with patch.object(dks, "get_service_supabase", return_value=db), patch.object(
            dks, "get_integration", return_value=_integration()
        ), patch.object(dks, "_access_token", side_effect=RuntimeError("google down")):
            summary = dks.sync_tenant_drive(TENANT_ID)
        assert "google down" in summary["error"]
        logged = chain.insert.call_args.args[0]
        assert logged["error"] is not None


class TestDailyDuePass:
    def _db(self, rows):
        chain = MagicMock()
        for m in ("select", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=rows)
        db = MagicMock()
        db.table.return_value = chain
        return db

    def test_syncs_only_due_integrations(self):
        rows = [
            {"client_id": "t-due", "last_synced_at": "2020-01-01T00:00:00+00:00"},
            {"client_id": "t-never", "last_synced_at": None},
            {"client_id": "t-fresh", "last_synced_at": "2099-01-01T00:00:00+00:00"},
        ]
        with patch.object(dks, "get_service_supabase", return_value=self._db(rows)), patch.object(
            dks, "sync_tenant_drive", return_value={}
        ) as sync:
            count = dks.run_drive_kb_sync_due()
        assert count == 2
        synced_ids = {c.args[0] for c in sync.call_args_list}
        assert synced_ids == {"t-due", "t-never"}

    def test_query_failure_returns_zero(self):
        with patch.object(dks, "get_service_supabase", side_effect=RuntimeError("db")):
            assert dks.run_drive_kb_sync_due() == 0


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class TestDriveRouter:
    def test_auth_endpoint_503_when_unconfigured(self, client, mock_supabase):
        with patch.multiple(
            dks.settings, google_client_id="", google_client_secret="",
            google_drive_redirect_uri="",
        ):
            resp = client.get(f"{DRIVE_BASE}/auth", headers=_auth_headers())
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "drive_kb_not_configured"

    def test_auth_endpoint_503_when_no_encryption_key(self, client, mock_supabase):
        with _with_oauth_settings(), patch.object(
            vault.settings, "integrations_enc_key", ""
        ), patch.object(vault.settings, "integrations_enc_keys", ""):
            resp = client.get(f"{DRIVE_BASE}/auth", headers=_auth_headers())
        assert resp.status_code == 503
        assert resp.json()["detail"]["error"] == "encryption_key_required"

    def test_auth_endpoint_returns_consent_url(self, client, mock_supabase):
        with _with_oauth_settings(), _with_key():
            resp = client.get(f"{DRIVE_BASE}/auth", headers=_auth_headers())
        assert resp.status_code == 200
        assert "accounts.google.com" in resp.json()["auth_url"]

    def test_status_disconnected(self, client, mock_supabase):
        with patch("backend.routers.kb_integrations.get_integration", return_value=None):
            resp = client.get(f"{DRIVE_BASE}/status", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["connected"] is False

    def test_status_connected_shows_folder(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.get_integration",
            return_value=_integration(last_synced="2026-07-13T07:00:00+00:00"),
        ):
            resp = client.get(f"{DRIVE_BASE}/status", headers=_auth_headers())
        body = resp.json()
        assert body["connected"] is True
        assert body["folder_name"] == "KB Docs"

    def test_sync_now_409_when_not_connected(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.sync_tenant_drive",
            return_value={"error": "drive not connected or disabled"},
        ):
            resp = client.post(f"{DRIVE_BASE}/sync-now", headers=_auth_headers())
        assert resp.status_code == 409

    def test_requires_auth(self, client):
        assert client.get(f"{DRIVE_BASE}/status").status_code in (401, 422)


# ---------------------------------------------------------------------------
# Router flows — callback, folders, folder pick, sync-now, log, disconnect
# ---------------------------------------------------------------------------

from backend.routers import kb_integrations as kbi  # noqa: E402


class TestDriveRouterFlows:
    def test_callback_saves_tokens_and_redirects(self, client, mock_supabase):
        state = kbi._encode_state(TENANT_ID)
        with patch(
            "backend.routers.kb_integrations.exchange_code",
            return_value={"access_token": "at", "refresh_token": "rt"},
        ), patch("backend.routers.kb_integrations.save_tokens") as save, patch.object(
            kbi.settings, "frontend_url", "https://app.example.com"
        ):
            resp = client.get(
                f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": state}
            )
        assert resp.status_code in (302, 307)
        assert "/dashboard/knowledge?drive=connected" in resp.headers["location"]
        assert save.call_args.args[0] == TENANT_ID

    def test_callback_html_fallback_without_frontend_url(self, client, mock_supabase):
        state = kbi._encode_state(TENANT_ID)
        with patch(
            "backend.routers.kb_integrations.exchange_code",
            return_value={"access_token": "at"},
        ), patch("backend.routers.kb_integrations.save_tokens"), patch.object(
            kbi.settings, "frontend_url", ""
        ):
            resp = client.get(
                f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": state}
            )
        assert resp.status_code == 200
        assert "Connected!" in resp.text

    def test_callback_rejects_bad_state(self, client, mock_supabase):
        resp = client.get(
            f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": "garbage"}
        )
        assert resp.status_code == 400

    def test_callback_rejects_wrong_purpose_state(self, client, mock_supabase):
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone

        state = jose_jwt.encode(
            {
                "tenant_id": TENANT_ID,
                "purpose": "something_else",
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            kbi._jwt_secret(),
            algorithm="HS256",
        )
        resp = client.get(
            f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": state}
        )
        assert resp.status_code == 400

    def test_callback_503_when_encryption_missing(self, client, mock_supabase):
        state = kbi._encode_state(TENANT_ID)
        with patch(
            "backend.routers.kb_integrations.exchange_code",
            side_effect=dks.EncryptionRequired("no key"),
        ):
            resp = client.get(
                f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": state}
            )
        assert resp.status_code == 503

    def test_callback_400_when_exchange_fails(self, client, mock_supabase):
        state = kbi._encode_state(TENANT_ID)
        with patch(
            "backend.routers.kb_integrations.exchange_code",
            side_effect=RuntimeError("google says no"),
        ):
            resp = client.get(
                f"{DRIVE_BASE}/callback", params={"code": "c0de", "state": state}
            )
        assert resp.status_code == 400

    def test_folders_listed(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.list_folders",
            return_value=[{"id": "f1", "name": "KB Docs"}],
        ):
            resp = client.get(f"{DRIVE_BASE}/folders", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["folders"][0]["name"] == "KB Docs"

    def test_folders_409_when_not_connected(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.list_folders",
            side_effect=ValueError("drive not connected"),
        ):
            resp = client.get(f"{DRIVE_BASE}/folders", headers=_auth_headers())
        assert resp.status_code == 409

    def test_folders_502_on_google_failure(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.list_folders",
            side_effect=RuntimeError("api down"),
        ):
            resp = client.get(f"{DRIVE_BASE}/folders", headers=_auth_headers())
        assert resp.status_code == 502

    def test_set_folder_triggers_first_sync(self, client, mock_supabase):
        with patch("backend.routers.kb_integrations.set_folder") as setf, patch(
            "backend.routers.kb_integrations.sync_tenant_drive",
            return_value={"added": 3, "updated": 0},
        ):
            resp = client.post(
                f"{DRIVE_BASE}/folder",
                headers=_auth_headers(),
                json={"folder_id": "f1", "folder_name": "KB Docs"},
            )
        assert resp.status_code == 200
        assert resp.json()["folder_set"] is True
        assert resp.json()["sync"]["added"] == 3
        assert setf.call_args.args == (TENANT_ID, "f1", "KB Docs")

    def test_set_folder_409_when_not_connected(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.set_folder",
            side_effect=ValueError("drive not connected"),
        ):
            resp = client.post(
                f"{DRIVE_BASE}/folder",
                headers=_auth_headers(),
                json={"folder_id": "f1", "folder_name": "KB Docs"},
            )
        assert resp.status_code == 409

    def test_sync_now_returns_summary(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.sync_tenant_drive",
            return_value={"added": 1, "updated": 2, "skipped": 0},
        ):
            resp = client.post(f"{DRIVE_BASE}/sync-now", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["sync"]["updated"] == 2

    def test_sync_log_returns_tenant_rows(self, client, mock_supabase):
        rows = [
            {"synced_at": "2026-07-13T07:00:00+00:00", "files_added": 2,
             "files_updated": 0, "files_skipped": 1, "files_pii_flagged": 0,
             "error": None},
        ]
        chain = MagicMock()
        for m in ("select", "eq", "order", "limit"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=rows)
        mock_supabase.table.return_value = chain
        resp = client.get(f"{DRIVE_BASE}/sync-log", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["log"][0]["files_added"] == 2
        mock_supabase.table.assert_called_with("integration_sync_log")

    def test_disconnect_removes_connection(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.disconnect", return_value=True
        ):
            resp = client.delete(f"{DRIVE_BASE}/", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["disconnected"] is True

    def test_disconnect_404_when_not_connected(self, client, mock_supabase):
        with patch(
            "backend.routers.kb_integrations.disconnect", return_value=False
        ):
            resp = client.delete(f"{DRIVE_BASE}/", headers=_auth_headers())
        assert resp.status_code == 404
