# Candidate Ideas — Run 115 (2026-09-03)

---

### Idea 1: Fix M9.2 dead code in `derive_workflow_status()`
**Evidence:** nightly-2026-09-03 code note explicitly flagged `engine.py:derive_workflow_status()` inner guard (line 109) as always True: the outer guard (line 105) restricts states to `{"succeeded", "cancelled"}` — but the inner `all(s != "failed" and s != "unknown" for s in states)` is redundant because `"failed"` and `"unknown"` can never appear after the outer `all(s in {"succeeded", "cancelled"})` check. Nightly deferred autonomous cleanup for a "new major module." Direct code read confirms.
**Action:** Remove lines 108-110 in `backend/services/os_workflows/engine.py` — delete the inner guard and its comment, return "succeeded" directly. 3-line deletion, no behavioral change.
**Impact:** Eliminates maintainer confusion about guard semantics; prevents future "fix" of dead code that could introduce a real bug; signals code quality standards for new M9.2 module.
**Category:** code_health

---

### Idea 2: Add `test_os_workflows_store.py` for WorkflowStore
**Evidence:** M9.2 (ff3ab04) shipped `engine.py` (474L) + `store.py` (429L). `test_os_workflows_engine.py` (461 lines) was added but no `test_os_workflows_store.py` exists. store.py handles all DB mutations: create/update/list workflow state, step transitions, client_id scoping.
**Action:** Create `backend/tests/test_os_workflows_store.py` with unit tests covering: create workflow, list by client_id, update step state, schema compliance (client_id not tenant_id), idempotency guard.
**Impact:** Closes direct test gap for DB-touching module; catches RLS/tenant-scope bugs in new workflow engine before they hit production.
**Category:** code_health

---

### Idea 3: Add Step 9L — Auto-enrich empty bug-patterns.md Details via nightly
**Evidence:** Last 7 days of bug-patterns.md: 5 consecutive entries with empty Details fields (gmail 401, sales exact-email, m8 input preservation, demo-role, brace-expansion). The nightly already produces per-commit triage summaries. Human never fills in root cause details (7+ days of silence on these entries).
**Action:** Add Step 9L to `.claude/skills/nightly-commit-review/SKILL.md`: when a commit is triaged as LOW/MEDIUM bug fix in Step 9A and its bug-patterns.md entry has empty Details, append a 1-sentence root cause derived from the nightly triage summary. Skip if Details already populated.
**Impact:** bug-patterns.md becomes self-maintaining; root causes compound as learning data for future subconscious runs; prevents class-level recurrences.
**Category:** workflow_efficiency

---

### Idea 4: os_tool_executions.py god class split — pending 4-day stability mandate
**Evidence:** `backend/services/os_tool_executions.py` is 775 lines (29% over the 600-line god class threshold). Last commits: 2 days ago (M8 finalization, 2026-09-01). M8 is now complete (PR #710 merged). CLAUDE.md Rule 9: ">600 lines → split first before adding." M9 will add more tool execution paths.
**Action:** Recommend split when `git log --since="4 days ago" -- backend/services/os_tool_executions.py` returns empty. Split into: `os_tool_dispatcher.py` (routing/delegation), `os_tool_executor.py` (execution), `os_tool_validators.py` (input validation).
**Impact:** Reduces blast radius for M9 additions; enables parallel dev on tool categories; enforces Rule 9 before next milestone adds to the god class.
**Category:** code_health

---

### Idea 5: GH #728 ai-ready escalation comment
**Evidence:** nightly-2026-09-03 Step 9D: 4 ai-ready issues open (#728, #669, #660, #643). GH #728 (2 days old) is oldest without a linked PR. Issue-to-PR loop stalled (GH #399, AUTOPILOT_GH_TOKEN expired, 58d+). GH #669 now fixed (demo-role middleware PR #749 merged). So real queue is 3.
**Action:** Post comment on GH #728 identifying: loop stall cause (GH #399 token rotation), manual implementation path, request for GH #399 priority escalation.
**Impact:** Keeps ai-ready backlog visible; creates paper trail; specific pressure on the root cause (GH #399) without duplicate generic escalation.
**Category:** operational
