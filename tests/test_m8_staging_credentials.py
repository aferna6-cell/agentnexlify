"""Tests for M8 staging server credential validation (legacy JWT + sb_secret_)."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from io import StringIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import m8_staging_credentials as creds


def _fake_jwt(payload: dict) -> str:
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"


STAGING_REF = creds.STAGING_SUPABASE_PROJECT_REF
LEGACY_SERVICE = _fake_jwt({"role": "service_role", "ref": STAGING_REF})
LEGACY_ANON = _fake_jwt({"role": "anon", "ref": STAGING_REF})
LEGACY_WRONG_REF = _fake_jwt({"role": "service_role", "ref": "wrongprojectref"})
MODERN_SECRET = "sb_secret_test_key_abcdefghijklmnopqrstuvwxyz"
MODERN_PUBLISHABLE = "sb_publishable_test_key_abcdefghijklmnopqrstuvwxyz"


class TestValidateStagingServerKey:
    def test_legacy_service_role_jwt_accepted(self):
        v = creds.validate_staging_server_key(
            LEGACY_SERVICE, expected_project_ref=STAGING_REF
        )
        assert v.ok is True
        assert v.kind == creds.StagingKeyKind.LEGACY_SERVICE_ROLE
        assert v.jwt_role == "service_role"
        assert v.jwt_ref == STAGING_REF

    def test_anon_jwt_rejected(self):
        v = creds.validate_staging_server_key(LEGACY_ANON)
        assert v.ok is False
        assert "service_role" in (v.error or "")

    def test_modern_secret_accepted(self):
        v = creds.validate_staging_server_key(MODERN_SECRET)
        assert v.ok is True
        assert v.kind == creds.StagingKeyKind.MODERN_SECRET

    def test_publishable_rejected_as_server_credential(self):
        v = creds.validate_staging_server_key(MODERN_PUBLISHABLE)
        assert v.ok is False
        assert "publishable" in (v.error or "")

    def test_masked_values_rejected(self):
        for masked in ("••••••", "sb_secret_••••", f"{MODERN_SECRET[:12]}••••"):
            v = creds.validate_staging_server_key(masked)
            assert v.ok is False, masked
            assert "masked" in (v.error or "")

    def test_wrong_project_legacy_jwt_rejected(self):
        v = creds.validate_staging_server_key(
            LEGACY_WRONG_REF, expected_project_ref=STAGING_REF
        )
        assert v.ok is False
        assert "does not match" in (v.error or "")


class TestSupabaseRestHeaders:
    def test_legacy_jwt_uses_bearer(self):
        headers = creds.supabase_rest_headers(LEGACY_SERVICE)
        assert headers["apikey"] == LEGACY_SERVICE
        assert headers["Authorization"] == f"Bearer {LEGACY_SERVICE}"

    def test_modern_secret_does_not_use_bearer(self):
        headers = creds.supabase_rest_headers(MODERN_SECRET)
        assert headers["apikey"] == MODERN_SECRET
        assert "Authorization" not in headers


class TestSafeKeyMetadata:
    def test_no_secret_contents_in_metadata(self):
        meta = creds.safe_key_metadata(
            MODERN_SECRET,
            creds.validate_staging_server_key(MODERN_SECRET),
        )
        dumped = json.dumps(meta)
        assert MODERN_SECRET not in dumped
        assert meta["key_kind"] == creds.StagingKeyKind.MODERN_SECRET.value
        assert meta["key_len"] == len(MODERN_SECRET)


class TestStagingTargetGuard:
    def test_rejects_production_supabase_url(self):
        fails = creds.staging_target_errors(
            supabase_url=f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co",
            api_base="https://agentnexlify-staging.up.railway.app",
        )
        assert any("production" in f.lower() for f in fails)

    def test_rejects_production_api_base(self):
        fails = creds.staging_target_errors(
            supabase_url=f"https://{STAGING_REF}.supabase.co",
            api_base="https://agentnexlify-production.up.railway.app",
        )
        assert any("production API" in f for f in fails)


class TestWireScriptOutput:
    def _load_wire_module(self):
        path = SCRIPTS / "m8_wire_staging_service_key.py"
        spec = importlib.util.spec_from_file_location("m8_wire_staging_service_key", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def test_wire_accepts_modern_secret_without_leaking(self, monkeypatch, tmp_path):
        mod = self._load_wire_module()
        monkeypatch.setattr(mod, "ENV_PATH", tmp_path / ".env.staging")
        monkeypatch.setenv("STAGING_SUPABASE_SERVICE_ROLE_KEY", MODERN_SECRET)
        monkeypatch.setenv(
            "SUPABASE_URL", f"https://{STAGING_REF}.supabase.co"
        )
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)

        buf = StringIO()
        monkeypatch.setattr(sys, "stdout", buf)
        rc = mod.main()
        assert rc == 0
        out = buf.getvalue()
        assert MODERN_SECRET not in out
        assert "key_kind" in out
        assert "modern_secret_key" in out
        written = (tmp_path / ".env.staging").read_text(encoding="utf-8")
        assert f"SUPABASE_SERVICE_KEY={MODERN_SECRET}" in written
        assert MODERN_SECRET not in out

    def test_wire_rejects_anon_jwt(self, monkeypatch, tmp_path, capsys):
        mod = self._load_wire_module()
        monkeypatch.setattr(mod, "ENV_PATH", tmp_path / ".env.staging")
        monkeypatch.setenv("STAGING_SUPABASE_SERVICE_ROLE_KEY", LEGACY_ANON)
        rc = mod.main()
        assert rc == 2
        out = capsys.readouterr().out
        assert LEGACY_ANON not in out


class TestBackendSupabaseClientPin:
    def test_requirements_pin_supports_modern_secret_keys(self):
        req = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
        assert "supabase==2.28.3" in req
