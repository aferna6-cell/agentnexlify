# Improvement Backlog — Run 83 (2026-07-08-pm)

---

## Active (approved or winner)

### Run 83 Winner — Issue-to-PR Loop Health Check (Step 9D)
- **Status:** `pending_autonomous` — nightly will add Step 9D to SKILL.md
- **Files:** `.claude/skills/nightly-commit-review/SKILL.md`
- **Effort:** XS
- **Autonomous:** yes
- **Mandate for run 84:** verify Step 9D executed correctly; confirm whether loop opened a PR for #385 or is confirmed stalled; if stalled, escalate to human-action-required

### Run 79 Winner — Brain Connector Credentials (#394)
- **Status:** `pending_human` — day 8. SUPABASE_ACCESS_TOKEN + GitHub PAT needed in Railway Variables
- **Effort:** 7 min human action
- **Blocked:** human must set env vars; autonomous cannot resolve credential issues
- **Note:** resolving #394 also unblocks KB pgvector upsert (run 82 winner dependency)

### Run 82 Winner — KB Autopopulate GitHub Actions
- **Status:** `implemented` (f958ab7 deployed `.github/workflows/kb-autopopulate.yml`)
- **Verification:** first run pending — next 6 AM or 6 PM UTC; check `knowledge-base/log.md` for new entry after that time

---

## Parking Lot (defer, not rejected)

### Lead Source Analytics Dashboard
- **Origin:** customer-gaps.md since run 2 (82-run parking lot)
- **Evidence:** `source` column exists on leads table (migration 122); Recharts installed; cross-industry, Low effort, HIGH impact
- **Why deferred run 83:** issue-to-pr-loop monitoring took priority; no new customer demand signal this run
- **Next trigger:** run 84 if loop health confirmed and pipeline clear; OR first customer request for lead reporting

### INGESTION-LOG.md in Subconscious Phase 2
- **Origin:** Idea 2 this run
- **Evidence:** brain connectors failing 8 days; subconscious Phase 2 doesn't read INGESTION-LOG.md directly
- **Why deferred run 83:** Step 9C (nightly) + Step 9D (winner) cover the monitoring gap more directly; triple-coverage with diminishing returns
- **Next trigger:** run 84 if Step 9C + Step 9D fail to catch a connector outage; or if nightly reliability degrades

### KB Autopopulate Monitoring (Step 9D alt)
- **Origin:** Idea 5 this run
- **Evidence:** kb-autopopulate.yml deployed today (f958ab7); `knowledge-base/log.md` has no entry after 2026-04-25; first run pending
- **Why deferred run 83:** Idea 1 (issue-to-pr-loop) took the Step 9D slot; KB verification is partly covered by run 83 mandate check
- **Next trigger:** run 84 — if kb-autopopulate.yml first run hasn't produced a `knowledge-base/log.md` entry, promote to winner immediately

### PR #387 + Dependabot Batch Merge
- **Origin:** Idea 4 this run; morning digest priority 3
- **Why not a subconscious winner:** operational housekeeping requiring human merge action; not an improvement to the system itself
- **Recommendation:** human should promote PR #387 from draft + merge 7 Dependabot PRs (#279 #281 #380 #381 #382 #383 #396) at earliest opportunity

---

## Rejected Paths (never recommend again)

- `ai_human_handoff` — frozen (governance.json `frozen_ideas`)
- None added this run

---

## Questions for Run 84

1. **Did Step 9D execute correctly?** Check nightly-2026-07-09 log for "Step 9D:" line.
2. **Did issue-to-pr-loop open a PR for #385?** If still no PR by run 84, the loop is confirmed stalled and `human-action-required` should be raised.
3. **Did kb-autopopulate.yml fire?** Check `knowledge-base/log.md` for entry after 2026-07-08 18:00 UTC.
4. **Is PR #387 merged?** Morning digest shows it's been draft 7 days.
5. **Brain connector credentials (#394)?** Day 8 by run 83. Day 9+ by run 84 unless human acts.
6. **Should lead source analytics get an ai-ready label?** If pipeline is confirmed working run 84, this is next customer-value winner.
