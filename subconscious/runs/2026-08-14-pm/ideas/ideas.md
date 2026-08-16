# Run 103 — Ideas (2026-08-14-pm)

Evidence window: 2026-08-12 → 2026-08-14. Zero production commits last 3 days. Loop stalled (AUTOPILOT_GH_TOKEN expired, #399 Day 36). KB 22 days stale. Run 102 winner (route-security-guard-audit SKILL.md) unimplemented — awaiting human approval.

---

## Idea 1 — Escalate route-security-guard-audit to AUTONOMOUS-EXECUTABLE (carry-forward)

**Category:** workflow  
**Effort:** XS (~10 min to update label + nightly picks it up)  
**Confidence:** HIGH  

**Evidence:**
- Run 102 winning-concept.md: status = "RECOMMENDED — awaiting human approval before execution"
- 3 days elapsed, no human approval observed
- This is the 1st carry-forward cycle (escalation to autonomous-executable typically at 3+ cycles)
- The SKILL.md content is already fully written in run 102 winning-concept.md
- GH #643 (appointment_briefs.py missing block_demo_role) open 7 days, still unpatched
- PR #653 exists as a manual fix but is in draft; autopilot loop cannot auto-merge
- block_demo_role pattern recurred in 3 commits + 1 open issue in 48h window

**Proposed action:**
Change run 102 winning-concept.md status from "awaiting human approval" to "AUTONOMOUS-EXECUTABLE" so nightly-commit-review picks it up and creates the SKILL.md. No backend code touched — documentation-only. Risk = near-zero.

**Why not yet autonomous:** Run 102 explicitly set "awaiting human approval." 1st carry-forward is too early to unilaterally escalate. Protocol calls for 3 cycles before the loop self-escalates. Keep as HIGH-priority recommendation, not autonomous yet.

---

## Idea 2 — Add age-since-last-run check to Step 9C (brain connector staleness alert)

**Category:** operational_efficiency  
**Effort:** S (~20 min to edit SKILL.md + add age threshold)  
**Confidence:** HIGH  

**Evidence:**
- Step 9C currently checks: `consecutive_failures >= 3` → alert. If last run was SUCCESS, consecutive_failures = 0, passes forever.
- Brain connector last run: 2026-07-23 (22 days ago). Step 9C reports PASS every night because no consecutive failures.
- KB autopopulate last run: 2026-07-23 (22 days ago). Step 9F alerts on staleness > 7 days — this works correctly.
- Brain connector has no equivalent age-staleness gate. Same silent-failure pattern that caused the 63-day KB gap before Step 9F was added.
- Morning digest confirms brain connector gap was NOT surfaced by automated monitoring — only visible through manual digest generation.
- Pattern: once a long-running infra component succeeds then silently stops, Step 9C never fires.

**Proposed action:**
Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9C to also alert when last-run age > 14 days (same threshold as KB, or slightly more lenient). Parse `INGESTION-LOG.md` last-entry timestamp, compute age, surface as a WARNING (not FAIL) when > 14 days with no consecutive failures. This prevents the silent-22-day-gap pattern from repeating.

**Risk:** Low. SKILL.md edit only. The nightly session reads SKILL.md fresh each time; change takes effect next night.

---

## Idea 3 — Diagnose and document Nexlify Score ai_usage_guard gap

**Category:** code_health / security  
**Effort:** S (~20 min to grep codebase + document finding)  
**Confidence:** MEDIUM  

**Evidence:**
- governance.json run_103_mandate item 1: "Verify response_score.py has ai_usage_guard properly called"
- Read `backend/routers/response_score.py` → FILE NOT FOUND
- Nexlify Score feature shipped 2026-08-06 per git log (commit e0e9be6, 22 files, 1528 lines added)
- ai_usage_guard is required on any route making Claude API calls — mandatory gating
- The mandate assumed response_score.py exists at backend/routers/ — path may differ or feature uses a different structure
- Not knowing where the endpoint lives = not knowing whether the guard exists
- This is a security/cost gap: unguarded AI endpoint on a paid-plan-only feature allows demo tenants to burn tokens

**Proposed action:**
Grep the codebase for the Nexlify Score entry point, locate where ai_usage_guard should be, document the finding as either (a) guard present (close mandate item), or (b) guard missing (open GH issue). The subconscious cannot implement the fix, but it can produce the diagnostic that removes ambiguity and unblocks human/autopilot action.

**Gap:** Subconscious can document the search path, but cannot run live grep tools to complete the diagnosis. This idea's value is highest if it results in a precise issue filed, not just a recommendation to investigate.

---

## Idea 4 — Step 9H v2: Idempotent stale-PR alerter (first design)

**Category:** operational_efficiency  
**Effort:** M (~45 min to design + write SKILL.md section)  
**Confidence:** MEDIUM  

**Evidence:**
- 5 subconscious draft PRs open: #575 (22d), #611 (15d), #613 (14d), #626 (12d), #653 (2d)
- No automated pressure to review/merge/close stale draft PRs
- Run 101 parking-lot item: "Step 9H redesign (idempotent PR pile alerter — current design would fire every nightly indefinitely)"
- Nightly-commit-review SKILL.md has no Step 9H currently
- Without idempotency, a naive alerter would spam every night for each stale PR

**Design constraint (from run 101 parking lot):**
Must use a "last-alerted" state mechanism — e.g., write `.claude/state/pr-alert-log.json` with `{pr_number: last_alert_date}` and only re-alert after N days (e.g., every 7 days per PR). Alert on first detection, then suppress for 7 days.

**Proposed action:**
Write Step 9H section in nightly SKILL.md with this idempotent design. This is a SKILL.md-only edit, no code.

**Why this is Idea 4 (not winner):** Design is solid but requires more thinking about edge cases (PR merged since last check, PR closed). Idea 2 (brain connector age) is simpler, equally valuable, and fully defined.

---

## Idea 5 — Promote PR #653 from draft to ready-for-review via GitHub comment

**Category:** customer_value / security  
**Effort:** XS (~5 min via GitHub MCP comment)  
**Confidence:** MEDIUM  

**Evidence:**
- PR #653 "subconscious: runs 102-105 — Fix appointment_briefs.py block_demo_role" — 2 days old, DRAFT
- Morning digest: "REVIEW + MERGE — fixes #643 (security)"
- GH #643 labeled `security` + `ai-ready`, 7 days open
- PR is draft — humans may not be aware it's ready for review
- Subconscious already wrote the fix (runs 102-105 claim) — just needs someone to flip it from draft to ready

**Proposed action:**
Post a GitHub comment on PR #653 noting: (a) this fixes GH #643 (security gap), (b) it has been in draft 2 days, (c) it is ready for human review and merge. This is a signal action — low effort, may directly accelerate a security fix.

**Why not winner:** Commenting on a PR is a good XS action but not a systemic improvement. Doesn't compound. The subconscious's value is structural improvements, not one-off nudges. Best handled as a bonus action alongside the winner.
