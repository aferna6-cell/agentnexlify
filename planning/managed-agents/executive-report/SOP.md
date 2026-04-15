# Executive Report Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 60-min discovery — map data sources, KPIs, audience
- [ ] Collect: API tokens (read-only), KPI list with definitions, brand assets, distribution list
- [ ] Contract + $1,500 deposit (50%)
- [ ] Create client dir: `planning/managed-agents/_clients/{{client_slug}}/`

## Day 1-4 — Build Pipeline
- [ ] Wire each MCP connection, verify read access
- [ ] Pull 90 days of history per metric
- [ ] Compute baseline (mean, stdev, percentiles) → store in `/baseline.json`
- [ ] Build report template per client brand
- [ ] Set up anomaly thresholds (default 2-stdev, tunable per metric)

## Day 5-7 — First Draft
- [ ] Generate report for last week
- [ ] Client review call — 45 min walkthrough
- [ ] Capture edits: tone, structure, chart choices, metric definitions

## Day 8-10 — Iteration
- [ ] Apply edits, regenerate
- [ ] 2nd review call — approve structure
- [ ] Tune anomaly thresholds based on client feedback

## Day 11-14 — Dry Run
- [ ] Generate 2 more reports (one for week prior, one for current)
- [ ] Verify email delivery + Slack post
- [ ] Verify PDF renders correctly in Outlook, Gmail, Apple Mail
- [ ] Client approves go-live

## Day 15 — Launch
- [ ] First real Monday report at 8 AM
- [ ] Collect remaining $1,500 payment
- [ ] Be on-call for Monday morning edits

## Week 2-4 — Stabilize
- [ ] Weekly: review delivery + engagement (open rate, Slack reactions)
- [ ] Weekly: tune anomaly flags based on false positives
- [ ] Month 1 end: 30-day review + performance snapshot

## Ongoing Retainer ($500/mo)
Covered:
- Weekly monitoring
- Monthly: 1 new metric added OR 1 new integration
- Quarterly: full re-baseline (seasonal adjustment)
- Unlimited: "why is this metric off" investigations
- Unlimited: edits to template, commentary style

NOT covered:
- New agent (separate product)
- Migration to new warehouse/tool stack
- Custom ad-hoc analyses >2 hrs each

## Monitoring Triggers
- Report fails to send by Monday 9 AM → P1, manual send + investigate
- Data source down >2 hrs on Sunday → pre-emptively notify client
- Anomaly rate >15% of metrics → review thresholds
- Open rate drops below 50% → content review

## Content Quality Rubric
Every report scored:
- Numbers sourced (yes/no)
- Commentary tied to numbers (yes/no)
- Anomalies actionable (yes/no)
- Length ≤800 words (yes/no)
- Charts necessary (not decorative)
Target: 4/5 minimum per report.

## Offboarding
- Export 24 months of reports as PDFs + raw data
- Hand over to client drive
- Deprovision agent
- Archive client dir
