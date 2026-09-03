"""Check product-specific invariants for the active AgentNexLiFy tree.

The checker is intentionally stdlib-only and keeps its scope to active
production surfaces so it is safe for CI and for agents running in the
workspace. It prints concise PASS/FAIL lines and exits nonzero when any
invariant is violated.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CODE_ROOTS = (
    ROOT / "backend",
    ROOT / "frontend",
    ROOT / "widget",
    ROOT / "agent-service",
    ROOT / "ai",
    ROOT / "chrome-extension",
    ROOT / "demo-platform",
    ROOT / "config",
    ROOT / "tools",
    ROOT / "supabase",
)

TEXT_EXTENSIONS = {
    ".html",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".css",
    ".ts",
    ".tsx",
    ".py",
}

SKIP_DIR_NAMES = {
    ".agents",
    ".claude",
    ".codex",
    ".git",
    ".pytest_cache",
    ".venv",
    ".venv312",
    ".venv313",
    "__pycache__",
    "_archive",
    "archive",
    "archives",
    "build",
    "coverage",
    "dist",
    "docs",
    "migrations",
    "node_modules",
    "plans",
    "planning",
    "research-briefs",
    "subconscious",
    "test",
    "tests",
    "e2e",
}

ROUTER_ROOT = ROOT / "backend" / "routers"
APPROVED_ANTHROPIC_WRAPPER = ROOT / "backend" / "services" / "llm_runtime.py"
WIDGET_ASSETS = (
    ("widget", "agentnexlify-widget.js"),
    ("widget", "preview.html"),
)
WIDGET_MIRRORS = (
    ROOT / "frontend" / "public" / "widget",
    ROOT / "landing-page-v2" / "widget",
)
WEBSITE_ROOTS = (
    ROOT / "frontend" / "index.html",
    ROOT / "frontend" / "src",
    ROOT / "frontend" / "public" / "widget",
    ROOT / "landing-page-v2",
    ROOT / "widget" / "agentnexlify-widget.js",
)

RETIRED_PLAN_WORDS = ("foundation", "operations")
LEAD_FIELD_WORDS = ("lead_stage", "service_interest")
PLAN_PATH_HINTS = ("billing", "pricing", "schemas.py")
PLAN_CONTEXT_MARKERS = (
    "billing",
    "description",
    "offer",
    "plan",
    "price",
    "pricing",
    "price-tag",
    "upgrade",
)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check(
    label: str, ok: bool, failures: list[str], details: list[str] | None = None
) -> None:
    if ok:
        print(f"PASS {label}")
        return

    print(f"FAIL {label}")
    for detail in details or []:
        print(f"  - {detail}")
    failures.append(label)


def iter_code_files() -> list[Path]:
    files: list[Path] = []
    for root in CODE_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in SKIP_DIR_NAMES and not name.startswith(".")
            ]
            for name in filenames:
                path = current / name
                if path.suffix.lower() in TEXT_EXTENSIONS:
                    files.append(path)
    return files


def iter_website_files() -> list[Path]:
    files: list[Path] = []
    for root in WEBSITE_ROOTS:
        if root.is_file():
            if root.suffix.lower() in TEXT_EXTENSIONS:
                files.append(root)
            continue
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            dirnames[:] = [
                name
                for name in dirnames
                if name not in SKIP_DIR_NAMES and not name.startswith(".")
            ]
            for name in filenames:
                path = current / name
                if path.suffix.lower() in TEXT_EXTENSIONS:
                    files.append(path)
    return files


def iter_backend_py_files(*, exclude: set[Path] | None = None) -> list[Path]:
    exclude = exclude or set()
    backend_root = ROOT / "backend"
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(backend_root):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIR_NAMES and not name.startswith(".")
        ]
        for name in filenames:
            path = current / name
            if path.suffix.lower() == ".py" and path not in exclude:
                files.append(path)
    return files


def iter_router_py_files() -> list[Path]:
    files: list[Path] = []
    if not ROUTER_ROOT.exists():
        return files
    for dirpath, dirnames, filenames in os.walk(ROUTER_ROOT):
        current = Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIR_NAMES and not name.startswith(".")
        ]
        for name in filenames:
            path = current / name
            if path.suffix.lower() == ".py":
                files.append(path)
    return files


def check_router_future_imports(failures: list[str]) -> None:
    matches: list[str] = []
    for path in iter_router_py_files():
        try:
            text = read_text(path)
        except OSError as exc:
            matches.append(f"{rel(path)}: unreadable ({exc})")
            continue
        # Parse to AST so we only flag a real `from __future__ import ...`
        # statement, not docstring/comment text that mentions the rule.
        try:
            tree = ast.parse(text)
        except SyntaxError:
            # Unparseable file: fall back to detecting the import only at the
            # start of a (stripped) line, never mid-sentence in a docstring.
            if any(
                line.strip().startswith("from __future__ import")
                for line in text.splitlines()
            ):
                matches.append(f"{rel(path)}")
            continue
        if any(
            isinstance(node, ast.ImportFrom) and node.module == "__future__"
            for node in ast.walk(tree)
        ):
            matches.append(f"{rel(path)}")
    check(
        "FastAPI router files avoid future annotations",
        not matches,
        failures,
        matches[:10],
    )


def check_widget_assets(failures: list[str]) -> None:
    issues: list[str] = []
    for folder_name, asset_name in WIDGET_ASSETS:
        canonical = ROOT / folder_name / asset_name
        if not canonical.is_file():
            issues.append(f"missing canonical asset: {rel(canonical)}")
            continue

        canonical_bytes = canonical.read_bytes()
        for mirror_root in WIDGET_MIRRORS:
            mirror = mirror_root / asset_name
            if not mirror.is_file():
                issues.append(f"missing mirrored asset: {rel(mirror)}")
                continue
            try:
                mirror_bytes = mirror.read_bytes()
            except OSError as exc:
                issues.append(f"{rel(mirror)} unreadable ({exc})")
                continue
            if mirror_bytes != canonical_bytes:
                issues.append(f"drift: {rel(canonical)} != {rel(mirror)}")

    check(
        "widget assets are byte-identical across mirrors",
        not issues,
        failures,
        issues[:10],
    )


def check_website_copy_avoids_em_dashes(failures: list[str]) -> None:
    issues: list[str] = []
    # Catch the literal em dash AND its HTML-entity spellings (&mdash;, &#8212;,
    # &#x2014;) \u2014 they render identically but a literal-only scan misses the
    # entities (e.g. landing-page-v2/index.html shipped a `&mdash;`).
    em_dash_markers = ("\u2014", "&mdash;", "&#8212;", "&#x2014;")

    for path in iter_website_files():
        try:
            lines = read_text(path).splitlines()
        except OSError as exc:
            issues.append(f"{rel(path)}: unreadable ({exc})")
            continue

        for lineno, line in enumerate(lines, start=1):
            lowered = line.lower()
            if any(marker in lowered for marker in em_dash_markers):
                issues.append(f"{rel(path)}:{lineno}: contains em dash")

    check(
        "website source avoids em dashes",
        not issues,
        failures,
        issues[:10],
    )


def check_live_schema_fields(failures: list[str]) -> None:
    issues: list[str] = []
    db_context_markers = (
        "db.table(",
        "tenant_insert(",
        "tenant_select(",
        "tenant_update(",
        ".select(",
        ".insert(",
        ".update(",
        ".eq(",
        ".filter(",
        ".match(",
    )

    for path in iter_backend_py_files():
        try:
            text = read_text(path)
        except OSError as exc:
            issues.append(f"{rel(path)}: unreadable ({exc})")
            continue

        lines = text.splitlines()

        for lineno, line in enumerate(lines, start=1):
            if "leads.tenant_id" in line:
                issues.append(f"{rel(path)}:{lineno}: leads.tenant_id")
                continue
            if "conversations.tenant_id" in line:
                issues.append(f"{rel(path)}:{lineno}: conversations.tenant_id")
                continue

            lowered = line.lower()
            if not any(field in lowered for field in LEAD_FIELD_WORDS):
                continue
            if not any(marker in lowered for marker in db_context_markers):
                continue
            issues.append(f"{rel(path)}:{lineno}: {line.strip()}")

    check(
        "active backend code avoids retired live-schema fields",
        not issues,
        failures,
        issues[:10],
    )


def check_retired_plan_names(failures: list[str]) -> None:
    issues: list[str] = []
    plan_context_re = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in RETIRED_PLAN_WORDS) + r")\b",
        re.IGNORECASE,
    )

    for path in iter_code_files():
        if not any(hint in rel(path).lower() for hint in PLAN_PATH_HINTS):
            continue
        try:
            lines = read_text(path).splitlines()
        except OSError as exc:
            issues.append(f"{rel(path)}: unreadable ({exc})")
            continue

        for index, line in enumerate(lines):
            if not plan_context_re.search(line):
                continue
            window = " ".join(
                lines[max(0, index - 1) : min(len(lines), index + 2)]
            ).lower()
            if not any(marker in window for marker in PLAN_CONTEXT_MARKERS):
                continue
            issues.append(f"{rel(path)}:{index + 1}: {line.strip()}")

    check(
        "retired plan names do not appear in plan-related code",
        not issues,
        failures,
        issues[:10],
    )


def check_anthropic_sdk_usage(failures: list[str]) -> None:
    issues: list[str] = []
    direct_pattern = re.compile(r"\bmessages\.create\s*\(")

    for path in iter_backend_py_files(exclude={APPROVED_ANTHROPIC_WRAPPER}):
        try:
            text = read_text(path)
        except OSError as exc:
            issues.append(f"{rel(path)}: unreadable ({exc})")
            continue

        if not direct_pattern.search(text):
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if direct_pattern.search(line):
                issues.append(f"{rel(path)}:{lineno}: {line.strip()}")
                break

    check(
        "direct Anthropic SDK message creation stays behind the runtime wrapper",
        not issues,
        failures,
        issues[:10],
    )


# Agent sessions a customer is actively waiting on. These are deliberately
# uncapped: a budget-truncated answer mid-sentence is worse for the customer
# than the marginal spend, and they already run under a wall-clock timeout.
# Everything else must carry a hard cap. See .claude/rules/task-budgets.md.
_INTERACTIVE_SESSION_FILES = {
    "backend/services/support_agent.py",  # widget chat second tier, 8s timeout
}


def check_agent_sessions_are_budgeted(failures: list[str]) -> None:
    """Every non-interactive create_session() must pass budget_cents.

    An unattended agent session with no ceiling bills unbounded if it loops.
    Adding the parameter once is easy; remembering it at every future call
    site is not — so this pins it. A budget can only be attached at session
    creation, so a missed call site cannot be fixed after the fact.
    """
    issues: list[str] = []
    call_pattern = re.compile(r"\.create_session\s*\(")

    for path in iter_backend_py_files():
        rel_path = rel(path)
        if rel_path in _INTERACTIVE_SESSION_FILES:
            continue
        try:
            text = read_text(path)
        except OSError as exc:
            issues.append(f"{rel_path}: unreadable ({exc})")
            continue

        lines = text.splitlines()
        for lineno, line in enumerate(lines, start=1):
            if not call_pattern.search(line):
                continue
            # A thin delegate — `def create_session(self, **kwargs)` and its
            # `return self._inner.create_session(**kwargs)` body — forwards
            # whatever it is given. Transparent, so not a call site to police.
            stripped = line.lstrip()
            if stripped.startswith("def ") or "**kwargs" in line:
                continue
            # Look ahead to the end of the call for the budget kwarg.
            window = "\n".join(lines[lineno - 1 : lineno + 25])
            if "budget_cents" not in window:
                issues.append(f"{rel_path}:{lineno}: {line.strip()}")

    check(
        "non-interactive agent sessions carry a hard spend cap",
        not issues,
        failures,
        issues[:10],
    )


def check_demo_role_middleware(failures: list[str]) -> None:
    """GH #669: central demo-role mutation guard must stay wired.

    Asserts middleware module + allowlist exist, main.py registers
    DemoRoleBlockMiddleware, and money/destructive routers keep
    belt-and-suspenders ``block_demo_role`` Depends.
    """
    guard = ROOT / "backend" / "middleware" / "demo_role_guard.py"
    main_py = ROOT / "backend" / "main.py"
    if not guard.is_file():
        check("demo-role middleware module present", False, failures, [str(guard)])
        return
    guard_text = read_text(guard)
    check(
        "DemoRoleBlockMiddleware class defined",
        "class DemoRoleBlockMiddleware" in guard_text,
        failures,
        [rel(guard)],
    )
    check(
        "DEMO_MUTATION_ALLOWLIST_PREFIXES defined",
        "DEMO_MUTATION_ALLOWLIST_PREFIXES" in guard_text,
        failures,
        [rel(guard)],
    )
    missing_prefixes = [
        prefix
        for prefix in ("/api/v1/auth", "/api/v1/webhooks", "/api/v1/widget")
        if prefix not in guard_text
    ]
    check(
        "demo mutation allowlist covers auth/webhooks/widget",
        not missing_prefixes,
        failures,
        missing_prefixes,
    )

    main_text = read_text(main_py)
    check(
        "DemoRoleBlockMiddleware registered in main.py",
        "add_middleware(DemoRoleBlockMiddleware)" in main_text,
        failures,
        [rel(main_py)],
    )

    money_routers = (
        ROOT / "backend" / "routers" / "billing.py",
        ROOT / "backend" / "routers" / "auth_billing.py",
        ROOT / "backend" / "routers" / "phone.py",
        ROOT / "backend" / "routers" / "account_deletion.py",
    )
    missing_depends = [
        rel(path)
        for path in money_routers
        if "block_demo_role" not in read_text(path)
    ]
    check(
        "money routers keep block_demo_role Depends",
        not missing_depends,
        failures,
        missing_depends,
    )


def check_workflow_planner_import_boundary(failures: list[str]) -> None:
    """M9: planner/workflow modules must not import Action Executor/providers.

    Turns the M9.1 ``assert_planner_cannot_execute`` rule into a repository
    boundary. Workflow code may reference the typed contract only — never
    provider SDKs or the Action Executor implementation.
    """
    import re

    roots = (
        ROOT / "backend" / "services" / "os_workflows",
        ROOT / "agent-service" / "src" / "agent-os" / "workflows",
    )
    forbidden_patterns = (
        re.compile(r"backend\.services\.os_tool_executions"),
        re.compile(r"backend\.services\.os_tools"),
        re.compile(r"backend\.services\.google_calendar"),
        re.compile(r"backend\.services\.gmail"),
        re.compile(r"backend\.services\.hubspot"),
        re.compile(r"agent-os/actions/executor"),
        re.compile(r"actions/executor"),
        re.compile(r"actions/tools/"),
        re.compile(r"GmailMailboxPort"),
        re.compile(r"CalendarPort"),
    )
    offenders: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if path.name.endswith(".test.ts") or path.name.startswith("test_"):
                continue
            text = read_text(path)
            for pattern in forbidden_patterns:
                if pattern.search(text):
                    offenders.append(f"{rel(path)} matches {pattern.pattern}")
                    break
    check(
        "workflow/planner modules do not import Action Executor/providers",
        not offenders,
        failures,
        offenders[:20],
    )


def check_action_manifest_catalog_parity(failures: list[str]) -> None:
    """M9.3+: Action manifest must match tool sources; planner catalog must match manifest.

    Keeps the planner import-isolated (JSON only) while failing CI when
    ``tool_catalog`` risk/approval/department semantics drift from Action tools.
    """
    import json
    import subprocess
    import sys

    gen = ROOT / "scripts" / "generate_action_manifest.py"
    manifest = (
        ROOT / "agent-service" / "src" / "agent-os" / "actions" / "action_manifest.json"
    )
    if not gen.is_file():
        check(
            "action manifest generator present",
            False,
            failures,
            [f"missing {rel(gen)}"],
        )
        return

    proc = subprocess.run(
        [sys.executable, str(gen), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    check(
        "action_manifest.json matches Action tool sources",
        proc.returncode == 0,
        failures,
        [proc.stdout.strip() or proc.stderr.strip() or "manifest drift"],
    )

    if not manifest.is_file():
        check(
            "action_manifest.json committed",
            False,
            failures,
            [f"missing {rel(manifest)}"],
        )
        return

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        tool_ids = sorted((data.get("tools") or {}).keys())
    except (OSError, json.JSONDecodeError) as exc:
        check(
            "action_manifest.json parseable",
            False,
            failures,
            [str(exc)],
        )
        return

    # Import catalog only after confirming manifest exists (avoids noisy ImportError).
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from backend.services.os_workflows.tool_catalog import (
            PLANNER_EXCLUDED_TOOLS,
            TOOL_CATALOG,
            assert_catalog_matches_manifest,
        )

        assert_catalog_matches_manifest()
        catalog_ok = set(TOOL_CATALOG.keys()) | set(PLANNER_EXCLUDED_TOOLS) == set(
            tool_ids
        ) and not (set(TOOL_CATALOG.keys()) & set(PLANNER_EXCLUDED_TOOLS))
        check(
            "planner tool_catalog matches Action manifest",
            catalog_ok,
            failures,
            [
                f"catalog={sorted(TOOL_CATALOG.keys())}",
                f"manifest={tool_ids}",
            ]
            if not catalog_ok
            else [],
        )
    except Exception as exc:  # noqa: BLE001 — surface parity errors in CI
        check(
            "planner tool_catalog matches Action manifest",
            False,
            failures,
            [str(exc)],
        )


def main() -> int:
    failures: list[str] = []
    check_router_future_imports(failures)
    check_agent_sessions_are_budgeted(failures)
    check_live_schema_fields(failures)
    check_retired_plan_names(failures)
    check_widget_assets(failures)
    check_website_copy_avoids_em_dashes(failures)
    check_anthropic_sdk_usage(failures)
    check_demo_role_middleware(failures)
    check_workflow_planner_import_boundary(failures)
    check_action_manifest_catalog_parity(failures)

    if failures:
        print(f"{len(failures)} invariant(s) failed.")
        return 1

    print("All project invariants passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
