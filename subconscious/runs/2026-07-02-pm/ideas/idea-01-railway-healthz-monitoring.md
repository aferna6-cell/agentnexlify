# Idea 01: Wire Railway Healthz Monitoring Alert

**Category:** operational  
**Effort:** S (~30-min script + docs)  
**Moratorium impact:** OVERRIDE — CRITICAL operational gap, silent downtime  
**Autonomous:** HYBRID — script AUTONOMOUS-EXECUTABLE, env var setup HUMAN (2 min in Railway dashboard)

## Evidence

- GH #388 CRITICAL (morning-digest-2026-07-02): `agentnexlify-production.up.railway.app/api/v1/healthz` timed out at 10:27 UTC
- `/version` returned 200 at same time → partial failure (handler hung, not full crash)
- `SLACK_ALERT_WEBHOOK_URL` not set in Railway env → alert system silently fails
- Zero notification on downtime → user-facing outages invisible to engineer
- 3+ days zero production commits → no human watching for drift

## Problem

Partial /healthz failures (hung background tasks, DB connection saturation) are undetectable:
1. Railway deploy succeeds (app boots)
2. /healthz handler hangs (background task or slow DB query)
3. SLACK_ALERT_WEBHOOK_URL not set → no alert fires
4. Engineer learns about outage from a customer complaint, not a dashboard

## Recommendation

**Step 1 (AUTONOMOUS-EXECUTABLE):** Write `ops/monitoring/healthz-alert.sh`
```bash
#!/usr/bin/env bash
# Probe /healthz with a tight timeout, fire Slack alert on failure
URL="https://agentnexlify-production.up.railway.app/api/v1/healthz"
TIMEOUT=10
WEBHOOK="${SLACK_ALERT_WEBHOOK_URL:-}"

response=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$URL" 2>/dev/null) || response="TIMEOUT"

if [[ "$response" != "200" ]]; then
  if [[ -n "$WEBHOOK" ]]; then
    curl -s -X POST "$WEBHOOK" \
      -H 'Content-type: application/json' \
      --data "{\"text\":\"🚨 /healthz FAIL: $response ($(date -u +%Y-%m-%dT%H:%M:%SZ))\"}"
  fi
  echo "ALERT: /healthz returned $response" >&2
  exit 1
fi
echo "OK: /healthz 200"
```

**Step 2 (AUTONOMOUS-EXECUTABLE):** Write `ops/monitoring/SETUP.md` documenting:
- Set `SLACK_ALERT_WEBHOOK_URL` in Railway project env
- Wire `ops/monitoring/healthz-alert.sh` to Railway's health-check config or external uptime tool (BetterUptime, UptimeRobot free tier)
- Cron option: `scripts/daily/` 5-min probe

**Step 3 (HUMAN-REQUIRED, 2 min):** Set `SLACK_ALERT_WEBHOOK_URL` in Railway dashboard

## Why now

Novel finding — never debated in any prior run. GH #388 is 1 day old. With no production commits in 3+ days, next outage will again be silent. Every day without this costs a silent window of undetected downtime.

## Score

| Dimension | Rating |
|-----------|--------|
| Evidence quality | HIGH — GH #388 confirmed, morning digest CRITICAL alert |
| Impact | HIGH — eliminates silent downtime blindspot |
| Effort | S (~30 min script + 2 min env var) |
| Novelty | HIGH — never debated, unique to this run |
| Moratorium | OVERRIDE (CRITICAL operational gap) |
| Autonomous | HYBRID (script autonomous, env var human) |

**Total: STRONG WIN candidate**
