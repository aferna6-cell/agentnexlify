# Candidate Ideas — Run 115 (2026-09-04)

## Evidence Digest
- 16 commits in last 24h: M9 planner bakeoff (5+ in 3 days), Website Connect v1 (PR #772, 2535 lines added), billing automation
- Step 9J: 19 Dependabot PRs detected — merge check deferred with "rate concern" rationale → 0 merges. Detection works, execution does not.
- Step 9I: filed GH #787 for website_connect.py POST routes missing block_demo_role (Step 9I working correctly)
- Step 9K: 1 subconscious PR (#782, 1 day old) — PASS, under threshold
- os_tool_executions.py: 783L, last commit 2026-09-02 (2 days ago) — not yet stable (mandate: 4d+)
- Brain connector: 43 days stale; SUPABASE_ACCESS_TOKEN not set in Railway
- AUTOPILOT_GH_TOKEN: 62 days (14 days from 76d expiry threshold)
- KB: 9 days stale (Step 9F alerted, Step 9G skipped — `gh` CLI unavailable in CCR)

---

### Idea 1: Fix Step 9J — Implement merge eligibility check (cap 10/run)
**Evidence:** nightly-2026-09-04 Step 9J: "19 Dependabot PRs open. Merge eligibility check deferred — requires mergeable_state per-PR read; no merges executed this run." Detection works (search_pull_requests fix from run 114 confirmed). The merge phase is not implemented: SKILL.md ends at detection without executing the merge loop. 19 PRs aging. "Rate concern" is a false alarm — 19 API calls is well within GitHub API limits. Step 9J has been in SKILL.md since run 108 (2026-08-20, 15 days) but has never successfully merged a PR.
**Action:** Edit Step 9J block in nightly-commit-review SKILL.md: after detecting PRs, add a merge eligibility loop — check `mergeable_state` for each PR (cap 10 per run), skip `unknown` (post `@dependabot rebase`), merge `clean` PRs with no blocking labels via `mcp__github__merge_pull_request` (squash). Log count.
**Impact:** Dependabot PRs merge automatically, CVE window closes from 2-3 weeks to <24h. Permanent compounding value.
**Category:** workflow

---

### Idea 2: os_tool_executions.py god-class split
**Evidence:** 783 lines (30% over 600L threshold). Run 115 mandate explicitly names this as candidate when stable ("0 commits 4d+"). Last commit: 2026-09-02 (f22ef04 — Billing Automation v1 wired invoicing actions). Only 2 days old — not stable.
**Action:** When stable (Sep 5+): invoke /god-class-splitter to split into os_tool_executions_core.py + os_tool_executions_billing.py + os_tool_executions_crm.py.
**Impact:** Reduces blast radius on changes. Easier to test in isolation.
**Category:** code_health
**Note:** PREMATURE — mandate requires 4d+ stability. Defer to run 116.

---

### Idea 3: Direct fix for GH #787 — website_connect.py block_demo_role
**Evidence:** nightly-2026-09-04 Step 9I: "website_connect.py two POST endpoints missing block_demo_role (9589c26)." GH #787 filed with ai-ready label. Demo tenants can persist website connections and trigger live HTTP fetches from the server. The issue-to-pr-loop is dark by design (GH Actions off, GH #500). The fix is 2 lines: add `Depends(block_demo_role)` to the two route signatures in backend/routers/website_connect.py.
**Action:** Add `Depends(block_demo_role)` to `/api/v1/website-connect` (POST) and `/api/v1/website-connect/verify` (POST) in backend/routers/website_connect.py.
**Impact:** Closes security gap on new feature. Demo tenant abuse prevented.
**Category:** code_health
**Note:** Narrow fix, already tracked in GH #787. Nightly auto-fix didn't apply it (MEDIUM risk). Should be handled by nightly or loop when unblocked.

---

### Idea 4: Step 9E early warning at 60 days (before 76d threshold)
**Evidence:** AUTOPILOT_GH_TOKEN: 62 days old (14 days from 76d expiry threshold). Current Step 9E fires only at >=76 days. The token has been stalling the automation loop since run 88 (2026-07-11, ~55 days). The first time it went critical (58 days to expiry) it blocked 40 ai-ready issues. A 60-day early warning would provide 2 weeks of lead time.
**Action:** Edit Step 9E block: add a second threshold at 60 days ("approaching expiry: rotate within 2 weeks") alongside the existing 76-day critical threshold.
**Impact:** 2-week lead time before automation stalls. Prevents future 58-day automation blackouts.
**Category:** operational

---

### Idea 5: M9 planner bakeoff offline quality gate in CI
**Evidence:** 5 M9 commits in 3 days (f669390, e2b500c, 27071b5, 50da659, 105a3c0) all hardening the planner evaluation system. 105a3c0 shipped a "durable bakeoff harness" with Dockerfile.m9-bakeoff + railway.m9-bakeoff.json + run_live_bakeoff.py. plan_eval.py exists with test_os_workflows_plan_eval.py (44 tests). The offline evaluator is deterministic. No minimum pass threshold enforced in CI.
**Action:** Add a minimum plan_eval.py pass rate threshold (e.g., 90%) to .github/workflows/pr-check.yml for PRs touching backend/services/os_workflows/. If planner score drops below threshold, CI fails.
**Impact:** Prevents planner regressions from merging. Compounds as the action space grows.
**Category:** agent_performance
**Note:** System still being hardened (5 commits in 3 days). Risk of gate being too brittle. Timing premature.
