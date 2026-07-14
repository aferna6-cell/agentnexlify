#!/usr/bin/env bash
# Shared static health snapshot for daily routines and manual checks.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

# Use grep as fallback when rg is not installed
search_cmd() {
    if command -v rg >/dev/null 2>&1; then
        rg "$@"
    else
        # Translate common rg flags to grep equivalents
        grep -rn "$@" 2>/dev/null
    fi
}

count_matches() {
    local pattern="$1"
    shift
    local matches
    if command -v rg >/dev/null 2>&1; then
        matches="$(rg -n "$pattern" "$@" || true)"
    else
        # Convert rg glob to grep include; simplified for common cases
        matches="$(grep -rn "$pattern" backend/ frontend/src/ --include='*.py' --include='*.js' --include='*.jsx' 2>/dev/null || true)"
    fi
    if [ -z "$matches" ]; then
        printf '0\n'
    else
        printf '%s\n' "$matches" | wc -l | tr -d ' '
    fi
}

echo "AgentNexLiFy Health Check"
echo "date=$(date '+%Y-%m-%d %H:%M:%S %Z')"

if command -v rg >/dev/null 2>&1; then
    dangerous_imports="$(rg -n '^[[:space:]]*from __future__ import annotations[[:space:]]*$' backend/routers --glob '*.py' || true)"
else
    dangerous_imports="$(grep -rn 'from __future__ import annotations' backend/routers/ --include='*.py' 2>/dev/null | grep -v '# NOTE' || true)"
fi
if [ -n "$dangerous_imports" ]; then
    echo "dangerous_router_imports=FOUND"
    printf '%s\n' "$dangerous_imports"
else
    echo "dangerous_router_imports=CLEAR"
fi

bare_except_count="$(count_matches '^[[:space:]]*except:[[:space:]]*$' backend)"
echo "bare_except_count=$bare_except_count"

silent_catch_count="$(count_matches '\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)' frontend/src)"
echo "silent_frontend_catch_count=$silent_catch_count"

if cmp -s widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js; then
    echo "widget_sync=OK"
else
    echo "widget_sync=DIFF"
fi

if grep -q '^\.env$' .gitignore 2>/dev/null; then
    echo "gitignore_env=YES"
else
    echo "gitignore_env=NO"
fi

# Prod error sink (error_events table, migration 156) - deterministic 24h
# report. Best-effort: prints error_events=UNAVAILABLE when creds/deps are
# missing on this machine, never fails the health check.
python scripts/daily/error_events_report.py 2>/dev/null \
    || python3 scripts/daily/error_events_report.py 2>/dev/null \
    || echo "error_events=UNAVAILABLE (python missing)"
