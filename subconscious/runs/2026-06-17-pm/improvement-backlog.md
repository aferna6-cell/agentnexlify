# Improvement Backlog — Run 2026-06-17-pm

Items surfaced this run but not selected as winner. Persisted for future runs.

---

## Parking Lot Additions

### Idea 4: Cross-Tenant Isolation Test for conversation_enrichment.py
- **Date added:** 2026-06-17-pm
- **ROI:** 2.1 (same class as os_graph_memory isolation test, run 54)
- **Autonomous-executable:** YES
- **Note:** PR #315 (93d9b85) shipped `conversation_enrichment.py` (197L) storing sentiment + intent — PII-adjacent. `test_conversation_enrichment.py` exists but no test verifies client_id=A cannot return enrichment for client_id=B. Add 2 mock-based cross-tenant tests. Can be implemented by nightly review immediately. Promoted to parking lot alongside existing os_graph_memory isolation test (run 54, same note).

---

## Active Directions Carried Forward

### Idea 2 (Bonus A): Fix GH #292/#293 — Wire chatbot/agent_os into 4 plan-name dicts
- **Status:** pending_approval (requires product decision on SMS tier)
- **Product decision needed:** chatbot SMS limit (propose 200/day), agent_os SMS limit (propose 500/day), Zapier on both plans or agent_os-only (propose: both)
- **Files:** sms_rate_limiter.py:10, api_key_auth.py:29, orchestrator.py:238/319, billing_reconciliation.py:35-49
- **Implementation path:** human sprint or interactive session, ~30 min

### Idea 3 (Bonus B): Plan-name guard in check_project_invariants.py
- **Status:** sequencing-dependent on Idea 2 / Bonus A
- **Autonomous-executable:** YES (after Bonus A lands)
- **Action:** Add check 7 to scripts/check_project_invariants.py — scan 4 files for current plan names, FAIL if missing
- **Note:** Prevents next repricing from silently breaking same 4 files

### email_sequences.py god-class split (run 41, day 28+)
- **Status:** active direction, still pending
- **Note:** 1143L. god-class-splitter SKILL.md ready. post-split-test-repair SKILL.md ready. Check 13 now live prevents invariant drift during split. Blocking: GH #112/#113 N+1 queries.
- **Unblocked when:** human sprint, M-effort

### AI-to-Human Handoff v1 (run 4, day 62+)
- **Status:** active direction, still pending (longest-running open item)
- **Category:** customer_value
- **Note:** Critical gap — complex queries never escalate to human. GoHighLevel has this. Our moat depends on it.

---

## Items Confirmed Implemented (this run's evidence)

- **Run 58 winner (Check 13 gate):** IMPLEMENTED — nightly review bc91e97 wired `check_project_invariants.py` into pre-commit as Check 13 at lines 290-291 of `scripts/hooks/pre-commit`.
- **Run 57 winner (widget sync fix):** IMPLEMENTED — confirmed via 3234597.
- **Run 55 winner (em-dash + __future__ fixes):** IMPLEMENTED — confirmed via 3234597.
