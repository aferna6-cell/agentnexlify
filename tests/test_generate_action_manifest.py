"""Registry-parity tests for the Action tool manifest generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import generate_action_manifest as gam

_MIN_TOOL = """\
export const {ident} = defineTool({{
  id: "{tool_id}",
  department: "{department}",
  riskLevel: {risk},
  requiresApproval: {approval},
  mutating: {mutating},
}});
"""

_MIN_REGISTRY = """\
{imports}
export const toolRegistry = new ToolRegistry();
{registers}
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tool_src(
    ident: str,
    tool_id: str,
    *,
    department: str = "admin_records",
    risk: str = "RISK_READ_ONLY",
    approval: str = "false",
    mutating: str = "false",
) -> str:
    return _MIN_TOOL.format(
        ident=ident,
        tool_id=tool_id,
        department=department,
        risk=risk,
        approval=approval,
        mutating=mutating,
    )


def _registry(pairs: list[tuple[str, str]]) -> str:
    imports = "\n".join(
        f'import {{ {ident} }} from "./tools/{filename}";' for ident, filename in pairs
    )
    registers = "\n".join(f"toolRegistry.register({ident});" for ident, _ in pairs)
    return _MIN_REGISTRY.format(imports=imports, registers=registers)


def _flags() -> str:
    return 'export const SALES_DEPARTMENT = "sales";\n'


@pytest.fixture
def action_tree(tmp_path: Path) -> Path:
    tools = tmp_path / "tools"
    tools.mkdir()
    _write(tmp_path / "flags.ts", _flags())
    _write(
        tools / "send_email.ts",
        _tool_src(
            "sendEmail",
            "send_email",
            department="sales",
            risk="RISK_EXTERNAL_COMMUNICATION",
            approval="true",
            mutating="true",
        ),
    )
    _write(
        tools / "search_customers.ts",
        _tool_src("searchCustomers", "search_customers"),
    )
    _write(
        tools / "ghost_tool.ts",
        _tool_src("ghostTool", "ghost_tool", department="sales"),
    )
    _write(
        tmp_path / "registry.ts",
        _registry(
            [
                ("sendEmail", "send_email.ts"),
                ("searchCustomers", "search_customers.ts"),
            ]
        ),
    )
    return tmp_path


def test_unregistered_tool_definition_is_not_planner_visible(action_tree: Path) -> None:
    manifest = gam.build_manifest(
        tools_dir=action_tree / "tools",
        registry_path=action_tree / "registry.ts",
        flags_path=action_tree / "flags.ts",
    )
    assert set(manifest["tools"]) == {"send_email", "search_customers"}
    assert "ghost_tool" not in manifest["tools"]
    assert (action_tree / "tools" / "ghost_tool.ts").is_file()


def test_registered_tool_cannot_be_omitted(action_tree: Path) -> None:
    manifest = gam.build_manifest(
        tools_dir=action_tree / "tools",
        registry_path=action_tree / "registry.ts",
        flags_path=action_tree / "flags.ts",
    )
    assert "send_email" in manifest["tools"]
    assert "search_customers" in manifest["tools"]
    assert manifest["tools"]["send_email"]["department"] == "sales"
    assert manifest["tools"]["send_email"]["requires_approval"] is True


def test_removing_register_call_drops_defined_tool(action_tree: Path) -> None:
    registry = (action_tree / "registry.ts").read_text(encoding="utf-8")
    assert "toolRegistry.register(sendEmail);" in registry
    (action_tree / "registry.ts").write_text(
        registry.replace("toolRegistry.register(sendEmail);", ""),
        encoding="utf-8",
    )
    manifest = gam.build_manifest(
        tools_dir=action_tree / "tools",
        registry_path=action_tree / "registry.ts",
        flags_path=action_tree / "flags.ts",
    )
    assert "send_email" not in manifest["tools"]
    assert "search_customers" in manifest["tools"]
    assert (action_tree / "tools" / "send_email.ts").is_file()


def test_registered_file_without_definetool_fails(action_tree: Path) -> None:
    (action_tree / "tools" / "send_email.ts").write_text(
        "export const sendEmail = { id: 'send_email' };\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no parseable defineTool"):
        gam.build_manifest(
            tools_dir=action_tree / "tools",
            registry_path=action_tree / "registry.ts",
            flags_path=action_tree / "flags.ts",
        )


def test_unsupported_register_argument_fails() -> None:
    text = """
export const toolRegistry = new ToolRegistry();
toolRegistry.register(defineTool({ id: "send_email" }));
"""
    with pytest.raises(ValueError, match="unsupported toolRegistry.register"):
        gam.parse_registry_registrations(text)


