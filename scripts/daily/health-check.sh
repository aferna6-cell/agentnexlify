#!/usr/bin/env bash
# Shared static health snapshot for daily routines and manual checks.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_DIR"

count_matches() {
    local pattern="$1"
    shift
    local matches
    matches="$(rg -n "$pattern" "$@" || true)"
    if [ -z "$matches" ]; then
        printf '0\n'
    else
        printf '%s\n' "$matches" | wc -l | tr -d ' '
    fi
}

echo "AgentNexLiFy Health Check"
echo "date=$(date '+%Y-%m-%d %H:%M:%S %Z')"

dangerous_imports="$(rg -n '^[[:space:]]*from __future__ import annotations[[:space:]]*$' backend/routers --glob '*.py' || true)"
if [ -n "$dangerous_imports" ]; then
    echo "dangerous_router_imports=FOUND"
    printf '%s\n' "$dangerous_imports"
else
    echo "dangerous_router_imports=CLEAR"
fi

bare_except_count="$(count_matches '^[[:space:]]*except:[[:space:]]*$' backend --glob '*.py')"
echo "bare_except_count=$bare_except_count"

silent_catch_count="$(count_matches '\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)|\.catch\(\s*\(\)\s*=>\s*null\s*\)|\.catch\(\s*\(\)\s*=>\s*undefined\s*\)' frontend/src backend --glob '*.{js,jsx,ts,tsx,py}')"
echo "silent_frontend_catch_count=$silent_catch_count"
if [ "$silent_catch_count" -gt 0 ]; then
    rg -n '\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)|\.catch\(\s*\(\)\s*=>\s*null\s*\)|\.catch\(\s*\(\)\s*=>\s*undefined\s*\)' frontend/src backend --glob '*.{js,jsx,ts,tsx,py}' || true
fi

if cmp -s widget/agentnexlify-widget.js frontend/public/widget/agentnexlify-widget.js; then
    echo "widget_sync=OK"
else
    echo "widget_sync=DIFF"
fi

if rg -n '^\.env$' .gitignore >/dev/null 2>&1; then
    echo "gitignore_env=YES"
else
    echo "gitignore_env=NO"
fi
