# Ideas — 2026-06-21-pm (Run 65)

## Context

RUN 65 MANDATE fires: GH #292/#293 confirmed unimplemented (sms_rate_limiter._UNLIMITED_PLANS line 10, api_key_auth._ALLOWED_PLANS line 29, billing_reconciliation._PLAN_AGENT_RUN_CAPS all missing chatbot/agent_os). Per run 64 winning-concept.md §RUN 65 MANDATE → winner switches back to GH #308.

New evidence this run: b3279b0 (today, Jun 21) fixed 7 failing tests from stale plan names in test_admin_analytics_mrr.py. The MRR test file asserted against retired names (growth/autopilot/professional/enterprise) while the product has pivoted to chatbot/agent_os 2-tier. This confirms plan-name drift is active across the codebase — not just the 3 target files for #292/#293. check_project_invariants.py PASSES but its plan-name check only validates ABSENCE of retired names, not PRESENCE of new names.

Both GH #308 and GH #292/#293 have now been alternating as winner/bonus for 7 consecutive cycles with zero implementation. Alternating mandate mechanism has not produced resolution.

---

### Idea 1: Combine GH #308 + GH #292/#293 into one "Fix Two Production Bugs" PR

**Evidence:** Both bugs have alternated as winner/bonus for 7 cycles (runs 59-65) without implementation. b3279b0 (today) fixed 7 stale-plan-name test failures in ONE commit across 2 files — proves "batch fix" is viable and delivers. GH #308 = payment recovery failure (idempotency.py missing delete_key, ~10 lines). GH #292/#293 = every new paid signup since Jun 16 gets wrong SMS limits and cannot use Zapier API keys (~10 lines across 3 files). Combined = ~25 lines, 5 files, ONE PR approval resolves both.

**Action:** Open one branch `fix/two-production-bugs`. File 1: add `async def delete_key(supabase, key)` to idempotency.py; call `await delete_key(db, idempotency_key)` in stripe_webhooks.py exception handler before re-raise. Files 2-4: add chatbot+agent_os to sms_rate_limiter._UNLIMITED_PLANS, api_key_auth._ALLOWED_PLANS, billing_reconciliation._PLAN_AGENT_RUN_CAPS/_PLAN_BASELINE_AI_TOKENS. File 5: regression test for both. One PR, one approval.

**Impact:** Exits the 7-cycle alternating mandate loop. Zero new paid signups blocked from SMS/Zapier. Payment recovery works after card-fix dunning. Activation energy: one PR review instead of two.

**Category:** code_health

---

### Idea 2: Fix GH #308 alone — Webhook Idempotency delete_key (mandate winner)

**Evidence:** Mandate fires: GH #292/#293 unimplemented → GH #308 is designated winner per run 64. idempotency.py has no delete_key method (direct grep confirms). stripe_webhooks.py:110 records idempotency row AFTER handler on success (line 110) but no cleanup on exception — Stripe retry short-circuits with is_new=False → returns 200 → event dropped. Introduced by 47c7f8b (launch hardening, Jun 16). 7th consecutive cycle.

**Action:** Add `async def delete_key(supabase, key): supabase.table("webhook_idempotency").delete().eq("key", key).execute()` to idempotency.py. In stripe_webhooks.py exception handler: `await delete_key(db, idempotency_key)` before re-raising HTTPException(500). Regression test must FAIL on HEAD, PASS after fix.

**Impact:** Payment recovery restored — dunning-lock after card fix no longer drops the retry event. Revenue impact: every failed-then-fixed payment that hasn't been manually recovered.

**Category:** code_health

---

### Idea 3: Add plan-name presence guard to check_project_invariants.py (Check 7) — AUTONOMOUS-EXECUTABLE after GH #292/#293

**Evidence:** b3279b0 (today) proves plan-name drift: test_admin_analytics_mrr.py had 5 failures from stale plan names. check_project_invariants.py PASSES on "retired plan names do not appear" but does NOT check that NEW plan names (chatbot, agent_os) ARE present in the plan-gating dicts. Scope gap: sms_rate_limiter.py, api_key_auth.py, billing_reconciliation.py have drifted without triggering the invariant. parking_lot candidate since run 61 (labeled Bonus B).

**Action:** After GH #292/#293 lands, add Check 7 to check_project_invariants.py: assert "chatbot" in sms_rate_limiter._UNLIMITED_PLANS AND "agent_os" in api_key_auth._ALLOWED_PLANS. If either missing, EXIT 1. This prevents the next repricing from silently omitting new plan names from the 3 gating dicts.

**Impact:** Eliminates future GH #292/#293-class bugs at every commit. Every future repricing/rename caught at pre-commit, not production.

**Category:** code_health (AUTONOMOUS-EXECUTABLE after #292/#293)

---

### Idea 4: Fix kb-autopopulate.sh — 46-day stale KB

**Evidence:** Last KB compile 2026-05-05 (46 days stale per run 64 memory). kb-autopopulate.sh fails silently — likely curl or python error causes early exit. KB contains 110+ articles; 46 days without compile means recent Stripe billing changes, leadgen pipeline patterns, AI legal developments absent from KB context. ROI 1.8 (parking lot run 60+).

**Action:** Read kb-autopopulate.sh, diagnose failure mode (likely missing API endpoint or env var). Fix: add `|| true` to non-critical steps, or replace broken curl call with working alternative. Test: run manually, confirm article count increases.

**Impact:** KB re-current, LLM council / /kb-query answers stop being 46 days stale. Low-priority vs active product bugs.

**Category:** operational

---

### Idea 5: Post-repricing audit — scan all plan-gating code for chatbot/agent_os gaps beyond the 3 known files

**Evidence:** b3279b0 found drift in test_admin_analytics_mrr.py. Governance runs 60-64 identified only 3 files (sms_rate_limiter, api_key_auth, billing_reconciliation). But the 2-plan repricing on Jun 16 (9bed342/PR #288) touched multiple constants. Other potential gaps: usage_meter.py PLAN caps, plan_gate.py, stripe_service.PLAN_PRICES, managed_agents_registry.py agent-tier mapping. A broader grep could surface additional omissions.

**Action:** grep -r "growth\|autopilot\|professional\|enterprise" backend/ --include="*.py" | grep -v test | grep -v migration | grep -v __pycache__ — review each hit for plan-gating context. Flag any dict/set that should include chatbot/agent_os but doesn't.

**Impact:** Surfaces the full blast radius of the repricing gap before fixing GH #292/#293, so the PR can be comprehensive instead of piecemeal.

**Category:** code_health
