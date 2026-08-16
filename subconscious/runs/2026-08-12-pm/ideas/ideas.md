# Run 103 — Candidate Ideas (2026-08-12-pm)

Generated from evidence: git log (3d + 7d), nightly-2026-08-12, morning-digest-2026-08-12, skill-discovery-2026-08-10, bug-patterns.md, governance run_103_mandate checks.

---

## Idea 1: Create `pr-backlog-triage` SKILL.md
**Category:** workflow_efficiency
**Effort:** S (~20 min)
**Confidence:** HIGH

**Evidence:**
- skill-discovery-2026-08-10 explicit proposal: "PR Backlog Triage — classifies and labels open PRs, ~20 min/triage saved"
- Morning digest 2026-08-12: 10 open PRs; "merge Dependabot PRs" listed as Top 3 Priority (consecutive days)
- 4 Dependabot PRs aging 2-9 days (#649 2d, #629 9d, #630 9d, #631 9d) — no action taken despite repeated flag
- 5 subconscious draft PRs open, including PR #653 (0d) opened by morning digest as carry-forward
- P1 parking lot debate (run 102): SURVIVED, conservative posture — classify + label + summary; merge only as opt-in with env gate
- Nightly Step 9D surfaces PR pile-up but has no structured action playbook; same ~20-min manual triage paid each session

**Why atomic:** One new SKILL.md file. No existing code touched. Opt-in env gates prevent autonomous action without explicit configuration.

---

## Idea 2: Carry-forward `route-security-guard-audit` SKILL.md (run 102 winner)
**Category:** code_health
**Effort:** S (~30 min)
**Confidence:** HIGH

**Evidence:**
- Run 102 winner: RECOMMENDED — awaiting human approval
- Skill dir `.claude/skills/route-security-guard-audit/` CONFIRMED MISSING (this run)
- cbbaae5 (2026-08-07): orphaned guard fix on detached HEAD; c204af2 (2026-08-08): correct fix applied; 228203d (2026-08-08): structural test added
- GH #643: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard (5 days open, autopilot stalled)
- skill-discovery-2026-08-10 explicit proposal

**Disposition note:** Per SKILL.md rule — prior winner still pending = carry to parking lot P1; select NEW winner. This is cycle 2 (not 3). No escalation to direct implementation yet.
**Run 104 flag:** If SKILL dir still missing in run 104, that = cycle 3 = escalation threshold → subconscious creates file directly.

---

## Idea 3: Add Dependabot safe-merge gate to nightly (Step 9H)
**Category:** operational
**Effort:** M (~45 min)
**Confidence:** MEDIUM

**Evidence:**
- 4 Dependabot PRs aging 2-9 days with no action across multiple nightly runs
- Morning digest flags Dependabot pile-up as Top 3 priority
- Nightly already has Step 9A-9G framework — adding 9H is incremental

**Risk factors:**
- AUTOPILOT_GH_TOKEN expired (GH #399) — unclear if MCP GitHub token can merge PRs
- Auto-merging requires CI verification pass; CI status check needs MCP tool confirmation
- "No auto-merge default" posture established in P1 parking lot debate for pr-backlog-triage
- M effort without verified execution path = risky as autonomous-first winner

---

## Idea 4: Governance correction — retire response_score.py mandate as N/A
**Category:** operational
**Effort:** XS (~5 min)
**Confidence:** HIGH

**Evidence:**
- run_103_mandate item 1: "Confirm backend/routers/response_score.py has ai_usage_guard call"
- Read tool (this run): file does not exist — never created or renamed/moved
- Stale mandate will repeat as dead mandate item in every future run until corrected
- Parking lot P2 (run 102): "KILLED — evidence threshold not met — assumption unverified." This run confirms: assumption was correct that the file doesn't exist.

**Disposition:** governance.json correction only. Not a new skill. Handled in Phase 6 persist step.

---

## Idea 5: Update `feature-build` SKILL.md with 5-file standard pattern
**Category:** workflow_efficiency
**Effort:** XS (~10 min)
**Confidence:** MEDIUM

**Evidence:**
- skill-discovery-2026-08-10 update proposal: "feature-build SKILL.md missing 5-file pattern observed in e0e9be6 and 4853c31"
- P3 parking lot (run 102): "low effort, can be bundled with another commit"
- Two commits confirm the pattern: router + schema + service + test + migration = standard 5-file feature build

**Disposition:** Low evidence density relative to Idea 1 and 2. Bundleable with any commit. Not strong enough as standalone winner.
