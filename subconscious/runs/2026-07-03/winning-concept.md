# Run 78 Winner: Add Step 9B to Nightly SKILL.md — Healthz Monitor Maintenance

**Date:** 2026-07-03  
**Category:** operational  
**Effort:** XS (SKILL.md edit ~10 min + script content already drafted in run 77)  
**Autonomous:** AUTONOMOUS-EXECUTABLE — SKILL.md edit is LOW-risk doc change within nightly's authority  
**Moratorium override:** YES — CRITICAL operational gap, run 78 mandate fires (second consecutive miss)  
**Confidence:** HIGH  
**Evidence source:** Run 78 mandate (ops/monitoring/healthz-alert.sh missing), GH #388 CRITICAL, 3+ days no production commits, healthz timeout 10:27 UTC 2026-07-02

---

## Problem

Run 78 mandate fires. `ops/monitoring/healthz-alert.sh` has NOT been created by nightly-commit-review since run 77 recommended it on 2026-07-02-pm. The monitoring gap persists:
- `/api/v1/healthz` timed out 10:27 UTC 2026-07-02 — partial failure, not crash
- `SLACK_ALERT_WEBHOOK_URL` not set in Railway → alerts fire silently to nowhere
- No external uptime monitor configured
- Second consecutive automated run has detected the gap but not resolved it

Root cause of run 77 miss: nightly SKILL.md Scheduled Task Prompt steps 1-9 have no explicit instruction to check for/create ops monitoring scripts. The run 77 AUTONOMOUS-EXECUTABLE flag was in winning-concept.md but nightly's LOW-risk auto-fix categories don't include "ops script creation." The explicit instruction was missing from nightly's Scheduled Task Prompt.

---

## Recommendation

Add Step 9B to nightly-commit-review SKILL.md Scheduled Task Prompt. Step 9B instructs nightly to check for `ops/monitoring/healthz-alert.sh` and write it from the embedded content below if missing.

---

## Implementation Sketch

### Step 1: Edit `.claude/skills/nightly-commit-review/SKILL.md` (AUTONOMOUS-EXECUTABLE)

In the "## Scheduled Task Prompt" section, insert after step 9A (Moratorium Escalation) and before step 10 (Push):

```
9B. (Healthz Monitor Maintenance) Check if `ops/monitoring/healthz-alert.sh` exists:
    ```bash
    ls ops/monitoring/healthz-alert.sh 2>/dev/null || echo "MISSING"
    ```
    If MISSING: write the file from the embedded content in the latest
    `subconscious/runs/*/winning-concept.md` that contains "## Script Content".
    Commit: `ops(monitoring): add healthz-alert.sh [auto-nightly-YYYY-MM-DD]`
    Also check if `ops/monitoring/SETUP.md` exists; write it if missing.
    After both files created: open GH issue "Set SLACK_ALERT_WEBHOOK_URL in Railway"
    with label `human-action-required` and body from ## Human Step below.
    If ALREADY EXISTS: log "healthz-alert.sh present — monitoring active" and skip.
```

---

## Script Content

Nightly should write this verbatim to `ops/monitoring/healthz-alert.sh`:

```bash
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
```

---

## SETUP.md Content

Nightly should write this verbatim to `ops/monitoring/SETUP.md`:

```markdown
# AgentNexLiFy Monitoring Setup

## healthz-alert.sh — Health Check Alert

Script: `ops/monitoring/healthz-alert.sh`
Checks `/api/v1/healthz` endpoint every invocation. Non-200 → Slack alert + exit 1.

### Required: Set SLACK_ALERT_WEBHOOK_URL (human action, 2 min)

1. Open Slack workspace → Apps → Incoming Webhooks
2. Add to channel → select `#alerts` (or create it)
3. Copy the webhook URL
4. Open Railway dashboard → your project → Variables tab
5. Add variable: `SLACK_ALERT_WEBHOOK_URL` = `https://hooks.slack.com/services/...`

Without this variable set, the script runs silently (no Slack alert). exit 1 still fires on non-200.

### Optional: UptimeRobot External Monitor (free)

1. Create account at uptimerobot.com
2. Add HTTP monitor: `https://agentnexlify-production.up.railway.app/api/v1/healthz`
3. Interval: 5 minutes
4. Alert: email + webhook (paste SLACK_ALERT_WEBHOOK_URL here too)

### Optional: Railway Scheduled Job

Add `ops/monitoring/healthz-alert.sh` as a Railway cron service (separate from main API):
- Schedule: `*/5 * * * *` (every 5 min)
- Command: `bash ops/monitoring/healthz-alert.sh`
- Environment: add SLACK_ALERT_WEBHOOK_URL

### Manual Test

```bash
SLACK_ALERT_WEBHOOK_URL=<url> bash ops/monitoring/healthz-alert.sh
```
```

---

## Human Step (still required)

After script is written, human must:
1. Create Slack incoming webhook for `#alerts` channel (2 min)
2. Set `SLACK_ALERT_WEBHOOK_URL` in Railway project Variables tab (1 min)
3. Optional: add UptimeRobot external monitor (5 min, free tier)

Without this env var, the script writes to stderr but no Slack notification fires.

---

## Run 79 Mandate

If `ops/monitoring/healthz-alert.sh` still NOT present after next nightly run:
- Escalate to P0 GH issue with `critical` + `blocker` labels
- Tag human in issue
- No further automated mandate — human must act

If SLACK_ALERT_WEBHOOK_URL still not set by run 79:
- Document as known gap in `ops/monitoring/SETUP.md` (if SETUP.md exists)
- No further automated mandate — human-only configuration

---

## Governance Corrections Applied This Run

1. **total_runs**: 77 → 78
2. **last_run**: "2026-07-02-pm" → "2026-07-03"
3. **B-003**: status remains `pending_autonomous` (script still missing, Step 9B now recommended)
4. **B-002**: status remains `pending_autonomous` (SMS Dashboard, issue-to-pr-loop active)

---

## Verification (post-implementation)

```
Verified: ops/monitoring/healthz-alert.sh exists — PENDING (nightly Step 9B)
Verified: ops/monitoring/SETUP.md documents setup — PENDING (nightly Step 9B)
Verified: Step 9B added to nightly SKILL.md — PENDING (AUTONOMOUS-EXECUTABLE this run → next nightly)
Verified: SLACK_ALERT_WEBHOOK_URL set in Railway env — PENDING (human step)
```
