"""Fail fast when Python tests reference repo-local modules that no longer exist.

This catches a specific regression class earlier than full pytest:
tests that still import or patch deleted modules after a dead-code sweep.
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DIRS = ("tests", "backend/tests")
LOCAL_PREFIXES = ("backend", "scripts")
PATCH_REFERENCE_RE = re.compile(r"\b(?:backend|scripts)(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")


def _iter_python_test_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for test_dir in TEST_DIRS:
        base = root / test_dir
        if base.exists():
            files.extend(sorted(base.rglob("test_*.py")))
            files.extend(
                sorted(
                    path
                    for path in base.rglob("*.py")
                    if path.name.endswith("_test.py")
                )
            )
    unique_files: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path not in seen:
            unique_files.append(path)
            seen.add(path)
    return unique_files


def _is_local_reference(dotted: str) -> bool:
    return (
        dotted == LOCAL_PREFIXES[0]
        or dotted == LOCAL_PREFIXES[1]
        or dotted.startswith(("backend.", "scripts."))
    )


def _module_file(root: Path, dotted: str) -> Path | None:
    path = root.joinpath(*dotted.split("."))
    py_file = path.with_suffix(".py")
    if py_file.is_file():
        return py_file
    package_init = path / "__init__.py"
    if package_init.is_file():
        return package_init
    if path.is_dir():
        return path
    return None


def _is_package_path(path: Path) -> bool:
    return path.is_dir() or path.name == "__init__.py"


def iter_assigned_names(node: ast.AST):
    """Yield names bound by an assignment node or assignment target."""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            yield from iter_assigned_names(target)
    elif isinstance(node, ast.Name):
        yield node.id
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            yield from iter_assigned_names(elt)
    elif isinstance(node, ast.Starred):
        yield from iter_assigned_names(node.value)


def _module_exports_name(module_path: Path, name: str) -> bool:
    if module_path.is_dir():
        return False

    try:
        tree = ast.parse(
            module_path.read_text(encoding="utf-8"), filename=str(module_path)
        )
    except SyntaxError:
        return False

    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == name
        ):
            return True
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                exported = alias.asname or alias.name
                if exported == name:
                    return True
        if isinstance(node, ast.Assign):
            if any(target == name for target in iter_assigned_names(node)):
                return True
        if isinstance(node, ast.AnnAssign):
            if name in iter_assigned_names(node.target):
                return True
    return False


def _longest_existing_module(
    root: Path, dotted: str
) -> tuple[str | None, Path | None, int]:
    parts = dotted.split(".")
    for end in range(len(parts), 0, -1):
        candidate = ".".join(parts[:end])
        resolved = _module_file(root, candidate)
        if resolved:
            return candidate, resolved, end
    return None, None, 0


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _collect_references(path: Path, root: Path) -> list[tuple[str, int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    refs: list[tuple[str, int, str]] = []

    class Visitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                if _is_local_reference(alias.name):
                    refs.append((alias.name, node.lineno, "import"))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if not node.module or not _is_local_reference(node.module):
                return

            refs.append((node.module, node.lineno, "from-import module"))

            # If this is importing from a package, also validate any obvious
            # submodule imports (`from backend.services import foo`).
            module_file = _module_file(root, node.module)
            if module_file and _is_package_path(module_file):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    submodule = f"{node.module}.{alias.name}"
                    if _module_file(root, submodule):
                        refs.append((submodule, node.lineno, "from-import submodule"))

        def visit_Call(self, node: ast.Call) -> None:
            call_name = _call_name(node.func) or ""
            if (
                "patch" in call_name
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                for match in PATCH_REFERENCE_RE.finditer(node.args[0].value):
                    refs.append(
                        (match.group(0), node.lineno, f"patch target via {call_name}")
                    )
            self.generic_visit(node)

    Visitor().visit(tree)
    return refs


def _validate_reference(root: Path, dotted: str, context: str) -> str | None:
    if "patch target" not in context and _module_file(root, dotted) is None:
        return f"missing local module `{dotted}`"

    module_name, module_path, prefix_len = _longest_existing_module(root, dotted)
    if not module_name or not module_path or prefix_len == 0:
        return f"missing local module `{dotted}`"

    if "patch target" not in context:
        return None

    parts = dotted.split(".")
    if _is_package_path(module_path) and prefix_len < len(parts):
        attribute_name = parts[prefix_len]
        if _module_exports_name(module_path, attribute_name):
            return None

        missing_submodule = ".".join(parts[: prefix_len + 1])
        if _module_file(root, missing_submodule) is None:
            return (
                f"patch target `{dotted}` resolves only to package `{module_name}`; "
                f"missing submodule `{missing_submodule}`"
            )
    return None


def find_invalid_references(root: Path) -> list[str]:
    issues: list[str] = []
    for path in _iter_python_test_files(root):
        for dotted, line_no, context in _collect_references(path, root):
            error = _validate_reference(root, dotted, context)
            if error:
                rel = path.relative_to(root)
                issues.append(f"{rel}:{line_no}: {error} ({context})")
    return sorted(set(issues))


def main() -> int:
    issues = find_invalid_references(REPO_ROOT)
    if issues:
        print("Stale local Python test references found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("PASS: local Python test references resolve cleanly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
