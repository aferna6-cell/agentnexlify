#!/usr/bin/env bash
# Wire to: Railway scheduled task, external uptime tool, or scripts/daily cron
# Env required: SLACK_ALERT_WEBHOOK_URL (set in Railway dashboard)
set -euo pipefail

PROD_URL="https://agentnexlify-production.up.railway.app/api/v1/healthz"
TIMEOUT=10
WEBHOOK="${SLACK_ALERT_WEBHOOK_URL:-}"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$PROD_URL" 2>/dev/null) || response="TIMEOUT"
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$response" != "200" ]]; then
  msg="AgentNexLiFy /healthz FAIL: $response at $ts — check Railway dashboard"
  if [[ -n "$WEBHOOK" ]]; then
    curl -s -X POST "$WEBHOOK" \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"$msg\"}" > /dev/null
  fi
  echo "ALERT: $msg" >&2
  exit 1
fi

echo "OK: /healthz 200 at $ts"
