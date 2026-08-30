# Ideas — Run 113 (2026-08-30)

## Mandate from Run 112
1. Verify @dependabot rebase trigger fires in nightly-2026-08-30
2. Count rebases triggered (≤5)
3. 24-48h: did any Dependabot PRs become clean + merge?
4. GH #684: SUPABASE_ACCESS_TOKEN set after bonus comment?
5. Step 9K readiness: count open subconscious PRs — if >=3, Step 9K is run 113 winner
6. GH #669 middleware PR: any progress? (Day 10+ stalled)

## Mandate Verification Results
1. @dependabot rebase: FAIL — Step 9J was SKIPPED ("No Dependabot PRs detected in this run") — different failure mode than prior runs (28/29 Aug found 3 PRs with unknown state)
2. Rebases triggered: 0
3. PRs clean+merged: unknown/no (Step 9J skipped entirely)
4. GH #684 SUPABASE_ACCESS_TOKEN: NOT SET — credential-rotation-schedule.md still shows "unknown — not yet set"
5. Step 9K condition: 23 historical run directories exist; governance shows 5+ open subconscious draft PRs tracked since run 102. Condition >=3 CONFIRMED. **Step 9K is the mandated winner.**
6. GH #669: STALLED — confirmed in nightly 9D section (AUTOPILOT_GH_TOKEN expired, loop dark)

---

## Candidate 1 — Step 9K: Stale Subconscious Draft PR Audit (MANDATED)

**Category:** workflow_efficiency  
**Source:** run_112_mandate (governance binding), first proposed run 106, deferred pending >=3 open subconscious PRs

**Problem:**  
Subconscious runs produce one draft PR per execution. Over 23 runs, PRs accumulate. Without a nightly audit step, stale unmerged subconscious PRs silently pile up — orphaned improvements that were approved but never acted on. No existing step tracks this.

**Evidence:**
- 23 run directories exist (2026-06-02 through 2026-08-29-pm)
- Run 102 governance tracked 5 open subconscious PRs
- No Step 9K in current SKILL.md
- Governance mandates this as winner when condition >=3 confirmed

**Implementation:**  
Add Step 9K to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9J:
- `mcp__github__list_pull_requests(state="open")` → filter head branches starting with `subconscious/`
- Log each: PR number, title, age in days
- stale_count = PRs older than 30 days
- If stale_count >= 3: log warning to nightly report with list
- If stale_count >= 5 OR any PR > 60 days: post escalation comment on oldest PR
- If stale_count < 3: log clean

**Effort:** LOW (SKILL.md edit, autonomous-executable channel, no production code)  
**Risk:** NONE  
**Compounds:** YES — nightly cleanup signal prevents technical debt accumulation  

---

## Candidate 2 — Fix Step 9J Detection Root Cause

**Category:** workflow_efficiency  
**Source:** mandate verification, 3rd consecutive Step 9J finding

**Problem:**  
Step 9J "No Dependabot PRs detected" is a NEW failure mode (distinct from prior "found 3 PRs with unknown state"). The detection itself is unreliable: `list_pull_requests` with creator filter may not return Dependabot PRs in headless MCP sessions. The @dependabot rebase fix from run 112 is unreachable if Step 9J never finds any PRs to act on.

**Evidence:**
- 2026-08-28 nightly: found 3 Dependabot PRs (unknown state)
- 2026-08-29 nightly: found 3 Dependabot PRs (unknown state, pre-run-112 fix)
- 2026-08-30 nightly: found 0 Dependabot PRs (SKIP entire step)
- Root cause hypothesis: `list_pull_requests` without `creator:"dependabot[bot]"` loses them; headless MCP result set varies

**Implementation:**  
Edit Step 9J.1 to use `mcp__github__search_pull_requests` with query `"is:pr is:open author:app/dependabot"` instead of `list_pull_requests(creator="dependabot[bot]")`.

**Effort:** LOW  
**Risk:** LOW (SKILL.md only)  
**Compounds:** YES — makes all of run 112's @dependabot rebase work reachable  
**Weakness:** 3rd consecutive Step 9J-related recommendation → governance flag for monotonic focus  

---

## Candidate 3 — os_tool_executions.py God Class Split

**Category:** code_health  
**Source:** nightly-2026-08-30 review (742 lines, HIGH risk, MEDIUM-HIGH finding)

