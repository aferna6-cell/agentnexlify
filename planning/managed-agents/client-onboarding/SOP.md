# Client Onboarding Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 60-min discovery call with client ops lead
- [ ] Collect: brand assets, voice samples, sample onboarding emails, required docs list, integration credentials (via 1Password share or secure portal)
- [ ] Confirm pricing tier + sign contract + collect 50% deposit
- [ ] Create client dir: `planning/managed-agents/_clients/{{client_slug}}/`
- [ ] Provision Claude Managed Agent via Anthropic console — name: `onboarding-{{client_slug}}`

## Day 1-3 — Build
- [ ] Copy `AGENT.md` template → fill `{{CLIENT_*}}` variables
- [ ] Wire integrations (MCP servers for each tool client uses)
- [ ] Set up approval webhook → routes to client's Slack or email
- [ ] Load welcome email template + doc checklist
- [ ] Configure cost caps + audit log destination

## Day 4-5 — Internal QA
- [ ] Run 5 synthetic customer intakes
- [ ] Verify every approval gate fires correctly
- [ ] Check audit log completeness
- [ ] Stress test: 20 concurrent intakes
- [ ] Confirm multi-tenant isolation (no leakage between test client_ids)

## Day 6-7 — Client Review
- [ ] 60-min demo call with client
- [ ] Run 2-3 real intakes with client watching
- [ ] Capture tune-up list (voice, speed, escalation triggers)
- [ ] Apply tune-ups same-day
- [ ] Collect remaining 50% payment → launch authorized

## Day 8 — Go-Live
- [ ] Flip DNS / webhook / inbox routing to production agent
- [ ] Monitor first 3 real intakes in real-time
- [ ] Be on call via Slack for first 24h

## Week 2-4 — Stabilize
- [ ] Daily: check audit log for errors/escalations
- [ ] Weekly: review 10 random sessions for quality
- [ ] Weekly: cost report to client
- [ ] End of week 4: 30-day review call

## Ongoing Retainer (month 2+)
Covered by $500/mo:
- Weekly: monitoring + anomaly review
- Monthly: 2 small feature adds (new integration, new email template, tuned escalation)
- Quarterly: pricing adjustment review + performance report
- Unlimited: bug fixes, prompt tuning in response to complaints

NOT covered (scoped separately):
- New agent (sold as new product)
- Major prompt rewrites (>50% change)
- New compliance requirement implementation (HIPAA migration etc.)

## Monitoring Triggers
- Escalation rate > 20% → investigate prompt drift
- Cost/day breaches 80% cap → alert + review
- Completion time jumps 2x → check integration latency
- Any PII leakage in logs → P0, pause agent + alert client + Anthropic

## Offboarding (client churns)
- Export audit log
- Hand over all data per contract
- Deprovision managed agent (releases cloud costs)
- Keep `{{client_slug}}` dir in `_archive/` for 90 days
