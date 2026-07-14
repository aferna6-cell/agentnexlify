# Idea Generation — Run 86 (2026-07-10)

## Evidence Digest

1. **Run 86 mandate FAILED on all 3 items**: Step 9E NOT in nightly SKILL.md (grep: no output). `ops/credential-rotation-schedule.md` MISSING. Lead Source Analytics GH issue NOT created (GH search: 0 results). Nightly 2026-07-10 log confirms "AUTO-FIXES: none" — no autonomous items executed.
2. **Heavy feature push (48h)**: bookable-by-default (migration 163), weekly funnel report, voice gate fix, last-call nudge, referral reward (kill-switched), G3 voice scope, IndexNow, ops automation revival. Zero new bugs in nightly triage.
3. **Two new GH issues from nightly**: #407 HIGH (referral reward needs 4-step human gate before `REFERRAL_REWARD_ENABLED=1`); #408 MEDIUM (landing-page-v2 widget policy ambiguous).
4. **Autonomous pipeline health**: Issue-to-pr-loop has 30+ consecutive failures (AUTOPILOT_GH_TOKEN expired). dfa8201 added PAT fallback; 39 ai-ready issues open, no new PRs confirmed. Brain connector still failing (GH #394 pending human). KB autopopulate RUNNING since 2026-07-08.
5. **Root cause of Step 9E miss (2 cycles)**: Prior Steps 9B/9C/9D all included EMBEDDED file content in their winning-concept.md. Run 84 winning-concept.md for Step 9E had a prose description but no inline file content. Nightly skips items requiring multi-file creation without embedded content.

---

### Idea 1: Add Step 9E to nightly SKILL.md (with embedded file content — 2nd-miss escalation)
**Evidence:** Step 9E missing after 2 consecutive nightly cycles (2026-07-09 + 2026-07-10). Both credential systems (AUTOPILOT_GH_TOKEN + brain connector PAT) expired 2026-07-04 with zero early warning. `ops/credential-rotation-schedule.md` MISSING. Root cause of 2-cycle miss identified: run 84 winning-concept.md had prose description but no inline file content; nightly skips multi-file items without embedded content. Steps 9B/9C/9D all succeeded because their winning-concept.md embedded exact file content.
**Action:** This winning-concept.md embeds EXACT content for both files: (1) `ops/credential-rotation-schedule.md` and (2) the Step 9E SKILL.md block — so nightly has zero ambiguity.
**Impact:** Closes the last proactive monitoring gap. Next credential expiry detected 14 days early vs discovered after 5+ days of downtime.
**Category:** operational

---

### Idea 2: Create Lead Source Analytics GH issue (run 85 winner, unexecuted)
**Evidence:** GH search returns 0 results for "lead source breakdown analytics." Run 85 winner was "Create GH issue labeled ai-ready." 83-run parking lot item from customer-gaps.md (still listed as Open Gap, Low effort). dfa8201 added PAT fallback to issue-to-pr-loop — loop SHOULD be healthy if GH #399 human action was taken.
**Action:** Create GH issue: `feat(analytics): add lead source breakdown chart to analytics page` with `ai-ready` label. Full body in `subconscious/runs/2026-07-09-pm/winning-concept.md`.
**Impact:** Delivers customer value via autonomous pipeline. Small businesses want "where are my leads from?" before investing in any channel.
**Category:** customer_value

---

### Idea 3: Fix nightly autonomous scope — add governance.json pending_autonomous scan
**Evidence:** Step 9E is the 2nd AUTONOMOUS-EXECUTABLE item to require 2+ cycles (same pattern as Item A moratorium loop, runs 42-46). Root cause differs: Item A was blocked by a prerequisite; Step 9E is blocked by missing inline content. A general governance.json pending_autonomous scan would be a meta-fix for the meta-problem.
**Action:** Add explicit instruction to nightly-commit-review SKILL.md: "In Phase 9, check governance.json `active_directions` for items where `status == 'pending_autonomous'` and `autonomous_executable == true`. Read the most recent `winning-concept.md` for each. Execute any item whose winning-concept.md includes embedded file content."
**Impact:** Eliminates the entire class of 2-cycle autonomous miss failures. HIGH ROI if reliable.
**Category:** workflow

---

### Idea 4: Resolve landing-page-v2 widget policy (GH #408)
**Evidence:** GH #408 MEDIUM: `landing-page-v2/widget/agentnexlify-widget.js` modified by 8b1e44b (brain sync + widget drift fix, PR #387) despite CLAUDE.md "do not touch" policy. Nightly opened #408 asking for human decision. This is the 3rd occurrence of landing-page-v2 policy ambiguity. Widget byte-identical rule is Critical Invariant #4. Policy needs resolution before next similar commit causes more confusion.
**Action:** Update CLAUDE.md to explicitly state whether `landing-page-v2/widget/` is: (a) in byte-identical sync scope (add to `check_project_invariants.py`) or (b) permanently excluded (add to pre-commit widget-sync exception list + close GH #408).
**Impact:** Closes GH #408. Prevents future nightly issues on same topic. Clarifies scope for all widget changes.
**Category:** code_health

---

### Idea 5: Warm lead recovery email — Sunset Mobile Detailing + Niko's Consulting
**Evidence:** run_86_mandate explicitly names warm lead recovery as secondary winner if both run 84 items confirmed. Both run 84 items are NOT confirmed (Step 9E missing, schedule.md missing). However: 7 real leads captured since deploy, 0 real bookings. The `last-call recovery email` (d14_lastcall nudge) shipped in 0e0ee00 targets abandoned signups, not post-capture cold leads. These two named tenants in the parking lot likely represent real warm leads that need personal follow-up.
**Action:** Query leads table for Sunset Mobile Detailing + Niko's Consulting. Draft one-shot email via Resend targeting leads at those domains. Use existing `activation_nudges.py` batch pattern.
**Impact:** Recovers potentially convertible leads. Zero tech cost (existing Resend integration).
**Category:** customer_value
