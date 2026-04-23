#!/usr/bin/env python3
"""Enforce changed-lines coverage for Python and JS/TS sources.

Python coverage uses XML reports (coverage.py / pytest-cov).
JS/TS coverage uses lcov reports.
"""

from __future__ import annotations

import argparse
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
# Paths deferred for coverage: Week 2 router PRs will add component tests
# alongside the backend endpoints that drive them.
JS_COVERAGE_DEFERRED = (
    "frontend/src/pages/onboarding-v2/",
    "frontend/src/components/onboarding-v2/",
)


def run(
    cmd: list[str],
    *,
    capture_output: bool = False,
    text: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=text,
        check=check,
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
    if any(marker in path for marker in JS_TEST_MARKERS):
        return False
    return not any(path.startswith(deferred) for deferred in JS_COVERAGE_DEFERRED)


def write_diff_file(compare_branch: str, files: list[str]) -> pathlib.Path:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".diff", delete=False
    ) as tmp:
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
