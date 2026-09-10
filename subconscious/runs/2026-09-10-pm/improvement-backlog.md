# Improvement Backlog — Run 118 (2026-09-10-pm)

## Winner (Run 118)
**Fix Step 9J token budget: cursor state + batch 5 Dependabot PRs per nightly**
- Category: workflow_efficiency
- Effort: S (SKILL.md edit, ~20 lines)
- Autonomous-executable: YES
- Evidence: 3-run evidence chain (runs 115/116/117: 17/19 PRs skipped)
- Security impact: CVE window closes within 4 nightly cycles

---

## Active Parking Lot (carry-forward candidates)

### 1. Split os_tool_executions.py god class (783L) [run 113+ candidate]
- Evidence: 783L, 8-10d stable, M8 OAuth and Calendar+CRM features next
- Proposed split: `tool_registry.py`, `tool_runner.py`, `tool_validators.py`, `tool_results.py`
- Caller update: backend/routers/os_tool_executions.py (411L), os_workflows/
- Trigger: first M8 OAuth or Calendar+CRM commit, OR GH #801 diagnosis activity in this module
- Effort: M (human sprint item, not autonomous-executable)
- Note: Also improves P0 (#801 approve_send_once) diagnosability

### 2. Step 9M: Auto-cleanup `__future__` annotations in test files
- Evidence: 3 files remain in GH #823 baseline: test_website_connect.py, test_local_seo_handlers.py, test_os_invoice_e2e.py
- CI guard already active (PR #834, check_backend_future_annotations.py blocks new violations)
- Human progress: 2 files cleaned 2026-09-10 (test_os_invoice_actions.py, test_os_calendar_crm.py)
- Trigger: if GH #823 still open after 2026-09-13 (3 more days)
- Effort: S (new Step 9M block in SKILL.md, same channel as Step 9J)
- Autonomous-executable: YES — but human actively cleaning, hold for 3 days

### 3. Diagnose P0 GH #801 (approve_send_once execution leak)
- Evidence: Morning digest 2026-09-10 flags P0, risk:high. No PR linked. 0 comments since filing.
- Root path: backend/services/os_workflows/engine.py — approve_send_once leaves execution running with no provider messageId
- Trigger: human sprint shift to Agent OS features; human explicitly asks for diagnosis
- Effort: M (read engine.py, write root cause comment, add ai-ready label)
- Note: Issue-to-pr-loop still stalled (GH #399, AUTOPILOT_GH_TOKEN expired). ai-ready label premature until #399 resolved.

### 4. GH #800 / Brain connector recovery (SUPABASE_ACCESS_TOKEN in Railway)
- Evidence: 44+ days stale. GH #800 filed. No human action.
- Trigger: human available for Railway env var config
- Effort: S (set env var in Railway settings)
- Autonomous-executable: NO (Railway access required)

---

## Governance Corrections Applied This Run
1. **Step 9L**: `implemented: false` → `implemented: true`. Grep confirmed functional block at SKILL.md lines 457/471. Carry-forward chain (runs 115/116/117) was tracking a stale governance state.
2. **check_ai_metering.py**: Confirmed exits RC=2 on violations (not RC=0 as briefly misread via pipe). 45 violations found, exit code 2. Script correct.

---

## Frozen Ideas
- `ai_human_handoff` — frozen per governance since run 21. Do not propose.

## Rejected This Run
- **Idea 1 (Fix check_ai_metering.py exit code)**: ELIMINATED. False premise — script exits RC=2 correctly.
- **Idea 4 (Diagnose P0 GH #801 and add ai-ready label)**: WEAKENED to parking lot. Human has full visibility (P0 in morning digest). No novel insight added without reading engine.py. Issue-to-pr-loop stalled (GH #399) so ai-ready label premature.
