# Run 77 Winner: Wire Railway Healthz Monitoring Alert

**Date:** 2026-07-02-pm  
**Category:** operational  
**Effort:** S (30-min script + 2-min env var)  
**Autonomous:** HYBRID — script AUTONOMOUS-EXECUTABLE via nightly, env var HUMAN-REQUIRED  
**Moratorium override:** YES — CRITICAL operational gap, zero pending_approval queue impact  
**Confidence:** HIGH  
**Evidence source:** GH #388 CRITICAL (morning-digest-2026-07-02), SLACK_ALERT_WEBHOOK_URL absent

---

## Problem

Railway partial failure (#388):
- `/api/v1/healthz` timed out at 10:27 UTC 2026-07-02
- `/version` returned 200 at same time → partial failure (not crash)
- `SLACK_ALERT_WEBHOOK_URL` not set in Railway env → alert silently fails
- Result: engineer has no notification pathway for production outages

With 3+ days of zero production commits and no human actively watching, the next partial outage will again be invisible until a user complains.

---

## Implementation Sketch

### Step 1: Write `ops/monitoring/healthz-alert.sh` (AUTONOMOUS-EXECUTABLE)

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
  msg="🚨 AgentNexLiFy /healthz FAIL: $response at $ts — check Railway dashboard"
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

### Step 2: Write `ops/monitoring/SETUP.md` (AUTONOMOUS-EXECUTABLE)

Document:
1. **Slack webhook**: Workspace → Apps → Incoming Webhooks → Add to channel → copy URL → set as `SLACK_ALERT_WEBHOOK_URL` in Railway project Variables tab
2. **External uptime**: UptimeRobot free tier — add HTTP monitor for `https://agentnexlify-production.up.railway.app/api/v1/healthz`, 5-min interval, alert email + webhook
3. **Railway scheduled job option**: Add `ops/monitoring/healthz-alert.sh` as a Railway cron service (separate from main API)
4. **Manual test**: `SLACK_ALERT_WEBHOOK_URL=<url> bash ops/monitoring/healthz-alert.sh`

### Step 3: Human action (2 min, Railway dashboard)

1. Create Slack incoming webhook for `#alerts` channel
2. Set `SLACK_ALERT_WEBHOOK_URL` in Railway project Variables
3. Optionally: add UptimeRobot external monitor (5 min, free tier)

---

## Bonus actions (nightly, no mandate)

1. Merge Dependabot PRs #381-383 (patch bumps, `npm audit fix` safe)
2. Grep `/healthz` handler: `grep -n "healthz" backend/main.py backend/routers/*.py` → read handler → document root cause of timeout in `docs/dev-knowledge/bug-patterns.md`

---

## Run 78 mandate

If `ops/monitoring/healthz-alert.sh` NOT created by nightly review:
- Escalate to explicit nightly instruction (add to SKILL.md Step 9C)
- Note: SLACK_ALERT_WEBHOOK_URL env var still requires human regardless

If SLACK_ALERT_WEBHOOK_URL still not set by run 78:
- No further subconscious mandate — this is human-only env var configuration
- Document as known gap in `ops/monitoring/SETUP.md`

---

## Governance corrections applied this run

1. **Zapier (runs 75+76)**: status `pending_autonomous` → `implemented` (GH #107 closed 2026-06-13, fix at `backend/routers/zapier.py:121-128`)
2. **AI-to-Human Handoff**: added to `frozen_ideas` (7 consecutive debate kills, run 76 designated freeze)
3. **Run 77 mandate from run 76**: VOID — Zapier fix already shipped, do NOT escalate CRITICAL
4. **total_runs**: 76 → 77
5. **last_run**: "2026-07-01-pm" → "2026-07-02-pm"

---

## Verification (post-implementation)

```
Verified: ops/monitoring/healthz-alert.sh exists — PASS
Verified: ops/monitoring/SETUP.md documents SLACK_ALERT_WEBHOOK_URL setup — PASS
Verified: SLACK_ALERT_WEBHOOK_URL set in Railway env — PENDING (human step)
```
