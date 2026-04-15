# Content Repurposer Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 60-min discovery — map source channels, target channels, volume
- [ ] Collect: 10-20 best past pieces (voice samples), brand guide, hashtag/CTA library, scheduler API access, source API access
- [ ] Audience description per channel (e.g., "LinkedIn = B2B decision makers, tone = founder mode")
- [ ] Confirm tier + pricing → contract + 50% deposit

## Day 1-4 — Voice Training
- [ ] Index voice samples → vector store
- [ ] Extract voice fingerprints: sentence length, punctuation quirks, opener patterns, CTA style
- [ ] Build templates per (source, output_channel) — e.g. blog→Twitter thread, podcast→LinkedIn post
- [ ] Run 10 test repurposes → client scores voice match (1-5)
- [ ] Iterate until avg score ≥4.2

## Day 5-7 — Integration
- [ ] Wire source MCPs (RSS, YouTube, podcast, CMS)
- [ ] Wire scheduler MCP (Buffer/Publer/etc. or AgentNexLiFy marketing)
- [ ] Wire analytics pull
- [ ] Set up webhook for new source content detection

## Day 8-10 — Shadow Run
- [ ] Client publishes 3 new pieces → agent repurposes each
- [ ] Client reviews ALL outputs before ANY schedule
- [ ] Capture edits: tone, hooks, CTAs, hashtag choices
- [ ] Goal: 70%+ outputs "would schedule as-is"

## Day 11-14 — Approval-Gated Launch
- [ ] Agent auto-generates outputs
- [ ] Every output routed to client for 1-click approval via Slack or email
- [ ] Measure approval rate per channel
- [ ] Tune channels with <80% approval

## Day 15 — Full Launch
- [ ] Channels with ≥90% approval → auto-schedule (agent makes call)
- [ ] Channels <90% → stay on approval gate
- [ ] Collect remaining 50% payment

## Day 30 — Performance Loop Activation
- [ ] Pull 30 days engagement per post
- [ ] Identify top 10% and bottom 10% by channel
- [ ] Feed top 10% back into voice samples (retraining)
- [ ] Flag bottom 10% patterns to avoid

## Ongoing Retainer ($500/mo)
Covered:
- Weekly: review scheduled vs auto-approved counts
- Monthly: voice retrain from top performers
- Monthly: 1 new output channel added (if integration exists)
- Quarterly: brand voice refresh
- Unlimited bug fixes

NOT covered:
- New source channel class (e.g., adding podcast when started as blog-only)
- Custom image generation (separate product)
- Translation/localization (separate product)
- Paid ad copy (different agent, separate sale)

## Monitoring Triggers
- Approval rate drops below 80% on any channel → voice re-score
- Engagement drops 2x week-over-week → content strategy review
- Any posted content violates brand guide (reported post-fact) → pause auto-schedule, human review
- Cost/piece exceeds target → prompt length audit

## Quality Gates (per piece, pre-approval)
- Voice match score ≥0.80 (auto-check)
- No fabricated claims (auto + human sample)
- Links back to source
- Channel-native format rules passed
- Hashtags relevant (auto-check against library)

## Offboarding
- Export all repurposed content + performance data
- Hand over voice model samples
- Deprovision agent
- Archive
