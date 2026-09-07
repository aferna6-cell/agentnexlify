# Candidate Ideas — 2026-09-07

## Idea 1: Fix `from __future__ import annotations` in os_workflows/
**Evidence:** nightly-commit-review-2026-09-07 filed a MEDIUM issue: `shadow_planner.py:15` (added in #780) has `from __future__ import annotations`. Same pattern found in `planner_bakeoff.py:13` and `tool_catalog.py:21`. CLAUDE.md Rule #5 explicitly bans this in FastAPI files — PEP 563 deferred annotations silently break Pydantic validation. Run 117 mandate check confirms nightly caught it and filed GH issue.
**Action:** Remove `from __future__ import annotations` from all 3 os_workflows files; replace any Python 3.9 union types with Python 3.11 `X | Y` syntax or `Optional[X]` — no import needed on Python 3.11.
**Impact:** Closes growing CLAUDE.md Rule #5 violation cluster before any os_workflows file gains a Pydantic model or FastAPI route import (M9 is active, more files incoming). Prevents future silent 422s.
**Category:** code_health

---

## Idea 2: Fix Step 9G cloud trigger to use mcp__github__actions_run_trigger
**Evidence:** Step 9G in the nightly runs `gh workflow run kb-autopopulate.yml`, but `gh` CLI is unavailable in cloud container sessions. KB log shows last autopopulate was 2026-08-26 (12d stale, over 7-day threshold). The MCP tool `mcp__github__actions_run_trigger` is available as a deferred tool in this session and could replace the `gh` call.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` Step 9G to use `mcp__github__actions_run_trigger` instead of `gh workflow run`. Add fallback note that real blocker is GH #403 (ANTHROPIC_API_KEY missing in GH Actions secrets).
**Impact:** Unblocks KB freshness trigger path for cloud sessions. However, underlying 403 blocker means no actual KB runs until secret is set — limited immediate value.
**Category:** workflow_efficiency

---

## Idea 3: Split os_tool_executions.py god class (10d stability gate)
**Evidence:** `backend/services/os_tool_executions.py` is 783L, `backend/routers/os_tool_executions.py` is 411L — 1194L combined. Last commit `f22ef04` (~2026-08-30) = 8 days stable. Run 117 mandate requires 10d+ stability before split. CLAUDE.md Rule #9 triggers at 600+ lines.
**Action:** DEFERRED — wait until 2026-09-10 (10d threshold). Then split into: `os_tool_executor_core.py` (run/cancel/status), `os_tool_registry.py` (catalog/discover), `os_tool_results.py` (parsing/formatting).
**Impact:** When executed, reduces god-class blast radius and simplifies M9.5 shadow-path integration. Not ready today.
**Category:** code_health

---

## Idea 4: Batch-file 20 check_ai_metering violations as GitHub issues
**Evidence:** `scripts/check_ai_metering.py` (shipped run 117, commit `1c5b749`) reports 20+ unguarded AI-calling functions. Step 9L (commit `88dac49`) was wired to run nightly and auto-file issues with labels `billing`+`ai-ready`. First Step 9L nightly run fires tonight.
**Action:** KILLED — Step 9L will file issues automatically tonight. Manual filing now is duplicate work and contradicts the autonomous purpose of the tool.
**Impact:** Zero marginal value; Step 9L handles this.
**Category:** operational

---

## Idea 5: Remove Step 9J per-run cap to process all 19 Dependabot PRs
**Evidence:** Step 9J merged 4 Dependabot PRs in 3 days but skips 17/19 per run due to a 5-per-run cap. Run 117 noted "17-skip diagnosis" as a mandate check item.
**Action:** Investigate the 5-per-run cap in `.claude/skills/nightly-commit-review/SKILL.md` Step 9J and raise or remove it.
**Impact:** Unclear — the cap may exist to limit CI blast radius or rate limits. No evidence that the 17 skipped PRs are causing problems. Insufficient signal to act.
**Category:** workflow_efficiency
