# Ideas — 2026-06-21 (Run 65)

## Evidence Digest

5 commits in last 3 days — all ops/planning (subconscious runs, nightly log, morning digest). Zero code changes. Nightly 2026-06-20 triaged all 5 LOW. GH #308 and GH #292/#293 both confirmed unimplemented by direct grep and nightly log. Leadgen pipeline shipping actively (OSM source, merge_leads.py, CAN-SPAM footer, enrich.py). KB 46+ days stale (no compile since 2026-05-05). Run 65 mandate fires per run 64 winning-concept.md §RUN 65 MANDATE: GH #292/#293 still unimplemented → winner switches back to GH #308.

---

### Idea 1: Fix GH #308 — Webhook Idempotency Early-Write Drops Payment Events

**Evidence:** `delete_key()` absent from `backend/services/idempotency.py` (confirmed by grep, confirmed by direct file read today). `check_and_record()` inserts idempotency row BEFORE handler runs (line 44-52). Handler failure → row persists with `response_body=NULL` → Stripe retry sees `is_new=False` → returns 200 without processing → event permanently dropped. Nightly 2026-06-20 flags as HIGH. 7 consecutive subconscious cycles unimplemented (runs 59-65). Run 64 winning-concept.md §RUN 65 MANDATE explicitly designates this as run 65 winner.

**Action:** Add `async def delete_key(supabase, key: str) -> None` to `backend/services/idempotency.py`. In `backend/routers/stripe_webhooks.py` exception handler, call `await delete_key(db, idempotency_key)` before `raise HTTPException(500)`. Add regression test: test must FAIL on HEAD, PASS after fix.

**Impact:** Tenants who fix their payment card get un-dunned. Stripe retries succeed. Payment events no longer permanently dropped on handler exception. Eliminates dunning-lock false-positive.

**Category:** code_health

---

### Idea 2: Fix GH #292/#293 — Wire chatbot/agent_os into Plan-Name Dicts

**Evidence:** Direct grep today: `sms_rate_limiter._UNLIMITED_PLANS` (line 10) and `api_key_auth._ALLOWED_PLANS` (line 29) both missing `chatbot`/`agent_os`. `billing_reconciliation._PLAN_AGENT_RUN_CAPS` and `_PLAN_BASELINE_AI_TOKENS` also missing entries. Active product breakage since repricing 2026-06-16 — every new paid signup gets wrong SMS limits and cannot create Zapier API keys. 3 cycles as winner/Bonus A (runs 62, 63 Bonus A, 64 winner) without implementation.

**Action:** Add `chatbot` and `agent_os` to `_UNLIMITED_PLANS` in `backend/services/sms_rate_limiter.py`; add to `_ALLOWED_PLANS` in `backend/routers/api_key_auth.py`; add cap entries to `billing_reconciliation.py`. Bonus: add plan-name guard Check 7 to `check_project_invariants.py`.

**Impact:** All paid tenants signed up since repricing get correct SMS limits and working Zapier API keys.

**Category:** code_health

---

### Idea 3: Fix kb-autopopulate.sh — KB 46 Days Stale

**Evidence:** Run 53 identified root cause: `agent-browser` CLI not installed at `kb-autopopulate.sh` script path. KB not compiled since 2026-05-05 (46 days). Product has fundamentally repositioned since: 2-plan pricing ($19.99/$99.99), Agent OS, AI Workforce framing, Spanish widget. KB wiki still references retired 5-plan model. Widget AI responses use KB context — stale KB = AI cites retired plans.

**Action:** Check if `agent-browser` CLI installed (`which agent-browser`). If not, patch `kb-autopopulate.sh` to use `WebFetch` MCP or skip the CLI dependency. Run `bash scripts/daily/kb-autopopulate.sh` to compile. Alternatively, create a `kb-compile-fallback.sh` that uses `WebFetch` directly.

**Impact:** KB restored to current product state. AI widget responses reflect 2-plan pricing and Agent OS positioning. Customer confusion from stale plan references eliminated.

**Category:** operational

---

### Idea 4: AI-to-Human Handoff v1 — 66-Day Critical Gap

**Evidence:** `customer-gaps.md` — Critical rating, all 7 industries. `os_outbound_mirror.py` shipped by PR #188 (2026-05-27) with 152 tests handling SMS/email/Facebook delivery. Run 38 reframed scope from ~3 days → ~1 day via Agent OS infrastructure. 66 days pending (run 4, oldest active_direction).

**Action:** Detect "transfer to human" / "speak to someone" trigger phrases in `widget_chat.py`. Write to `handoff_requests` table (needs migration). Call `os_outbound_mirror.send_sms()` to notify owner. Return handoff confirmation message to customer.

**Impact:** Fills Critical gap across all verticals. Enables complex queries to route to human. First AI-to-human workflow for all tenants.

**Category:** customer_value

---

### Idea 5: Add _TENANT_COLUMN_OVERRIDES Checklist to schema-discipline.md + check_project_invariants.py

**Evidence:** 3 consecutive new-table misses of `_TENANT_COLUMN_OVERRIDES` config: `os_graph_nodes`, `os_graph_edges` (PR #208, run 54), `os_action_dispatch` (Phase 4, run 53). Each miss silently breaks multi-tenant isolation for the new table. Run 61 parking lot entry "schema-discipline new-table checklist." God-class-refactor plan has 14+ remaining splits — each will create new tables.

**Action:** Add "New Table Checklist" section to `.claude/rules/schema-discipline.md` listing 5 required steps for every new Supabase table: migration file, RLS policy, `_TENANT_COLUMN_OVERRIDES`, tenant-scoped query helper, test coverage. Add `check_project_invariants.py` check for known new tables (query information_schema against `_TENANT_COLUMN_OVERRIDES` registry).

**Impact:** Prevents silent multi-tenant isolation misses on future table sprints. Estimated 14+ future splits remaining — each currently unguarded.

**Category:** code_health
