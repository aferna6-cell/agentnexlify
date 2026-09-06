# Improvement Backlog — Run 116 (2026-09-06)

## Active

- **Step 9L: AI metering coverage nightly check** — Add `scripts/check_ai_metering.py` (AST-based) + Step 9L block to `nightly-commit-review/SKILL.md`. Files GH issues (labels: billing, ai-ready) for functions calling Claude without metering guard. 1st carry-forward from run 115. Escalation to autonomous-executable at run 117.

## Parking Lot (survived debate but not chosen)

- **os_tool_executions.py god class split** — 783L service + 411L router = 1194L total. CLAUDE.md Rule 9 threshold exceeded. Last commit f22ef04 ~7 days stable. Split into focused modules: execution_dispatcher.py, result_parser.py, file_ops.py, process_runner.py. Run 117 candidate — hold until Step 9L implemented.
- **Step 9M: tenant_api_keys client_id guard sweep** — Nightly grep for `.tenant_id` on `tenant_api_keys` table (bug-patterns.md 2026-08-01 confirms regression class). Low ROI relative to Step 9L. Revisit after Step 9L proven pattern.

## Rejected This Run

- **Step 9J token budget fix** — KILLED. Insufficient diagnostic data to propose solution. "17/19 skipped due to token budget" in nightly log doesn't identify whether the cap or session budget is binding. Needs nightly log transcript analysis first.
- **CLAUDE.md exemption marker documentation** — KILLED. Premature — documents a feature (`# ai-metering-exempt:`) that doesn't exist yet. Subordinate to Step 9L; add after Step 9L ships.

## Questions for Next Run

1. Does nightly-2026-09-07 contain a `Step 9L:` line? If yes: how many violations found, how many GH issues filed?
2. Has human approved Step 9L between runs? If `grep -c 'Step 9L' .claude/skills/nightly-commit-review/SKILL.md` still returns 0: run 117 autonomous-executable escalation fires.
3. os_tool_executions.py: still 0 commits since f22ef04? If yes: god class split is run 117 candidate (8+ days stable = safe window).
4. Step 9J token budget: can we find the nightly session token usage breakdown to identify where the 17-skip budget limit is actually hit?
5. GH #800 (brain connector 44d stale): has SUPABASE_ACCESS_TOKEN been set in Railway?
