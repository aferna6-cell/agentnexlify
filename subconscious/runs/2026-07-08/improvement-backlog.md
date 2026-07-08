# Improvement Backlog — 2026-07-08 (Run 83)

## Active
- **Lead source analytics dashboard** (run 83 winner): Add `LeadSourceChart` component to Leads dashboard page. `leads.lead_source` column exists, Recharts installed. Group by source, `<PieChart>` with empty state. Mirror `AnalyticsPage.jsx` pattern. `autonomous_executable: false` — human UI review needed.

## Autonomous Bonus (Nightly — No Queue Slot Needed)
- **Add brain/INGESTION-LOG.md to Phase 2 evidence in SKILL.md** (idea 2): One-line "Also read:" addition in `.claude/skills/subconscious/SKILL.md`. Autonomous-executable. Brain connector health signal in every future run. Nightly can implement tonight without pending slot.

## Parking Lot (survived debate, not chosen this run)

- **Verify kb-autopopulate.yml first cron run** (idea 3): `knowledge-base/log.md` still at 2026-05-05. Workflow created 2026-07-08 by f958ab7. Next cron: 6 AM or 6 PM UTC. If human wants to end 63-day gap today: `gh workflow run kb-autopopulate.yml`. Medium — workflow fires automatically anyway, manual trigger optional.

- **Add SUPABASE_ACCESS_TOKEN + VOYAGE_API_KEY to GitHub repo secrets** (idea 4): Without these, kb-autopopulate.yml compiles wiki articles but skips pgvector embedding upserts. If run 79 pending_human action is taken (token rotation), adding secrets is an additional 2-min step. Compound action when human resolves #394.

- **SMS Dashboard PR follow-through** (idea 5 — killed in debate): GH #385 has ai-ready label. Issue-to-pr-loop should handle autonomously. Check `gh pr list --label ai-ready` if loop appears stalled.

## Still Pending (human-required)

- **Fix brain connector credentials** (run 79 winner, pending_human): Rotate GitHub token with repo/issues scope (~5 min) + set SUPABASE_ACCESS_TOKEN in cron environment (~2 min). See `subconscious/runs/2026-07-05/winning-concept.md`.

## Questions for Next Run (Run 84)

1. Was the lead source analytics chart implemented? Check `frontend/src/pages/LeadsPage.jsx` (or equivalent) for `LeadSourceChart` component.
2. Did nightly implement the INGESTION-LOG.md autonomous bonus? Check `.claude/skills/subconscious/SKILL.md` Phase 2 "Also read:" section.
3. Did `kb-autopopulate.yml` fire (either cron or manually triggered)? Check `knowledge-base/log.md` for entries after 2026-07-08.
4. Has GH #394 (brain connector credentials) received human action? Check `brain/INGESTION-LOG.md` for consecutive success entries.
5. Did issue-to-pr-loop open a draft PR for GH #385 SMS Compliance Dashboard? Check open PRs — should have "SMS" or "compliance" in title.
6. If run 83 winner implemented AND run 79 resolved: pending=0. Run 84 can recommend a third item. Candidates: KB secrets (idea 4), SMS dashboard frontend page (from #385 PR), or next customer gap from customer-gaps.md.
