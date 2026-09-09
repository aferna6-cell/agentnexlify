# Ideas — Run 2026-09-09-pm

## Evidence Digest

**Step 9L**: Confirmed in nightly SKILL.md (grep=2). Added after nightly-2026-09-09 ran; first execution still pending. Mandate condition 1 PASSES.

**os_tool_executions.py**: 783L, 30+ functions, last commit `9589c26` (10+ days ago, 2026-08-29). Mandate condition 2 PASSES (10d+ stable + Step 9L confirmed = god class split is run 118 winner per governance).

**Dependabot PRs**: Multiple merged this week (recharts, jsdom, uvicorn, @vitejs/plugin-react, @testing-library/jest-dom, eslint, @playwright/test). Step 9J making progress but still skipping 17/19 PRs per token budget.

**New CI gate**: PR #834 blocks new `from __future__ import annotations` in backend. GH #823 tracks 5 existing test-file violations. Nightly 2026-09-08 auto-fixed 2 production service files.

**KB**: 14 days stale (last compile 2026-08-26). Step 9G cloud trigger still broken (gh CLI unavailable in headless sessions). ANTHROPIC_API_KEY missing from GH Actions (root blocker, GH #403).

**meter-ai-endpoint SKILL.md** (b20ece0): new skill codifying the reserve/record/release pattern for future unmetered endpoints.

---

### Idea 1: os_tool_executions.py God Class Split
**Evidence:** 783L at last commit `9589c26` (10+ days stable). 30+ functions spanning 4 concerns: (a) tool lifecycle — persist_tool_executions, find_by_idempotency_key, claim_for_execution, record_execution_outcome, mark_engine_unavailable; (b) lead/note operations — apply_customer_notes, _append_lead_note, _mark_note_execution_unverified; (c) email operations — validate_before_claim, email_recipient_from_input, _normalize_email, input_passes_python_email_gate; (d) data plane — _run_data_plane_tool, propose_tool_execution, list_tool_executions, get_tool_execution, present_tool_execution. Mandate condition met: Step 9L confirmed + 10d+ stable.
**Action:** Recommend splitting into 4 focused modules: `os_tool_lifecycle.py` (core CRUD + claim lifecycle, ~250L), `os_tool_lead_actions.py` (customer notes + lead note writes, ~80L), `os_tool_email.py` (email validation + normalization + recipient resolution, ~120L), `os_tool_data_plane.py` (execution dispatch + list + get + present, ~200L). Update callers and add re-export shim in `os_tool_executions.py` for backward compatibility during migration.
**Impact:** Each file <250L, single-concern, independently testable. Blast radius per change shrinks from 783L to <250L. Rule 9 compliance. Easier for parallel agents to work on different concerns without merge conflicts.
**Category:** code_health

---

### Idea 2: Fix Step 9G Cloud Execution Path
**Evidence:** run_117 mandate noted "Step 9G cloud trigger: CONFIRMED BROKEN — gh CLI unavailable in cloud sessions". KB at 14-day stale threshold. KB feeds AI chat responses directly. `mcp__github__actions_run_trigger` tool IS available in tool manifest (deferred tools list confirms `mcp__github__actions_run_trigger`). But root blocker is ANTHROPIC_API_KEY missing from GH Actions (#403), not trigger mechanism.
**Action:** Edit Step 9G in .claude/skills/nightly-commit-review/SKILL.md to use `mcp__github__actions_run_trigger` instead of `gh workflow run`. Add explicit error logging when the trigger returns non-204 response, with ANTHROPIC_API_KEY setup path in the error message.
**Impact:** Step 9G becomes functional in cloud sessions. KB self-healing can proceed once GH #403 is resolved (ANTHROPIC_API_KEY added).
**Category:** operational

---

### Idea 3: Step 9M — Future-Annotations Test File Cleanup in Nightly
**Evidence:** GH #823 tracks 5 test files with `from __future__ import annotations` (test_website_connect.py:16, test_local_seo_handlers.py:8, test_os_invoice_actions.py:8, test_os_calendar_crm.py:3, test_os_invoice_e2e.py:16). PR #834 CI gate blocks new violations. CLAUDE.md Rule 5 prohibits this import in FastAPI files; test files don't cause 422s but violate house style. Nightly already auto-fixed 2 production service files in 2026-09-08 run.
**Action:** Add Step 9M to nightly SKILL.md: grep test files for `from __future__ import annotations`, auto-remove from any file in `backend/tests/`, verify py_compile passes, commit autonomously (LOW risk per nightly precedent).
**Impact:** GH #823 resolved autonomously. CI gate stays clean. All 5 violations fixed within 1 nightly cycle.
**Category:** code_health

---

### Idea 4: Step 9J Token Budget Fix — Move Dependabot Check Earlier
**Evidence:** 17/19 Dependabot PRs still skipped per token budget (confirmed runs 115/116/117). Step 9J runs late in nightly sequence (after Steps 9A-9L). Earlier steps consume token budget, leaving insufficient for Step 9J's PR enumeration + merge logic. Step 9J detection fixed (search_pull_requests works), but 17/19 still skipped due to budget exhaustion.
**Action:** Move Step 9J block earlier in nightly SKILL.md — after Step 9C but before Steps 9D–9L. At that point, token budget is nearly full. Dependabot merges complete before heavier analysis steps run.
**Impact:** All 19 Dependabot PRs checked and merged (if eligible) each nightly instead of only 2. Security patches merged within 24h consistently.
**Category:** workflow_efficiency

---

### Idea 5: GH #800 SUPABASE_ACCESS_TOKEN Critical Escalation
**Evidence:** GH #800 tracks SUPABASE_ACCESS_TOKEN not set in Railway. Brain connector 44d+ stale. run_116_mandate_executed confirmed "NOT SET — brain connector 44d+ stale". Three automated comments posted without human action. Step 9E fires but human has not acted.
**Action:** Post a severity-upgraded comment on GH #800 reframing as CRITICAL: "Brain connector has been dark 44+ days. KB feeds widget AI responses. 44-day stale KB = 44-day-old answers to customer questions. 5-minute fix: Railway dashboard → AgentNexLiFy → Variables → Add SUPABASE_ACCESS_TOKEN." Autonomous-executable, comment-only.
**Impact:** Escalation comment in front of owner before week starts. May unblock KB compile, brain sync, and Supabase MCP in headless sessions.
**Category:** operational
