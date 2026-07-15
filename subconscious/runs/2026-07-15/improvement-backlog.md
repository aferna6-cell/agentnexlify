# Improvement Backlog — 2026-07-15 (Run 94)

## Active

- Fix `_SESSION_TURN_COUNTS` in `widget_guard.py:141` — replace bare dict with bounded OrderedDict (maxsize=10k, LRU eviction). Autonomous-executable. 8–10 lines, no new deps.

## Parking Lot (survived debate but not chosen)

- **Step 9F: nightly infra staleness check** — add to `.claude/skills/nightly-commit-review/SKILL.md`: check ai-ready infrastructure-blocking issues (GH #399, #403) daily; escalate if >7 days stale. Debated: SURVIVES. Not chosen because GH #399/#403 already heavily escalated — marginal value lower than code fix.
- **Attribution dashboard GH issue** — file issue with `ai-ready` label for `AttributionPage.jsx` to surface `attribution.py` + migration 172 data. Debated: WEAKENED (router endpoint unverified; issue-to-pr-loop blocked by GH #403). Worth filing once GH #403 resolves.
- **BotHealthPage.jsx** — no frontend for the largest new service from PR #431. Not debated but clear future work. Candidate for run 95 once baseline new services stabilize.
- **Manual KB refresh script** — `scripts/kb-refresh-local.sh` to unstick 72+ day stale KB while GH #403 awaits resolution. Not debated. Autonomous-executable; worth doing in a future run.

## Rejected This Run

None killed in debate (all 3 debated ideas survived with varying strength).

## Persistent Blockers (human action required)

- **REFERRAL_REWARD_ENABLED=1** in Railway Variables — 5-run subconscious chain answered all 10 checklist items. Human has not acted after 4 automated comments. Day 23+.
- **Keys Koffee business hours** — email/call tenant. Day 23+, still 0 business_hours rows. 3 leads unable to book.
- **GH #399** — rotate AUTOPILOT_GH_TOKEN. Day 12+. Unblocks 40 ai-ready issues.
- **GH #403** — add ANTHROPIC_API_KEY to GitHub Actions secrets. Day 12+. Unblocks KB autopopulate + autopilot loop.

## Questions for Next Run

1. Did nightly review commit the widget_guard fix autonomously? (check nightly-2026-07-16 log)
2. Is the bounded LRU approach stable under load? (regression test should confirm)
3. Should attribution dashboard issue be filed now vs waiting for GH #403 resolution?
4. Step 9F: is there a clean staleness-escalation cap that avoids noise after Day 14?
