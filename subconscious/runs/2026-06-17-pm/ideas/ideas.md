# Ideation — Run 2026-06-17-pm

## Evidence Summary

**What changed (last 3 days):**
Check 13 (project invariants gate) wired by nightly review bc91e97 — run 58 winner implemented. Nine feature PRs merged (PRs #311-320): Conversation Insights (sentiment+intent, migration 154), Instant KB from URL in onboarding, Lead Alerts extraction, Usage Upgrade Nudge, Front Desk Health card, Outbound Outreach agent, brand repositioning to "AI Workforce" framing, 2-plan repricing ($19.99 chatbot / $99.99 agent_os).

**What broke:**
- GH #308: Webhook idempotency early-write drops payment events — tenant stays dunning-locked after card fix
- GH #292/#293: sms_rate_limiter, api_key_auth, orchestrator.py, billing_reconciliation.py all missing new plan names (chatbot/agent_os) — new paid tenants get SMS hard-capped at 50/day, Zapier returns 402, branded email skipped
- GH #263 (CRITICAL): 24 pending migrations unsynced

**What's working:**
check_project_invariants.py passes all 6 checks. New services (conversation_enrichment.py, lead_alerts.py, instant_kb.py) all have test files.

**What's missing:**
AI-to-Human Handoff (62+ days, Critical gap). email_sequences.py still 1143L. React 18→19 PRs unreviewed. KB stale (agent-browser CLI not installed).

---

## Candidate Ideas

### Idea 1: Fix GH #308 — Webhook Idempotency Early-Write
**Evidence:** Introduced by 47c7f8b (launch hardening, 2026-06-16). `idempotency.py:85-93` writes idempotency row BEFORE handler completes. Handler failure → row exists → Stripe retry sees `is_new=False` → returns 200 without processing → event permanently dropped. Morning digest marks this #1 priority. Confirmed by nightly-commit-review 2026-06-17 (GH #308 filed).
**Action:** Wrap handler call in try/except in `billing.py:233-236` + `stripe_webhooks.py:64-66`; delete idempotency row on exception before re-raising 500. Add regression test seeding a handler-throw scenario and asserting Stripe retry processes the event.
**Impact:** Prevents tenants staying dunning-locked after card recovery. Payment recovery is load-bearing for retention.
**Category:** code_health

### Idea 2: Fix GH #292 + #293 — Wire chatbot/agent_os into 4 Plan-Name Dicts
**Evidence:** Repricing sprint (PRs #285-295) introduced `chatbot`/`agent_os` as the new canonical plan names. Four files missed the update: `sms_rate_limiter.py:10` (chatbot tenants hit 50 SMS/day floor), `api_key_auth.py:29` (chatbot/agent_os get 402 on Zapier page), `orchestrator.py:238/319` (agent_os tenants never get branded email), `billing_reconciliation.py:35-49` (caps report wrong for both plans). Morning digest marks this #2 priority.
**Action:** Add chatbot/agent_os entries to the 4 plan-name dicts. Requires product decision: SMS limits for chatbot? Zapier on both plans or agent_os-only?
**Impact:** Unblocks paid-signup funnel — every new chatbot/agent_os tenant currently has broken SMS, Zapier, and email flows.
**Category:** code_health

### Idea 3: Add Plan-Name Guard to check_project_invariants.py (Systemic Prevention)
**Evidence:** Repricing missed 4 files immediately (GH #292/#293). check_project_invariants.py already guards retired plan names — adding a forward-looking check for current plan names (chatbot, agent_os) would catch this at commit time. Check 13 now live (bc91e97), so the guard fires at every commit. Evidence from runs 55-58: plan-name drift is a repeating class (billing runs 30-34 were all plan name bugs).
**Action:** Add check 7 to `scripts/check_project_invariants.py`: scan `sms_rate_limiter.py`, `api_key_auth.py`, `billing_reconciliation.py` for current plan names. FAIL if any missing. AUTONOMOUS-EXECUTABLE. Must wait until GH #292/#293 fixes land first.
**Impact:** Prevents every future plan repricing from breaking 4 services silently. Self-healing: guards what Check 13 now enforces.
**Category:** code_health

### Idea 4: Cross-Tenant Isolation Test for conversation_enrichment.py
**Evidence:** 93d9b85 (PR #315) ships `conversation_enrichment.py` (197L) storing sentiment + intent from conversations. This is new PII-adjacent data (intent signals reveal business relationships). `test_conversation_enrichment.py` exists but the run 54 parking lot flagged cross-tenant isolation tests as ROI 2.1 for new Agent OS services. Pattern: os_graph_memory.py had same gap; no test verifies client_id=A cannot return enrichment data for client_id=B.
**Action:** Add 2 mock-based cross-tenant tests: enrich_conversation(client_id=A), then query enrichment(client_id=B) → empty result. AUTONOMOUS-EXECUTABLE.
**Impact:** Closes a PII isolation gap before any tenant data accumulates in the enrichment store.
**Category:** code_health

### Idea 5: email_sequences.py God-Class Split
**Evidence:** Still 1143L (down from 1255L). Active direction run 41 (28+ days). GH #112/#113 N+1 queries unlocked post-split. god-class-splitter SKILL.md ready. post-split-test-repair SKILL.md ready. Check 13 now live prevents invariant drift during split.
**Action:** Invoke /god-class-splitter on email_sequences.py → email_crud + email_enrollment + email_processor.
**Impact:** Unlocks N+1 query fix, reduces blast radius on email automation bugs, closes 28-day active direction.
**Category:** code_health

---

## Ranking (for debate)

1. Idea 1 — Fix GH #308 (HIGHEST urgency, clear fix, no decision needed)
2. Idea 2 — Fix GH #292/#293 (active breakage but requires product decision)
3. Idea 3 — Plan-name guard (systemic but sequencing-dependent on Idea 2)
