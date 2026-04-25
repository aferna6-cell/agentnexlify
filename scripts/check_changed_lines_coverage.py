#!/usr/bin/env python3
"""Enforce changed-lines coverage for Python and JS/TS sources.

Python coverage uses XML reports (coverage.py / pytest-cov).
JS/TS coverage uses lcov reports.

For Python files, the base version from compare_branch is normalized through
Black (if available) before diffing, so formatter-only changes are excluded
from the coverage requirement.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

PYTHON_SOURCE_PREFIXES = ("backend/",)
JS_SOURCE_PREFIXES = (
    "frontend/src/",
    "demo-platform/src/",
    "widget/",
    "chrome-extension/",
)
JS_SOURCE_EXTENSIONS = (".js", ".jsx", ".ts", ".tsx")
JS_TEST_MARKERS = (".test.", ".spec.", "__tests__/")


def run(
    cmd: list[str],
    *,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
    input: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=text,
        check=check,
        input=input,
    )


def changed_files(compare_branch: str) -> list[str]:
    result = run(
        ["git", "diff", "--name-only", f"{compare_branch}...HEAD"],
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"Unable to compute changed files against {compare_branch}: {stderr}"
        )
    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def is_python_source(path: str) -> bool:
    if not path.endswith(".py"):
        return False
    if not path.startswith(PYTHON_SOURCE_PREFIXES):
        return False
    return "/tests/" not in path


def is_js_source(path: str) -> bool:
    if not path.endswith(JS_SOURCE_EXTENSIONS):
        return False
    if not path.startswith(JS_SOURCE_PREFIXES):
        return False
    return not any(marker in path for marker in JS_TEST_MARKERS)


def _black_available() -> bool:
    result = run(["black", "--version"], capture_output=True)
    return result.returncode == 0


def _format_with_black(content: str) -> str:
    """Format Python source through black stdin mode; return original on failure."""
    result = run(
        ["black", "--quiet", "-"],
        capture_output=True,
        input=content,
    )
    return result.stdout if result.returncode == 0 else content


def _build_normalized_py_diff(compare_branch: str, file_path: str, tmpdir: str) -> str:
    """
    Generate a unified diff for a Python file with the base normalized through Black.
    This excludes formatter-only changes from coverage requirements.
    """
    # Get base content from compare_branch
    base_result = run(
        ["git", "show", f"{compare_branch}:{file_path}"],
        capture_output=True,
    )
    if base_result.returncode != 0:
        # New file — fall back to standard git diff (full file is "new")
        diff_result = run(
            [
                "git",
                "diff",
                "--unified=0",
                "--no-color",
                f"{compare_branch}...HEAD",
                "--",
                file_path,
            ],
            capture_output=True,
        )
        return diff_result.stdout

    # Format base with black to match the project's formatter output
    formatted_base = _format_with_black(base_result.stdout)

    base_tmp = os.path.join(tmpdir, "base_" + os.path.basename(file_path))
    with open(base_tmp, "w", encoding="utf-8") as f:
        f.write(formatted_base)

    # Get HEAD version
    head_result = run(
        ["git", "show", f"HEAD:{file_path}"],
        capture_output=True,
    )
    if head_result.returncode != 0:
        return ""

    head_tmp = os.path.join(tmpdir, "head_" + os.path.basename(file_path))
    with open(head_tmp, "w", encoding="utf-8") as f:
        f.write(head_result.stdout)

    # Generate diff with file labels matching what diff-cover expects.
    # Prepend the "diff --git" header diff-cover requires to identify the file.
    diff_result = run(
        [
            "diff",
            "--unified=0",
            f"--label=a/{file_path}",
            f"--label=b/{file_path}",
            base_tmp,
            head_tmp,
        ],
        capture_output=True,
    )
    # diff returns 1 when files differ (normal), 2 on error
    if diff_result.returncode == 2:
        return ""
    if not diff_result.stdout:
        return ""
    git_header = f"diff --git a/{file_path} b/{file_path}\n"
    return git_header + diff_result.stdout


def write_diff_file(compare_branch: str, files: list[str]) -> pathlib.Path:
    py_files = [f for f in files if f.endswith(".py")]
    other_files = [f for f in files if not f.endswith(".py")]

    use_normalized = py_files and _black_available()

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".diff", delete=False
    ) as tmp:
        if use_normalized:
            with tempfile.TemporaryDirectory() as tmpdir:
                parts: list[str] = []
                for file_path in py_files:
                    chunk = _build_normalized_py_diff(compare_branch, file_path, tmpdir)
                    if chunk:
                        parts.append(chunk)
                if other_files:
                    diff_result = run(
                        [
                            "git",
                            "diff",
                            "--unified=0",
                            "--no-color",
                            f"{compare_branch}...HEAD",
                            "--",
                            *other_files,
                        ],
                        capture_output=True,
                    )
                    if diff_result.stdout:
                        parts.append(diff_result.stdout)
                tmp.write("\n".join(parts))
        else:
            # Fallback: standard git diff (no black normalization)
            diff_result = run(
                [
                    "git",
                    "diff",
                    "--unified=0",
                    "--no-color",
                    f"{compare_branch}...HEAD",
                    "--",
                    *files,
                ],
                capture_output=True,
            )
            if diff_result.returncode != 0:
                stderr = (diff_result.stderr or "").strip()
                raise RuntimeError(f"Unable to generate git diff file: {stderr}")
            tmp.write(diff_result.stdout)

        return pathlib.Path(tmp.name)


def run_diff_cover(
    *,
    coverage_reports: list[str],
    diff_file: pathlib.Path,
    fail_under: int,
) -> int:
    cmd = [
        sys.executable,
        "-m",
        "diff_cover.diff_cover_tool",
        *coverage_reports,
        "--diff-file",
        str(diff_file),
        "--fail-under",
        str(fail_under),
        "--quiet",
    ]
    result = run(cmd)
    return result.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail if changed Python/JS lines are not covered by tests."
    )
    parser.add_argument(
        "--compare-branch",
        default="origin/main",
        help="Git branch to compare against (default: origin/main).",
    )
    parser.add_argument(
        "--python-report",
        default="coverage-python.xml",
        help="Python XML coverage report path.",
    )
    parser.add_argument(
        "--python-fail-under",
        type=int,
        default=85,
        help="Minimum changed-lines coverage for Python sources.",
    )
    parser.add_argument(
        "--js-report",
        action="append",
        default=[],
        help="JS/TS lcov report path. Can be provided multiple times.",
    )
    parser.add_argument(
        "--js-fail-under",
        type=int,
        default=80,
        help="Minimum changed-lines coverage for JS/TS sources.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    changed = changed_files(args.compare_branch)

    py_changed = [path for path in changed if is_python_source(path)]
    js_changed = [path for path in changed if is_js_source(path)]

    failures = 0

    if py_changed:
        python_report = pathlib.Path(args.python_report)
        if not python_report.exists():
            print(
                f"Python changed-lines coverage failed: missing report {python_report.as_posix()}."
            )
            failures += 1
        else:
            py_diff = write_diff_file(args.compare_branch, py_changed)
            try:
                exit_code = run_diff_cover(
                    coverage_reports=[python_report.as_posix()],
                    diff_file=py_diff,
                    fail_under=args.python_fail_under,
                )
                if exit_code != 0:
                    print(
                        "Python changed-lines coverage failed. "
                        f"Required >= {args.python_fail_under}%."
                    )
                    failures += 1
                else:
                    print(
                        "Python changed-lines coverage passed "
                        f"(>= {args.python_fail_under}%)."
                    )
            finally:
                py_diff.unlink(missing_ok=True)
    else:
        print(
            "No changed Python source files under backend/; skipping Python diff coverage."
        )

    if js_changed:
        js_reports = [
            pathlib.Path(path).as_posix()
            for path in args.js_report
            if pathlib.Path(path).exists()
        ]
        if not js_reports:
            print(
                "JS/TS changed-lines coverage failed: JS/TS source files changed but no lcov report "
                "was found. Provide --js-report paths and generate lcov coverage in CI."
            )
            failures += 1
        else:
            js_diff = write_diff_file(args.compare_branch, js_changed)
            try:
                exit_code = run_diff_cover(
                    coverage_reports=js_reports,
                    diff_file=js_diff,
                    fail_under=args.js_fail_under,
                )
                if exit_code != 0:
                    print(
                        "JS/TS changed-lines coverage failed. "
                        f"Required >= {args.js_fail_under}%."
                    )
                    failures += 1
                else:
                    print(
                        "JS/TS changed-lines coverage passed "
                        f"(>= {args.js_fail_under}%)."
                    )
            finally:
                js_diff.unlink(missing_ok=True)
    else:
        print(
            "No changed JS/TS source files under frontend/widget/chrome-extension/demo-platform; "
            "skipping JS/TS diff coverage."
        )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
