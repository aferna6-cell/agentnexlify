#!/usr/bin/env bash
#
# healthz-alert.sh — probe prod /healthz and alert the owner on failure.
#
# Alert channel is EMAIL via Resend (scripts/monitoring/send-alert-email.sh),
# per the 2026-06-23 dependency-reduction decision that retired the Slack
# webhook path. SLACK_ALERT_WEBHOOK_URL is intentionally NOT used and NOT
# required (closes #391 without a new secret).
#
# Wire to: Railway scheduled task, GitHub Actions cron, or scripts/daily cron.
#
# Env required for email alerting (same pair the monitoring workflows use):
#   RESEND_API_KEY     Resend API key
#   OWNER_ALERT_EMAIL  Recipient address
# If either is missing the alert still prints to stderr and the script still
# exits 1, so a supervising workflow can raise its own durable alert
# (GitHub issue) — email is best-effort, the exit code is the contract.
set -uo pipefail

PROD_URL="${HEALTHZ_URL:-https://agentnexlify-production.up.railway.app/api/v1/healthz}"
TIMEOUT="${HEALTHZ_TIMEOUT:-10}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMAIL_SENDER="${SCRIPT_DIR}/../../scripts/monitoring/send-alert-email.sh"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$PROD_URL" 2>/dev/null) || response="TIMEOUT"
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$response" != "200" ]]; then
  msg="AgentNexLiFy /healthz FAIL: $response at $ts — check Railway dashboard"
  if [[ -f "$EMAIL_SENDER" ]]; then
    bash "$EMAIL_SENDER" "ALERT: AgentNexLiFy /healthz failing" "$msg" || true
  fi
  echo "ALERT: $msg" >&2
  exit 1
fi

echo "OK: /healthz 200 at $ts"
