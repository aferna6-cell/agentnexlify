# Executive Report Agent — Sales Spec

## One-line Pitch
"Every Monday at 8 AM, a KPI digest lands in your inbox — synthesized from Stripe, Supabase, GA4, ad platforms, and Slack — with commentary, not just numbers."

## Problem Solved
SMB owners + operators spend 2-4 hrs/week pulling numbers from 6 tools, pasting into a sheet, writing a status update nobody reads. Either it gets skipped or it's stale by Tuesday.

## Target Customer
- SMB doing $50k-$5M ARR
- Uses 3+ tools for ops/finance/marketing data
- Has a team that needs visibility (not a solo shop)
- Current process: manual spreadsheet or skipped entirely

## Pricing
Flat: **$3,000 setup + $500/month retainer.**

Setup includes integration with up to 6 data sources. 7+ = +$500 per additional source.

## Deliverables
- Weekly Monday 8 AM email (branded, PDF attached)
- Monthly deep-dive (1st Monday of month — includes trend analysis)
- Slack/Teams digest thread (condensed)
- Dashboard link (static snapshot, hosted on our infra)
- "Ask the report" chat: client DMs a question → agent queries + answers
- Anomaly detection: flags metrics outside normal range

## Standard Metrics Pulled
- Revenue (Stripe, QB, direct)
- New customers + churn
- MRR / ARR movement
- Top products + top churn reasons
- Pipeline (HubSpot, Pipedrive)
- Ad spend + CAC + ROAS (Google Ads, Meta)
- Support metrics (Intercom, Zendesk, AgentNexLiFy widget)
- Website traffic + conversion (GA4)
- Team velocity (Linear, Jira, GitHub)

## Integrations Supported
Stripe · QuickBooks · Supabase · Postgres · BigQuery · GA4 · Google Ads · Meta Ads · HubSpot · Pipedrive · Intercom · Zendesk · Linear · Jira · GitHub · Slack · Notion

## Client Requirements
- Read-only API tokens for each tool
- List of 10-20 KPIs that matter
- Definition of "normal range" per KPI (or baseline period to auto-infer)
- Brand assets for report template
- Distribution list (emails + Slack channels)

## Setup Timeline
| Day | Milestone |
|-----|-----------|
| 0 | Kickoff + data access confirmed |
| 1-4 | Build data pipeline + integrations |
| 5-7 | Draft first report → client review |
| 8-10 | Iterate on commentary style + visual design |
| 11-14 | Send 2 practice reports → tune anomaly thresholds |
| 15 | Launch: first live Monday report |

## Success Metrics
- Open rate (target >80% internal)
- Time-to-read (target <10 min)
- Decisions influenced (quarterly survey)
- Hours saved per week (self-reported by client)

## Why Managed Agent
- Session memory = week-over-week context ("last week you asked about X, here's the update")
- Approval gate on external-facing reports
- Auto-retry when a data source is temporarily down
- No server for client to maintain
