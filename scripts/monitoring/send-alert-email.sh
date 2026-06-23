#!/usr/bin/env bash
#
# send-alert-email.sh
#
# Sends a monitoring alert email via the Resend HTTP API using curl. This
# replaces the retired Slack webhook alert path (railway-error-to-slack.sh).
# Resend is already a core dependency (RESEND_API_KEY), so no new vendor is
# introduced. This script does not import backend code, so it stays usable
# inside CI runners with only curl available.
#
# Usage:
#   send-alert-email.sh "<subject>" "<body text>"
#   echo "<body text>" | send-alert-email.sh "<subject>"
#
# Required environment:
#   RESEND_API_KEY     Resend API key (Bearer auth). Same key the backend uses.
#   OWNER_ALERT_EMAIL  Recipient address for monitoring alerts.
#
# Optional environment:
#   ALERT_FROM_ADDRESS From header (default: AgentNexLiFy Alerts <noreply@agentnexlify.com>)
#
# Behaviour:
#   Best-effort. Exit code is always 0 so a failed email send never hard-fails
#   the calling workflow. Failures print a ::warning:: line for the Actions log.
#   The GitHub-issue-on-failure path stays the durable alert of record.

set -u
set -o pipefail

SUBJECT="${1:-AgentNexLiFy monitoring alert}"

# Body from arg 2 if present, else from stdin.
if [ "$#" -ge 2 ]; then
    BODY="$2"
else
    BODY="$(cat || true)"
fi
[ -z "$BODY" ] && BODY="(no alert body provided)"

FROM_ADDRESS="${ALERT_FROM_ADDRESS:-AgentNexLiFy Alerts <noreply@agentnexlify.com>}"

if [ -z "${RESEND_API_KEY:-}" ] || [ -z "${OWNER_ALERT_EMAIL:-}" ]; then
    echo "::warning::send-alert-email: RESEND_API_KEY or OWNER_ALERT_EMAIL not set, skipping email alert"
    exit 0
fi

# Build JSON safely. Prefer python3 (always present on GitHub runners) so the
# subject and body are escaped correctly regardless of quotes or newlines.
PAYLOAD="$(
    SUBJECT="$SUBJECT" BODY="$BODY" FROM_ADDRESS="$FROM_ADDRESS" OWNER_ALERT_EMAIL="$OWNER_ALERT_EMAIL" \
    python3 -c '
import json, os
print(json.dumps({
    "from": os.environ["FROM_ADDRESS"],
    "to": [os.environ["OWNER_ALERT_EMAIL"]],
    "subject": os.environ["SUBJECT"],
    "text": os.environ["BODY"],
}))
' 2>/dev/null || true
)"

if [ -z "$PAYLOAD" ]; then
    echo "::warning::send-alert-email: failed to build JSON payload, skipping email alert"
    exit 0
fi

HTTP_STATUS="$(curl -sS -o /tmp/resend-alert-resp.txt -w '%{http_code}' \
    -X POST 'https://api.resend.com/emails' \
    -H "Authorization: Bearer ${RESEND_API_KEY}" \
    -H 'Content-Type: application/json' \
    --data "$PAYLOAD" 2>/dev/null || echo "000")"

if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
    echo "send-alert-email: alert emailed to OWNER_ALERT_EMAIL (HTTP $HTTP_STATUS)"
    exit 0
fi

echo "::warning::send-alert-email: Resend POST failed (HTTP $HTTP_STATUS), GitHub issue remains the alert of record"
cat /tmp/resend-alert-resp.txt 2>/dev/null || true
exit 0
