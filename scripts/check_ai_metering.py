#!/usr/bin/env python3
"""Detect backend functions that call AI without metering guards.

Violations are emitted as identifier-only lines in ``path:function:line`` format.
A clean scan exits 0, metering violations exit 2, and parse/read failures exit 1.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Iterable

AI_CALL_NAMES = {"call_claude_messages"}
ROUTER_GUARD = "ai_usage_guard"
SERVICE_GUARDS = {"ai_usage_guard"}
LIFECYCLE_RESERVE = {"reserve_ai_tokens"}
LIFECYCLE_RECORD = {"record_ai_usage"}
LIFECYCLE_RELEASE = {"release_ai_token_reservation"}
METERED_WRAPPERS: set[str] = set()
RAW_PROVIDER_RUNTIME = Path("backend/services/llm_runtime.py")
RAW_PROVIDER_FUNCTIONS = {"_call_single_model"}
EXCLUDED_PARTS = {"tests", "test", "docs", "knowledge-base", "_archive", "offline"}
EXEMPTION_MARKER = "# ai-metering-exempt:"
EXEMPTION_RE = re.compile(r"# ai-metering-exempt:\s*([^:\s][^:]*)\s*:\s*(\S.*)$")


class ScanError(RuntimeError):
    """Raised when a source file cannot be safely analyzed."""


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _is_messages_create(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "create"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "messages"
    )


def resolve_aliases(tree: ast.AST) -> dict[str, str]:
    """Map local imported names to canonical names used by the detector."""
    tracked = (
        AI_CALL_NAMES
        | {ROUTER_GUARD}
        | SERVICE_GUARDS
        | LIFECYCLE_RESERVE
        | LIFECYCLE_RECORD
        | LIFECYCLE_RELEASE
        | METERED_WRAPPERS
        | {"Depends"}
    )
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            if alias.name in tracked:
                aliases[alias.asname or alias.name] = alias.name
    return aliases


class _FunctionBodyCalls(ast.NodeVisitor):
    """Collect calls belonging to one function, without leaking nested-function calls."""

    def __init__(self, root: ast.FunctionDef | ast.AsyncFunctionDef, aliases: dict[str, str]) -> None:
        self.root = root
        self.aliases = aliases
        self.calls: set[str] = set()
        self.has_messages_create = False

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast.NodeVisitor API
        if _is_messages_create(node):
            self.has_messages_create = True
        name = _call_name(node)
        if name:
            self.calls.add(self.aliases.get(name, name))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if node is self.root:
            for statement in node.body:
                self.visit(statement)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        if node is self.root:
            for statement in node.body:
                self.visit(statement)

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return


def _function_calls(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, aliases: dict[str, str]
) -> tuple[set[str], bool]:
    visitor = _FunctionBodyCalls(fn, aliases)
    visitor.visit(fn)
    return visitor.calls, visitor.has_messages_create


def fn_has_ai_call(fn: ast.FunctionDef | ast.AsyncFunctionDef, aliases: dict[str, str]) -> bool:
    calls, has_messages_create = _function_calls(fn, aliases)
    return has_messages_create or bool(calls & AI_CALL_NAMES)


def _canonical_name(expr: ast.expr, aliases: dict[str, str]) -> str | None:
    if isinstance(expr, ast.Name):
        return aliases.get(expr.id, expr.id)
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return None


def _router_has_guard(fn: ast.FunctionDef | ast.AsyncFunctionDef, aliases: dict[str, str]) -> bool:
    defaults = list(fn.args.defaults) + [item for item in fn.args.kw_defaults if item is not None]
    for default in defaults:
        if not isinstance(default, ast.Call):
            continue
        if _canonical_name(default.func, aliases) != "Depends":
            continue
        for argument in default.args:
            if _canonical_name(argument, aliases) == ROUTER_GUARD:
                return True
    return False


def fn_has_guard(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    is_router: bool,
    aliases: dict[str, str],
) -> bool:
    if is_router and _router_has_guard(fn, aliases):
        return True

    calls, _ = _function_calls(fn, aliases)
    if calls & SERVICE_GUARDS:
        return True
    if calls & METERED_WRAPPERS:
        return True
    return bool(
        calls & LIFECYCLE_RESERVE
        and calls & LIFECYCLE_RECORD
        and calls & LIFECYCLE_RELEASE
    )


def fn_is_exempt(fn: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> bool:
    start = max(fn.lineno - 1, 0)
    end = min(start + 3, len(source_lines))
    for line in source_lines[start:end]:
        if EXEMPTION_MARKER not in line:
            continue
        match = EXEMPTION_RE.search(line)
        if match and match.group(1).strip() and match.group(2).strip():
            return True
    return False


def _iter_scannable_functions(tree: ast.Module) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield every named function/method independently, including nested call functions.

    Each yielded function is analyzed with ``_FunctionBodyCalls``, which deliberately
    does not traverse into nested function bodies. This keeps guards scoped to the
    function that actually owns the provider call while still detecting factory-style
    nested callables such as graph node closures.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _is_raw_provider_entrypoint(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    normalized = Path(path.as_posix())
    return normalized.as_posix().endswith(RAW_PROVIDER_RUNTIME.as_posix()) and node.name in RAW_PROVIDER_FUNCTIONS


def scan_file(path: Path, is_router: bool) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ScanError(f"unable to read {path}: {exc}") from exc

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise ScanError(f"unable to parse {path}:{exc.lineno}: {exc.msg}") from exc

    aliases = resolve_aliases(tree)
    source_lines = source.splitlines()
    violations: list[str] = []
    for node in _iter_scannable_functions(tree):
        if node.name in METERED_WRAPPERS:
            continue
        if _is_raw_provider_entrypoint(path, node):
            continue
        if fn_is_exempt(node, source_lines):
            continue
        if fn_has_ai_call(node, aliases) and not fn_has_guard(node, is_router, aliases):
            violations.append(f"{path.as_posix()}:{node.name}:{node.lineno}")
    return violations


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def collect_violations(root: Path = Path(".")) -> list[str]:
    """Scan all shipped backend Python, excluding explicit non-production paths."""
    violations: list[str] = []
    target = root / "backend"
    if not target.exists():
        return violations

    for path in sorted(target.rglob("*.py")):
        relative = path.relative_to(root)
        if _is_excluded(relative):
            continue
        is_router = len(relative.parts) > 1 and relative.parts[1] == "routers"
        violations.extend(scan_file(path, is_router))
    return violations


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    root = Path(args[0]) if args else Path(".")
    try:
        violations = collect_violations(root)
    except ScanError as exc:
        print(f"check_ai_metering: {exc}", file=sys.stderr)
        return 1

    for violation in violations:
        print(violation)
    return 2 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
