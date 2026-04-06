#!/usr/bin/env python3
"""Fail on low-value Python test anti-patterns.

Rules:
1) no-mock-echo-implementation
2) no-interaction-only-tests
3) no-trivial-test-assertions
"""

from __future__ import annotations

import ast
import pathlib
import sys
from dataclasses import dataclass


INTERACTION_ASSERT_PREFIXES = (
    "assert_called",
    "assert_not_called",
    "assert_called_once",
    "assert_called_once_with",
    "assert_called_with",
    "assert_has_calls",
    "assert_any_call",
    "assert_awaited",
    "assert_not_awaited",
    "assert_awaited_once",
    "assert_awaited_once_with",
    "assert_awaited_with",
    "assert_has_awaits",
)

TRIVIAL_ASSERT_METHODS = {
    "assertEqual",
    "assertNotEqual",
    "assertIs",
    "assertIsNot",
    "assertTrue",
    "assertFalse",
}


@dataclass
class Finding:
    path: pathlib.Path
    line: int
    col: int
    rule: str
    message: str

    def render(self) -> str:
        return (
            f"{self.path.as_posix()}:{self.line}:{self.col}: "
            f"{self.rule} {self.message}"
        )


def is_test_file(path: pathlib.Path) -> bool:
    if path.suffix != ".py":
        return False
    normalized = path.as_posix()
    return (
        path.name.startswith("test_")
        or "/tests/" in normalized
        or normalized.startswith("tests/")
    )


def same_ast(left: ast.AST, right: ast.AST) -> bool:
    return ast.dump(left, include_attributes=False) == ast.dump(
        right, include_attributes=False
    )


def is_echo_expression(expr: ast.AST, params: set[str]) -> bool:
    if isinstance(expr, ast.Name):
        return expr.id in params
    if isinstance(expr, ast.Subscript):
        return (
            isinstance(expr.value, ast.Name)
            and expr.value.id in params
            and isinstance(expr.slice, ast.Constant)
            and expr.slice.value == 0
        )
    if isinstance(expr, ast.Await):
        return is_echo_expression(expr.value, params)
    return False


def is_echo_callable(node: ast.AST) -> bool:
    if isinstance(node, ast.Lambda):
        params = {arg.arg for arg in node.args.args}
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if not params:
            return False
        return is_echo_expression(node.body, params)
    return False


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def is_pytest_raises(call: ast.Call) -> bool:
    if isinstance(call.func, ast.Attribute):
        return isinstance(call.func.value, ast.Name) and call.func.value.id == "pytest" and call.func.attr == "raises"
    return False


def is_trivial_assert_stmt(node: ast.Assert) -> bool:
    test = node.test
    if isinstance(test, ast.Constant) and test.value is True:
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
        return same_ast(test.left, test.comparators[0])
    return False


def is_trivial_assert_call(node: ast.Call) -> bool:
    name = call_name(node)
    if name not in TRIVIAL_ASSERT_METHODS:
        return False
    if len(node.args) < 1:
        return False
    if name in {"assertTrue", "assertFalse"}:
        if isinstance(node.args[0], ast.Constant):
            return (name == "assertTrue" and node.args[0].value is True) or (
                name == "assertFalse" and node.args[0].value is False
            )
        return False
    if len(node.args) < 2:
        return False
    return same_ast(node.args[0], node.args[1])


class FunctionAssertionAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.total_assertions = 0
        self.outcome_assertions = 0
        self.interaction_assertions = 0
        self.trivial_asserts: list[tuple[int, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Skip nested functions for interaction-only classification.
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Assert(self, node: ast.Assert) -> None:
        self.total_assertions += 1
        if is_trivial_assert_stmt(node):
            self.trivial_asserts.append((node.lineno, node.col_offset + 1))
        else:
            self.outcome_assertions += 1

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node)
        if name.startswith("assert"):
            self.total_assertions += 1
            if is_trivial_assert_call(node):
                self.trivial_asserts.append((node.lineno, node.col_offset + 1))
            elif name.startswith(INTERACTION_ASSERT_PREFIXES):
                self.interaction_assertions += 1
            else:
                self.outcome_assertions += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and is_pytest_raises(ctx):
                self.total_assertions += 1
                self.outcome_assertions += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.visit_With(node)  # same semantics


class TestQualityVisitor(ast.NodeVisitor):
    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def add(self, node: ast.AST, rule: str, message: str) -> None:
        self.findings.append(
            Finding(
                path=self.path,
                line=getattr(node, "lineno", 1),
                col=getattr(node, "col_offset", 0) + 1,
                rule=rule,
                message=message,
            )
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "side_effect":
                if is_echo_callable(node.value):
                    self.add(
                        node.value,
                        "no-mock-echo-implementation",
                        "mock side_effect echoes test input; model real behavior instead",
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = call_name(node)
        if name in {"Mock", "MagicMock", "AsyncMock"}:
            for keyword in node.keywords:
                if keyword.arg == "side_effect" and keyword.value and is_echo_callable(keyword.value):
                    self.add(
                        keyword.value,
                        "no-mock-echo-implementation",
                        "mock side_effect echoes test input; model real behavior instead",
                    )
        self.generic_visit(node)

    def _analyze_test_function(self, node: ast.AST, name: str) -> None:
        if not name.startswith("test_"):
            return
        analyzer = FunctionAssertionAnalyzer()
        for stmt in getattr(node, "body", []):
            analyzer.visit(stmt)

        for line, col in analyzer.trivial_asserts:
            self.findings.append(
                Finding(
                    path=self.path,
                    line=line,
                    col=col,
                    rule="no-trivial-test-assertions",
                    message="tautological assertion does not validate behavior",
                )
            )

        if analyzer.total_assertions > 0 and analyzer.outcome_assertions == 0 and analyzer.interaction_assertions > 0:
            self.add(
                node,
                "no-interaction-only-tests",
                "test only checks mock/spies interactions; assert observable behavior",
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_test_function(node, node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_test_function(node, node.name)
        self.generic_visit(node)


def files_to_scan(argv: list[str]) -> list[pathlib.Path]:
    if argv:
        candidates = [pathlib.Path(arg) for arg in argv]
    else:
        candidates = list(pathlib.Path("tests").rglob("*.py"))
    return [p for p in candidates if p.exists() and is_test_file(p)]


def main(argv: list[str]) -> int:
    files = files_to_scan(argv)
    findings: list[Finding] = []

    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path.as_posix())
        except SyntaxError as exc:
            findings.append(
                Finding(
                    path=path,
                    line=exc.lineno or 1,
                    col=exc.offset or 1,
                    rule="parse-error",
                    message=f"unable to parse test file: {exc.msg}",
                )
            )
            continue

        visitor = TestQualityVisitor(path)
        visitor.visit(tree)
        findings.extend(visitor.findings)

    if findings:
        for finding in findings:
            print(finding.render())
        print(f"\n{len(findings)} Python test-quality violation(s) found.")
        return 1

    if files:
        print(f"Python test-quality lint passed ({len(files)} file(s) checked).")
    else:
        print("No Python test files found for linting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
