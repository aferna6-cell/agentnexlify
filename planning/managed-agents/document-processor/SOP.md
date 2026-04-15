# Document Processor Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 60-min discovery — map doc types, target systems, volume
- [ ] Collect: 50+ sample docs per type, target system API tokens, schema definitions
- [ ] Confirm tier (Basic/Standard/Premium) + pricing
- [ ] Contract + 50% deposit

## Day 1-5 — Schema + Extraction
- [ ] Define JSON schema per doc type
- [ ] Label 20 samples per type as ground truth
- [ ] Run extraction on remaining 30 samples — measure field-level accuracy
- [ ] Tune prompts until ≥95% field accuracy on test set
- [ ] Set confidence thresholds per field (critical fields higher bar)

## Day 6-8 — Integration
- [ ] Wire target system MCP
- [ ] Build push-to-system logic with idempotency
- [ ] Set up drop zone (email inbox, Dropbox folder, webhook endpoint)
- [ ] Approval webhook for high-$ gates

## Day 9-11 — Accuracy Testing
- [ ] Process 50 live docs per type (held-out set)
- [ ] Manual QA every field
- [ ] Calculate accuracy, retune if <97%
- [ ] Document known edge cases → playbook

## Day 12-14 — Human-in-Loop
- [ ] Launch with 100% human review initially
- [ ] Human corrections → training loop
- [ ] Drop review rate as accuracy proves out
- [ ] Build audit trail view (client-facing dashboard)

## Day 15 — Launch
- [ ] Production traffic enabled
- [ ] Human reviews flagged-only (10-20% of volume)
- [ ] Collect remaining 50% payment

## Week 2-4 — Stabilize
- [ ] Daily: review all human corrections → feed back into prompts
- [ ] Weekly: accuracy report to client
- [ ] Month 1 end: 30-day performance review

## Ongoing Retainer ($500/mo)
Covered:
- Continuous accuracy tuning
- Monthly: 1 new doc type adjacent to existing (e.g., adding "credit memo" alongside "invoice")
- Quarterly: schema evolution (new fields, new target systems same type)
- Unlimited: bug fixes, prompt tuning

NOT covered:
- Entirely new doc category (new product)
- New target system migration
- Custom vision model training
- OCR of handwriting beyond configured scope

## Monitoring Triggers
- Field accuracy drops below 95% on any doc type → pause + investigate
- Cost/doc exceeds target by 20% → prompt length review
- Human review queue >24hr backlog → alert client
- Any PII leakage in logs → P0, HIPAA/PII review

## Quality Gates
Sample 5% of auto-pushed docs weekly:
- Field accuracy vs ground truth
- Target system entry correct
- Audit trail complete
- Retention policy honored

## Offboarding
- Export all extracted data + original docs per retention policy
- Hand over to client's chosen storage
- Deprovision agent
- Archive for compliance hold period
