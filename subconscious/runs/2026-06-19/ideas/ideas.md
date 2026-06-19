# Ideas — 2026-06-19 (Run 61)

## Evidence Digest

14 commits in 3 days: leadgen pipeline expanded (OSM source 371L, merge_leads.py 171L,
enrich.py SSRF hardening), security consolidation, onboarding activation improvements,
CI cron throttling. Active product velocity. No new check_project_invariants failures.

GH #308 (idempotency early-write drops payment events): 3rd consecutive carry-over.
`delete_key` absent from idempotency.py confirmed by grep. Nightly 2026-06-19 ran (6310848)
but no implementation commit — nightly_review_path = true, autonomous_executable = false.

GH #292/#293: chatbot/agent_os absent from sms_rate_limiter.py (37L) + billing_reconciliation.py
(294L). Every new paid tenant since 2026-06-16 repricing gets wrong SMS limits + cannot use Zapier.

Moratorium active, true pending ~9, GH #308 moratorium override still valid.

---

### Idea 1: Fix GH #308 — Webhook Idempotency Early-Write (3rd consecutive carry-over)
**Evidence:** grep confirms `delete_key` absent from idempotency.py. 3 runs carried (59/60/61).
47c7f8b (2026-06-16) introduced the bug. Nightly 2026-06-19 ran but did not implement
(non-autonomous). Full sketch in subconscious/runs/2026-06-18-pm/winning-concept.md.
**Action:** Add `delete_key()` to idempotency.py; call in stripe_webhooks.py exception
handler before re-raising; add regression test that FAILS on HEAD, PASSES after fix.
**Impact:** Fixes silent permanent payment event loss. Tenants who fix card stay dunning-locked.
**Category:** code_health

---

### Idea 2: Fix GH #292/#293 — Add chatbot/agent_os to Plan-Name Dicts
**Evidence:** grep confirms chatbot/agent_os absent from sms_rate_limiter.py AND
billing_reconciliation.py. 9bed342 (PR #288, 2026-06-16) repriced to 2-plan model but
missed 4 downstream consumer files. Bonus A in runs 59+60 never implemented.
**Action:** Add "chatbot" and "agent_os" to sms_rate_limiter._UNLIMITED_PLANS +
api_key_auth._ALLOWED_PLANS + billing_reconciliation plan caps. Proposed limits:
chatbot = 200/day SMS, agent_os = 500/day SMS. ~10 min, S-effort, 3 files.
**Impact:** Fixes broken experience for every new paid tenant since 2026-06-16.
**Category:** code_health

---

### Idea 3: Add Plan-Name Invariant Guard (check 7) to check_project_invariants.py
**Evidence:** Bonus B from runs 59+60, never implemented. 4 consumer files still missing
chatbot/agent_os. check_project_invariants.py has 6 checks currently. Prevents future
repricing from silently breaking downstream consumers.
**Action:** Add ~15 lines Python to check_project_invariants.py: scan sms_rate_limiter.py,
api_key_auth.py, billing_reconciliation.py for "chatbot" and "agent_os". FAIL if absent.
Sequencing: GH #292/#293 must land first (otherwise check immediately fails on install).
**Impact:** Systematic guard — prevents next repricing from reintroducing #292/#293 class.
**Category:** code_health / workflow

---

### Idea 4: Cross-Tenant Isolation Test for os_graph_memory
**Evidence:** Parking lot since run 54 (ROI 2.1). c8a0460 landed os_graph_memory.py (397L)
with 284 mock tests but NO cross-tenant test. RLS migration 133 exists but no app-level
safety net. Agent OS now customer-facing (PR #207 shipped, paying tenants on platform).
**Action:** Write 2 tests: accumulate_from_turn(client_id=A) then graph_kb_entries(client_id=B)
→ empty. ~30 min, M-effort. Tests in backend/tests/test_os_graph_memory_isolation.py.
**Impact:** Prevents cross-tenant data leak in Agent OS knowledge graph.
**Category:** code_health

---

### Idea 5: Add New-Table Checklist to schema-discipline.md
**Evidence:** Parking lot since run 54 (ROI 2.0). Third confirmed occurrence of
_TENANT_COLUMN_OVERRIDES miss (os_graph_nodes + os_graph_edges, c6805a5). 5-question
checklist append to .claude/rules/schema-discipline.md. Path-scoped to backend/**/*.py —
auto-loads in backend sessions. Same file class nightly successfully creates/edits.
**Action:** Append "New Table Checklist" (5 questions) to schema-discipline.md: 
Does new table have client_id? Is client_id in _TENANT_COLUMN_OVERRIDES? RLS migration?
**Impact:** Prevents next Agent OS service from silently missing tenant scoping.
**Category:** code_health
