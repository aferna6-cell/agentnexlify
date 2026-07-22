# Run 100 — Ideas Generated 2026-07-22

## Evidence base
- Architecture audit: `audits/audit-architecture-2026-07-22.md` (fresh, run today)
- Nightly review: `docs/dev-knowledge/nightly-reviews/2026-07-22.md` (18 commits, guardrail tripped)
- Governance mandate items: `subconscious/state/governance.json` → `run_100_mandate`
- Customer gaps: `docs/dev-knowledge/customer-gaps.md`
- Bug patterns: `docs/dev-knowledge/bug-patterns.md`

---

## Idea 1 — Fix Agent OS plan gate coverage gap (H1) ★ WINNER
**Category:** code_health / security  
**Evidence:** Audit H1: 10 of 21 `os_*` routers lack `require_agent_os_access` dependency.  
**Ungated routers:** `os_agent_runs`, `os_backlog`, `os_files`, `os_graph`, `os_insights`, `os_memory`, `os_run_trace`, `os_sync`, `os_usage`, `os_usage_breakdown`  
**Impact:** `chatbot`-plan ($19.99/mo) tenants silently access `agent_os` ($99.99/mo) features. Revenue leak + tier integrity violation.  
**Recommendation:** File GH issue listing all 10 ungated routers + required test coverage in `test_plan_gating_new_plans.py`. Effort M.

---

## Idea 2 — File GH issue: SUPABASE_ACCESS_TOKEN never set ★ PARKING LOT
**Category:** operational  
**Evidence:** Nightly review Step 9E: `last_rotated = "unknown — not yet set"`. Brain connector supabase permanently skipped in every INGESTION-LOG.md entry. INGESTION-LOG consistently shows "skipped — SUPABASE_ACCESS_TOKEN not set".  
**Impact:** Supabase brain connector dead. Memory sync for DB schema, live data patterns, and tenant signals never runs.  
**Recommendation:** File GH issue: "Set SUPABASE_ACCESS_TOKEN in GitHub Actions secrets — brain connector supabase permanently blocked."

---

## Idea 3 — Zapier plan_status verification gap ✗ KILLED
**Category:** code_health  
**Evidence (initial):** Zapier auth test in `zapier/authentication.js` calls `/api/zapier/leads/new` — potentially bypasses plan gate.  
**Kill reason:** On inspection, `zapier/authentication.js:14` inline comment explicitly states "a Free/cancelled tenant returns 402" confirming backend already enforces plan_status on this path. Bug #107 (2026-06-13) already fixed this. No gap exists.

---

## Idea 4 — Add Step 9G: Drive KB health to nightly review ★ PARKING LOT
**Category:** workflow_efficiency  
**Evidence:** Three new Drive KB routers shipped (d6897df, 9d3cfa2). No nightly health monitoring step exists. Pattern established by Step 9F (KB autopopulate staleness) in run 99.  
**Recommendation:** Add Step 9G to nightly-commit-review SKILL.md: check `drive_kb_configs` for tenants with `sync_enabled=true`, verify last sync timestamp, escalate if >48h stale.

---

## Idea 5 — Extract mock DB helpers to shared test fixture
**Category:** code_health  
**Evidence:** Audit M1: mock DB helpers copy-pasted 4× across route test suites (`test_routes_*.py`). Drifting — 3 suites pass `mock_db.client_id`, 1 passes `mock_db.tenant_id` (invariant violation risk).  
**Recommendation:** Create `backend/tests/conftest.py` shared fixture `mock_supabase_client` with canonical field names (`client_id`). Replace 4 copy-paste blocks. Effort S.
