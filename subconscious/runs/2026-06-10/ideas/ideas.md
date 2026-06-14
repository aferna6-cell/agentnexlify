# Ideas — Run 2026-06-10

## Evidence Digest

- **c6805a5 (2026-06-10)**: Nightly caught `os_graph_nodes`/`os_graph_edges` missing from `_TENANT_COLUMN_OVERRIDES` in `tenant_scope.py`. 3rd occurrence of "new table added, tenant scope override missed." Test suite passed because mocks ignore column names. Production would have failed at query time.
- **c8a0460 (2026-06-10)**: Agent OS knowledge graph landed — `os_graph_memory.py` (397L), `os_graph.py` (45L), `MemoryPanel.jsx` (190L), 284 mock-based tests, migration 133. **Re-introduced 3 em-dash violations** in `MemoryPanel.jsx:180` + `AgentOS.jsx:197/224`. `check_project_invariants.py` now exits 1, blocking Item A (Check 10) autonomous wire.
- **Run 53 winner IMPLEMENTED**: `test_os_action_dispatch.py` created by nightly c6805a5 (5 tests, queue_action_for_run coverage).
- **Billing still broken**: `billing.py` `AMOUNT_TO_PLAN` confirmed missing 15000→autopilot + 25000→professional. PR #183 17d pending, unmerged.
- **email_sequences.py** 1255L — run 41 winner, 30+ days pending.
- **check-widget-sync.sh** still MISSING — run 7/50, 46 days.

---

### Idea 1: Fix 3 JSX em-dash violations in c8a0460 UI copy

**Evidence:** `python3 scripts/check_project_invariants.py` exits 1 — `MemoryPanel.jsx:180`, `AgentOS.jsx:197`, `AgentOS.jsx:224` contain em dashes (—) introduced by c8a0460. Same class as run 49 winner (5 violations in 8db33df, fixed autonomously). Item A (check_project_invariants Check 10 wire) pre-condition requires exit 0.
**Action:** Replace 3 em dashes with hyphens in the affected JSX files. AUTONOMOUS-EXECUTABLE via nightly (8db33df precedent).
**Impact:** Restores check_project_invariants exit 0 → unblocks Item A autonomous wire tonight → Check 10 enters pre-commit → future em-dash violations caught at commit time (self-healing loop).
**Category:** code_health

---

### Idea 2: Add tenant scope registration checklist to schema-discipline.md

**Evidence:** c6805a5 today caught the 3rd occurrence of `_TENANT_COLUMN_OVERRIDES` miss for new tables. Pattern: new service → `tenant_table()` calls → missing override → production column-not-found error. Mock tests hide it. 13 existing entries; 3 tables have slipped through (os_graph_nodes, os_graph_edges + at least 1 prior). `schema-discipline.md` is path-scoped to `backend/**/*.py` — will auto-load when writing new service files.
**Action:** Append a "New Table Checklist" (5 questions) to `.claude/rules/schema-discipline.md` — specifically: "Does this table use `client_id` or `tenant_id`? Did you add it to `_TENANT_COLUMN_OVERRIDES`?" AUTONOMOUS-EXECUTABLE (rule file addition, same channel as prior SKILL.md adds).
**Impact:** Every Claude session creating a new Supabase table is prompted to register the column override. Prevents production tenant_scope failures before nightly can catch them.
**Category:** code_health / workflow

---

### Idea 3: Fix kb-autopopulate.sh (35d broken — agent-browser CLI not installed)

**Evidence:** governance.json run 53 note: "kb-autopopulate broken 35 days (agent-browser CLI not installed)." `scripts/daily/kb-autopopulate.sh` uses `agent-browser` CLI that is not available in this environment. KB has been stale 35+ days.
**Action:** Update `scripts/daily/kb-autopopulate.sh` to replace `agent-browser` invocations with `curl` or native `WebFetch` calls. ~20-min fix. Or set the script to skip silently when agent-browser unavailable.
**Impact:** Restores twice-daily KB auto-population → competitive intelligence current → `kb-first` rule effective again.
**Category:** operational

---

### Idea 4: Add cross-tenant isolation test to test_os_graph_memory.py

**Evidence:** c8a0460 landed os_graph_memory.py (397L) with 284 mock-based tests. Nightly explicitly flagged: "Tests passed because mock DB ignores column names." c6805a5 caught a tenant_scope override gap for os_graph_nodes/edges. No existing test verifies that a query for `client_id=A` cannot return nodes belonging to `client_id=B`. This is a data isolation invariant for a SaaS product.
**Action:** Add 2 tests to `test_os_graph_memory.py` that assert cross-tenant isolation: create nodes for two mock client_ids, query one, verify the other's nodes are absent. AUTONOMOUS-EXECUTABLE (test file addition, nightly channel).
**Impact:** Safety net if RLS is accidentally dropped or altered in future migration. Catches client_id filter bugs at unit test level before production.
**Category:** security / code_health

---

### Idea 5: Update governance.json to mark run 53 as implemented + correct moratorium count

**Evidence:** Run 53 winner (`test_os_action_dispatch.py`) confirmed IMPLEMENTED by c6805a5. `governance.json` active_directions run 53 still shows `status: "pending_autonomous"`. Moratorium implementation_lag_warning is stale. Correct governance state unblocks accurate moratorium exit tracking.
**Action:** Update governance.json: run 53 status `pending_autonomous → implemented`, `implemented_date: "2026-06-10"`, `implemented_by: "nightly-commit-review 2026-06-10 c6805a5"`. Decrement pending count.
**Impact:** Accurate moratorium tracking. Prevents future runs from over-counting pending items.
**Category:** workflow
