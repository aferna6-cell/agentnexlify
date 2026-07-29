# Improvement Backlog — 2026-07-29-pm (Run 104)

## Active — Just Implemented This Run

### feature-docs-trio SKILL.md (WINNER — IMPLEMENTED)
**Status:** IMPLEMENTED — `.claude/skills/feature-docs-trio/SKILL.md` created
**Category:** workflow
**Effort:** XS
**Evidence:** 3 occurrences in 7 days. 3-cycle carry-forward (runs 101-103). Run 103 mandate fired.
**Verified:** file created, feature-build/SKILL.md updated.

---

## Active — Promoted This Run

### Autonomy sweeper nightly health (Step 9I candidate)
**Status:** Promoted from debate #2 — pending run 105 decision
**Category:** operational
**Effort:** XS (~15 bash lines in nightly SKILL.md)
**Evidence:** Sweeper shipped (8e78f5b), runs on demand only. No nightly invocation = latent value. 422 tests pass.
**Action:** Add Step 9I bash block: `python3 scripts/autonomy/run_loop.py sweep --dry-run` → if stranded > 0 → comment on GH #403.
**Note:** Add `|| echo "sweeper unavailable"` guard in case Python env differs from nightly.
**Promote when:** Step 9G confirmed firing correctly for 2+ nightly runs, or first stranded run detected in prod.

---

## Parking Lot

### Silent-green tenant heartbeat (Step 9H)
**Status:** Backlog — design blocked on Supabase credential verification
**Category:** operational
**Effort:** S (~40 bash lines + Supabase REST query)
**Evidence:** Keys Koffee went 5+ weeks undetected (bug-patterns.md). 3 live paid tenants. Any silent tenant is churn risk.
**Blocked by:** (1) Verify `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` available as env vars in nightly bash env. (2) Design false-positive dedup (new tenant grace period? tenant-specific last-seen tracking?).
**Promote when:** Supabase credential path verified OR second silent-tenant incident occurs.

### round-iteration-loop SKILL.md
**Status:** Backlog — low urgency
**Category:** workflow
**Effort:** XS
**Evidence:** 3 occurrences in 7 days (Agent OS refinement patterns). Natural next skill after feature-docs-trio.
**Promote when:** Agent OS loop runs 10+ times OR new improvement loop started from scratch.

### LoopHealthPage.jsx
**Status:** Deferred — threshold not met
**Category:** customer_value
**Effort:** M
**Evidence:** admin_loop_health endpoint operational. 2-3 Agent OS tenants active (below 5-tenant threshold).
**Promote when:** Agent OS tenant count >5 OR loop health incident requires ad-hoc JSON polling.

### conversation_enrichment_job.py cron scheduling
**Status:** Backlog (run 98 parking lot) — BLOCKED
**Category:** operational
**Effort:** S
**Blocked by:** GH #399 (AUTOPILOT_GH_TOKEN) still stalled.
**Promote when:** GH #399 resolved OR autonomy loop takes over cron scheduling.

### KB hybrid retrieval pilot (Keys Koffee)
**Status:** Backlog (run 98 parking lot) — BLOCKED
**Category:** customer_value
**Effort:** S
**Blocked by:** No settings UI for widget_configs feature flags; GH #399 stalled.
**Promote when:** Settings UI exists OR GH #399 clears.

---

## Previously Active (Implemented)

### Step 9G CORRECTED — CCR Routine health check
**Status:** IMPLEMENTED (run 103, 2026-07-29)
**Channel:** nightly-commit-review SKILL.md bash block (after Step 9F)
**Notes:** Checks `git log --since='48 hours ago' -- knowledge-base/` for CCR commits. Posts CCR stall alert to GH #403 if KB >7d stale and no recent KB commits.

### god-class-splitter SKILL.md update
**Status:** IMPLEMENTED (run 102, 2026-07-28-pm)
**Notes:** Added backward-compat re-export step + test patch-target grep step.

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED (run 97, 2026-07-22)
**Notes:** Working as designed. Step 9G builds on it.
