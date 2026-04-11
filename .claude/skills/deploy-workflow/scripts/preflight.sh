#!/usr/bin/env bash
#
# preflight.sh — pre-deploy gate runner for agentnexlify.
#
# Runs 7 gates in sequence. Exits 0 if all pass, 1 on first failure.
# Intended to be invoked by Claude via the deploy-workflow skill OR
# by a human via `bash .claude/skills/deploy-workflow/scripts/preflight.sh`.
#
# Fast-fail by design — if Gate 2 breaks, we don't waste 30s running Gate 3.
#
# Usage:
#   bash .claude/skills/deploy-workflow/scripts/preflight.sh
#   bash .claude/skills/deploy-workflow/scripts/preflight.sh --skip-build
#   bash .claude/skills/deploy-workflow/scripts/preflight.sh --skip-tests

set -u

# --- Config -----------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

SKIP_BUILD=0
SKIP_TESTS=0
for arg in "$@"; do
    case "$arg" in
        --skip-build) SKIP_BUILD=1 ;;
        --skip-tests) SKIP_TESTS=1 ;;
        --help|-h)
            grep '^#' "$0" | head -20
            exit 0
            ;;
    esac
done

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

pass() { printf "${GREEN}PASS${NC} %s\n" "$1"; }
fail() { printf "${RED}FAIL${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}WARN${NC} %s\n" "$1"; }
gate() { printf "\n=== Gate %s: %s ===\n" "$1" "$2"; }

# --- Gate 1: Clean working tree --------------------------------------------

gate 1 "Clean working tree"
UNCOMMITTED=$(git status --porcelain 2>/dev/null | grep -v "^??" | grep -v "\.env\.example" || true)
if [[ -n "$UNCOMMITTED" ]]; then
    printf "Uncommitted changes:\n%s\n" "$UNCOMMITTED"
    fail "Stage and commit or stash before deploying."
fi
pass "Working tree clean (ignoring .env.example + untracked)."

# --- Gate 2: Frontend build -------------------------------------------------

gate 2 "Frontend build"
if [[ $SKIP_BUILD -eq 1 ]]; then
    warn "Skipped (--skip-build)"
else
    if [[ ! -d frontend ]]; then
        fail "frontend/ directory not found. Wrong repo?"
    fi
    ( cd frontend && npm run build >/tmp/agentnexlify-build.log 2>&1 )
    if [[ $? -ne 0 ]]; then
        tail -20 /tmp/agentnexlify-build.log
        fail "Frontend build failed. See /tmp/agentnexlify-build.log"
    fi
    BUILD_LINE=$(grep -E "built in" /tmp/agentnexlify-build.log | tail -1)
    pass "Frontend build OK ($BUILD_LINE)"
fi

# --- Gate 3: Backend tests --------------------------------------------------

gate 3 "Backend tests"
if [[ $SKIP_TESTS -eq 1 ]]; then
    warn "Skipped (--skip-tests)"
else
    python3 -m pytest backend/tests/ -q >/tmp/agentnexlify-tests.log 2>&1
    if [[ $? -ne 0 ]]; then
        tail -40 /tmp/agentnexlify-tests.log
        fail "Backend tests failed. See /tmp/agentnexlify-tests.log"
    fi
    SUMMARY=$(grep -E "passed|failed" /tmp/agentnexlify-tests.log | tail -1)
    pass "Backend tests OK ($SUMMARY)"
fi

# --- Gate 4: Widget file sync -----------------------------------------------

gate 4 "Widget file sync"
WIDGET_A="widget/agentnexlify-widget.js"
WIDGET_B="frontend/public/widget/agentnexlify-widget.js"
if [[ ! -f "$WIDGET_A" || ! -f "$WIDGET_B" ]]; then
    warn "One or both widget files missing ($WIDGET_A, $WIDGET_B)."
else
    if ! diff -q "$WIDGET_A" "$WIDGET_B" >/dev/null 2>&1; then
        diff -u "$WIDGET_A" "$WIDGET_B" | head -20
        fail "Widget files drifted. Sync before deploying."
    fi
    pass "Widget files byte-identical."
fi

# --- Gate 5: Migration status -----------------------------------------------

gate 5 "Migration status"
LATEST_MIGRATION=$(ls -1 migrations/ 2>/dev/null | grep -E "^[0-9]+" | sort -V | tail -1)
if [[ -z "$LATEST_MIGRATION" ]]; then
    warn "No migrations found."
else
    printf "Latest migration: %s\n" "$LATEST_MIGRATION"
    warn "Verify this is applied in prod via Supabase MCP before deploying."
fi

# --- Gate 6: Secret scan on staged diff -------------------------------------

gate 6 "Secret scan"
SECRETS=$(git diff --cached 2>/dev/null | grep -E "sk-ant-[a-zA-Z0-9]{10,}|sk-live-[a-zA-Z0-9]{10,}|rk_live_|SUPABASE_SERVICE_KEY\s*=\s*[a-zA-Z0-9]" || true)
if [[ -n "$SECRETS" ]]; then
    printf "%s\n" "$SECRETS"
    fail "Secret(s) detected in staged diff. Unstage before deploying."
fi
pass "No secrets detected in staged diff."

# --- Gate 7: Local health (optional) ----------------------------------------

gate 7 "Local health endpoint"
HEALTH=$(curl -s -m 2 http://localhost:8000/health 2>/dev/null || true)
if [[ -z "$HEALTH" ]]; then
    warn "Local backend not running — skipped."
else
    printf "Response: %s\n" "$HEALTH"
    pass "Local backend healthy."
fi

# --- Summary ----------------------------------------------------------------

printf "\n"
printf "${GREEN}=== ALL GATES PASSED ===${NC}\n"
printf "Ready for: git push origin main\n"
printf "Then verify: https://agentnexlify-production.up.railway.app/health\n"
exit 0
