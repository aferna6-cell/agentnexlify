"""Tests for the memory-hygiene frontmatter backfill (issue #68).

App-free: imports the script directly, operates on tmp files. No conftest in
this subtree, so these run without the FastAPI app.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import backfill_frontmatter as bf  # noqa: E402

MANAGED = ("confidence", "last_verified", "access_count")


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_adds_all_fields_when_no_frontmatter(tmp_path):
    f = _write(tmp_path / "note.md", "# A memory\n\nBody line one.\nBody line two.\n")
    bf.process(tmp_path)
    out = f.read_text(encoding="utf-8")
    assert out.startswith("---\n")
    for field in MANAGED:
        assert f"\n{field}:" in "\n" + out or out.startswith(f"{field}:") or f"{field}:" in out
    assert "confidence: 0.8" in out
    assert "access_count: 0" in out
    # Body preserved verbatim after the frontmatter block.
    assert out.endswith("# A memory\n\nBody line one.\nBody line two.\n")


def test_appends_only_missing_fields_and_preserves_order(tmp_path):
    f = _write(
        tmp_path / "note.md",
        "---\ntopic: billing\nconfidence: 0.5\n---\nExisting body.\n",
    )
    bf.process(tmp_path)
    out = f.read_text(encoding="utf-8")
    # Existing field + value untouched (not reset to the 0.8 default).
    assert "confidence: 0.5" in out
    assert "confidence: 0.8" not in out
    # Existing custom field preserved and still ordered before the additions.
    assert out.index("topic: billing") < out.index("last_verified:")
    assert out.index("topic: billing") < out.index("access_count:")
    # Missing managed fields added.
    assert "last_verified:" in out
    assert "access_count: 0" in out
    # Body preserved.
    assert out.endswith("---\nExisting body.\n")


def test_idempotent_second_run_is_noop(tmp_path):
    f = _write(tmp_path / "note.md", "---\nconfidence: 0.9\n---\nBody.\n")
    bf.process(tmp_path)
    after_first = f.read_text(encoding="utf-8")
    bf.process(tmp_path)
    after_second = f.read_text(encoding="utf-8")
    assert after_first == after_second


def test_index_file_is_skipped(tmp_path):
    idx = _write(tmp_path / "MEMORY.md", "# Index\n\n- link\n")
    bf.process(tmp_path)
    assert idx.read_text(encoding="utf-8") == "# Index\n\n- link\n"


def test_dry_run_does_not_write(tmp_path):
    original = "# note\nbody\n"
    f = _write(tmp_path / "note.md", original)
    scanned, updated, unchanged = bf.process(tmp_path, dry_run=True)
    assert f.read_text(encoding="utf-8") == original  # unchanged on disk
    assert scanned == 1 and updated == 1 and unchanged == 0


def test_missing_dir_is_safe(tmp_path):
    scanned, updated, unchanged = bf.process(tmp_path / "does-not-exist")
    assert (scanned, updated, unchanged) == (0, 0, 0)
