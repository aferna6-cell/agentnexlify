from pathlib import Path

from scripts import check_ai_metering as meter


def _write(tmp_path: Path, relative: str, source: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_collect_violations_scans_backend_outside_routers_and_services(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "backend/graph/adapters/llm.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def invoke_model():\n"
        "    return call_claude_messages()\n",
    )

    violations = meter.collect_violations(tmp_path)

    assert any("backend/graph/adapters/llm.py:invoke_model:" in item for item in violations)


def test_collect_violations_still_excludes_backend_tests(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "backend/tests/test_fake_provider.py",
        "def fake(client):\n"
        "    return client.messages.create(model='test', messages=[])\n",
    )

    assert meter.collect_violations(tmp_path) == []
