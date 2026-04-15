# Customer Support Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 90-min discovery + ticket walk-through
- [ ] Collect: 100 sample tickets, KB export, brand voice, escalation rules, API tokens
- [ ] Confirm tier (Basic/Standard/Premium) + pricing
- [ ] Contract + 50% deposit

## Day 1-4 — KB Embedding + Training
- [ ] Import KB articles → chunk + embed → vector store
- [ ] Label 100 sample tickets (L1/L2/P0) — feeds classification accuracy baseline
- [ ] Build escalation playbook from client's existing rules
- [ ] Tune confidence thresholds

## Day 5-7 — Prompt + Integration
- [ ] Customize role prompt per client voice
- [ ] Wire ticketing system MCP
- [ ] Wire escalation channel (Slack/Teams)
- [ ] Approval webhook tested

## Day 8-10 — Shadow Mode
- Agent drafts every reply, NEVER sends
- Human reviews + sends (or overrides)
- Track: draft-accepted %, draft-edited %, draft-rejected %
- Goal: 70%+ accepted before moving to next phase

## Day 11-14 — Supervised Mode
- Agent auto-sends L1 replies
- Human QA reviews 100% of L1 replies (daily batch)
- Human handles all L2 drafts
- Adjust prompts from QA feedback

## Day 15 — Autonomous Launch
- Agent auto-sends L1 fully autonomous
- L2 goes to human queue with agent draft attached
- P0 pages immediately
- Collect remaining 50% payment

## Week 2-4 — Stabilize
- Daily: escalation log review (look for missed P0s)
- Weekly: random QA of 25 L1 replies
- Weekly: top-10 missed questions → KB gap fill
- End week 4: deflection + CSAT report to client

## Ongoing Retainer ($500/mo)
Covered:
- Weekly KB gap filling (up to 10 new articles)
- Monthly prompt tune based on quality metrics
- Quarterly voice refresh
- Unlimited bug fixes
- New channel integration (existing MCPs only)

NOT covered:
- New ticketing system migration
- Languages beyond contracted scope
- Voice channel integration (separate product)
- Custom ML models

## Monitoring Triggers
- Deflection rate drops below 50% → investigate KB drift
- CSAT drops below 3.8 → pause auto-reply, human review all
- Escalation rate above 40% → classification threshold review
- Any P0 missed (discovered later) → immediate debrief + fix

## Quality Gates
Every L1 reply scored by Haiku QA pass:
- KB-sourced ✓
- Correct tone ✓
- Action-oriented ✓
- Under 150 words ✓
- Ticket ID included ✓
Target: 95%+ pass

## Offboarding
- Export 24 months of support_log
- Hand over KB updates made during engagement
- Deprovision agent
- Archive client dir
