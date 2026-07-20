#!/usr/bin/env bash
# ci_local.sh — run the full pr-check.yml gate suite locally, zero Actions minutes.
#
# Born from GH #500 (Actions spending limit exhausted): any environment with the
# repo's dev deps can produce the exact same verification GitHub-hosted runners
# would. Run before merging any PR and paste the summary as merge evidence.
#
#   bash scripts/ci_local.sh                  # compare against origin/main
#   bash scripts/ci_local.sh origin/develop   # custom compare ref
#
# Gate parity with .github/workflows/pr-check.yml. Network-dependent audits
# (semgrep, pip-audit, npm audit) are OPTIONAL: they warn when the tool or
# network is unavailable instead of failing the run.

set -u
COMPARE_BRANCH="${1:-origin/main}"
COMPARE_REF="$(git merge-base "$COMPARE_BRANCH" HEAD 2>/dev/null || echo "$COMPARE_BRANCH")"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# npm guarantees Node is present for this gate. Route every Python command
# through the same cross-platform interpreter selector used by package.json,
# so macOS, Windows, worktrees, and AGENTNEXLIFY_PYTHON behave identically.
python() { node scripts/run_python.cjs "$@"; }

PASS=()
FAIL=()
SKIP=()

run_gate() { # name, required(1/0), command...
  local name="$1" required="$2"
  shift 2
  echo ""
  echo "=== GATE: $name ==="
  if "$@"; then
    PASS+=("$name")
  else
    if [ "$required" = "1" ]; then
      FAIL+=("$name")
    else
      SKIP+=("$name (optional — tool/network unavailable or advisory failure)")
    fi
  fi
}

dangerous_patterns() {
  local errors=0
  if grep -rnE "^[[:space:]]*from __future__ import annotations" backend/routers/ 2>/dev/null; then
    echo "ERROR: from __future__ import annotations in router files"
    errors=$((errors + 1))
  fi
  if grep -rn "sk_live_\|sk_test_\|sk-ant-" backend/ frontend/src/ \
      --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" 2>/dev/null; then
    echo "ERROR: possible hardcoded secrets"
    errors=$((errors + 1))
  fi
  if git diff --name-only "$COMPARE_REF" HEAD 2>/dev/null | grep -q "\.env"; then
    echo "ERROR: .env file in diff"
    errors=$((errors + 1))
  fi
  [ "$errors" -eq 0 ]
}

migration_numbering() {
  local changed
  changed=$(git diff --name-only "$COMPARE_REF" HEAD -- migrations/ 2>/dev/null | grep -E '^migrations/[0-9]+' || true)
  [ -z "$changed" ] && { echo "No migration changes."; return 0; }
  local ok=0
  for f in $changed; do
    num=$(basename "$f" | grep -oE '^[0-9]+')
    count=$(ls migrations/ | grep -cE "^${num}_") || true
    if [ "$count" -gt 1 ]; then
      echo "ERROR: migration number $num collides ($count files)"
      ok=1
    fi
  done
  return $ok
}

js_coverage() {
  # Only needed when JS/TS sources changed — the coverage gate skips otherwise.
  if git diff --name-only "$COMPARE_REF" HEAD | grep -qE '^(frontend/src/|demo-platform/src/|widget/|chrome-extension/).*\.(js|jsx|ts|tsx)$'; then
    (cd frontend && npm run test:coverage)
  else
    echo "No JS/TS source changes — lcov not required."
  fi
}

run_gate "diff hygiene (git diff --check)" 1 git diff --check "$COMPARE_REF" HEAD
run_gate "dangerous patterns" 1 dangerous_patterns
run_gate "agent system guardrails" 1 python scripts/check_agent_system.py
run_gate "project invariants" 1 python scripts/check_project_invariants.py
run_gate "instruction budget" 1 python scripts/check_instruction_budget.py
run_gate "root quick check" 1 npm run check:quick --silent
run_gate "JS/TS test quality lint" 1 npm run lint:test-quality --silent
run_gate "Python test quality lint" 1 python scripts/lint_python_test_quality.py
run_gate "local Python test refs" 1 python scripts/check_test_local_refs.py
run_gate "managed agents preflight" 1 python scripts/managed_agents/preflight.py
run_gate "backend tests + coverage" 1 python -m pytest backend/tests/ -q --cov=backend --cov-report=xml:coverage-python.xml
run_gate "key vault 100% coverage" 1 python -m pytest backend/tests/test_integration_key_vault.py -q \
  --cov=backend.services.integration_key_vault --cov-branch --cov-fail-under=100
run_gate "JS coverage (when JS changed)" 1 js_coverage
run_gate "changed-lines coverage >=85% py / >=80% js" 1 python scripts/check_changed_lines_coverage.py \
  --compare-branch "$COMPARE_REF" \
  --python-report coverage-python.xml --python-fail-under 85 \
  --js-report frontend/coverage/lcov.info --js-fail-under 80
run_gate "migration numbering" 1 migration_numbering
if git diff --name-only "$COMPARE_REF" HEAD | grep -q '^frontend/'; then
  run_gate "frontend tests" 1 sh -c "cd frontend && npm run test -- --run"
  run_gate "frontend build" 1 sh -c "cd frontend && npm run build"
else
  SKIP+=("frontend tests/build (no frontend/ changes)")
fi
run_gate "AgentShield config scan" 1 npm run agent-config:scan --silent
run_gate "semgrep appsec scan (optional)" 0 sh -c "command -v semgrep >/dev/null && semgrep scan --config auto --error -q"
run_gate "pip-audit backend deps (optional)" 0 sh -c "command -v pip-audit >/dev/null && pip-audit -r backend/requirements.txt --progress-spinner off"
run_gate "npm audit frontend (optional)" 0 sh -c "cd frontend && npm audit --audit-level=high"

echo ""
echo "==================== CI LOCAL SUMMARY ===================="
echo "Compare ref: $COMPARE_REF ($(git rev-parse --short HEAD) vs $COMPARE_BRANCH)"
for g in "${PASS[@]}";  do echo "  PASS  $g"; done
for g in "${SKIP[@]+"${SKIP[@]}"}"; do echo "  SKIP  $g"; done
for g in "${FAIL[@]+"${FAIL[@]}"}"; do echo "  FAIL  $g"; done
echo "=========================================================="
if [ "${#FAIL[@]}" -gt 0 ]; then
  echo "RESULT: FAIL (${#FAIL[@]} required gate(s) failed)"
  exit 1
fi
echo "RESULT: PASS (${#PASS[@]} required gates green)"
