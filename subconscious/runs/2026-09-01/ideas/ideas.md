# Ideas — Run 115 (2026-09-01)

## Evidence gathered
- Nightly-2026-09-01: 18 commits reviewed, 0 auto-fixes, Steps 9A-9K all executed
- Step 9K: 3 open subconscious PRs (30-35d), below comment threshold — HEALTHY
- Step 9J: found Dependabot PRs #721/#722, triggered @dependabot rebase — WORKING
- GH #684 SUPABASE_ACCESS_TOKEN: still NOT SET, brain connector 40d stale
- os_tool_executions.py: last commit 2026-08-30 (2 days ago) — NOT stable yet (need 3+)
- M8 OAuth/service_role HOLD: still active, Calendar+CRM deploy blocked
- bug-patterns.md 2026-09-01 entry: M8 E2E strict gate fix logged
- PRs #726 + #727: BOTH fix same Haiku CRM field-omission class (name/email/status missing)
  - #726 merged 2026-08-31: backfill name/email in admin_records_actions.ts
  - #727 merged 2026-09-01: backfill status in admin_records_actions.ts
  - Root: _extract.ts extraction layer doesn't enforce required CRM fields when Haiku omits them
- KB: 124 articles, last compiled 2026-08-26 (6 days) — healthy within 7d threshold

## Ideas

### Idea 1 — Haiku CRM field-omission guard at _extract.ts (code_health)
**Category:** code_health
**Confidence:** HIGH
**Evidence:** Two PRs fixing the same bug class in 2 days (#726, #727). Both patch admin_records_actions.ts with backfill logic — the symptom. Root cause: _extract.ts doesn't enforce required CRM fields when Haiku classification omits name/email/status. Each new Haiku CRM intent that omits a field creates another PR. The fix belongs at extraction time.
**Action:** File GH issue with ai-ready label — implement a guard in agent-service/src/agent-os/agents/_extract.ts that validates required CRM fields (name, email, status) are present after Haiku extraction; if absent, throw a structured error or apply safe defaults with a logged warning rather than silently passing incomplete data downstream to admin_records_actions.ts.
**Effort:** S (guard function + tests, no schema change)
**Autonomous-executable:** NO — requires human GH issue creation as catalyst for issue-to-pr-loop

### Idea 2 — Step 9K extension: auto-close implemented subconscious PRs (workflow_efficiency)
**Category:** workflow_efficiency
**Confidence:** MEDIUM
**Evidence:** Step 9K just launched and fired (3 PRs, 30-35d, below threshold). Run 114 winner. Step 9K counts open PRs but cannot distinguish "implemented" from "pending human review." If governance.json marks an active_direction as `implemented`, the corresponding PR should auto-close with a comment.
**Action:** Extend Step 9K in nightly-commit-review SKILL.md: for each open subconscious/* PR, cross-reference governance.json `active_directions[*].status == "implemented"` — if match, post close comment and close the PR.
**Effort:** M (cross-referencing governance.json from nightly, fragile coupling)
**Autonomous-executable:** YES — SKILL.md edit channel

### Idea 3 — Step 9L: M8 deploy HOLD tracker in nightly (operational)
**Category:** operational
**Confidence:** LOW
**Evidence:** M8 OAuth/service_role HOLD mentioned in run_114_mandate but is a transient state — it will resolve when human deploys Calendar+CRM. No persistent tracking needed; nightly already logs deploy state via existing steps.
**Action:** Add Step 9L to nightly SKILL.md: check M8 HOLD status and log whether Calendar+CRM are deployed. Comment on relevant GH issue if HOLD persists >7 days.
**Effort:** S (SKILL.md edit)
**Autonomous-executable:** YES — but thin evidence for permanent nightly step

### Idea 4 — Step 9C escalation path: SUPABASE_ACCESS_TOKEN 40d comment (operational)
**Category:** operational
**Confidence:** MEDIUM
**Evidence:** Step 9C already commented on GH #684 today (40d stale). Brain connector has been stale multiple consecutive runs. The existing step fires correctly. No new mechanism needed — human simply hasn't acted.
**Action:** No new step needed. Brain connector staleness is tracked. Adding escalation would duplicate existing Step 9C behavior.
**Verdict:** WEAKENED at ideation — evidence confirms existing mechanism working, problem is human action delay not tooling gap.

### Idea 5 — os_tool_executions.py god class split: file GH issue (code_health)
**Category:** code_health
**Confidence:** MEDIUM
**Evidence:** 758-line god class at backend/services/os_tool_executions.py. Last commit 2026-08-30 (2 days ago). Mandate condition: 3+ days stable. NOT met yet (needs 1 more day). Run 113 stability condition still outstanding.
**Action:** Defer per mandate. Monitor. If stable by run 116 (0 commits from 2026-08-30+3 = 2026-09-02), promote to winner.
**Verdict:** DEFERRED per governance mandate — 1 day short of stability condition.
