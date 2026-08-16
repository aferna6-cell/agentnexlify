# Ideas — Run 107 (2026-08-16-pm)

## Idea 1: Fix scoring_config.py missing block_demo_role
**Evidence:** GH #661 filed by nightly-2026-08-16 (2026-08-16). `backend/routers/scoring_config.py` — 4 mutating endpoints (PUT, POST, DELETE, POST /reset) lack `block_demo_role`. Same class as appointment_briefs.py (GH #643), which run 106 fixed. route-security-guard-audit SKILL.md (commit 60d132f) written this cycle to guide exactly this type of fix. Demo tenants can create/modify/delete scoring factors and reset to defaults — real data integrity hole.
**Action:** Add `block_demo_role` import and router-level `dependencies=[Depends(block_demo_role)]` to `backend/routers/scoring_config.py`, following the pattern in appointment_briefs.py.
**Impact:** Closes GH #661. Demo tenants can no longer corrupt scoring configuration. Eliminates one confirmed attack surface from the security backlog.
**Category:** code_health

## Idea 2: Update ops/credential-rotation-schedule.md AUTOPILOT_GH_TOKEN threshold from 76d to 45d
**Evidence:** Run 106 Bonus B changed Step 9E alert threshold in `.claude/skills/nightly-commit-review/SKILL.md` from 76d to 45d. `ops/credential-rotation-schedule.md` AUTOPILOT_GH_TOKEN row still documents ">=76 days" threshold in the comment field. AUTOPILOT_GH_TOKEN is now 38+ days expired (GH #399). At 45d it crosses the new threshold — 7 days from now. If the schedule doc and the SKILL.md disagree, the nightly review will alert at 45d but the ops doc will still say 76d, creating confusion about when action was expected.
**Action:** In `ops/credential-rotation-schedule.md`, update AUTOPILOT_GH_TOKEN row comment from ">=76 days" to ">=45 days". Single line change.
**Impact:** Ops doc matches SKILL.md. No ambiguity about when Step 9E fires. Consistent escalation path when token expires.
**Category:** operational

## Idea 3: Step 9I nightly paying-tenant zero-conversation alert
**Evidence:** Parking lot since run 104 (two cycles). Customer gap: tenants on paid plans who haven't had a chat conversation in 14+ days are churn risks. The nightly-commit-review SKILL.md has steps 9A through 9H; Step 9I (paying tenant engagement check) was proposed in run 104 and placed in parking lot for later consideration. No implementation exists. Churn prevention is a revenue-critical gap.
**Action:** Add Step 9I to nightly-commit-review SKILL.md: query Supabase for tenants on `chatbot` or `agent_os` plan with zero conversations in last 14 days, surface as MEDIUM finding with churn_risk label.
**Impact:** Proactive churn signal. Catches at-risk paid tenants before they lapse.
**Category:** customer_value

## Idea 4: ai_usage_guard in appointment_briefs.py service layer
**Evidence:** Run 106 deferred ai_usage_guard for appointment_briefs.py because `reserve_ai_tokens()` requires a full tenant dict which wasn't available at router level. The dependency is present in other routers — `backend/services/ai_usage_guard.py` exposes `reserve_ai_tokens(tenant, tokens)`. appointment_briefs.py already has the tenant from `_get_current_tenant()`. The guard prevents AI token budget exhaustion per tenant. Run 106 comment in appointment_briefs.py: "ai_usage_guard deferred — requires reserve_ai_tokens() with full tenant dict."
**Action:** Add `reserve_ai_tokens()` call in appointment_briefs.py at the point before AI processing, pattern-matching existing guarded routers.
**Impact:** Prevents AI budget overrun per tenant on appointment AI features. Consistent guard coverage across routers.
**Category:** code_health

## Idea 5: Step 9H v2 — idempotent subconscious PR pile alerter
**Evidence:** PR #653 (`subconscious/run-103` branch) has been draft for 12+ days. Subconscious PR dedup guard (added 2026-07-20 in SKILL.md) was installed after run 99 opened 4 duplicate draft PRs. The dedup guard works — run 107 correctly found the existing PR. But the guard doesn't alert the owner when a subconscious PR has been open for an extended period without merge. Result: subconscious work accumulates on a branch the owner hasn't reviewed.
**Action:** Add Step 9H v2 to nightly-commit-review SKILL.md: check for open subconscious/* draft PRs older than 7 days; surface as LOW finding with link and age.
**Impact:** Owner gets notified when subconscious work needs attention. Prevents stale PR pile-up.
**Category:** workflow