def test_generic_register_shape_fails() -> None:
    text = """
export const toolRegistry = new ToolRegistry();
toolRegistry.register<ErasedTool>(sendEmail);
"""
    with pytest.raises(ValueError, match="unsupported generic"):
        gam.parse_registry_registrations(text)


def test_constructor_registration_fails() -> None:
    text = """
export const toolRegistry = new ToolRegistry([sendEmail]);
"""
    with pytest.raises(ValueError, match="unsupported ToolRegistry constructor"):
        gam.parse_registry_registrations(text)


def test_unsupported_tools_import_fails() -> None:
    text = """
import { sendEmail, extra } from "./tools/send_email.ts";
export const toolRegistry = new ToolRegistry();
toolRegistry.register(sendEmail);
"""
    with pytest.raises(ValueError, match="unsupported/ambiguous ./tools/ import"):
        gam.parse_registry_tool_imports(text)


def test_register_without_matching_import_fails(action_tree: Path) -> None:
    (action_tree / "registry.ts").write_text(
        """
export const toolRegistry = new ToolRegistry();
toolRegistry.register(sendEmail);
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="has no supported"):
        gam.build_manifest(
            tools_dir=action_tree / "tools",
            registry_path=action_tree / "registry.ts",
            flags_path=action_tree / "flags.ts",
        )


def test_commented_out_register_is_not_counted() -> None:
    text = """
import { sendEmail } from "./tools/send_email.ts";
export const toolRegistry = new ToolRegistry();
// toolRegistry.register(sendEmail);
"""
    assert gam.parse_registry_registrations(text) == []


def test_repo_manifest_ids_match_registered_tools_exactly() -> None:
    """Committed manifest IDs == registered Action tools, including billing."""
    generated = gam.build_manifest()
    committed = json.loads(gam.MANIFEST_PATH.read_text(encoding="utf-8"))
    generated_ids = set(generated["tools"])
    committed_ids = set(committed["tools"])
    assert generated_ids == committed_ids

    aliases = gam._load_flag_aliases()
    defined_ids: set[str] = set()
    for path in sorted(gam.TOOLS_DIR.glob("*.ts")):
        if path.name.endswith(".test.ts"):
            continue
        parsed = gam.parse_tool_file(path, aliases)
        if parsed is not None:
            defined_ids.add(parsed["id"])

    # Unregistered definitions cannot remain planner-visible.
    unregistered = defined_ids - generated_ids
    assert unregistered.isdisjoint(committed_ids)

    # Registered tools cannot be omitted (including planner-excluded billing).
    registry_text = gam.REGISTRY_PATH.read_text(encoding="utf-8")
    idents = gam.parse_registry_registrations(registry_text)
    assert len(idents) == len(generated_ids)
    for excluded in (
        "list_overdue_invoices",
        "get_invoice",
        "create_invoice_draft",
        "send_invoice",
        "send_invoice_reminder",
    ):
        assert excluded in generated_ids
    assert "send_email" in generated_ids
    assert "mark_invoice_paid" not in generated_ids


def test_repo_unregistering_send_email_drops_it_from_generated_manifest(
    tmp_path: Path,
) -> None:
    original = gam.REGISTRY_PATH.read_text(encoding="utf-8")
    assert "toolRegistry.register(sendEmail);" in original
    mutated = tmp_path / "registry.ts"
    mutated.write_text(
        original.replace("toolRegistry.register(sendEmail);", ""),
        encoding="utf-8",
    )
    full = gam.build_manifest()
    dropped = gam.build_manifest(
        tools_dir=gam.TOOLS_DIR,
        registry_path=mutated,
        flags_path=gam.FLAGS_PATH,
    )
    assert "send_email" in full["tools"]
    assert "send_email" not in dropped["tools"]
    assert "send_invoice" in dropped["tools"]
    assert (gam.TOOLS_DIR / "send_email.ts").is_file()


def test_check_fails_when_committed_manifest_keeps_unregistered_id(
    tmp_path: Path, action_tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    generated = gam.build_manifest(
        tools_dir=action_tree / "tools",
        registry_path=action_tree / "registry.ts",
        flags_path=action_tree / "flags.ts",
    )
    stale = dict(generated)
    stale_tools = dict(generated["tools"])
    stale_tools["ghost_tool"] = {
        "id": "ghost_tool",
        "department": "sales",
        "risk_level": 0,
        "requires_approval": False,
        "mutating": False,
        "verifiable": False,
    }
    stale["tools"] = stale_tools
    manifest_path = tmp_path / "action_manifest.json"
    manifest_path.write_text(json.dumps(stale, indent=2) + "\n", encoding="utf-8")
    rc = gam.check_manifest(generated, manifest_path=manifest_path)
    out = capsys.readouterr().out
    assert rc == 1
    assert "ghost_tool" in out
    assert "id only in manifest" in out
