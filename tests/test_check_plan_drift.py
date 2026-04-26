"""Tests for scripts/check_plan_drift.py — ghost-ref detector for plans/audits."""

from pathlib import Path

from scripts.check_plan_drift import extract_refs, is_external, is_ignorable, scan


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---- extract_refs: markdown links ----


def test_extracts_markdown_link_with_slash():
    refs = extract_refs("see [the file](backend/services/foo.py) for context")
    assert refs == {"backend/services/foo.py"}


def test_extracts_markdown_link_with_line_anchor():
    refs = extract_refs("see [foo](backend/services/foo.py:42)")
    assert refs == {"backend/services/foo.py"}


def test_extracts_markdown_link_with_hash_line():
    refs = extract_refs("see [foo](backend/services/foo.py#L42)")
    assert refs == {"backend/services/foo.py"}


def test_extracts_markdown_link_with_line_range():
    refs = extract_refs("see [foo](backend/services/foo.py#L42-L51)")
    assert refs == {"backend/services/foo.py"}


# ---- extract_refs: backticks ----


def test_extracts_backtick_path_with_slash():
    refs = extract_refs("call `backend/routers/auth.py` to handle it")
    assert refs == {"backend/routers/auth.py"}


def test_skips_bare_filename_in_backticks():
    # Bare filenames without "/" are too noisy — skip
    refs = extract_refs("the `auth.py` module handles login")
    assert refs == set()


def test_extracts_backtick_with_line_anchor():
    refs = extract_refs("see `backend/routers/auth.py:100`")
    assert refs == {"backend/routers/auth.py"}


# ---- skip marker ----


def test_skip_marker_suppresses_line():
    text = "see `backend/foo.py` here <!-- drift-skip -->"
    assert extract_refs(text) == set()


def test_skip_marker_only_affects_marked_line():
    text = (
        "real `backend/real.py` here\n"
        "proposed `backend/future.py` <!-- drift-skip -->\n"
    )
    assert extract_refs(text) == {"backend/real.py"}


# ---- is_external ----


def test_is_external_http():
    assert is_external("http://example.com/foo.py")
    assert is_external("https://example.com/foo.py")


def test_is_external_not_local_path():
    assert not is_external("backend/foo.py")
    assert not is_external("./foo.py")


# ---- is_ignorable ----


def test_ignores_externals():
    assert is_ignorable("https://example.com/foo.py")


def test_ignores_globs():
    assert is_ignorable("backend/**/*.py")
    assert is_ignorable("backend/?.py")


def test_ignores_brace_expansion():
    assert is_ignorable("backend/{services,routers}/foo.py")


def test_ignores_absolute_paths():
    assert is_ignorable("~/foo.py")
    assert is_ignorable("/home/aidan/foo.py")
    assert is_ignorable("/c/Users/aidan/foo.py")
    assert is_ignorable("/usr/local/foo.py")
    assert is_ignorable("/etc/config.py")


def test_does_not_ignore_normal_path():
    assert not is_ignorable("backend/services/foo.py")


# ---- scan: end-to-end ----


def test_scan_reports_stale_ref(tmp_path: Path, monkeypatch):
    # Override REPO_ROOT so resolve() works against tmp_path
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    plans = tmp_path / "plans"
    _write(plans / "test_plan.md", "see [missing](backend/missing.py) for details\n")

    drift = scan([plans])
    key = str(Path("plans/test_plan.md"))
    assert key in drift
    assert drift[key] == ["backend/missing.py"]


def test_scan_ignores_existing_ref(tmp_path: Path, monkeypatch):
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    plans = tmp_path / "plans"
    _write(tmp_path / "backend" / "real.py", "x = 1\n")
    _write(plans / "test_plan.md", "see [real](backend/real.py) for details\n")

    drift = scan([plans])
    assert drift == {}


def test_scan_skips_external_links(tmp_path: Path, monkeypatch):
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    plans = tmp_path / "plans"
    _write(plans / "test_plan.md", "[anthropic](https://anthropic.com/foo.py)\n")

    drift = scan([plans])
    assert drift == {}


def test_scan_skips_globs(tmp_path: Path, monkeypatch):
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    plans = tmp_path / "plans"
    _write(plans / "test_plan.md", "scan `backend/**/*.py` for issues\n")

    drift = scan([plans])
    assert drift == {}


def test_scan_handles_missing_dir(tmp_path: Path, monkeypatch):
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    drift = scan([tmp_path / "nonexistent"])
    assert drift == {}


def test_scan_resolves_relative_to_source_file(tmp_path: Path, monkeypatch):
    import scripts.check_plan_drift as mod
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)

    plans = tmp_path / "plans"
    # Source-file-relative resolution: ../audits/foo.md from plans/test_plan.md
    _write(tmp_path / "audits" / "foo.md", "stub\n")
    _write(plans / "test_plan.md", "see [audit](../audits/foo.md) for context\n")

    drift = scan([plans])
    assert drift == {}
