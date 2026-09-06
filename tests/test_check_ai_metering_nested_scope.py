from pathlib import Path

from scripts import check_ai_metering as meter


def _functions(violations: list[str]) -> set[str]:
    return {item.rsplit(":", 2)[1] for item in violations}


def test_nested_provider_call_is_scanned_as_its_own_function(tmp_path: Path) -> None:
    path = tmp_path / "backend/services/factory.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def factory():\n"
        "    def _call():\n"
        "        return call_claude_messages()\n"
        "    return _call\n",
        encoding="utf-8",
    )

    assert _functions(meter.scan_file(path, is_router=False)) == {"_call"}


def test_nested_guard_does_not_mask_outer_provider_call(tmp_path: Path) -> None:
    path = tmp_path / "backend/services/outer_call.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def outer():\n"
        "    def nested():\n"
        "        reserve_ai_tokens(); record_ai_usage(); release_ai_token_reservation()\n"
        "    return call_claude_messages()\n",
        encoding="utf-8",
    )

    assert _functions(meter.scan_file(path, is_router=False)) == {"outer"}


def test_real_graph_adapter_nested_node_is_metered() -> None:
    path = Path("backend/graph/adapters/llm.py")

    assert "_node" not in _functions(meter.scan_file(path, is_router=False))
