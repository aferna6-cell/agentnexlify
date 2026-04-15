# Project Management Agent — Operations SOP

## Day 0 — Kickoff
- [ ] 90-min discovery + team call (meet everyone)
- [ ] Collect: PM tool access, roster with roles + managers + TZ, active projects, sample standups
- [ ] Voice samples from 3-5 team members (for chase tone calibration)
- [ ] Confirm tier + pricing → contract + 50% deposit

## Day 1-4 — Wire + Build
- [ ] Wire PM tool MCP (read/write with approval scopes)
- [ ] Wire Slack/Teams for standup + chase channels
- [ ] Wire git for commit-to-ticket correlation
- [ ] Build team model: who reports to whom, who's on what project
- [ ] Import current sprint → baseline velocity per person

## Day 5-7 — Shadow Run
- Sprint runs normally with agent watching, NOT sending
- Agent drafts every standup, chase, status report
- PM lead reviews drafts daily
- Feedback → prompt tuning
- Goal: 70%+ drafts "would send as-is"

## Day 8-10 — Supervised
- Standup auto-posts (low risk)
- Chase emails drafted for PM approval (one-click send)
- Status reports drafted for PM review + share
- Measure: response-to-chase rate, standup quality (team feedback)

## Day 11-14 — Autonomous Launch
- Standup fully automated
- Chase auto-sends for first attempt (2 days stale) — approval for repeat
- Status reports auto-share to configured channels
- Retro drafts auto-post in retro doc for PM to edit

## Day 15 — Full Launch
- All automation live
- Weekly PM lead check-in for first month
- Collect final payment

## Ongoing Retainer ($500/mo)
Covered:
- Weekly: review chase effectiveness + tone
- Monthly: retro synthesis improvements
- Monthly: 1 new automation added (e.g., "auto-close tickets merged >30 days")
- Quarterly: full team check-in survey
- Unlimited bug fixes

NOT covered:
- Entirely new PM tool migration
- Custom dashboard work (scope as project)
- Resource leveling algorithms (premium tier feature)

## Monitoring Triggers
- Chase response rate drops below 60% → tone review
- Team satisfaction survey drops below 4/5 → immediate review
- Any public-shaming incident reported → P0, pause + post-mortem
- Cost/day breaches cap → investigate scope creep

## Team Trust Metrics (monthly survey, ≤30 sec)
- Standup useful (1-5)
- Chase tone appropriate (1-5)
- Reports accurate (1-5)
- Would keep the agent (yes/no)
Target: ≥4.2 avg, <10% "would remove"

## Offboarding
- Export: standup history, retros, velocity data
- Hand over to client PM tool
- Deprovision agent
- Archive
