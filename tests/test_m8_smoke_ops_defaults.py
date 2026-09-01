"""Ops/smoke helpers must not default SEND_EMAIL_ENABLED or external-send on."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

_ON = r"(?:1|true|TRUE|yes|YES|on|ON)"
_FLAG_KEYS = ("SEND_EMAIL_ENABLED", "M8_SMOKE_ALLOW_EXTERNAL_SEND")

_WORKFLOW = ROOT / ".github/workflows/m8-support-smoke-manual.yml"
_IMPORT = SCRIPTS / "m8_import_railway_vars_json.py"
_WIRE = SCRIPTS / "m8_wire_smoke_secrets.py"
_PULL = SCRIPTS / "m8_pull_railway_staging_env.py"
_RUN = SCRIPTS / "m8_run_support_smoke.sh"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _defaults_on(defaults: dict, key: str) -> bool:
    val = str(defaults.get(key, "")).strip().lower()
    return val in {"1", "true", "yes", "on"}


def _source_defaults_key_on(src: str, key: str) -> bool:
    patterns = (
        rf"{re.escape(key)}\s*:\s*[\"']?{_ON}[\"']?",
        rf"[\"']{re.escape(key)}[\"']\s*:\s*[\"']{_ON}[\"']",
        rf"{re.escape(key)}\s*=\s*[\"']{_ON}[\"']",
        rf"{re.escape(key)}\s*=\s*{_ON}\b",
        rf"{re.escape(key)}\s*=\s*[\"']?\$\{{{re.escape(key)}:-{_ON}\}}",
        rf"setdefault\(\s*[\"']{re.escape(key)}[\"']\s*,\s*[\"']{_ON}[\"']",
    )
    return any(re.search(pattern, src) for pattern in patterns)


class TestWorkflowDoesNotDefaultSendFlagsOn:
    def test_manual_workflow_omits_on_defaults(self):
        src = _WORKFLOW.read_text(encoding="utf-8")
        for key in _FLAG_KEYS:
            assert not _source_defaults_key_on(src, key), f"{key} defaults on in workflow"


class TestHelperDefaultsDoNotEnableSend:
    def test_import_railway_vars_defaults(self):
        mod = _load_module("m8_import_railway_vars_json", _IMPORT)
        for key in _FLAG_KEYS:
            assert not _defaults_on(mod.DEFAULTS, key), f"{key} in import DEFAULTS"

    def test_wire_smoke_secrets_defaults(self):
        mod = _load_module("m8_wire_smoke_secrets", _WIRE)
        for key in _FLAG_KEYS:
            assert not _defaults_on(mod.DEFAULTS, key), f"{key} in wire DEFAULTS"

    def test_pull_railway_staging_defaults(self):
        mod = _load_module("m8_pull_railway_staging_env", _PULL)
        defaults = getattr(mod, "DEFAULTS", {})
        for key in _FLAG_KEYS:
            assert not _defaults_on(defaults, key), f"{key} in pull DEFAULTS"
        src = _PULL.read_text(encoding="utf-8")
        for key in _FLAG_KEYS:
            assert not _source_defaults_key_on(src, key), f"{key} setdefault-on in pull script"

    def test_run_support_smoke_shell_defaults(self):
        src = _RUN.read_text(encoding="utf-8")
        for key in _FLAG_KEYS:
            assert not _source_defaults_key_on(src, key), f"{key} defaults on in run script"

    def test_named_ops_files_have_no_on_literals(self):
        files = (_WORKFLOW, _IMPORT, _WIRE, _PULL, _RUN)
        for path in files:
            src = path.read_text(encoding="utf-8")
            for key in _FLAG_KEYS:
                assert not _source_defaults_key_on(src, key), f"{key}=on in {path.name}"

    def test_import_does_not_persist_send_flags_from_railway_json(self):
        mod = _load_module("m8_import_railway_vars_json", _IMPORT)
        merged = mod.merge_imported(
            {"GOOGLE_CLIENT_ID": "cid"},
            {
                "GOOGLE_CLIENT_SECRET": "csec",
                "SEND_EMAIL_ENABLED": "1",
                "M8_SMOKE_ALLOW_EXTERNAL_SEND": "1",
            },
        )
        for key in _FLAG_KEYS:
            assert key not in merged

    def test_wire_does_not_persist_send_flags_from_existing_env(self):
        mod = _load_module("m8_wire_smoke_secrets", _WIRE)
        merged = mod.merge_wired(
            {
                "GOOGLE_CLIENT_ID": "cid",
                "SEND_EMAIL_ENABLED": "1",
                "M8_SMOKE_ALLOW_EXTERNAL_SEND": "true",
            },
            {"GOOGLE_CLIENT_SECRET": "csec"},
        )
        for key in _FLAG_KEYS:
            assert key not in merged

    def test_pull_does_not_persist_send_flags_from_railway(self):
        mod = _load_module("m8_pull_railway_staging_env", _PULL)
        merged = mod.merge_pulled(
            {
                "GOOGLE_CLIENT_ID": "cid",
                "GOOGLE_CLIENT_SECRET": "csec",
                "SEND_EMAIL_ENABLED": "1",
                "M8_SMOKE_ALLOW_EXTERNAL_SEND": "1",
            }
        )
        for key in _FLAG_KEYS:
            assert key not in merged
        for key in _FLAG_KEYS:
            assert key not in mod.PULL_KEYS
