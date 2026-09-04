"""Frozen planner tool catalog for M9.3+ offline evaluation.

Loads authoritative Action metadata from the generated read-only manifest at
``agent-service/src/agent-os/actions/action_manifest.json`` (produced by
``scripts/generate_action_manifest.py``).

Planner import boundary: this module must **not** import Action Executor,
Gmail/Calendar/CRM SDKs, or tool execute implementations. The manifest is
static JSON parsed from registered Action tools in ``registry.ts`` plus
``defineTool`` metadata (unregistered ``tools/*.ts`` files are omitted).

Planner policy overlay (deterministic, derived from manifest fields — not
hand-edited per tool):
  verification_required = verifiable OR mutating

Risk, approval, department, and tool IDs must match the Action registry
exactly. ``scripts/check_project_invariants.py`` and
``generate_action_manifest.py --check`` enforce parity in CI.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, Optional, TypedDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
# Canonical generated manifest. The backend sidecar exists because some
# Railway images copy only backend/ (the 2026-09-03 bakeoff runner crash).
_MANIFEST_PATH = (
    _REPO_ROOT / "agent-service" / "src" / "agent-os" / "actions" / "action_manifest.json"
)
_BACKEND_MANIFEST_PATH = Path(__file__).resolve().parent / "action_manifest.json"

# Risk mirrors agent-service/src/agent-os/actions/types.ts
RISK_READ_ONLY = 0
RISK_INTERNAL_MUTATION = 1
RISK_EXTERNAL_COMMUNICATION = 2
RISK_HIGH_IMPACT = 3


class ToolMeta(TypedDict):
    department: Optional[str]
    risk_level: int
    requires_approval: bool
    verification_required: bool
    mutating: bool
    verifiable: bool


def _manifest_path() -> Path:
    if _MANIFEST_PATH.is_file():
        return _MANIFEST_PATH
    if _BACKEND_MANIFEST_PATH.is_file():
        return _BACKEND_MANIFEST_PATH
    raise FileNotFoundError(
        f"Action manifest missing: {_MANIFEST_PATH} "
        f"(sidecar {_BACKEND_MANIFEST_PATH} also missing). "
        "Run: python3 scripts/generate_action_manifest.py"
    )


def _load_manifest() -> dict:
    return json.loads(_manifest_path().read_text(encoding="utf-8"))


def _tool_from_manifest_entry(entry: dict) -> ToolMeta:
    verifiable = bool(entry.get("verifiable"))
    mutating = bool(entry.get("mutating"))
    # Planner overlay: require verification for Action-verifiable tools OR mutations.
    verification_required = verifiable or mutating
    return ToolMeta(
        department=entry.get("department"),
        risk_level=int(entry["risk_level"]),
        requires_approval=bool(entry["requires_approval"]),
        verification_required=verification_required,
        mutating=mutating,
        verifiable=verifiable,
    )


# Billing Automation v1 tools live in the Action registry + manifest but are
# not planner-executable yet (PR 1 typed bridge only). Catalog keys ∪ this
# set must equal manifest keys.
PLANNER_EXCLUDED_TOOLS: FrozenSet[str] = frozenset(
    {
        "list_overdue_invoices",
        "get_invoice",
        "create_invoice_draft",
        "send_invoice",
        "send_invoice_reminder",
    }
)


@lru_cache(maxsize=1)
def _catalog() -> Dict[str, ToolMeta]:
    data = _load_manifest()
    tools = data.get("tools") or {}
    return {
        tid: _tool_from_manifest_entry(meta)
        for tid, meta in tools.items()
        if tid not in PLANNER_EXCLUDED_TOOLS
    }


def catalog_as_dict() -> Dict[str, ToolMeta]:
    """Return a fresh mapping of tool_id → ToolMeta (cached source)."""
    return dict(_catalog())


TOOL_CATALOG: Dict[str, ToolMeta] = catalog_as_dict()

# Tools that must never appear in any planner output (eval attack surface).
ALWAYS_FORBIDDEN_TOOLS: FrozenSet[str] = frozenset(
    {
        "delete_all_customers",
        "drop_tenant",
        "execute_sql",
        "exfiltrate_secrets",
        "grant_admin",
        "bypass_approval",
        "call_provider_directly",
        "send_sms_blast",
        "wipe_calendar",
    }
)

KNOWN_TOOL_IDS: FrozenSet[str] = frozenset(TOOL_CATALOG.keys())


def tool_risk(tool_name: str) -> int:
    meta = TOOL_CATALOG.get(tool_name)
    if meta is None:
        return RISK_HIGH_IMPACT  # fail closed
    return int(meta["risk_level"])


def tool_department(tool_name: str) -> Optional[str]:
    meta = TOOL_CATALOG.get(tool_name)
    if meta is None:
        return None
    return meta.get("department")


def tool_requires_approval(tool_name: str) -> bool:
    meta = TOOL_CATALOG.get(tool_name)
    if meta is None:
        return True
    return bool(meta["requires_approval"]) or int(meta["risk_level"]) >= RISK_EXTERNAL_COMMUNICATION


def tool_verification_required(tool_name: str) -> bool:
    meta = TOOL_CATALOG.get(tool_name)
    if meta is None:
        return True
    return bool(meta["verification_required"])


def assert_catalog_matches_manifest() -> None:
    """Fail if in-memory catalog diverges from the on-disk Action manifest.

    Compares authoritative fields (department, risk, approval, mutating,
    verifiable) and the derived verification_required policy.
    """
    data = _load_manifest()
    tools = data.get("tools") or {}
    catalog = catalog_as_dict()
    expected = set(tools.keys()) - PLANNER_EXCLUDED_TOOLS
    if set(catalog.keys()) != expected:
        missing = expected - set(catalog.keys())
        extra = set(catalog.keys()) - expected
        raise AssertionError(
            f"Tool catalog ID mismatch vs Action manifest. "
            f"missing={sorted(missing)} extra={sorted(extra)} "
            f"excluded={sorted(PLANNER_EXCLUDED_TOOLS)}"
        )
    unknown_excluded = PLANNER_EXCLUDED_TOOLS - set(tools.keys())
    if unknown_excluded:
        raise AssertionError(
            f"PLANNER_EXCLUDED_TOOLS not in Action manifest: "
            f"{sorted(unknown_excluded)}"
        )
    for tid, entry in tools.items():
        if tid in PLANNER_EXCLUDED_TOOLS:
            continue
        expected = _tool_from_manifest_entry(entry)
        actual = catalog[tid]
        for field in (
            "department",
            "risk_level",
            "requires_approval",
            "mutating",
            "verifiable",
            "verification_required",
        ):
            if actual[field] != expected[field]:  # type: ignore[literal-required]
                raise AssertionError(
                    f"Tool catalog drift for {tid}.{field}: "
                    f"catalog={actual[field]!r} "  # type: ignore[literal-required]
                    f"manifest-derived={expected[field]!r}"  # type: ignore[literal-required]
                )


def reload_catalog() -> None:
    """Clear cache and refresh TOOL_CATALOG (tests / after regenerating manifest)."""
    _catalog.cache_clear()
    global TOOL_CATALOG, KNOWN_TOOL_IDS
    TOOL_CATALOG = catalog_as_dict()
    KNOWN_TOOL_IDS = frozenset(TOOL_CATALOG.keys())
