# Ideas — Run 114 (2026-08-31-pm)

### Idea 1: Step 9K — Stale Subconscious Draft PR Audit in nightly SKILL.md
**Evidence:** Step 9K absent (grep -c 'Step 9K' SKILL.md = 0). run_113_mandate binding: "if >=3, Step 9K is run 113 winner — condition CONFIRMED (23 run dirs, 5+ open subconscious PRs)." Governance: autonomous_executable_run_114_if_not_approved. 1st carry-forward fires this run. Same channel as Steps 9C/9E/9F/9G/9I/9J.
**Action:** Add Step 9K block to .claude/skills/nightly-commit-review/SKILL.md after Step 9J block. Also fix Step 9J detection (bonus: search_pull_requests vs list_pull_requests).
**Impact:** Subconscious draft PRs no longer accumulate unreviewed forever. Nightly surfaces backlog every run. Same SKILL.md-edit channel — 6 prior implementations proved it reliable.
**Category:** workflow_efficiency

### Idea 2: M8 Invariant Scan — Add __future__ annotations sweep to M8 pre-deploy gate
**Evidence:** c159976 (nightly 2026-08-31) auto-fixed `from __future__ import annotations` removal from backend/services/m8_action_flags.py. M8 sprint generated 7+ files in 3 days; at least one violated CLAUDE.md invariant #5. Pre-commit guards this, but the violation reached main and required nightly cleanup.
**Action:** Add an M8-specific invariant sweep step to docs/ops/m8-staging-setup.md deploy checklist: `grep -rn 'from __future__ import annotations' backend/services/m8_*.py` — fail deploy if any found.
**Impact:** M8 deploy cannot proceed with hidden Pydantic failures. Fast: doc-only addition to existing checklist.
**Category:** code_health

### Idea 3: Step 9J Detection Fix — Change list_pull_requests to search_pull_requests
**Evidence:** nightly-2026-08-30 Step 9J skipped entirely: "No Dependabot PRs detected" — new failure mode. list_pull_requests with creator filter unreliable for bot PRs in headless sessions. search_pull_requests with "is:pr is:open author:app/dependabot" is more reliable.
**Action:** Edit Step 9J.1 in SKILL.md: replace list_pull_requests(creator='dependabot[bot]') with search_pull_requests(query='is:pr is:open author:app/dependabot').
**Impact:** Step 9J detection goes from flaky to reliable. Compounding: every nightly thereafter has accurate Dependabot PR view.
**Category:** workflow_efficiency

### Idea 4: os_tool_executions.py God Class Split (deferred — NOT ready)
**Evidence:** 758L, last commit 2026-08-30 (1 day ago). run_113_mandate: "os_tool_executions.py stable (0 commits 3d+)? If yes: run 114 god class split candidate." Condition NOT met.
**Action:** DEFERRED — re-evaluate at run 115 if stable for 3+ days.
**Impact:** N/A this run — split during active sprint risks merge conflicts.
**Category:** code_health

### Idea 5: M8 OAuth Blocker Documentation
**Evidence:** b786aeb "Calendar/Gmail OAuth HOLD", fa83852 "staging RLS on; service_role wiring scripts", 47cda00 "OAuth/service_role HOLD". M8 stuck at staging gate for 1+ days. No precise OAuth failure documented.
**Action:** Add structured "OAuth HOLD" diagnostic section to docs/ops/m8-staging-setup.md: exact error, root cause hypothesis, two unblocking options (service_role vs OAuth app).
**Impact:** Reduces M8 unblock time. But run 113 winner is still pending — lower priority than governance mandate.
**Category:** operational
