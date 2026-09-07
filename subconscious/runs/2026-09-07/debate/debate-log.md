# Debate Log — 2026-09-07

## Top 3 ideas (ranked by impact):
1. Fix `from __future__ import annotations` in os_workflows/ (3 files)
2. Fix Step 9G cloud trigger (mcp__github__actions_run_trigger)
3. Split os_tool_executions.py god class

---

## Idea 1: Fix `from __future__ import annotations` in os_workflows/

### Challenge
- Is the evidence strong enough? Three files with the banned annotation, but none are in the FastAPI import chain yet. Active risk is LOW (nightly confirmed this). Why act now?
- Is this the highest-leverage thing? Pattern is spreading, but M9.5 is zero-I/O skeleton only — no Pydantic models yet. Could wait.
- What could go wrong? Removal might break Python 3.9 compatibility if files use `X | Y` union syntax that requires 3.11+.
- Has something similar been tried? Run 117 carried forward "os_workflows spreading annotation pattern" as a parking-lot concern. No prior rejection.
- Too similar to active direction? Active direction is Step 9L (AI metering). This is code_health, different lane.

### Defend
- CLAUDE.md Rule #5 is explicit: NEVER in FastAPI files. The nightly caught this and filed a GH issue TODAY (2026-09-07). The system is telling us to act.
- "Wait until Pydantic model is added" is exactly the failure mode the rule guards against. By the time a Pydantic model is added, this gets shipped to prod and breaks validation silently.
- Python 3.11 handles `X | Y` union syntax natively. The 3 files use `@dataclass`, not Pydantic models. Removing the import and checking for any `X | Y` syntax (there won't be any in a new skeleton file) is 3 lines of change.
- M9 is active with 2 new files per week (shadow_planner, planner_bakeoff, tool_catalog all landed in the last 2 weeks). Pattern accelerating, not stable.
- Cost of action: 3 file edits, 3 one-line removals. Autonomous-executable in <2 minutes. Risk: near zero.

### Verdict: SURVIVES — chosen as winner

---

## Idea 2: Fix Step 9G cloud trigger (mcp__github__actions_run_trigger)

### Challenge
- Is the evidence strong enough? KB is 12d stale, but Step 9G fix only addresses the dispatch mechanism — not the actual execution. GH #403 (ANTHROPIC_API_KEY missing in GH Actions) is the real blocker. Fixing the trigger call doesn't populate the secret.
- Is this the highest-leverage thing? No. Even with the trigger fix, KB autopopulate will fail in GH Actions until the secret is set. SUPABASE_ACCESS_TOKEN is also unset (run 118 mandate finding).
- What could go wrong? Editing the SKILL.md Step 9G incorrectly could break the nightly flow. The mcp__github__actions_run_trigger API shape needs verification first.
- Has something similar been tried? Step 9G fix was discussed in runs 114-116 but was never the winner because the underlying secret blocker dominates.

### Defend
- The SKILL.md fix is still correct — `gh` CLI is unavailable in cloud sessions and the nightly currently fails silently at Step 9G. Replacing with `mcp__github__actions_run_trigger` at least gives visible error output.
- KB staleness is a real quality problem — 12d stale affects tenant-facing knowledge.

### Verdict: WEAKENED — patching the dispatch call is correct but insufficient while secrets aren't set. Fix the dispatch AND raise the secret issue, or wait until secret blockers are resolved. Move to parking lot.

---

## Idea 3: Split os_tool_executions.py god class

### Challenge
- 783L service + 411L router = 1194L combined. Clear CLAUDE.md Rule #9 violation.
- But run 117 mandate explicitly requires 10d+ stability before split. Last commit 2026-08-30 = 8d. Not eligible today.
- M9.5 shadow-path skeleton (commit `6063bbb`) is freshly landed — splitting os_tool_executions.py NOW might conflict with in-progress M9.5 integration.

### Defend
- File is already past the 600L threshold and getting larger with M9 work.
- The split plan is clear: 3 modules (executor_core, registry, results). Low ambiguity.

### Verdict: DEFERRED — mandate threshold not met (8d < 10d). Re-evaluate 2026-09-10+. Park in backlog with countdown note.

---

## Winner
**Idea 1: Fix `from __future__ import annotations` in os_workflows/**

Highest impact-to-risk ratio, autonomous-executable, CLAUDE.md hard rule, nightly confirmed today.
