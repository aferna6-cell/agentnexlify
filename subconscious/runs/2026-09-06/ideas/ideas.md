# Ideas — Run 116 (2026-09-06)

## Evidence Digest

- `grep -c 'Step 9L' .claude/skills/nightly-commit-review/SKILL.md` → **0** (Step 9L absent, governance mandate fires at run 116)
- 7 emergency AI metering retrofit PRs (#792–#799) in last 7 days — each requiring 498–1726 new test lines
- 13 confirmed unguarded routers (direct grep, run 115-pm): menu.py, widget_photo_quote.py, platform_support.py, content.py, jobs.py, snippets.py, reviews.py, os_files.py, onboarding.py, insights.py, bids.py, marketing_campaigns.py, social_media.py
- Nightly 2026-09-06: clean (9 commits, 0 violations, 1 fix — missing EOF newline in pr-check.yml)
- os_tool_executions.py: 783L service + 411L router = 1194L, last commit f22ef04 (~7 days stable)
- Step 9J: 17/19 Dependabot PRs still skipped (token budget problem persists)
- GH #800 filed: brain connector 44d stale, SUPABASE_ACCESS_TOKEN still not set in Railway
- bug-patterns.md latest: client_id vs tenant_id on tenant_api_keys (zapier connector, 2026-08-01)

---

## Idea 1: Step 9L — AI Metering Coverage Nightly Check (CARRY-FORWARD)

**Evidence:** 7 emergency AI metering retrofit PRs (#792–#799) in 3 days. `grep -c 'Step 9L'` returns 0 — Step 9L absent from SKILL.md. `autonomous_executable_run: 116` governance condition fires (1st carry-forward). 13 confirmed unguarded routers. Step 9I (same mechanism for block_demo_role) has caught security-class bugs every week since implementation with 0 false positives.

**Action:** Add Step 9L block to `.claude/skills/nightly-commit-review/SKILL.md` and create `scripts/check_ai_metering.py` — AST-based detector scanning `backend/routers/` and `backend/services/` for functions calling Claude without a metering guard. File GH issues (labels: `billing`, `ai-ready`) for unguarded routes, dedup against existing open issues.

**Impact:** Prevents next multi-day retroactive billing sprint (estimated 1,200+ test lines per future sprint). Self-compounding: every nightly run catches new unguarded routes on the day they land.

**Category:** code_health

---

## Idea 2: Split os_tool_executions.py God Class (run 117 candidate, HOLD)

**Evidence:** `wc -l backend/services/os_tool_executions.py` → 783L. `wc -l backend/routers/os_tool_executions.py` → 411L. Total: 1194L. Last commit f22ef04 ~7 days ago (stable). CLAUDE.md Rule 9 threshold is 600L — both files exceed it. Prior splits (appointment_booker, bot_health, notify_common) improved test isolation and review speed.

**Action:** Split `backend/services/os_tool_executions.py` into focused modules (execution_dispatcher.py, result_parser.py, file_ops.py, process_runner.py). Update router imports. One PR.

**Impact:** Code reviewable in chunks. Bug blast radius narrows. Test files can isolate failure domain. Rule 9 compliance.

**Category:** code_health

**Hold reason:** HOLD until Step 9L implemented (billing/security wins are higher priority than code cleanliness). Backend is stable — no urgency. Run 117 candidate.

---

## Idea 3: Step 9J Token Budget Fix — Expand Dependabot PR Processing Cap

**Evidence:** Step 9J found 19 Dependabot PRs in nightly-2026-09-05, triggered rebase on 2, skipped 17 due to token budget (`rebase_trigger_count` cap of 5/run plus session limits). 17/19 skipped = 89% skip rate. CVE window open for skipped PRs.

**Action:** Increase rebase-trigger cap in Step 9J from 5/run to 10/run. Add batch processing for `rebase_trigger_count` — process in two passes (clean PRs first, then unknown-state PRs). Adjust per-PR token allocation.

**Impact:** 17/19 → ideally 0-5 skipped per run. Security patches within 24h instead of 3+ weeks.

**Category:** operational

**Weakness:** Token budget problem may be session-level (not just cap). Increasing cap without fixing underlying budget will fail. Would need investigation of actual limit hit. WEAKENED.

---

## Idea 4: Add `# ai-metering-exempt:` Exemption Marker Documentation to CLAUDE.md

**Evidence:** Step 9L winning concept (run 115) defines an exemption marker (`# ai-metering-exempt: <owner>: <reason>`) for per-function opt-out. Once Step 9L files GH issues for 13 unguarded routers, developers need to know how to suppress false positives. CLAUDE.md currently has no mention of this marker.

**Action:** Add one line to CLAUDE.md under the "Critical invariants" section: "AI metering exemptions: `# ai-metering-exempt: <owner>: <reason>` within 3 lines of function def — bare marker without owner+reason is invalid and flagged."

**Impact:** Prevents developer confusion when Step 9L fires on genuinely exempt functions (test helpers, scaffolding). Reduces false-positive GH issues.

**Category:** workflow_efficiency

**Weakness:** Only meaningful AFTER Step 9L is implemented. Premature to document a guard before the guard exists. KILLED — subordinate to Idea 1.

---

## Idea 5: Nightly Tenant_api_keys client_id Guard Sweep

**Evidence:** bug-patterns.md latest entry (2026-08-01): zapier connector bug used `tenant_id` instead of `client_id` on `tenant_api_keys` table. CLAUDE.md Critical Invariant #1 prohibits this on `leads` + `conversations` but the invariant is not explicitly extended to `tenant_api_keys`. Same class as block_demo_role (structural gap, recurring).

**Action:** Add a grep-based Step 9M to nightly-commit-review that scans `backend/routers/` and `backend/services/` for code touching `tenant_api_keys` with `.tenant_id` — flags and files GH issue.

**Impact:** Prevents the next zapier-class regression before it ships to production.

**Category:** code_health

**Weakness:** Very narrow scope (one table, one column). Step 9I catches the broader class (security guards). Step 9L catches AI billing guards. Step 9M would be the 3rd sweeper — viable but lowest ROI of the three. Parking lot until Step 9L is implemented and pattern proven again. WEAKENED.
