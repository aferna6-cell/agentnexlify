"""Tests for the read-only schema-log vs live schema_migrations checker.

Covers the 196/197 stale-docs regression, deferred 201 vs unexpected unapplied,
live-missing docs, duplicate/version-name edges, and fail-closed live-read
errors. No live DB.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.check_schema_log_migrations import (
    AllowlistUnavailable,
    DEFAULT_DEFERRED,
    DEFAULT_WATCH_FROM,
    LiveStateUnavailable,
    compare,
    load_deferred_allowlist,
    load_live_rows,
    main,
    parse_schema_log,
    redact_secrets,
    run_check,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


NOT_YET_196_197 = """
## Migration 196_os_tool_executions_status_no_approved — tighten status CHECK (NOT YET APPLIED)
Follow-on to 195.

## Migration 197_os_tool_executions_l2_idempotency_required — L2 must have a key (NOT YET APPLIED)
Follow-on to 195/196.
"""

DEFERRED_201 = """
## 201_website_connections.sql (2026-09-03)

**Applied:** NOT applied (this PR is code-only; no prod/schema deploy).
"""

APPLIED_196 = """
## Migration 196_os_tool_executions_status_no_approved — tighten status CHECK (APPLIED 2026-08-30)

**Applied (live versions, not this hour):** prod
(`196_os_tool_executions_status_no_approved`, 20260830024338).
"""

LIVE_196_197 = [
    {"version": "20260830024338", "name": "196_os_tool_executions_status_no_approved"},
    {"version": "20260830024346", "name": "197_os_tool_executions_l2_idempotency_required"},
]


def _kinds(findings):
    return [item.kind for item in findings]


def test_live_applied_docs_unapplied_is_196_197_regression():
    docs = parse_schema_log(NOT_YET_196_197)
    findings = compare(docs, LIVE_196_197, deferred=DEFAULT_DEFERRED, watch_from=195)
    kinds = _kinds(findings)
    assert kinds.count("live_applied_docs_unapplied") == 2
    numbers = {item.number for item in findings if item.kind == "live_applied_docs_unapplied"}
    assert numbers == {196, 197}


def test_intentionally_deferred_201_is_ok_when_live_missing():
    docs = parse_schema_log(DEFERRED_201)
    findings = compare(docs, [], deferred=frozenset({201}), watch_from=195)
    assert findings == []


def test_non_deferred_unapplied_live_missing_is_drift():
    docs = parse_schema_log(
        "## Migration 202_unexpected_unapplied — leftover (NOT YET APPLIED)\n"
    )
    findings = compare(docs, [], deferred=frozenset({201}), watch_from=195)
    assert _kinds(findings) == ["docs_unapplied_live_missing"]
    assert findings[0].number == 202
    assert "not on the deferred allowlist" in findings[0].detail


def test_deferred_201_silent_while_unexpected_unapplied_is_finding():
    docs = parse_schema_log(
        DEFERRED_201 + "\n## Migration 202_unexpected_unapplied (NOT YET APPLIED)\n"
    )
    findings = compare(docs, [], deferred=frozenset({201}), watch_from=195)
    assert _kinds(findings) == ["docs_unapplied_live_missing"]
    assert [item.number for item in findings] == [202]


def test_201_is_flagged_when_allowlist_is_empty():
    docs = parse_schema_log(DEFERRED_201)
    findings = compare(docs, [], deferred=frozenset(), watch_from=195)
    assert _kinds(findings) == ["docs_unapplied_live_missing"]
    assert findings[0].number == 201


def test_deferred_201_still_fails_if_live_has_it_and_docs_say_unapplied():
    docs = parse_schema_log(DEFERRED_201)
    live = [{"version": "20260903120000", "name": "201_website_connections"}]
    findings = compare(docs, live, deferred=frozenset({201}), watch_from=195)
    assert _kinds(findings) == ["live_applied_docs_unapplied"]
    assert findings[0].number == 201


def test_docs_applied_live_missing_mismatch():
    docs = parse_schema_log(APPLIED_196)
    findings = compare(docs, [], deferred=DEFAULT_DEFERRED, watch_from=195)
    assert _kinds(findings) == ["docs_applied_live_missing"]
    assert findings[0].number == 196


def test_prod_195_name_without_number_prefix_matches():
    docs = parse_schema_log(
        "## Migration 195_os_tool_executions — os_tool_executions (APPLIED 2026-08-28)\n"
    )
    live = [{"version": "20260828175205", "name": "os_tool_executions"}]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert findings == []


def test_canonical_schema_log_accepts_prod_195_unprefixed_name():
    docs = parse_schema_log(
        (REPO_ROOT / "docs" / "dev-knowledge" / "schema-log.md").read_text(encoding="utf-8")
    )
    live = [
        {"version": "20260828175205", "name": "os_tool_executions"},
        {"version": "20260830024338", "name": "196_os_tool_executions_status_no_approved"},
        {"version": "20260830024346", "name": "197_os_tool_executions_l2_idempotency_required"},
        {"version": "20260830030000", "name": "198_tenant_kb_chunks"},
        {"version": "20260902000000", "name": "199_os_workflows"},
        {"version": "20260902010000", "name": "200_os_workflows_integrity"},
    ]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert findings == []


def test_run_check_unexpected_unapplied_exits_1_while_deferred_201_is_ok(tmp_path: Path):
    schema_log = tmp_path / "schema-log.md"
    schema_log.write_text(
        DEFERRED_201 + "\n## Migration 202_unexpected_unapplied (NOT YET APPLIED)\n",
        encoding="utf-8",
    )
    live_json = tmp_path / "live.json"
    live_json.write_text("[]", encoding="utf-8")
    code, lines = run_check(schema_log=schema_log, live_json=live_json, deferred=[201])
    assert code == 1
    assert any("docs_unapplied_live_missing" in line and "202" in line for line in lines)
    assert not any("201" in line and "docs_unapplied_live_missing" in line for line in lines)

    schema_log.write_text(DEFERRED_201, encoding="utf-8")
    code_ok, lines_ok = run_check(schema_log=schema_log, live_json=live_json, deferred=[201])
    assert code_ok == 0
    assert any(line.startswith("OK:") for line in lines_ok)


def test_duplicate_doc_numbers_are_findings():
    text = NOT_YET_196_197 + "\n## Migration 196_os_tool_executions_status_no_approved (APPLIED)\n"
    docs = parse_schema_log(text)
    findings = compare(docs, LIVE_196_197, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert "duplicate_doc" in _kinds(findings)
    assert any(item.number == 196 for item in findings if item.kind == "duplicate_doc")


def test_duplicate_live_name_and_version_are_findings():
    docs = parse_schema_log(APPLIED_196)
    live = [
        {"version": "20260830024338", "name": "196_os_tool_executions_status_no_approved"},
        {"version": "20260830024338", "name": "196_os_tool_executions_status_no_approved"},
    ]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    kinds = set(_kinds(findings))
    assert "duplicate_live_name" in kinds
    assert "duplicate_live_version" in kinds


def test_version_name_mismatch_same_number_different_slug():
    docs = parse_schema_log(APPLIED_196)
    live = [{"version": "20260830024338", "name": "196_wrong_slug"}]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert "name_mismatch" in _kinds(findings)
    assert findings[0].number == 196


def test_empty_live_name_or_version_is_edge_finding():
    docs = parse_schema_log(APPLIED_196)
    live = [{"version": "", "name": "196_os_tool_executions_status_no_approved"}]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert "unparseable_live_row" in _kinds(findings)


def test_fail_closed_when_live_state_unavailable():
    docs = parse_schema_log(APPLIED_196)
    findings = compare(docs, None, deferred=DEFAULT_DEFERRED, watch_from=195)
    assert _kinds(findings) == ["live_unreadable"]


def test_load_live_rows_missing_source_raises():
    with pytest.raises(LiveStateUnavailable):
        load_live_rows(None)


def test_load_live_rows_invalid_json_raises(tmp_path: Path):
    path = tmp_path / "live.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(LiveStateUnavailable):
        load_live_rows(path)


def test_load_live_rows_rejects_non_object_rows(tmp_path: Path):
    path = tmp_path / "live.json"
    path.write_text(json.dumps(["196_os_tool_executions_status_no_approved"]), encoding="utf-8")
    with pytest.raises(LiveStateUnavailable):
        load_live_rows(path)


def test_run_check_fail_closed_on_missing_live_json(tmp_path: Path):
    schema_log = tmp_path / "schema-log.md"
    schema_log.write_text(APPLIED_196, encoding="utf-8")
    code, lines = run_check(schema_log=schema_log, live_json=None)
    assert code == 2
    assert any("live_unreadable" in line for line in lines)
    joined = "\n".join(lines)
    assert "postgres://" not in joined
    assert "SERVICE" not in joined


def test_run_check_does_not_echo_credential_shaped_errors(tmp_path: Path):
    schema_log = tmp_path / "schema-log.md"
    schema_log.write_text(APPLIED_196, encoding="utf-8")
    live_json = tmp_path / "live.json"
    live_json.write_text(
        "postgres://user:supersecret@db.example.supabase.co:5432/postgres",
        encoding="utf-8",
    )
    code, lines = run_check(schema_log=schema_log, live_json=live_json)
    assert code == 2
    joined = "\n".join(lines)
    assert "supersecret" not in joined
    assert "postgres://user:" not in joined


def test_redact_secrets_strips_urls_and_keys():
    raw = "failed postgres://user:hunter2@db.host/postgres Bearer eyJabc.def SUPABASE_SERVICE_KEY=sk-live"
    cleaned = redact_secrets(raw)
    assert "hunter2" not in cleaned
    assert "eyJabc" not in cleaned
    assert "sk-live" not in cleaned


def test_default_allowlist_is_201_only():
    assert DEFAULT_DEFERRED == frozenset({201})
    assert DEFAULT_WATCH_FROM == 195
    loaded = load_deferred_allowlist(REPO_ROOT / "ops" / "schema" / "deferred-migrations.json")
    assert loaded == frozenset({201})


def test_year_date_headings_are_not_migration_202():
    text = (
        "## 2026-06-12 — migration 144: tenants.is_demo\n\n"
        "## 201_website_connections.sql (2026-09-03)\n\n"
        "**Applied:** NOT applied (code-only).\n"
    )
    docs = parse_schema_log(text)
    assert [entry.number for entry in docs] == [201]


def test_parser_reads_applied_field_and_heading_status():
    docs = parse_schema_log(DEFERRED_201 + APPLIED_196)
    by_number = {entry.number: entry for entry in docs}
    assert by_number[201].status == "unapplied"
    assert by_number[201].slug == "website_connections"
    assert by_number[196].status == "applied"
    assert by_number[196].slug == "os_tool_executions_status_no_approved"


def test_compare_output_never_includes_customer_fields():
    docs = parse_schema_log(NOT_YET_196_197)
    live = [
        {
            "version": "20260830024338",
            "name": "196_os_tool_executions_status_no_approved",
            "email": "customer@example.com",
            "statements": ["SELECT * FROM leads"],
        }
    ]
    findings = compare(docs, live, deferred=DEFAULT_DEFERRED, watch_from=195)
    blob = " ".join(f"{item.kind} {item.number} {item.name} {item.detail}" for item in findings)
    assert "customer@example.com" not in blob
    assert "leads" not in blob


def _write_allowlist(path: Path, payload) -> Path:
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _cli_argv(tmp_path: Path, *, allowlist, live=None, schema=DEFERRED_201, extra=None):
    schema_log = tmp_path / "schema-log.md"
    schema_log.write_text(schema, encoding="utf-8")
    live_json = tmp_path / "live.json"
    live_json.write_text(json.dumps([] if live is None else live), encoding="utf-8")
    deferred_json = tmp_path / "deferred-migrations.json"
    argv = [
        "--schema-log",
        str(schema_log),
        "--live-json",
        str(live_json),
        "--deferred-json",
        str(deferred_json),
    ]
    if allowlist is not None:
        _write_allowlist(deferred_json, allowlist)
    if extra:
        argv.extend(extra)
    return argv


def test_empty_allowlist_file_stays_empty_and_does_not_restore_default(tmp_path: Path):
    path = _write_allowlist(tmp_path / "deferred.json", {"deferred_unapplied": []})
    assert load_deferred_allowlist(path) == frozenset()
    assert load_deferred_allowlist(path) != DEFAULT_DEFERRED


def test_load_missing_allowlist_raises(tmp_path: Path):
    missing = tmp_path / "missing-deferred.json"
    with pytest.raises(AllowlistUnavailable, match="missing"):
        load_deferred_allowlist(missing)


def test_load_malformed_allowlist_raises(tmp_path: Path):
    path = _write_allowlist(tmp_path / "deferred.json", "{not json")
    with pytest.raises(AllowlistUnavailable, match="not valid JSON"):
        load_deferred_allowlist(path)


def test_load_wrong_shape_allowlist_raises(tmp_path: Path):
    array_path = _write_allowlist(tmp_path / "as-array.json", [201])
    with pytest.raises(AllowlistUnavailable, match="JSON object"):
        load_deferred_allowlist(array_path)
    missing_key = _write_allowlist(tmp_path / "no-key.json", {"note": "no list"})
    with pytest.raises(AllowlistUnavailable, match="missing deferred_unapplied"):
        load_deferred_allowlist(missing_key)
    bad_type = _write_allowlist(tmp_path / "string-list.json", {"deferred_unapplied": "201"})
    with pytest.raises(AllowlistUnavailable, match="JSON array"):
        load_deferred_allowlist(bad_type)


def test_load_non_integer_and_duplicate_entries_raise(tmp_path: Path):
    non_int = _write_allowlist(
        tmp_path / "non-int.json", {"deferred_unapplied": [201, "two"]}
    )
    with pytest.raises(AllowlistUnavailable, match="positive integers; invalid entry at index 1"):
        load_deferred_allowlist(non_int)
    boolean_entry = _write_allowlist(
        tmp_path / "bool.json", {"deferred_unapplied": [True]}
    )
    with pytest.raises(AllowlistUnavailable, match="invalid entry at index 0"):
        load_deferred_allowlist(boolean_entry)
    duplicates = _write_allowlist(
        tmp_path / "dupes.json", {"deferred_unapplied": [201, 201]}
    )
    with pytest.raises(AllowlistUnavailable, match="duplicate entry 201 at index 1"):
        load_deferred_allowlist(duplicates)


def test_cli_explicit_201_exits_0(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist={"deferred_unapplied": [201]})
    assert main(argv) == 0
    assert "OK:" in capsys.readouterr().out


def test_cli_empty_allowlist_flags_201_exits_1(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist={"deferred_unapplied": []})
    assert main(argv) == 1
    out = capsys.readouterr().out
    assert "docs_unapplied_live_missing" in out
    assert "201" in out


def test_cli_missing_allowlist_fail_closed(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist=None)
    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "allowlist_unreadable" in out
    assert "missing" in out


def test_cli_malformed_json_fail_closed(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist="{not json")
    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "allowlist_unreadable" in out
    assert "not valid JSON" in out


def test_cli_non_integer_entries_fail_closed(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist={"deferred_unapplied": [201, "two"]})
    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "allowlist_unreadable" in out
    assert "invalid entry at index 1" in out


def test_cli_duplicate_entries_fail_closed(tmp_path: Path, capsys):
    argv = _cli_argv(tmp_path, allowlist={"deferred_unapplied": [201, 201]})
    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "allowlist_unreadable" in out
    assert "duplicate entry 201 at index 1" in out


def test_cli_allowlist_errors_do_not_echo_secrets(tmp_path: Path, capsys):
    secret = "postgres://user:supersecret@db.example.supabase.co:5432/postgres"
    argv = _cli_argv(tmp_path, allowlist=secret)
    assert main(argv) == 2
    out = capsys.readouterr().out
    assert "supersecret" not in out
    assert "postgres://user:" not in out
    assert "allowlist_unreadable" in out
