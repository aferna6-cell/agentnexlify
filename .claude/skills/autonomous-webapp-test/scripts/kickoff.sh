#!/usr/bin/env bash
#
# kickoff.sh — prereq check + kickoff prompt printer for autonomous-webapp-test.
#
# Checks that the frontend and backend dev servers are running locally,
# verifies Playwright MCP is configured, and prints the exact prompt to
# paste into Claude Code to start an autonomous crawl.
#
# Usage:
#   bash .claude/skills/autonomous-webapp-test/scripts/kickoff.sh
#   bash .claude/skills/autonomous-webapp-test/scripts/kickoff.sh --skip-check

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

SKIP_CHECK=0
for arg in "$@"; do
    [[ "$arg" == "--skip-check" ]] && SKIP_CHECK=1
done

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

pass() { printf "${GREEN}PASS${NC} %s\n" "$1"; }
fail() { printf "${RED}FAIL${NC} %s\n" "$1"; exit 1; }
warn() { printf "${YELLOW}WARN${NC} %s\n" "$1"; }

if [[ $SKIP_CHECK -eq 0 ]]; then
    printf "\n=== Prereq check ===\n"

    # Frontend dev server
    if curl -s -m 2 http://localhost:5173 >/dev/null 2>&1; then
        pass "Frontend dev server responding on :5173"
    else
        fail "Frontend dev server not running. Start with: cd frontend && npm run dev"
    fi

    # Backend dev server
    if curl -s -m 2 http://localhost:8000/health >/dev/null 2>&1; then
        pass "Backend dev server responding on :8000"
    else
        fail "Backend dev server not running. Start with: uvicorn backend.main:app --reload --port 8000"
    fi

    # Playwright MCP config
    if grep -q '"playwright"' .mcp.json 2>/dev/null; then
        pass "Playwright MCP configured in .mcp.json"
    else
        fail "Playwright MCP missing from .mcp.json"
    fi

    # Test fixtures exist
    if [[ -d backend/tests/fixtures ]] || grep -qr "test+autobot\|test_api_key" backend/tests/ 2>/dev/null; then
        pass "Test fixtures available"
    else
        warn "No test fixtures found — you'll need to pass real test creds in the prompt"
    fi

    printf "\n"
fi

cat <<'EOF'
=== KICKOFF PROMPT — paste into Claude Code ===

Run the autonomous-webapp-test skill against localhost.

Target: http://localhost:5173 (dashboard) + widget
Test email: test+autobot@agentnexlify.com
Test password: <fill from your fixtures>
Test tenant api_key: <fill from your fixtures>

Scope:
- All dashboard pages reachable from the sidebar
- Widget chat flow (open, greeting, factual question, contact capture, handoff)
- Any modals or forms exposed by the above
- Skip: landing page, /signup (we already know those work), any /admin routes

Known issues to ignore:
- (list any pre-filed bugs by URL or description)

Budget: 10 minutes wall time max. If past 12 min, stop and report what you found.

Expected output:
1. Structured Markdown bug report (CRITICAL / HIGH / MEDIUM / LOW)
2. Console error dump (grouped by source file)
3. Network failure dump (4xx/5xx with URL, status, body snippet)
4. Screenshots of any visual regression or error state
5. Coverage summary (pages visited, forms submitted, modals opened)

Constraints:
- Do NOT commit anything
- Do NOT touch prod URLs (agentnexlify-production.up.railway.app)
- Do NOT modify any tenant data beyond the test tenant
- If you hit a 500 on an API, log it and keep going — don't try to fix it mid-test

=== END KICKOFF PROMPT ===
EOF

printf "\n${GREEN}Ready.${NC} Copy the prompt above into Claude Code.\n"
