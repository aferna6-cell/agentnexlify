"""Tests for M8 staging server credential validation (legacy JWT + sb_secret_)."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import socket
import sys
import urllib.request
import urllib.response
from email.message import Message
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

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
CLAIM_CANARY = "SECRET_CANARY_VALUE"
LEGACY_CANARY_ROLE = _fake_jwt({"role": CLAIM_CANARY, "ref": STAGING_REF})
LEGACY_CANARY_REF = _fake_jwt({"role": "service_role", "ref": CLAIM_CANARY})
MODERN_SECRET = "sb_secret_test_key_abcdefghijklmnopqrstuvwxyz"
MODERN_PUBLISHABLE = "sb_publishable_test_key_abcdefghijklmnopqrstuvwxyz"
STAGING_API = "https://agentnexlify-staging.up.railway.app"
STAGING_SB = f"https://{STAGING_REF}.supabase.co"
PROD_API = "https://agentnexlify-production.up.railway.app"
PROD_SB = f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co"
CANARY = "URL_CANARY"
_RAW_IO_COUNTS = ("urlopen", "getaddrinfo", "create_connection")
_IO_COUNTS = ("_get", "_post_json") + _RAW_IO_COUNTS


def _reason_lines(out: str) -> list[str]:
    lines = []
    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:])
    return lines


def _watch(counts: dict[str, int], name: str):
    def _inner(*args, **kwargs):
        counts[name] += 1
        raise AssertionError(name)

    return _inner


def _bind_raw_sentinels(monkeypatch, counts: dict[str, int]) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _watch(counts, "urlopen"))
    monkeypatch.setattr(socket, "getaddrinfo", _watch(counts, "getaddrinfo"))
    monkeypatch.setattr(socket, "create_connection", _watch(counts, "create_connection"))


def _assert_counts(counts: dict[str, int], names: tuple[str, ...]) -> None:
    assert counts == {name: 0 for name in names}


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
            supabase_url=PROD_SB,
            api_base=STAGING_API,
        )
        assert fails == [creds.REASON_PRODUCTION_SUPABASE]

    def test_rejects_production_api_base(self):
        fails = creds.staging_target_errors(
            supabase_url=STAGING_SB,
            api_base=PROD_API,
        )
        assert fails == [creds.REASON_PRODUCTION_API]

    def test_both_production_reasons_are_distinct(self):
        fails = creds.staging_target_errors(
            supabase_url=f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF.upper()}.SUPABASE.CO.",
            api_base="https://AGENTNEXLIFY-PRODUCTION.UP.RAILWAY.APP:443",
        )
        assert fails == [creds.REASON_PRODUCTION_SUPABASE, creds.REASON_PRODUCTION_API]

    def test_allows_case_normalized_staging_hosts(self):
        fails = creds.staging_target_errors(
            supabase_url=f"https://{STAGING_REF.upper()}.supabase.co.:443",
            api_base="HTTPS://AGENTNEXLIFY-STAGING.UP.RAILWAY.APP:443/",
        )
        assert fails == []

    def test_rejects_cleartext_approved_staging_hosts(self):
        fails = creds.staging_target_errors(
            supabase_url=f"http://{STAGING_REF.upper()}.supabase.co",
            api_base="http://AGENTNEXLIFY-STAGING.UP.RAILWAY.APP:80",
        )
        assert fails == [creds.REASON_HTTPS_SUPABASE, creds.REASON_HTTPS_API]

    @pytest.mark.parametrize(
        "suffix",
        ["/extra", "/;params", "?q=1", "#frag"],
        ids=["path", "params", "query", "fragment"],
    )
    def test_rejects_approved_host_that_is_not_a_strict_origin(self, suffix):
        api_fails = creds.staging_target_errors(
            supabase_url=STAGING_SB,
            api_base=f"{STAGING_API}{suffix}",
        )
        assert api_fails == [creds.REASON_STRICT_ORIGIN_API]
        supabase_fails = creds.staging_target_errors(
            supabase_url=f"{STAGING_SB}{suffix}",
            api_base=STAGING_API,
        )
        assert supabase_fails == [creds.REASON_STRICT_ORIGIN_SUPABASE]
        assert CANARY not in " ".join(api_fails + supabase_fails)

    def test_empty_path_and_single_root_slash_stay_approved(self):
        assert creds.staging_target_errors(supabase_url=STAGING_SB, api_base=STAGING_API) == []
        assert creds.staging_target_errors(
            supabase_url=f"{STAGING_SB}/",
            api_base=f"{STAGING_API}/",
        ) == []

    @pytest.mark.parametrize("suffix", ["//", "///"])
    def test_multiple_trailing_slashes_are_not_a_root_origin(self, suffix):
        assert creds.staging_target_errors(
            supabase_url=STAGING_SB,
            api_base=f"{STAGING_API}{suffix}",
        ) == [creds.REASON_STRICT_ORIGIN_API]
        assert creds.staging_target_errors(
            supabase_url=f"{STAGING_SB}{suffix}",
            api_base=STAGING_API,
        ) == [creds.REASON_STRICT_ORIGIN_SUPABASE]

    def test_unset_targets_are_not_target_errors(self):
        assert creds.staging_target_errors(supabase_url="", api_base="") == []


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


class _RedirectRecorder(urllib.request.BaseHandler):
    handler_order = 0

    def __init__(self, status: int, location: str):
        self.status = status
        self.location = location
        self.requests = []

    def https_open(self, req):
        self.requests.append(req)
        headers = Message()
        headers["Location"] = self.location
        response = urllib.response.addinfourl(io.BytesIO(b""), headers, req.full_url, self.status)
        response.msg = "Redirect"
        return response


class TestVerifyScriptOutput:
    def _load_verify_module(self):
        path = SCRIPTS / "m8_verify_staging_step3.py"
        spec = importlib.util.spec_from_file_location("m8_verify_staging_step3", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod

    def _install_boundary_sentinels(self, monkeypatch, mod):
        counts = {name: 0 for name in _IO_COUNTS}
        monkeypatch.setattr(mod, "_get", _watch(counts, "_get"))
        monkeypatch.setattr(mod, "_post_json", _watch(counts, "_post_json"))
        _bind_raw_sentinels(monkeypatch, counts)
        return counts

    def _run_invalid_main(self, monkeypatch, capsys, api: str, supabase: str):
        mod = self._load_verify_module()
        counts = self._install_boundary_sentinels(monkeypatch, mod)
        monkeypatch.setenv("M8_SMOKE_API_BASE", api)
        monkeypatch.setenv("SUPABASE_URL", supabase)
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", MODERN_SECRET)
        monkeypatch.setenv("M8_SMOKE_CLIENT_ID", "7451537b-a694-4c31-83b0-1b804df3d757")
        monkeypatch.setenv("M8_SMOKE_LOGIN_EMAIL", f"{CANARY}@agentnexlify.invalid")
        monkeypatch.setenv("M8_SMOKE_LOGIN_PASSWORD", CANARY)
        raised = None
        rc = None
        try:
            rc = mod.main()
        except AssertionError as exc:
            raised = exc
        captured = capsys.readouterr()
        return rc, raised, counts, captured.out, captured.err

    def _assert_rejected(self, rc, raised, counts, out, err, api, supabase, reasons):
        _assert_counts(counts, _IO_COUNTS)
        assert raised is None
        assert rc == 1
        text = out + err
        assert _reason_lines(out) == list(reasons)
        for reason in reasons:
            assert out.count(reason) == 1
        assert "PASS" not in out
        assert "Traceback" not in text
        assert "ValueError" not in text
        assert CANARY not in text
        assert MODERN_SECRET not in text
        assert api not in text
        assert supabase not in text

    def _install_raw_io_sentinels(self, monkeypatch):
        counts = {name: 0 for name in _RAW_IO_COUNTS}
        _bind_raw_sentinels(monkeypatch, counts)
        return counts

    def _fake_success_handlers(self, calls, base, sb, client_id):
        anon_url = f"{sb}/rest/v1/tenant_kb_chunks?select=id&limit=3"
        service_url = (
            f"{sb}/rest/v1/tenant_kb_chunks?select=id"
            f"&client_id=eq.{client_id}&status=eq.active&limit=5"
        )
        health_url = f"{base}/health"
        login_url = f"{base}/api/v1/auth/login"

        def fake_get(url, headers):
            if url == health_url:
                calls.append("health")
                return 200, {"status": "ok"}
            if url == anon_url and headers.get("apikey") == LEGACY_ANON:
                assert "Authorization" in headers
                calls.append("anonymous")
                return 200, []
            if url == service_url and headers.get("apikey") == MODERN_SECRET:
                assert "Authorization" not in headers
                calls.append("service")
                return 200, [{"id": "chunk-1"}]
            raise AssertionError(url)

        def fake_post(url, payload):
            assert url == login_url
            assert payload["password"] == CANARY
            calls.append("login")
            return 200, {"token": "jwt"}

        return fake_get, fake_post

    def test_verify_modern_secret_functional_path(self, monkeypatch, capsys):
        mod = self._load_verify_module()
        client_id = "7451537b-a694-4c31-83b0-1b804df3d757"
        calls = []
        counts = self._install_raw_io_sentinels(monkeypatch)
        fake_get, fake_post = self._fake_success_handlers(calls, STAGING_API, STAGING_SB, client_id)

        monkeypatch.setenv("M8_SMOKE_API_BASE", STAGING_API)
        monkeypatch.setenv("SUPABASE_URL", STAGING_SB)
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", MODERN_SECRET)
        monkeypatch.setenv("M8_SMOKE_CLIENT_ID", client_id)
        monkeypatch.setenv("M8_SMOKE_LOGIN_EMAIL", f"{CANARY}@agentnexlify.invalid")
        monkeypatch.setenv("M8_SMOKE_LOGIN_PASSWORD", CANARY)
        monkeypatch.setattr(mod, "_get", fake_get)
        monkeypatch.setattr(mod, "_post_json", fake_post)

        rc = mod.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert calls == ["health", "anonymous", "service", "login"]
        _assert_counts(counts, _RAW_IO_COUNTS)
        assert MODERN_SECRET not in out
        assert CANARY not in out
        assert LEGACY_ANON not in out
        assert "modern_secret_key" in out
        assert "OK step-3 verification complete" in out

    def test_verify_accepts_normalized_staging_hosts(self, monkeypatch, capsys):
        mod = self._load_verify_module()
        client_id = "7451537b-a694-4c31-83b0-1b804df3d757"
        base = "https://AGENTNEXLIFY-STAGING.UP.RAILWAY.APP:443"
        sb = f"https://{STAGING_REF.upper()}.SUPABASE.CO."
        calls = []
        counts = self._install_raw_io_sentinels(monkeypatch)
        fake_get, fake_post = self._fake_success_handlers(calls, base, sb, client_id)
        monkeypatch.setenv("M8_SMOKE_API_BASE", base)
        monkeypatch.setenv("SUPABASE_URL", sb)
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", MODERN_SECRET)
        monkeypatch.setenv("M8_SMOKE_CLIENT_ID", client_id)
        monkeypatch.setenv("M8_SMOKE_LOGIN_EMAIL", f"{CANARY}@agentnexlify.invalid")
        monkeypatch.setenv("M8_SMOKE_LOGIN_PASSWORD", CANARY)
        monkeypatch.setattr(mod, "_get", fake_get)
        monkeypatch.setattr(mod, "_post_json", fake_post)

        rc = mod.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert calls == ["health", "anonymous", "service", "login"]
        _assert_counts(counts, _RAW_IO_COUNTS)
        assert CANARY not in out
        assert MODERN_SECRET not in out

    def test_verify_accepts_normalized_supabase_with_legacy_service_jwt(self, monkeypatch, capsys):
        mod = self._load_verify_module()
        client_id = "7451537b-a694-4c31-83b0-1b804df3d757"
        base = "https://AGENTNEXLIFY-STAGING.UP.RAILWAY.APP:443"
        sb = f"https://{STAGING_REF.upper()}.SUPABASE.CO.:443"
        calls = []
        counts = self._install_raw_io_sentinels(monkeypatch)
        anon_url = f"{sb}/rest/v1/tenant_kb_chunks?select=id&limit=3"
        service_url = (
            f"{sb}/rest/v1/tenant_kb_chunks?select=id"
            f"&client_id=eq.{client_id}&status=eq.active&limit=5"
        )

        def fake_get(url, headers):
            if url == f"{base}/health":
                calls.append("health")
                return 200, {"status": "ok"}
            if url == anon_url and headers.get("apikey") == LEGACY_ANON:
                assert headers.get("Authorization") == f"Bearer {LEGACY_ANON}"
                calls.append("anonymous")
                return 200, []
            if url == service_url and headers.get("apikey") == LEGACY_SERVICE:
                assert headers.get("Authorization") == f"Bearer {LEGACY_SERVICE}"
                calls.append("service")
                return 200, [{"id": "chunk-1"}]
            raise AssertionError(url)

        def fake_post(url, payload):
            assert url == f"{base}/api/v1/auth/login"
            assert payload["password"] == CANARY
            calls.append("login")
            return 200, {"token": "jwt"}

        for key in (
            "SUPABASE_SERVICE_ROLE_KEY",
            "STAGING_SUPABASE_SERVICE_ROLE_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("M8_SMOKE_API_BASE", base)
        monkeypatch.setenv("SUPABASE_URL", sb)
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", LEGACY_SERVICE)
        monkeypatch.setenv("M8_SMOKE_CLIENT_ID", client_id)
        monkeypatch.setenv("M8_SMOKE_LOGIN_EMAIL", f"{CANARY}@agentnexlify.invalid")
        monkeypatch.setenv("M8_SMOKE_LOGIN_PASSWORD", CANARY)
        monkeypatch.setattr(mod, "_get", fake_get)
        monkeypatch.setattr(mod, "_post_json", fake_post)

        rc = mod.main()
        out = capsys.readouterr().out
        assert rc == 0
        assert calls == ["health", "anonymous", "service", "login"]
        _assert_counts(counts, _RAW_IO_COUNTS)
        assert LEGACY_SERVICE not in out
        assert LEGACY_ANON not in out
        assert CANARY not in out
        assert CLAIM_CANARY not in out
        assert "legacy_service_role_jwt" in out
        assert "OK step-3 verification complete" in out

    def test_verify_rejects_production_api_base(self, monkeypatch, capsys):
        rc, raised, counts, out, err = self._run_invalid_main(
            monkeypatch, capsys, PROD_API, STAGING_SB
        )
        self._assert_rejected(
            rc, raised, counts, out, err, PROD_API, STAGING_SB, [creds.REASON_PRODUCTION_API]
        )

    @pytest.mark.parametrize(
        ("api", "supabase", "reasons"),
        [
            (PROD_API, STAGING_SB, [creds.REASON_PRODUCTION_API]),
            (STAGING_API, PROD_SB, [creds.REASON_PRODUCTION_SUPABASE]),
            (PROD_API, PROD_SB, [creds.REASON_PRODUCTION_SUPABASE, creds.REASON_PRODUCTION_API]),
            (
                "https://AGENTNEXLIFY-PRODUCTION.UP.RAILWAY.APP",
                STAGING_SB,
                [creds.REASON_PRODUCTION_API],
            ),
            (
                STAGING_API,
                f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF.upper()}.SUPABASE.CO",
                [creds.REASON_PRODUCTION_SUPABASE],
            ),
            ("https://agentnexlify-production.up.railway.app.", STAGING_SB, [creds.REASON_PRODUCTION_API]),
            (
                "https://agentnexlify-production.up.railway.app:443",
                STAGING_SB,
                [creds.REASON_PRODUCTION_API],
            ),
            (
                STAGING_API,
                f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co.",
                [creds.REASON_PRODUCTION_SUPABASE],
            ),
            (
                STAGING_API,
                f"https://{creds.PRODUCTION_SUPABASE_PROJECT_REF}.supabase.co:443",
                [creds.REASON_PRODUCTION_SUPABASE],
            ),
            ("https://", STAGING_SB, [creds.REASON_MALFORMED_API]),
            ("agentnexlify-production.up.railway.app", STAGING_SB, [creds.REASON_MALFORMED_API]),
            ("https://[::1", STAGING_SB, [creds.REASON_MALFORMED_API]),
            (
                "https://agentnexlify-staging.up.railway.app:bad",
                STAGING_SB,
                [creds.REASON_MALFORMED_API],
            ),
            (
                f"https://user:{CANARY}@agentnexlify-staging.up.railway.app",
                STAGING_SB,
                [creds.REASON_USERINFO_API],
            ),
            (
                "https://agentnexlify-staging.up.railway.app@evil.example",
                STAGING_SB,
                [creds.REASON_UNAPPROVED_API],
            ),
            (
                STAGING_API,
                f"https://user:{CANARY}@{STAGING_REF}.supabase.co",
                [creds.REASON_USERINFO_SUPABASE],
            ),
            (
                STAGING_API,
                f"https://{STAGING_REF}.supabase.co@evil.example",
                [creds.REASON_UNAPPROVED_SUPABASE],
            ),
            ("https://evil.example", STAGING_SB, [creds.REASON_UNAPPROVED_API]),
            (STAGING_API, f"https://{STAGING_REF}.supabase.co:bad", [creds.REASON_MALFORMED_SUPABASE]),
            (STAGING_API, "https://[::1", [creds.REASON_MALFORMED_SUPABASE]),
            (
                "http://agentnexlify-staging.up.railway.app",
                STAGING_SB,
                [creds.REASON_HTTPS_API],
            ),
            (
                STAGING_API,
                f"http://{STAGING_REF}.supabase.co",
                [creds.REASON_HTTPS_SUPABASE],
            ),
            (
                "http://AGENTNEXLIFY-STAGING.UP.RAILWAY.APP",
                f"http://{STAGING_REF.upper()}.SUPABASE.CO",
                [creds.REASON_HTTPS_SUPABASE, creds.REASON_HTTPS_API],
            ),
            (f"{STAGING_API}/extra", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (f"{STAGING_API}/;params", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (f"{STAGING_API}?q=1", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (f"{STAGING_API}#frag", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (STAGING_API, f"{STAGING_SB}/extra", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
            (STAGING_API, f"{STAGING_SB}/;params", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
            (STAGING_API, f"{STAGING_SB}?q=1", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
            (STAGING_API, f"{STAGING_SB}#frag", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
            (f"{STAGING_API}//", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (f"{STAGING_API}///", STAGING_SB, [creds.REASON_STRICT_ORIGIN_API]),
            (STAGING_API, f"{STAGING_SB}//", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
            (STAGING_API, f"{STAGING_SB}///", [creds.REASON_STRICT_ORIGIN_SUPABASE]),
        ],
    )
    def test_real_main_rejects_invalid_targets_before_io(
        self, monkeypatch, capsys, api, supabase, reasons
    ):
        rc, raised, counts, out, err = self._run_invalid_main(monkeypatch, capsys, api, supabase)
        self._assert_rejected(rc, raised, counts, out, err, api, supabase, reasons)

    @pytest.mark.parametrize(
        ("field", "value", "reason"),
        [
            ("M8_SMOKE_API_BASE", None, "M8_SMOKE_API_BASE unset"),
            ("SUPABASE_URL", None, "SUPABASE_URL unset"),
            ("SUPABASE_KEY", None, "SUPABASE_KEY unset"),
            ("SUPABASE_SERVICE_KEY", None, "local server credential invalid: empty credential"),
            ("M8_SMOKE_CLIENT_ID", None, "M8_SMOKE_CLIENT_ID unset"),
            ("M8_SMOKE_LOGIN_EMAIL", None, "M8_SMOKE_LOGIN_EMAIL unset"),
            ("M8_SMOKE_LOGIN_PASSWORD", None, "M8_SMOKE_LOGIN_PASSWORD unset"),
            ("SUPABASE_KEY", CANARY, "SUPABASE_KEY is not anon JWT"),
            (
                "SUPABASE_SERVICE_KEY",
                f"not-a-server-credential-{CANARY}",
                "local server credential invalid: "
                "expected legacy service_role JWT (eyJ...) or modern secret key (sb_secret_...)",
            ),
            (
                "SUPABASE_SERVICE_KEY",
                LEGACY_CANARY_ROLE,
                "local server credential invalid: JWT role is not service_role",
            ),
            (
                "SUPABASE_SERVICE_KEY",
                LEGACY_CANARY_REF,
                "local server credential invalid: JWT ref does not match expected project",
            ),
        ],
        ids=[
            "missing-api-base",
            "missing-supabase-url",
            "missing-anon-key",
            "missing-service-credential",
            "missing-client-id",
            "missing-login-email",
            "missing-login-password",
            "invalid-anon-key",
            "invalid-service-credential",
            "invalid-legacy-role",
            "invalid-legacy-ref",
        ],
    )
    def test_real_main_rejects_incomplete_local_configuration(
        self, monkeypatch, capsys, field, value, reason
    ):
        mod = self._load_verify_module()
        counts = self._install_boundary_sentinels(monkeypatch, mod)
        client_id = "7451537b-a694-4c31-83b0-1b804df3d757"
        for key in (
            "SUPABASE_SERVICE_KEY",
            "SUPABASE_SERVICE_ROLE_KEY",
            "STAGING_SUPABASE_SERVICE_ROLE_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("M8_SMOKE_API_BASE", STAGING_API)
        monkeypatch.setenv("SUPABASE_URL", STAGING_SB)
        monkeypatch.setenv("SUPABASE_KEY", LEGACY_ANON)
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", MODERN_SECRET)
        monkeypatch.setenv("M8_SMOKE_CLIENT_ID", client_id)
        monkeypatch.setenv("M8_SMOKE_LOGIN_EMAIL", f"{CANARY}@agentnexlify.invalid")
        monkeypatch.setenv("M8_SMOKE_LOGIN_PASSWORD", CANARY)
        if value is None:
            monkeypatch.delenv(field, raising=False)
        else:
            monkeypatch.setenv(field, value)

        raised = None
        rc = None
        try:
            rc = mod.main()
        except AssertionError as exc:
            raised = exc
        captured = capsys.readouterr()
        text = captured.out + captured.err
        assert raised is None
        assert rc == 1
        _assert_counts(counts, _IO_COUNTS)
        assert _reason_lines(captured.out) == [reason]
        assert captured.out.count(reason) == 1
        success_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip().startswith(("PASS", "OK"))
        ]
        assert success_lines == []
        assert "Traceback" not in text
        assert "ValueError" not in text
        assert CANARY not in text
        assert CLAIM_CANARY not in text
        assert MODERN_SECRET not in text
        assert LEGACY_ANON not in text
        assert LEGACY_CANARY_ROLE not in text
        assert LEGACY_CANARY_REF not in text
        assert STAGING_API not in text
        assert STAGING_SB not in text
        assert client_id not in text
        assert "/health failed" not in text
        assert "FAIL step-3 verification:" in captured.out
        if value is not None:
            assert value not in text

    def test_opener_disables_stock_redirects(self):
        mod = self._load_verify_module()
        opener = mod._build_opener()
        assert any(isinstance(handler, mod._RejectCredentialRedirects) for handler in opener.handlers)
        assert not any(type(handler) is urllib.request.HTTPRedirectHandler for handler in opener.handlers)

    @pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
    @pytest.mark.parametrize("kind", ["get", "post"])
    def test_credential_requests_do_not_follow_cross_origin_redirects(
        self, monkeypatch, status, kind
    ):
        mod = self._load_verify_module()
        recorder = _RedirectRecorder(status, "https://evil.example/steal")
        real_build = mod._build_opener

        def build():
            opener = real_build()
            opener.add_handler(recorder)
            return opener

        monkeypatch.setattr(mod, "_build_opener", build)
        counts = self._install_raw_io_sentinels(monkeypatch)
        for key in (
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ):
            monkeypatch.delenv(key, raising=False)

        if kind == "get":
            url = f"{STAGING_SB}/rest/v1/tenant_kb_chunks?select=id&limit=3"
            approved = f"{STAGING_REF}.supabase.co"
            code, body = mod._get(
                url,
                {"apikey": CANARY, "Authorization": f"Bearer {CANARY}"},
            )
        else:
            url = f"{STAGING_API}/api/v1/auth/login"
            approved = "agentnexlify-staging.up.railway.app"
            code, body = mod._post_json(
                url,
                {"email": f"{CANARY}@agentnexlify.invalid", "password": CANARY},
            )

        _assert_counts(counts, _RAW_IO_COUNTS)
        assert code == status
        assert len(recorder.requests) == 1
        assert urlparse(recorder.requests[0].full_url).hostname == approved
        off_origin = 0
        for item in recorder.requests:
            host = urlparse(item.full_url).hostname
            blob = " ".join(f"{key}:{value}" for key, value in item.header_items())
            data = item.data.decode() if item.data else ""
            if host != approved:
                off_origin += 1
                assert CANARY not in blob
                assert "apikey" not in blob.lower()
                assert "authorization" not in blob.lower()
                assert CANARY not in data
                assert "evil.example" == host or "evil.example" in item.full_url
        assert off_origin == 0
        assert CANARY not in str(body)
        assert "evil.example" not in recorder.requests[0].full_url
