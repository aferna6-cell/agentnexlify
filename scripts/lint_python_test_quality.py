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

INTERACTION_ATTRS = {
    "called",
    "call_count",
    "call_args",
    "call_args_list",
    "mock_calls",
    "await_count",
    "await_args",
    "await_args_list",
    "awaited",
}

MOCK_FACTORIES = {"Mock", "MagicMock", "AsyncMock", "create_autospec"}
PATCH_CONTEXT_CALLS = {
    "patch",
    "patch.object",
    "mock.patch",
    "mock.patch.object",
    "unittest.mock.patch",
    "unittest.mock.patch.object",
    "mocker.patch",
    "mocker.patch.object",
}

EXPRESSION_HELPER_NAMES = {
    "len",
    "all",
    "any",
    "sum",
    "sorted",
    "set",
    "list",
    "tuple",
    "dict",
    "str",
    "int",
    "float",
    "bool",
    "min",
    "max",
    "round",
    "isinstance",
}

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


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    return ""


def expression_root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return expression_root_name(node.value)
    if isinstance(node, ast.Subscript):
        return expression_root_name(node.value)
    if isinstance(node, ast.Call):
        return expression_root_name(node.func)
    if isinstance(node, ast.Await):
        return expression_root_name(node.value)
    return None


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
    if not isinstance(node, ast.Lambda):
        return False
    params = {arg.arg for arg in node.args.args}
    if node.args.vararg:
        params.add(node.args.vararg.arg)
    if not params:
        return False
    return is_echo_expression(node.body, params)


def is_mock_factory_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    name = qualified_name(node.func)
    short = name.rsplit(".", 1)[-1]
    if short in MOCK_FACTORIES:
        return True
    return short.endswith("Mock") and short != "Mocker"


def is_patch_context_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return qualified_name(node.func) in PATCH_CONTEXT_CALLS


def is_monkeypatch_setattr_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "setattr"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "monkeypatch"
    )


def is_pytest_raises(call: ast.Call) -> bool:
    return qualified_name(call.func) == "pytest.raises"


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


def iter_assigned_names(target: ast.AST) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in target.elts:
            names.extend(iter_assigned_names(elt))
        return names
    return []


def collect_mock_symbols(node: ast.AST) -> set[str]:
    symbols: set[str] = set()

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            if arg.arg.startswith("mock_") or arg.arg.endswith("_mock"):
                symbols.add(arg.arg)
        if node.args.vararg and node.args.vararg.arg.endswith("_mock"):
            symbols.add(node.args.vararg.arg)
        if node.args.kwarg and node.args.kwarg.arg.endswith("_mock"):
            symbols.add(node.args.kwarg.arg)

    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and is_mock_factory_call(child.value):
            for target in child.targets:
                symbols.update(iter_assigned_names(target))
        elif isinstance(child, ast.AnnAssign) and child.value and is_mock_factory_call(child.value):
            symbols.update(iter_assigned_names(child.target))
        elif isinstance(child, (ast.With, ast.AsyncWith)):
            for item in child.items:
                if item.optional_vars and is_patch_context_call(item.context_expr):
                    symbols.update(iter_assigned_names(item.optional_vars))

    return symbols


def is_literal_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(is_literal_expression(elt) for elt in node.elts)
    if isinstance(node, ast.Dict):
        keys_ok = all(key is None or is_literal_expression(key) for key in node.keys)
        values_ok = all(is_literal_expression(value) for value in node.values)
        return keys_ok and values_ok
    return False


class InteractionExpressionVisitor(ast.NodeVisitor):
    def __init__(self, mock_symbols: set[str]) -> None:
        self.mock_symbols = mock_symbols
        self.saw_mock_reference = False
        self.saw_interaction_attr = False
        self.saw_non_mock_name = False

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if node.id in self.mock_symbols:
                self.saw_mock_reference = True
            elif node.id in EXPRESSION_HELPER_NAMES:
                return
            else:
                self.saw_non_mock_name = True

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in INTERACTION_ATTRS:
            self.saw_interaction_attr = True
        root = expression_root_name(node)
        if root and root in self.mock_symbols:
            self.saw_mock_reference = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        root = expression_root_name(node.func)
        if root and root in self.mock_symbols:
            self.saw_mock_reference = True
        self.generic_visit(node)


def is_interaction_expression(expr: ast.AST, mock_symbols: set[str]) -> bool:
    inspector = InteractionExpressionVisitor(mock_symbols)
    inspector.visit(expr)
    if inspector.saw_non_mock_name:
        return False
    return inspector.saw_mock_reference or inspector.saw_interaction_attr


def is_assertion_call_interaction_only(call: ast.Call, mock_symbols: set[str]) -> bool:
    exprs = list(call.args)
    exprs.extend(keyword.value for keyword in call.keywords if keyword.value is not None)
    if not exprs:
        return False

    saw_interaction = False
    for expr in exprs:
        if is_interaction_expression(expr, mock_symbols):
            saw_interaction = True
            continue
        if is_literal_expression(expr):
            continue
        return False
    return saw_interaction


class FunctionAssertionAnalyzer(ast.NodeVisitor):
    def __init__(self, mock_symbols: set[str]) -> None:
        self.mock_symbols = mock_symbols
        self.total_assertions = 0
        self.outcome_assertions = 0
        self.interaction_assertions = 0
        self.trivial_asserts: list[tuple[int, int]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Skip nested function defs for interaction-only classification.
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Assert(self, node: ast.Assert) -> None:
        self.total_assertions += 1
        if is_trivial_assert_stmt(node):
            self.trivial_asserts.append((node.lineno, node.col_offset + 1))
            return
        if is_interaction_expression(node.test, self.mock_symbols):
            self.interaction_assertions += 1
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
            elif is_assertion_call_interaction_only(node, self.mock_symbols):
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
        self.visit_With(node)


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
                if (
                    keyword.arg in {"side_effect", "new"}
                    and keyword.value
                    and is_echo_callable(keyword.value)
                ):
                    self.add(
                        keyword.value,
                        "no-mock-echo-implementation",
                        "mock side_effect/new echoes test input; model real behavior instead",
                    )

        if is_monkeypatch_setattr_call(node):
            patch_value: ast.AST | None = None
            if len(node.args) >= 3:
                patch_value = node.args[2]
            else:
                for keyword in node.keywords:
                    if keyword.arg == "value":
                        patch_value = keyword.value
                        break
            if patch_value and is_echo_callable(patch_value):
                self.add(
                    patch_value,
                    "no-mock-echo-implementation",
                    "monkeypatch setattr uses echo lambda; model real behavior instead",
                )

        self.generic_visit(node)

    def _analyze_test_function(self, node: ast.AST, name: str) -> None:
        if not name.startswith("test_"):
            return

        mock_symbols = collect_mock_symbols(node)
        analyzer = FunctionAssertionAnalyzer(mock_symbols)
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

        if (
            analyzer.total_assertions > 0
            and analyzer.outcome_assertions == 0
            and analyzer.interaction_assertions > 0
        ):
            self.add(
                node,
                "no-interaction-only-tests",
                "test only checks mocks/interactions; assert observable behavior or state",
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
