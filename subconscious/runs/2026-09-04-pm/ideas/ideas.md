# Ideas — Run 115 (2026-09-04-pm)

## Evidence Summary

3-day commit window (2026-09-01→04): M9 planner bakeoff dominates (10+ commits); Billing Automation v1 landed; Website/Chatbot Connect v1 (migration 201) shipped; schema-log drift guard (check_schema_log_migrations.py, PR #788) added but not yet in CI. Two usage metering fixes (extract_action_items #793, voice respond #792) — same class of missing metering on new AI endpoints. Nightly-2026-09-04: Step 9K PASS (1 subconscious PR open, under threshold), Step 9J detected 19 Dependabot PRs but deferred merge eligibility check (rate concern — no merges executed). KB 9 days stale (Step 9G blocked — gh CLI unavailable). Brain connector 43 days stale (GH #684). os_tool_executions.py: 783L, last commit 2026-09-01 (3 days stable — borderline run_115 mandate condition). PR #782 (draft, 1d) references "Step 9L unapplied migration alerter" from apparent prior automated run.

Run 115 mandate checks (from run_114):
1. Step 9K fires in nightly-2026-09-01: PASS (3 stale PRs found, below threshold)
2. Step 9J detection: PASS (triggered rebase on #721/#722 in nightly-2026-09-01)
3. GH #684 SUPABASE_ACCESS_TOKEN: NOT RESOLVED (43d stale)
4. os_tool_executions.py: 783L, 3 days stable — mandate condition borderline met
5. M8 OAuth/service_role HOLD: transitioned to M9 bakeoff work

---

### Idea 1: Add nightly migration alerter — Unapplied Migration Alerter to nightly SKILL.md
**Evidence:** feat(schema) PR #788 added scripts/check_schema_log_migrations.py (schema-log vs live migration drift guard). PR #782 (draft subconscious PR, 2026-09-03) explicitly names "unapplied migration alerter" — confirms prior automated run identified this. Migration drift causes silent prod failures. Schema-log updated manually (f72a274, 2026-09-04). No automated daily check exists.
**Action:** Add a migration alerter block to .claude/skills/nightly-commit-review/SKILL.md — run check_schema_log_migrations.py, report result, file GH issue if drift found.
**Impact:** Catches unapplied migrations before they cause prod failures. Same autonomous-executable SKILL.md channel as Steps 9F-9K. Zero code risk.
**Category:** code_health

---

### Idea 2: Split os_tool_executions.py god class (783L → 3 modules)
**Evidence:** 783L (30% above 600L god class threshold). Last commit f22ef04 (Billing Automation v1, 2026-09-01) — 3 days stable. Run_115_mandate item 5 explicitly names this as candidate ("if stable, run 115 god class split candidate"). Contains: tool dispatch, approval flows, action bridge logic — three distinct concerns.
**Action:** Split into os_tool_dispatch.py (routing), os_tool_approvals.py (approval flows), os_action_bridge.py (billing bridge). Use god-class-splitter skill.
**Impact:** Reduces blast radius for M9 bakeoff changes, improves reviewability, makes future AI action additions safer. Rule 9 compliance.
**Category:** code_health

---

### Idea 3: Fix Step 9J merge eligibility deferral — rate-limited per-PR check
**Evidence:** Nightly-2026-09-04: "19 open Dependabot PRs. Merge eligibility check deferred — requires mergeable_state per-PR read; rate concern. No merges executed." Step 9J detects PRs correctly now (search_pull_requests fix worked, nightly-2026-09-01 triggered rebases) but NEVER merges because eligibility check always defers. PRs #630/#631 at 32 days (critical threshold approaching). CVE window grows.
**Action:** Add rate-limit guard to Step 9J eligibility check: check mergeable_state for max 5 PRs per run (smallest, highest CVE severity first). Cache results for 24h to avoid re-check spam.
**Impact:** Closes the last gap in Dependabot automation — PRs will actually merge. Steps 9J is currently 0% effective despite detection working.
**Category:** workflow

---

### Idea 4: Add Step 9L — Nightly AI usage metering coverage check
**Evidence:** #793 (fix(widget): meter extract_action_items) + #792 (fix(voice): meter live-AI respond) both landed in last 3 days — same class of bug: new AI endpoint shipped without reserve/record/release metering. This is identical to the block_demo_role recurrence pattern that spawned Step 9I. Each unmetered endpoint is silent revenue leakage. No systematic nightly sweep exists.
**Action:** Add Step 9L to SKILL.md — grep backend/routers/ for AI calls (call_claude_messages, claude_client.messages) that lack ai_usage_guard or reserve_tokens calls. File ai-ready issue if found.
**Impact:** Prevents silent revenue leakage. Same SKILL.md-edit channel as Steps 9I-9K (autonomous-executable). Closes a whole class of recurring misses permanently.
**Category:** code_health / operational

---

### Idea 5: Wire PR #788 (schema-log drift guard) into CI pipeline
**Evidence:** PR #788 (scripts/check_schema_log_migrations.py) is open, non-draft, ready for merge (nightly shows it at "0d" in PR list). Script validates schema-log.md vs live migrations. Currently manual-only. check_project_invariants.py is the CI model for this class of script.
**Action:** Add check_schema_log_migrations.py to .github/workflows/pr-check.yml alongside check_project_invariants.py. Merge PR #788.
**Impact:** Every PR touching migrations gets automated drift check. Prevents "applied migration but forgot schema-log update" — a class of bug that caused 30+ schema-log drift incidents.
**Category:** code_health
