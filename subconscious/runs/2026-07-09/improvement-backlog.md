# Improvement Backlog — Run 84 (2026-07-09)

---

## Active (approved or winner)

### Run 84 Winner — Proactive Credential Rotation Tracking (Step 9E)
- **Status:** `pending_autonomous` — nightly will add Step 9E to SKILL.md + create ops/credential-rotation-schedule.md
- **Files:** `.claude/skills/nightly-commit-review/SKILL.md`, `ops/credential-rotation-schedule.md`
- **Effort:** XS
- **Autonomous:** yes
- **Mandate for run 85:** verify Step 9E added to SKILL.md and ops/credential-rotation-schedule.md created; if pipeline healthy (GH #399 + #394 resolved), promote lead source analytics dashboard to winner

### Run 79 Winner — Brain Connector Credentials (#394)
- **Status:** `pending_human` — day 9. SUPABASE_ACCESS_TOKEN + GitHub PAT needed in Railway Variables
- **Effort:** 7 min human action
- **Blocked:** human must set env vars; autonomous cannot resolve credential issues
- **Note:** GH #394 still open. GH #399 (AUTOPILOT_GH_TOKEN) also human-required. Both filed as human-action-required.

### Run 82 Winner — KB Autopopulate GitHub Actions
- **Status:** `implemented` (f958ab7 deployed `.github/workflows/kb-autopopulate.yml`)
- **Verification:** CONFIRMED — first run succeeded 2026-07-08T19:02:13Z. 63-day gap closed.

---

## Parking Lot (defer, not rejected)

### Lead Source Analytics Dashboard
- **Origin:** customer-gaps.md since run 2 (84-run parking lot)
- **Evidence:** `source` column exists on leads table (migration 122); Recharts installed; cross-industry, Low effort, HIGH impact
- **Why deferred run 84:** mandate condition unmet — pipeline not healthy (loop stalled, brain connector down). No new customer demand signal this run.
- **Next trigger:** run 85 IF GH #399 resolved AND loop confirmed healthy; OR first customer request for lead reporting
- **Activate condition:** `mcp__github__list_issues` shows GH #399 CLOSED + autopilot-issue-loop last run < 4h ago

### INGESTION-LOG.md in Subconscious Phase 2
- **Origin:** Idea 4 this run, Idea 2 in run 83
- **Evidence:** brain connectors failing 9+ days; subconscious Phase 2 doesn't read INGESTION-LOG.md directly
- **Why deferred run 84:** Step 9C already catches this; triple-coverage with diminishing returns
- **Next trigger:** run 85 if Step 9C + Step 9D fail to catch an outage; or if nightly reliability degrades

### KB Autopopulate Monitoring
- **Status:** RESOLVED — kb-autopopulate.yml first run confirmed 2026-07-08T19:02:13Z. No longer needs parking lot promotion.

### PR #387 + Dependabot Batch Merge
- **Origin:** run 83 parking lot
- **Recommendation:** human should promote PR #387 from draft + merge 7 Dependabot PRs (#279 #281 #380 #381 #382 #383 #396) at earliest opportunity
- **Why not winner:** operational housekeeping requiring human merge action; not a system improvement

---

## Rejected Paths (never recommend again)

- `ai_human_handoff` — frozen (governance.json `frozen_ideas`)
- None added this run

---

## Questions for Run 85

1. **Did Step 9E execute correctly?** Check nightly-2026-07-10 log for "Step 9E:" line and ops/credential-rotation-schedule.md existence.
2. **Is GH #399 closed?** AUTOPILOT_GH_TOKEN rotation is 5-min human action — key unblocking step.
3. **Is GH #394 closed?** Brain connector credentials — day 9+ by run 84.
4. **Did issue-to-pr-loop resume?** After #399 resolved, loop should pick up all 30 stalled ai-ready issues. Check autopilot-issue-loop.yml last run.
5. **Lead source analytics?** If pipeline healthy (loop running, #399/#394 resolved), promote to run 85 winner.
6. **Did PR #387 merge?** Day 8+ draft.
