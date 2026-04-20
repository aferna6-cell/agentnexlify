"""
Unit tests for scripts/memory/backfill_frontmatter.py

Acceptance criteria:
- backfill preserves body content
- backfill adds missing fields
- re-run is a no-op (idempotent)
- dry-run does not write files
- MEMORY.md is not touched
- files without frontmatter are skipped gracefully
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Load the module without installing it as a package
_SCRIPT = Path(__file__).parent.parent / "scripts/memory/backfill_frontmatter.py"
_spec = importlib.util.spec_from_file_location("backfill_frontmatter", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

process_file = _mod.process_file
main = _mod.main


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_memory_file(dir_: Path, name: str, content: str) -> Path:
    p = dir_ / name
    p.write_text(content, encoding="utf-8")
    return p


MINIMAL_FM = """\
---
name: Test Memory
description: A test memory entry
type: user
---

Body content here.
"""

FULL_FM = """\
---
name: Full Memory
description: Already has all fields
type: feedback
confidence: 0.9
last_verified: 2026-01-01T00:00:00Z
access_count: 5
---

Body with all fields.
"""

NO_FM = """\
# Just a heading

No frontmatter here.
"""


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProcessFile:
    def test_adds_missing_fields(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)
        result = process_file(p, dry_run=False)

        assert result["changed"] is True
        assert set(result["added"]) == {"confidence", "last_verified", "access_count"}

        new_content = p.read_text()
        assert "confidence: 0.8" in new_content
        assert "last_verified:" in new_content
        assert "access_count: 0" in new_content

    def test_preserves_body(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)
        process_file(p, dry_run=False)

        new_content = p.read_text()
        assert "Body content here." in new_content

    def test_preserves_existing_fields(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)
        process_file(p, dry_run=False)

        new_content = p.read_text()
        assert "name: Test Memory" in new_content
        assert "description: A test memory entry" in new_content
        assert "type: user" in new_content

    def test_idempotent_rerun(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)

        process_file(p, dry_run=False)
        content_after_first = p.read_text()

        result2 = process_file(p, dry_run=False)
        content_after_second = p.read_text()

        assert result2["changed"] is False
        assert result2["added"] == []
        assert content_after_first == content_after_second

    def test_already_has_all_fields_is_noop(self, tmp_path):
        p = make_memory_file(tmp_path, "full.md", FULL_FM)
        original = p.read_text()

        result = process_file(p, dry_run=False)

        assert result["changed"] is False
        assert p.read_text() == original

    def test_dry_run_does_not_write(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)
        original = p.read_text()

        result = process_file(p, dry_run=True)

        assert result["changed"] is True
        assert p.read_text() == original  # file unchanged

    def test_no_frontmatter_skipped(self, tmp_path):
        p = make_memory_file(tmp_path, "no_fm.md", NO_FM)
        original = p.read_text()

        result = process_file(p, dry_run=False)

        assert result["skipped"] is True
        assert p.read_text() == original

    def test_last_verified_is_iso8601(self, tmp_path):
        p = make_memory_file(tmp_path, "test.md", MINIMAL_FM)
        process_file(p, dry_run=False)

        content = p.read_text()
        # Extract last_verified value
        import re
        m = re.search(r"last_verified: (\S+)", content)
        assert m, "last_verified not found in content"
        val = m.group(1)
        # Should match ISO8601 format YYYY-MM-DDTHH:MM:SSZ
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", val), f"Not ISO8601: {val}"


class TestMain:
    def test_main_updates_files(self, tmp_path):
        make_memory_file(tmp_path, "a.md", MINIMAL_FM)
        make_memory_file(tmp_path, "b.md", MINIMAL_FM)

        ret = main(["--memory-dir", str(tmp_path)])

        assert ret == 0
        for name in ["a.md", "b.md"]:
            content = (tmp_path / name).read_text()
            assert "confidence: 0.8" in content

    def test_main_dry_run_no_writes(self, tmp_path):
        p = make_memory_file(tmp_path, "a.md", MINIMAL_FM)
        original = p.read_text()

        ret = main(["--dry-run", "--memory-dir", str(tmp_path)])

        assert ret == 0
        assert p.read_text() == original

    def test_main_skips_MEMORY_md(self, tmp_path):
        make_memory_file(tmp_path, "MEMORY.md", MINIMAL_FM)
        original = (tmp_path / "MEMORY.md").read_text()

        main(["--memory-dir", str(tmp_path)])

        assert (tmp_path / "MEMORY.md").read_text() == original

    def test_main_missing_dir_returns_1(self, tmp_path):
        ret = main(["--memory-dir", str(tmp_path / "nonexistent")])
        assert ret == 1

    def test_main_idempotent(self, tmp_path):
        make_memory_file(tmp_path, "a.md", MINIMAL_FM)

        main(["--memory-dir", str(tmp_path)])
        content_after_first = (tmp_path / "a.md").read_text()

        main(["--memory-dir", str(tmp_path)])
        content_after_second = (tmp_path / "a.md").read_text()

        assert content_after_first == content_after_second
