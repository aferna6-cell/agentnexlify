#!/usr/bin/env bash
#
# railway-error-to-slack.sh
#
# Polls Railway deploy logs for WARNING/ERROR levelname entries in the last
# lookback window and posts a compact summary to a Slack incoming webhook.
#
# Runs either locally (dev/ops) or in CI (see
# `.github/workflows/railway-error-watch.yml`). Idempotent — keeps a
# small seen-log state file to avoid re-posting the same lines.
#
# Required environment:
#   RAILWAY_TOKEN             — Railway project token (Railway CLI auth)
#   SLACK_ALERT_WEBHOOK_URL   — Slack incoming webhook URL
#
# Optional environment:
#   LOOKBACK_LINES            — how many recent log lines to scan (default 400)
#   DEDUP_STATE_FILE          — path to seen-hash file (default /tmp/railway-error-seen.txt)
#   ENVIRONMENT               — Railway environment name (default: linked env)
#   SERVICE                   — Railway service name (default: linked service)
#
# Exit codes:
#   0  — ran successfully, may or may not have posted
#   2  — missing required env vars
#   3  — railway CLI not on PATH
#   4  — webhook POST failed

set -u
set -o pipefail

LOOKBACK_LINES="${LOOKBACK_LINES:-400}"
DEDUP_STATE_FILE="${DEDUP_STATE_FILE:-/tmp/railway-error-seen.txt}"

if [ -z "${SLACK_ALERT_WEBHOOK_URL:-}" ]; then
    echo "railway-error-to-slack: SLACK_ALERT_WEBHOOK_URL not set" >&2
    exit 2
fi

if ! command -v railway >/dev/null 2>&1; then
    echo "railway-error-to-slack: railway CLI not installed" >&2
    exit 3
fi

touch "$DEDUP_STATE_FILE"

# Pull recent logs filtered to WARNING or ERROR levelname.
# `--json` would be cleaner but requires CLI v4.9+; fall back to grep pattern.
RAW_LOGS="$(railway logs \
    --lines "$LOOKBACK_LINES" \
    --filter 'levelname="ERROR" OR levelname="WARNING"' \
    2>/dev/null || true)"

if [ -z "$RAW_LOGS" ]; then
    echo "railway-error-to-slack: no new errors/warnings in window"
    exit 0
fi

# Build a de-duplicated list of error lines. We hash each line so the same
# error doesn't spam Slack on every run. Keep the last 2000 hashes only.
declare -a NEW_LINES=()
while IFS= read -r line; do
    [ -z "$line" ] && continue
    # Only keep lines that actually log a traceback or an error-level record.
    if echo "$line" | grep -qE 'levelname="(ERROR|WARNING)"|Traceback \(most recent call last\)'; then
        HASH="$(printf '%s' "$line" | sha1sum | awk '{print $1}')"
        if ! grep -q "^${HASH}$" "$DEDUP_STATE_FILE"; then
            NEW_LINES+=("$line")
            echo "$HASH" >> "$DEDUP_STATE_FILE"
        fi
    fi
done <<< "$RAW_LOGS"

# Trim dedup state to last 2000 entries.
if [ "$(wc -l < "$DEDUP_STATE_FILE")" -gt 2000 ]; then
    tail -n 2000 "$DEDUP_STATE_FILE" > "${DEDUP_STATE_FILE}.tmp"
    mv "${DEDUP_STATE_FILE}.tmp" "$DEDUP_STATE_FILE"
fi

if [ "${#NEW_LINES[@]}" -eq 0 ]; then
    echo "railway-error-to-slack: all warnings/errors already seen"
    exit 0
fi

# Cap the payload — Slack blocks long messages.
MAX_LINES=12
if [ "${#NEW_LINES[@]}" -gt "$MAX_LINES" ]; then
    TRUNCATED="$(( ${#NEW_LINES[@]} - MAX_LINES ))"
    NEW_LINES=("${NEW_LINES[@]:0:$MAX_LINES}")
else
    TRUNCATED=0
fi

# Build Slack payload. Use mrkdwn code block for readability.
BODY="$(printf '*Railway warnings/errors — %d new line(s)*\n```\n' "${#NEW_LINES[@]}")"
for line in "${NEW_LINES[@]}"; do
    # Truncate each line to 500 chars to keep the payload reasonable.
    short="$(printf '%s' "$line" | cut -c1-500)"
    BODY+="${short}\n"
done
BODY+="\`\`\`"
if [ "$TRUNCATED" -gt 0 ]; then
    BODY+="\n_+${TRUNCATED} more line(s) suppressed — run \`railway logs --filter '@level:error'\` for full list._"
fi

# Escape for JSON.
JSON_TEXT="$(printf '%s' "$BODY" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"
PAYLOAD="{\"text\": ${JSON_TEXT}}"

HTTP_STATUS="$(curl -sS -o /tmp/slack-resp.txt -w '%{http_code}' \
    -X POST -H 'Content-Type: application/json' \
    --data "$PAYLOAD" \
    "$SLACK_ALERT_WEBHOOK_URL")"

if [ "$HTTP_STATUS" -ne 200 ]; then
    echo "railway-error-to-slack: Slack POST failed (HTTP $HTTP_STATUS):" >&2
    cat /tmp/slack-resp.txt >&2 || true
    exit 4
fi

echo "railway-error-to-slack: posted ${#NEW_LINES[@]} line(s) to Slack"
