#!/usr/bin/env bash
#
# ci-local.sh — run PR Validation's real gates locally, zero GitHub Actions minutes.
#
# Why this exists: when the GitHub Actions minute quota is exhausted, every CI
# job fails at runner allocation (~2s, HTTP 404 logs) and PRs can't gate. This
# script mirrors the high-signal gates from .github/workflows/pr-check.yml so a
# change can be verified locally and fast-forward merged to main safely.
#
# It is NOT a full replica. It skips network-bound / low-signal steps:
#   - Semgrep appsec scan (needs network + registry)
#   - npm audit (needs network)
#   - pip-audit (needs network, continue-on-error in CI anyway)
#   - Vercel preview (cloud)
# Those are advisory; the gates below are the ones that catch merge-breaking bugs.
#
# Usage:
#   bash scripts/ci-local.sh            # full local gate (invariants + tests + build)
#   bash scripts/ci-local.sh --fast     # skip the frontend build (slowest step)
#   bash scripts/ci-local.sh --no-tests # skip backend pytest (copy/docs-only changes)
#
# Exit code 0 = all run gates passed. Non-zero = at least one gate failed.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

WORKFLOW=".github/workflows/pr-check.yml"
PYTHON_BIN="${AGENTNEXLIFY_PYTHON:-python3}"

RUN_BUILD=1
RUN_TESTS=1
for arg in "$@"; do
  case "$arg" in
    --fast)     RUN_BUILD=0 ;;
    --no-tests) RUN_TESTS=0 ;;
    -h|--help)  grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg (try --help)"; exit 2 ;;
  esac
done

FAILURES=()
run_gate() {
  # run_gate "<label>" <command...>
  local label="$1"; shift
  echo ""
  echo "=== $label ==="
  if "$@"; then
    echo "PASS: $label"
  else
    echo "FAIL: $label"
    FAILURES+=("$label")
  fi
}

# --- Gate 1: project invariants (em-dash ban, schema discipline, __future__, secrets) ---
run_gate "project invariants" "$PYTHON_BIN" scripts/check_project_invariants.py

# --- Gate 2: agent system guardrail (CLAUDE.md / agents / pin / issue-to-PR intact) ---
run_gate "agent system guardrail" "$PYTHON_BIN" scripts/check_agent_system.py

# --- Gate 3: python test-quality linter ---
run_gate "python test quality" "$PYTHON_BIN" scripts/lint_python_test_quality.py

# --- Gate 4: local python test references ---
run_gate "local test refs" "$PYTHON_BIN" scripts/check_test_local_refs.py

# --- Gate 5: widget byte-identical sync ---
run_gate "widget sync" "$PYTHON_BIN" scripts/sync_widget_assets.py --check

# --- Gate 6: backend pytest — allowlist pulled live from the workflow (no drift) ---
if [ "$RUN_TESTS" -eq 1 ]; then
  # Extract the exact `python -m pytest ...` invocation from pr-check.yml so the
  # local run can never diverge from CI's allowlist. We strip the leading
  # `python -m pytest` and the trailing coverage flags (no coverage gate locally).
  PYTEST_LINE="$(grep -E '^\s*python -m pytest tests ' "$WORKFLOW" | head -1)"
  if [ -z "$PYTEST_LINE" ]; then
    echo "FAIL: could not find pytest allowlist in $WORKFLOW"
    FAILURES+=("pytest allowlist lookup")
  else
    # Drop everything from the coverage flag onward; drop the command prefix.
    TARGETS="$(echo "$PYTEST_LINE" \
      | sed -E 's/.*python -m pytest //' \
      | sed -E 's/ -q --cov.*$//' \
      | sed -E 's/ --cov.*$//')"
    # shellcheck disable=SC2086
    run_gate "backend pytest (workflow allowlist)" \
      "$PYTHON_BIN" -m pytest $TARGETS -q
  fi
else
  echo ""
  echo "=== backend pytest: SKIPPED (--no-tests) ==="
fi

# --- Gate 7: frontend build ---
if [ "$RUN_BUILD" -eq 1 ]; then
  run_gate "frontend build" bash -c "cd frontend && npm run build"
else
  echo ""
  echo "=== frontend build: SKIPPED (--fast) ==="
fi

echo ""
echo "========================================"
if [ "${#FAILURES[@]}" -eq 0 ]; then
  echo "ALL GATES PASSED — safe to fast-forward merge to main."
  exit 0
fi
echo "GATES FAILED (${#FAILURES[@]}):"
for f in "${FAILURES[@]}"; do echo "  - $f"; done
echo "Fix before merging to main."
exit 1
