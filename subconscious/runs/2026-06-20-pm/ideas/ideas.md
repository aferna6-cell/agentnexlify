# Ideas — Subconscious Run 2026-06-20-pm (Run 64)

**Evidence base:** git log 3 days, nightly-commit-review 2026-06-20, idempotency.py grep, sms_rate_limiter.py grep, api_key_auth.py grep, billing_reconciliation.py grep, governance.json mandates.

---

### Idea 1: Fix GH #292/#293 — Wire chatbot/agent_os into plan-name dicts

**Evidence:**
- Run 64 mandate fires: GH #308 still unimplemented per nightly 2026-06-20 and direct idempotency.py grep (no `delete_key`). Governance protocol: alternating mandate, switch back to GH #292/#293.
- Direct grep confirms all 3 files still unpatched:
  - `sms_rate_limiter._UNLIMITED_PLANS` line 10: `{"growth","professional","autopilot","enterprise"}` — chatbot/agent_os absent
  - `api_key_auth._ALLOWED_PLANS`: grep returns empty output — chatbot/agent_os absent
  - `billing_reconciliation._PLAN_AGENT_RUN_CAPS`: grep returns empty output — chatbot/agent_os absent
- All new paid tenants since repricing 2026-06-16 get wrong SMS limits and cannot use Zapier API keys.
- Full sketch exists: `subconscious/runs/2026-06-19-pm/winning-concept.md`

**Action:** Fix `sms_rate_limiter._UNLIMITED_PLANS` + `api_key_auth._ALLOWED_PLANS` + `billing_reconciliation._PLAN_AGENT_RUN_CAPS/_PLAN_BASELINE_AI_TOKENS` to include chatbot and agent_os. Confirm chatbot SMS limit with product before merge.

**Impact:** All new paid tenants get correct SMS/Zapier access. Closes GH #292/#293. Unblocks plan-name guard Check 7 (Bonus B, AUTONOMOUS-EXECUTABLE).

**Category:** code_health

---

### Idea 2: Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events

**Evidence:**
- `backend/services/idempotency.py` grep confirms no `delete_key` method exists (6th consecutive confirmation).
- Nightly 2026-06-20 explicitly flags as "DAY 4, 5th cycle — Cannot auto-fix: touches Stripe payment handling."
- `check_and_record()` writes idempotency row BEFORE handler completes. Handler failure → row persists → Stripe retry returns 200 without processing → payment event permanently dropped.
- Introduced by 47c7f8b (2026-06-16). Tenants who fix payment card stay dunning-locked.

**Action:** Add `async def delete_key(supabase, key)` to `idempotency.py`. In `stripe_webhooks.py` exception handler call `await delete_key(db, idempotency_key)` before re-raising.

**Impact:** Payment recovery restored for dunning-locked tenants. Direct revenue impact.

**Category:** code_health

---

### Idea 3: Fix kb-autopopulate.sh — Restore 46-Day Stale KB

**Evidence:**
- Parking lot since run 54, ROI 1.8.
- `scripts/daily/kb-autopopulate.sh` uses `agent-browser` CLI which is not installed in this environment.
- KB stale 46+ days (last compiled 2026-05-05 per governance.json).
- Twice-daily auto-populate was the design; it has been silent for 46 days.
- No active bug filed but CLAUDE.md references `scripts/daily/kb-autopopulate.sh` as the canonical automation path.

**Action:** Update `scripts/daily/kb-autopopulate.sh` to replace `agent-browser` CLI calls with `curl` or WebFetch, or add `|| true` silent fallback. Re-verify script runs without error.

**Impact:** Restores twice-daily KB auto-population. KB freshness is a developer workflow multiplier.

**Category:** operational

---

### Idea 4: Add New-Table Checklist to schema-discipline.md

**Evidence:**
- Parking lot since run 54, ROI 2.0.
- 3 occurrences of `_TENANT_COLUMN_OVERRIDES` miss on new tables (os_graph_nodes, os_graph_edges, third via c6805a5 fix).
- `schema-discipline.md` is path-scoped to `backend/**/*.py` — auto-loads in backend sessions.
- 14+ god-class split targets remain in the backlog; each creates new tables.

**Action:** Append 5-question "New Table Checklist" to `.claude/rules/schema-discipline.md`: (1) table has RLS policy, (2) table has `client_id` column, (3) `_TENANT_COLUMN_OVERRIDES` updated, (4) migration numbered sequentially, (5) schema-log.md updated.

**Impact:** Prevents tenant isolation gaps on new tables. Applies to all future god-class splits and new services.

**Category:** workflow / code_health

---

### Idea 5: Add Cross-Tenant Isolation Test for os_graph_memory.py

**Evidence:**
- Parking lot since run 54, ROI 2.1.
- `os_graph_memory.py` (397L) has 284 mock-based tests (migration 133) but none verify client_id=A cannot read nodes from client_id=B.
- Agent OS knowledge graph (`os_graph.py`, `os_graph_memory.py`) stores per-tenant context. Cross-tenant leak would expose business data.
- No active exploit but no test safety net either.

**Action:** Add 2 tests to `backend/tests/test_os_graph_memory.py`: `accumulate_from_turn(client_id="A")` then `graph_kb_entries(client_id="B")` → empty result.

**Impact:** Detects tenant data leakage in Agent OS knowledge graph before it reaches production.

**Category:** code_health
