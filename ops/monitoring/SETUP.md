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
