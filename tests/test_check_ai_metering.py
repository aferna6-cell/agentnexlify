from pathlib import Path

import pytest

from scripts import check_ai_metering as meter


def _write(tmp_path: Path, relative: str, source: str) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _functions(violations: list[str]) -> set[str]:
    return {item.rsplit(":", 2)[1] for item in violations}


def test_unmetered_service_is_flagged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/unmetered_svc.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def generate_response():\n"
        "    return call_claude_messages()\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"generate_response"}


def test_real_appointment_brief_budget_helper_has_full_lifecycle() -> None:
    path = Path("backend/services/appointment_brief.py")
    violations = meter.scan_file(path, is_router=False)
    assert "_call_claude_with_budget" not in _functions(violations)


def test_recognized_metered_wrapper_is_not_flagged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(meter, "METERED_WRAPPERS", {"call_guarded_claude"})
    path = _write(
        tmp_path,
        "backend/services/guarded_wrapper.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def call_guarded_claude():\n"
        "    return call_claude_messages()\n",
    )
    assert meter.scan_file(path, is_router=False) == []


def test_mixed_router_flags_only_unguarded_function(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/routers/mixed.py",
        "from fastapi import Depends\n"
        "from backend.dependencies import ai_usage_guard\n"
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def guarded_fn(_guard=Depends(ai_usage_guard)):\n"
        "    return call_claude_messages()\n"
        "def unguarded_fn():\n"
        "    return call_claude_messages()\n",
    )
    assert _functions(meter.scan_file(path, is_router=True)) == {"unguarded_fn"}


def test_ai_call_alias_is_detected(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/alias_user.py",
        "from backend.services.llm_runtime import call_claude_messages as call_llm\n"
        "def generate():\n"
        "    return call_llm()\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"generate"}


def test_excluded_directories_are_not_scanned(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "backend/services/tests/test_ai.py",
        "def fake(client):\n    return client.messages.create()\n",
    )
    _write(
        tmp_path,
        "docs/sample.py",
        "def fake(client):\n    return client.messages.create()\n",
    )
    _write(
        tmp_path,
        "scripts/offline/process.py",
        "def fake(client):\n    return client.messages.create()\n",
    )
    assert meter.collect_violations(tmp_path) == []


def test_direct_messages_create_is_flagged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/direct_sdk.py",
        "def send_message(client):\n"
        "    return client.messages.create(model='test', messages=[])\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"send_message"}


def test_class_method_messages_create_is_flagged(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/class_service.py",
        "class Service:\n"
        "    def send_message(self, client):\n"
        "        return client.messages.create(model='test', messages=[])\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"send_message"}


def test_nested_function_inside_method_does_not_mask_method(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/class_nested.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "class Service:\n"
        "    def send_message(self):\n"
        "        def nested():\n"
        "            reserve_ai_tokens(); record_ai_usage(); release_ai_token_reservation()\n"
        "        return call_claude_messages()\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"send_message"}


def test_raw_provider_entrypoint_is_exempt_only_in_llm_runtime(tmp_path: Path) -> None:
    runtime = _write(
        tmp_path,
        "backend/services/llm_runtime.py",
        "def _call_single_model(client):\n"
        "    return client.messages.create(model='test', messages=[])\n",
    )
    other = _write(
        tmp_path,
        "backend/services/other_runtime.py",
        "def _call_single_model(client):\n"
        "    return client.messages.create(model='test', messages=[])\n",
    )
    assert meter.scan_file(runtime, is_router=False) == []
    assert _functions(meter.scan_file(other, is_router=False)) == {"_call_single_model"}


@pytest.mark.parametrize(
    ("body", "function_name"),
    [
        ("reserve_ai_tokens()", "reserve_only"),
        ("reserve_ai_tokens(); record_ai_usage()", "reserve_and_record"),
        ("reserve_ai_tokens(); release_ai_token_reservation()", "reserve_and_release"),
    ],
)
def test_partial_lifecycle_is_flagged(tmp_path: Path, body: str, function_name: str) -> None:
    path = _write(
        tmp_path,
        f"backend/services/{function_name}.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        f"def {function_name}():\n"
        f"    {body}\n"
        "    return call_claude_messages()\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {function_name}


def test_full_lifecycle_is_accepted(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/full_lifecycle.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def metered():\n"
        "    reserve_ai_tokens()\n"
        "    try:\n"
        "        value = call_claude_messages()\n"
        "        record_ai_usage()\n"
        "        return value\n"
        "    except Exception:\n"
        "        release_ai_token_reservation()\n"
        "        raise\n",
    )
    assert meter.scan_file(path, is_router=False) == []


def test_bare_exemption_is_invalid_but_owner_reason_exemption_is_valid(tmp_path: Path) -> None:
    bare = _write(
        tmp_path,
        "backend/services/bare_exempt.py",
        "def bare_exempt(client):\n"
        "    # ai-metering-exempt:\n"
        "    return client.messages.create()\n",
    )
    valid = _write(
        tmp_path,
        "backend/services/valid_exempt.py",
        "def valid_exempt(client):\n"
        "    # ai-metering-exempt: billing-platform: provider call is metered upstream\n"
        "    return client.messages.create()\n",
    )
    assert _functions(meter.scan_file(bare, is_router=False)) == {"bare_exempt"}
    assert meter.scan_file(valid, is_router=False) == []


def test_guard_alias_is_recognized(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/routers/aliased_guard.py",
        "from fastapi import Depends as Inject\n"
        "from backend.dependencies import ai_usage_guard as meter_guard\n"
        "def guarded(client, _guard=Inject(meter_guard)):\n"
        "    return client.messages.create()\n",
    )
    assert meter.scan_file(path, is_router=True) == []


def test_nested_function_does_not_mask_outer_function(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "backend/services/nested.py",
        "from backend.services.llm_runtime import call_claude_messages\n"
        "def outer():\n"
        "    def nested():\n"
        "        reserve_ai_tokens(); record_ai_usage(); release_ai_token_reservation()\n"
        "    return call_claude_messages()\n",
    )
    assert _functions(meter.scan_file(path, is_router=False)) == {"outer"}


def test_parse_error_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path, "backend/services/broken.py", "def broken(:\n")
    with pytest.raises(meter.ScanError):
        meter.scan_file(path, is_router=False)
