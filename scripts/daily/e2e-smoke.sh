#!/usr/bin/env bash
# Nightly E2E smoke test — hits widget endpoints for each live tenant.
# Exit code 0 = all pass, 1 = at least one failure.
#
# Usage: ./scripts/daily/e2e-smoke.sh
# Intended to run nightly via cron or Task Scheduler.

set -uo pipefail

BACKEND_URL="${BACKEND_URL:-https://agentnexlify-production.up.railway.app}"
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="$REPO_DIR/docs/daily-logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/e2e-smoke-$(date +%Y-%m-%d).md"

PASS=0
FAIL=0
RESULTS=""

# Tenant API keys to test (add more as tenants go live)
declare -A TENANTS=(
  ["MTOptions"]="anx_zc2Gfxz5n1oZgrYbM1biHWRI1oV1rMSIBFuIDtaCK3k"
  ["MTOptions-growth"]="anx_dtQSMJCrXH_7yyOrSqs7m9Ndgrm-VtFWmi9A0Y0mTiA"
)

check() {
  local name="$1" url="$2" expected_status="$3" body_check="${4:-}"
  local status body

  if [ -n "$body_check" ]; then
    body=$(curl -sf -w "\n%{http_code}" --max-time 15 "$url" 2>/dev/null) || body="000"
  else
    body=$(curl -sf -w "\n%{http_code}" --max-time 15 "$url" 2>/dev/null) || body="000"
  fi

  status=$(echo "$body" | tail -1)
  body_content=$(echo "$body" | sed '$d')

  if [ "$status" = "$expected_status" ]; then
    if [ -n "$body_check" ] && ! echo "$body_content" | grep -q "$body_check"; then
      FAIL=$((FAIL + 1))
      RESULTS+="- FAIL: $name (status=$status but missing '$body_check')\n"
      return 1
    fi
    PASS=$((PASS + 1))
    RESULTS+="- PASS: $name\n"
    return 0
  else
    FAIL=$((FAIL + 1))
    RESULTS+="- FAIL: $name (expected=$expected_status got=$status)\n"
    return 1
  fi
}

chat_test() {
  local tenant_name="$1" api_key="$2"
  local session_id="smoke_$(date +%s)_$$"
  local status body

  body=$(curl -sf -w "\n%{http_code}" --max-time 30 \
    -X POST "$BACKEND_URL/api/v1/widget/chat" \
    -H "Content-Type: application/json" \
    -d "{\"api_key\":\"$api_key\",\"session_id\":\"$session_id\",\"message\":\"hello\"}" \
    2>/dev/null) || body="000"

  status=$(echo "$body" | tail -1)
  body_content=$(echo "$body" | sed '$d')

  if [ "$status" = "200" ] && echo "$body_content" | grep -q '"response"'; then
    PASS=$((PASS + 1))
    RESULTS+="- PASS: $tenant_name chat response\n"
    return 0
  else
    FAIL=$((FAIL + 1))
    RESULTS+="- FAIL: $tenant_name chat (status=$status)\n"
    return 1
  fi
}

echo "Running E2E smoke tests against $BACKEND_URL ..."

# 1. Health check
check "Health endpoint" "$BACKEND_URL/health" "200" "supabase"

# 2. Per-tenant tests
for tenant_name in "${!TENANTS[@]}"; do
  api_key="${TENANTS[$tenant_name]}"

  # Config endpoint
  check "$tenant_name config" "$BACKEND_URL/api/v1/widget/config/$api_key" "200" "bot_name"

  # Chat endpoint (sends a test message)
  chat_test "$tenant_name" "$api_key"
done

# Write results
{
  echo "# E2E Smoke Test — $(date '+%Y-%m-%d %H:%M')"
  echo ""
  echo "Backend: $BACKEND_URL"
  echo "Passed: $PASS | Failed: $FAIL"
  echo ""
  echo "## Results"
  echo -e "$RESULTS"
} > "$LOG_FILE"

echo ""
echo "Results: $PASS passed, $FAIL failed"
echo "Log: $LOG_FILE"

if [ "$FAIL" -gt 0 ]; then
  echo "SMOKE TEST FAILURES DETECTED"
  cat "$LOG_FILE"
  exit 1
fi

echo "All smoke tests passed."
exit 0
