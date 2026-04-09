from pathlib import Path

from scripts.check_test_local_refs import find_invalid_references


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_reports_missing_import_module(tmp_path: Path):
    _write(tmp_path / "backend" / "__init__.py", "")
    _write(tmp_path / "backend" / "services" / "__init__.py", "")
    _write(
        tmp_path / "tests" / "test_missing_import.py",
        "from backend.services.intent_detection import detect_intent\n",
    )

    issues = find_invalid_references(tmp_path)

    assert len(issues) == 1
    assert "backend.services.intent_detection" in issues[0]


def test_reports_missing_patch_submodule(tmp_path: Path):
    _write(tmp_path / "backend" / "__init__.py", "")
    _write(tmp_path / "backend" / "services" / "__init__.py", "")
    _write(
        tmp_path / "tests" / "test_missing_patch.py",
        "from unittest.mock import patch\n\n"
        "def test_it():\n"
        "    with patch('backend.services.embeddings.httpx.AsyncClient'):\n"
        "        pass\n",
    )

    issues = find_invalid_references(tmp_path)

    assert len(issues) == 1
    assert "backend.services.embeddings" in issues[0]


def test_allows_existing_local_references(tmp_path: Path):
    _write(tmp_path / "backend" / "__init__.py", "")
    _write(tmp_path / "backend" / "services" / "__init__.py", "")
    _write(tmp_path / "backend" / "services" / "managed_agents.py", "VALUE = 1\n")
    _write(
        tmp_path / "tests" / "test_ok.py",
        "from backend.services.managed_agents import VALUE\n"
        "from unittest.mock import patch\n\n"
        "def test_it():\n"
        "    with patch('backend.services.managed_agents.time.sleep'):\n"
        "        assert VALUE == 1\n",
    )

    assert find_invalid_references(tmp_path) == []