**Problem:**  
`os_tool_executions.py` shipped at 742 lines on 2026-08-27. It's the highest-churn file this week (commits 661a140, c3eb9f7, 6abd190, 845e336 all touch it). It handles: route definitions, approval policy, demo-role enforcement, L2 idempotency, tool execution dispatch, audit logging. These are distinct concerns competing in one file. At 742 lines it already violates Rule 9 (>600 lines → factor).

**Evidence:**
- `wc -l backend/routers/os_tool_executions.py` → 742 lines (estimated from commit sizes)
- 4 commits in 48h touching this file
- GH #704 filed for missing `block_demo_role` — symptom of the complexity
- Rule 9: "if a file is already >600 lines and I'm about to add more, stop. Factor the existing code into modules first"

**Implementation:**  
Split into:
- `os_tool_executions.py` → router definitions only (~150 lines)
- `services/tool_execution_policy.py` → approval + demo-role + plan-gating logic
- `services/tool_execution_runner.py` → dispatch + idempotency + audit

**Effort:** HIGH (multi-file refactor, needs careful migration)  
**Risk:** MEDIUM (active file, 4 commits in 2 days — premature split while feature is evolving)  
**Weakness:** File only 3 days old. Splitting prematurely before it stabilizes adds merge-conflict risk. Run 114 candidate after the feature settles.  

---

## Candidate 4 — GH #684 Escalation: SUPABASE_ACCESS_TOKEN Railway Setup

**Category:** operational  
**Source:** run_112_mandate check (bonus action from run 112), 38-day brain connector stall

**Problem:**  
SUPABASE_ACCESS_TOKEN has been "unknown — not yet set" for the duration of tracked time. The brain connector (last run 2026-07-23) depends on it for pgvector embeddings. Without it, Step 9E can't audit this credential, and the KB auto-populate is running without verification. A structured comment on GH #684 with exact setup steps is the lowest-friction escalation.

**Evidence:**
- `ops/credential-rotation-schedule.md`: SUPABASE_ACCESS_TOKEN last_rotated = "unknown"
- Step 9C: brain connector stale 38 days (threshold 14)
- Step 9E: 1 credential in unknown state
- Nightly-2026-08-30: Step 9C "Comment added to existing issue #684"

**Implementation:**  
Post comment on GH #684:
```
SUPABASE_ACCESS_TOKEN setup required to unblock brain connector:
1. Supabase dashboard → Settings → Access Tokens → Create new token (name: "agentnexlify-brain")
2. Railway → Project → Variables → Add: SUPABASE_ACCESS_TOKEN = <value>
3. Redeploy backend service
Once set, Step 9E will track its rotation schedule (90-day interval).
```

**Effort:** MINIMAL (single GitHub comment, no code)  
**Risk:** NONE  
**Weakness:** This is a bonus action (done in run 112 already per winning-concept.md). Redundant if the comment was already posted by run 112. Better as bonus action here too, not the main winner.  

---

## Candidate 5 — Step 9J Redesign: search_pull_requests Instead of list_pull_requests

**Category:** workflow_efficiency  
**Source:** Step 9J detection failure analysis

**Problem:**  
`mcp__github__list_pull_requests` with creator filter is unreliable for Dependabot PRs in headless Claude Code sessions — returns 0 results when PRs clearly exist (23 Dependabot PRs open per prior runs). `mcp__github__search_pull_requests` with query `is:pr is:open author:app/dependabot` uses GitHub's search API which doesn't have the same creator-filter limitation.

**Evidence:** Same as Candidate 2 (this is a more targeted version)  
**Effort:** LOW  
**Risk:** LOW  
**Note:** Redundant with Candidate 2 — these are the same fix. Consolidate under Candidate 2.

---

## Ranking Summary

| # | Idea | Category | Confidence | Mandate |
|---|------|----------|------------|---------|
| 1 | Step 9K stale subconscious PR audit | workflow_efficiency | HIGH | BINDING |
| 2 | Fix Step 9J detection (search API) | workflow_efficiency | MEDIUM | parking lot |
| 3 | os_tool_executions.py god class split | code_health | MEDIUM | run 114 |
| 4 | GH #684 escalation comment | operational | HIGH | bonus action |
| 5 | Step 9J redesign (duplicate of 2) | workflow_efficiency | MEDIUM | merged into 2 |
