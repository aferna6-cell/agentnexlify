# Debate Log — Run 58 — 2026-06-16

Top 3 ideas by impact: Idea 1 (Check 13 wire), Idea 2 (RequirePaid E2E), Idea 3 (JWT stale claims).

---

## Idea 1: Wire check_project_invariants.py into pre-commit as Check 13

### Round 1
**Challenge:** This has been recommended in some form since run 8 (2026-04-25) — 46 days ago — and it's never been implemented. What's different this time? The mechanism has failed repeatedly despite AUTONOMOUS-EXECUTABLE labels.

**Defend:** The actual blocker history is traceable:
- Runs 8-43: em-dash violations in JSX blocked check_project_invariants from passing (it would fire false positives). Fixed in 3234597.
- Runs 44-57: Various attempts to fix invariants + scope — all resolved by 3234597.
- Today: check_project_invariants.py exits 0 on clean state. Zero false positives. This is the first time this has been true since the script was created.

The mechanism is proven: Check 11 (061582c, autonomous nightly, 22-line bash) and Check 12 (ca3ce68, autonomous nightly, 20-line bash) both landed without human intervention. Same execution path.

### Round 2
**Challenge:** Does wrapping check_project_invariants in pre-commit add value beyond Check 2 (from __future__) which already exists? Pre-commit already has 12 checks.

**Defend:** check_project_invariants.py covers 6 distinct invariant classes, only one of which overlaps with Check 2:
1. Retired live-schema fields (`tenant_id`, `lead_stage`, `service_interest`) — not in any existing check
2. Retired plan names (`foundation`, `operations`) — not in any existing check
3. Widget byte-identical across 3 mirrors — not in any existing check  
4. em-dash in website copy (JSX/frontend) — not in any existing check
5. from __future__ in FastAPI files — overlaps with Check 2 (belt+suspenders fine)
6. Direct Anthropic SDK calls bypassing runtime wrapper — not in any existing check

Five of six are unguarded at pre-commit. The launch sprint added pay_gate.py, billing_usage.py, billing.py, etc. — any of these could slip in a retired plan name or a direct SDK call without Check 13 catching it.

### Round 3
**Challenge:** Adding a Python subprocess to pre-commit adds latency to every commit. Is that worth it?

**Defend:** check_project_invariants.py is stdlib-only, no imports, ~100ms runtime. Check 2 already runs grep over all Python files in a bash loop — check_project_invariants is faster than that. Pre-commit latency is not a practical concern.

**Verdict: SURVIVES → WINNER**

---

## Idea 2: E2E integration test for RequirePaid.jsx payment gate

### Round 1
**Challenge:** E2E tests require the full app running (Playwright + backend + frontend). Is Playwright infrastructure confirmed working in this repo?

**Defend:** Yes — e2e/ directory has multiple spec files (onboarding-wizard.spec.ts, demo-smoke.spec.ts). .github/workflows/pr-check.yml already runs E2E. The infrastructure exists. The test would be additive.

### Round 2
**Challenge:** RequirePaid.jsx has 14 backend + 68 frontend unit tests. The unit tests cover the exemption logic, plan-check logic, and rendering states. Is an E2E test the highest-leverage addition right now, during an active launch sprint?

**Defend:** Unit tests test the component in isolation. They can't catch integration failures like: backend returns wrong plan_name → frontend doesn't recognize it → RequirePaid blocks a paying tenant. An E2E test that hits a real endpoint catches that class of bug. Given that RequirePaid wraps ALL routes (~6 route groups), a false-lock is a P0 customer issue.

### Round 3
**Challenge:** Writing E2E Playwright tests for authentication/payment flows requires test fixtures with fake Stripe events or mocked payment state. This is M-effort (2+ hours), not S-effort. Moratorium protocol prioritizes S-effort items. WEAKENED.

**Defend:** Could write smoke-level E2E — login as tenant with is_pay_gate_exempt=True from existing test fixtures, verify dashboard loads. That's 30 min. But the full 4-scenario coverage is M-effort.

**Verdict: WEAKENED → parking lot. Smoke-level E2E is valid but narrower than full 4-scenario coverage. Not chosen as winner due to M-effort classification during moratorium.**

---

## Idea 3: Fix JWT stale plan claims (M3 from launch audit)

### Round 1
**Challenge:** The launch audit explicitly labeled M3 as "deferred — touch hot paths, warrant a dedicated unrushed change." If the domain experts who wrote the audit decided to defer it, why should the subconscious override that judgment?

**Defend:** The audit deferred M3 for two specific reasons: (a) per-request DB read on auth hot path (perf) and (b) backward-compat risk of mass logout. These are legitimate concerns, but they're engineering tradeoffs, not blockers. A bounded fix — only re-validate on billing-related routes — avoids hot-path cost while closing the billing tier window.

### Round 2
**Challenge:** How large is the actual exposure? The two new plans (chatbot $19.99, agent_os $99.99) use different Stripe product IDs. A tenant upgrading triggers a Stripe webhook that updates the DB immediately. The JWT claim drifts up to 24h — but the ai_usage_guard reads from DB directly or from the DB-backed plan gate? Let me think: if ai_usage_guard.py reads settings from DB on every AI call, the JWT plan claim isn't what governs usage. The JWT might only affect UI gating.

**Defend:** If ai_usage_guard.py reads DB directly, M3's practical risk is limited to UI display showing wrong plan name for up to 24h — not a billing error, just confusing UX. The audit's deferral judgment is probably correct for the actual risk magnitude.

### Round 3
**Challenge:** Even if M3 is a real risk, fixing it requires: (a) understanding the full JWT validation path, (b) a DB migration or token versioning schema, (c) careful backward-compat testing. This is M-L effort and the domain experts deferred it. The subconscious should not override a deliberate engineering deferral with a recommendation that could cause mass logout.

**Verdict: KILLED — deliberate audit deferral + non-trivial scope + launch sprint timing. Not moratorium-friendly. Domain experts made the right call.**

---

## Summary
- Idea 1: SURVIVES → WINNER
- Idea 2: WEAKENED → parking lot (smoke E2E is valid future work)
- Idea 3: KILLED (deliberate deferral, M-L effort, correct engineering judgment)
