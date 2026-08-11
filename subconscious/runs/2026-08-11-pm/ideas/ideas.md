# Run 102 — Candidate Ideas (2026-08-11-pm)

## Idea 1: Create `route-security-guard-audit` SKILL.md
**Category:** code_health
**Effort:** S (~30 min)
**Confidence:** HIGH

**Evidence:**
- `docs/skill-discovery/2026-08-10.md` explicitly proposes this skill with 6-step checklist
- 3 commits in 48h (cbbaae5+c204af2+228203d) applied the same block_demo_role pattern: fix → fix-again-after-orphaned-HEAD → structural-test
- GH #643 open 4 days: appointment_briefs.py missing `block_demo_role` + plan gate + `ai_usage_guard` — security+ai-ready labels
- nightly-2026-08-11 Step 9D stalled means #643 will not self-resolve via issue-to-pr-loop
- `docs/dev-knowledge/bug-patterns.md`: connector_awareness.py used wrong column (tenant_id) on 2026-08-01 — adjacent pattern; guard regressions are systemic not one-off

**Action:** Write `.claude/skills/route-security-guard-audit/SKILL.md` with 6-step audit checklist:
1. `grep -rn "block_demo_role" backend/routers/` — build guard inventory
2. Identify payment/billing/account-mutation routes missing guard (compare to billing.py:33 canonical)
3. Add `dependencies=[Depends(block_demo_role)]` + import line
4. Add structural assertion to `backend/tests/test_plan_gating_new_plans.py` (introspect route.dependencies)
5. `ast.parse()` syntax check
6. Commit: `fix: add block_demo_role guard to <endpoint>` + `test: assert block_demo_role guard on <endpoint>`

**Why this wins over manual each time:** The same 15-min re-discovery cost (billing.py:33 reference, introspection test shape) has already been paid twice in 48h. A skill amortizes it forever.

---

## Idea 2: Create `pr-backlog-triage` SKILL.md
**Category:** workflow
**Effort:** S (~25 min)
**Confidence:** HIGH

**Evidence:**
- `docs/skill-discovery/2026-08-10.md` explicitly proposes this skill
- morning-digest-2026-08-11: 10 open PRs, 4 Dependabot-ready (#649, #630, #631, #629) sitting for 1-8 days
- morning-digest flagged PR backlog as Top 3 priority on 2026-08-11 AND previous days
- 5 stale subconscious drafts (#626, #613, #611, #606, #575) — root cause is unmerged Step 9G but the skill accumulation itself is a systemic issue
- No current skill handles PR lifecycle management autonomously

**Action:** Write `.claude/skills/pr-backlog-triage/SKILL.md` with classification + action steps:
1. List all open PRs via `mcp__github__list_pull_requests`
2. Classify into 4 buckets: merge-ready / superseded / stale-draft / active
3. merge-ready (Dependabot CI-green): merge
4. superseded: close with comment
5. stale-draft (autonomy-authored, 7+ days, no recent push): add `needs-review` label + one-line comment
6. Write summary to `ops/routines/logs/pr-triage-YYYY-MM-DD.md`

---

## Idea 3: Add `ai_usage_guard` call to response_score.py (Nexlify Score)
**Category:** operational
**Effort:** XS (2-line addition)
**Confidence:** MEDIUM

**Evidence:**
- `e0e9be6` (2026-08-06) shipped `backend/routers/response_score.py` for Nexlify Score AI endpoint
- parking lot from run 101: new AI-powered route needs `ai_usage_guard` call to prevent demo tenant token burn
- morning-digest confirms no fix applied in 24h window (only ops/docs commits)
- No structural test asserting `ai_usage_guard` is present on response_score route

**Action:** Add `ai_usage_guard(client_id, estimated_tokens=500)` call in response_score.py before Claude API call + add structural assertion to test file.

**Caveat:** Not confirmed response_score.py is missing the guard — could have been added at commit time. Needs verification before implementation.

---

## Idea 4: Post GH #643 implementation sketch comment
**Category:** operational
**Effort:** XS (GitHub comment)
**Confidence:** HIGH

**Evidence:**
- GH #643 open 4 days: appointment_briefs.py missing block_demo_role + plan gate + ai_usage_guard
- autopilot loop stalled (Step 9D, GH #399) — issue cannot self-resolve
- nightly-2026-08-11 commented on #643 noting loop is broken, but no implementation guidance given
- File is `backend/routers/appointment_briefs.py` (path needs confirmation)

**Action:** Post a GitHub comment on #643 with exact diff needed: import statement + dependencies=[] argument + ai_usage_guard call pattern (with line references from billing.py:33 canonical).

**Note:** Superseded by Idea 1 — if `route-security-guard-audit` SKILL.md is written, it becomes the implementation guide and can be pointed to from #643.

---

## Idea 5: Add 5-file standard pattern to `feature-build` SKILL.md
**Category:** workflow
**Effort:** XS (doc addition)
**Confidence:** MEDIUM

**Evidence:**
- `docs/skill-discovery/2026-08-10.md` proposes adding canonical 5-file set to feature-build
- Both e0e9be6 (Nexlify Score: 3 services + 3 routers + 4 tests) and 4853c31 (appointment briefs: 1 router + 1 test + 1 page) follow the same pattern
- Without the named pattern, developers infer the file set from examples each time

**Action:** Add "Standard 5-file set" block to feature-build SKILL.md Pre-Build Checklist section:
- backend/routers/<feature>.py
- backend/services/<feature>.py
- backend/tests/test_<feature>.py
- frontend/src/pages/<Feature>.jsx
- frontend/src/utils/api/<feature>.js
- Plus: name missing files explicitly in commit message for backend-only or frontend-only features.

**Why weaker than Ideas 1-2:** Skill-discovery labeled it as "Existing Skill Update" not a new skill — less impact than route-security-guard-audit which prevents security regressions.
