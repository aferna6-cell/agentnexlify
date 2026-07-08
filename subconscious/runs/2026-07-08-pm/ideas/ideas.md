# Ideas — 2026-07-08-pm (Run 83)

## Context
- Run 82 winner (kb-autopopulate.yml) IMPLEMENTED by nightly-2026-07-08 ✓
- Run 81 winner (ai-ready label on #385) IMPLEMENTED by nightly-2026-07-08 ✓
- Brain connectors: 8 consecutive failures (GH #394, human-required, day 8)
- Issue-to-pr-loop: ai-ready label applied to #385 but NO PR confirmed yet
- KB autopopulate.yml deployed today — first run pending (next 6am/6pm UTC)
- moratorium_active: false
- PR #387 (brain Maps + widget drift fix): 7d draft, ready to promote

---

### Idea 1: Add issue-to-pr-loop health check to nightly SKILL.md as Step 9D
**Evidence:** ai-ready label applied to GH #385 (SMS Dashboard) at nightly-2026-07-08. Morning digest (2026-07-08) says "issue-to-pr-loop should have triggered" — passive phrasing, no PR confirmed. Autopilot-issue-loop.yml exists (.github/workflows/autopilot-issue-loop.yml) but loop dormancy has been mentioned in runs 21-25. Same silent-failure pattern that let brain connectors fail 8 days (Step 9C) and KB autopopulate fail 63 days (run 82). Run 83 mandate explicitly: "Verify issue-to-pr-loop opened a draft PR for SMS Compliance Dashboard."
**Action:** Add Step 9D to .claude/skills/nightly-commit-review/SKILL.md — check for ai-ready GH issues with no PR opened in >24h; if found, add comment to issue with diagnostic info; alert if loop appears stalled (last run >4h ago per GH Actions logs).
**Impact:** Closes monitoring gap — issue-to-pr-loop failures detected within 24h instead of days/weeks. Every future ai-ready label gets automatic follow-through verification. Prevents GH #385 from becoming another 63-day silent gap.
**Category:** workflow

---

### Idea 2: Add brain/INGESTION-LOG.md to subconscious Phase 2 evidence sources
**Evidence:** Brain connectors failing 8 days (Jul 1–8). Subconscious Phase 2 currently reads: git log, bug-patterns.md, customer-gaps.md, knowledge-base/INDEX.md, daily logs. INGESTION-LOG.md is not in the evidence list. Step 9C in nightly SKILL.md added brain connector detection — but subconscious runs could surface this independently by reading INGESTION-LOG.md directly. Run 79 was the first detection run (4 days after failure started) — INGESTION-LOG.md in Phase 2 would have caught it on run 80 (day 5) or earlier.
**Action:** Add `brain/INGESTION-LOG.md` as an evidence source in subconscious SKILL.md Phase 2 — read last 10 lines, flag if consecutive failures > 2 days.
**Impact:** Earlier detection of brain connector failures. Reduces failure-to-detection lag from 4+ days to 1 day. Pairs with Step 9C (nightly) for double-coverage.
**Category:** workflow

---

### Idea 3: Lead source analytics dashboard — /api/leads/source-analytics + Recharts bar chart
**Evidence:** customer-gaps.md lists "Lead source analytics" as cross-industry, Low effort, HIGH impact. Has been parking lot since run 2 (82 runs ago). `source` column exists in leads table (migration 122). Recharts already installed in frontend. Morning digest notes no new product features in last 24h. Issue-to-pr-loop now activated (ai-ready on #385) — a second ai-ready issue could be tagged for this.
**Action:** Tag existing GH issue or create new one for lead source analytics dashboard (1 backend endpoint + 1 frontend Recharts bar/pie chart). Add ai-ready label so issue-to-pr-loop picks it up.
**Impact:** Customer-visible feature showing lead source distribution (widget, Google, referral, etc.). Demonstrates ROI to business owners. Cross-industry value. Low engineering effort (80% infrastructure exists).
**Category:** customer_value

---

### Idea 4: Promote PR #387 from draft and batch-merge 7 Dependabot dep bumps
**Evidence:** PR #387 (brain Maps sync + widget byte-identical fix) has been draft for 7 days. Morning digest says "the only real work item (ready for promote+merge)." 7 Dependabot PRs aging 2-23 days (#279 #281 #380 #381 #382 #383 #396). 10 open PRs total. PR queue creates cognitive overhead and blocks future branch merges.
**Action:** Promote PR #387 from draft to ready-for-review and merge. Batch-merge the 7 Dependabot dep bumps. Reduces open PRs from 10 to 2 (PR #86 + PR #372 remain).
**Impact:** Clears PR queue debt. Widget byte-identical fix lands (reduces check_project_invariants failure risk). Dependency security patches applied. 15 min total.
**Category:** operational

---

### Idea 5: Add Step 9D kb-autopopulate.yml verification to nightly SKILL.md
**Evidence:** kb-autopopulate.yml deployed today (nightly-2026-07-08, f958ab7). knowledge-base/log.md last entry: 2026-04-25 (before the new workflow). First scheduled run: next 6am or 6pm UTC. If the workflow fails silently, we won't know — the same pattern that caused the 63-day gap in the first place. No monitoring exists for the new workflow.
**Action:** Add Step 9D to nightly SKILL.md — check knowledge-base/log.md for entries after 2026-07-07; if missing after 2+ nightly runs post-workflow-deployment → create GH issue with label `kb-autopopulate-failure`. AUTONOMOUS-EXECUTABLE (SKILL.md edit, XS effort).
**Impact:** Prevents silent recurrence of 63-day KB gap. Closes monitoring loop on run 82 winner. Low risk, high prevention value.
**Category:** operational
