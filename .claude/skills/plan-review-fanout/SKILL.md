---
name: plan-review-fanout
description: Run 8 specialist review agents in parallel against a drafted plan before execution. Load when a plan is produced and about to move to Execute phase, or user says /plan-review, 'fanout review', 'pressure-test plan'. Skip for one-line fixes and trivial renames.
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - /plan-review
  - fanout review
  - pressure-test plan
  - plan-review-fanout
  - 8-agent review
  - specialist review
allowed-tools: [Read, Glob, Grep, Bash]
effort: high
---

# Plan Review Fanout — 8 Parallel Specialists

**ultrathink** — each specialist reasons against its domain in the same turn. Aggregate only after all 8 return. Do not serialize.

Inspired by MAG7-adjacent principal-engineer workflow: every drafted plan passes 8 specialist subagents before any code is written. Missed a specialist once → regressions ship.

## When to Use

- Immediately after `/compound` Plan phase produces a draft plan
- After `write-prd` → `prd-to-plan` completes
- Before execute phase of any task touching 2+ files
- User says `/plan-review`, "fanout review", "pressure-test plan"
- Risky refactor, schema change, auth change, widget change, payments change

## When NOT to Use

- Single-file bug fixes under 20 lines
- Typo/rename/format-only changes
- Plan already reviewed this session (no regression)
- Time-critical hotfix with user approval to skip

## The 8 Specialists

Spawn in same turn. Each reviews the plan against its exclusive lens.

| # | Specialist | Lens | Veto authority |
|---|-----------|------|----------------|
| 1 | architect | layer boundaries, coupling, god-class risk | yes |
| 2 | schema-guardian | migrations, `client_id` discipline, RLS, indexes | yes |
| 3 | security-reviewer | auth, input validation, secrets, OWASP | yes |
| 4 | widget-specialist | byte-identical copy rule, cross-origin, widget JS invariants | yes (widget-touching only) |
| 5 | tenant-isolation | every query scoped to tenant/client, no unscoped writes | yes |
| 6 | perf-hunter | N+1, sync-in-async, missing indexes, bundle bloat | advisory |
| 7 | ui-reviewer | dark theme, empty/loading/error states, Sidebar.jsx registration | advisory |
| 8 | standards-keeper | SOLID/DRY/KISS/YAGNI, no `from __future__ import annotations`, 600-line cap | advisory |

## Fan-Out Directive (explicit, Opus 4.7 literal)

Use this phrasing. 4.7 under-delegates on implicit requests (see `opus-4-7-prompting.md §4`).

> "Spawn 8 Agent calls in a single tool-call batch. Do not serialize. Each agent reviews the plan from exactly one lens below. Return verdict {PASS | CONCERN | VETO} + specific findings with file:line refs. Agents: architect, schema-guardian, security-reviewer, widget-specialist, tenant-isolation, perf-hunter, ui-reviewer, standards-keeper."

## Agent Mapping

Use existing `.claude/agents/` where possible. Fall back to `codex:rescue` per `codex-subagents.md` when reviewing live code, but native agents are required here because review is read-only and reviewer-specific.

| Specialist | Agent |
|-----------|-------|
| architect | `code-architect` or `opus-advisor` (Opus) |
| schema-guardian | `schema-guardian` |
| security-reviewer | `security-reviewer` |
| widget-specialist | `widget-specialist` |
| tenant-isolation | `code-reviewer` with tenant-scoped prompt |
| perf-hunter | `performance-optimizer` |
| ui-reviewer | `frontend-dev` (read-only mode) |
| standards-keeper | `code-reviewer` with SOLID/DRY prompt |

## Verdict Aggregation

After all 8 return:

1. Any `VETO` from a veto-authority specialist → plan BLOCKED. Fix cited issues, re-run fanout.
2. Any `CONCERN` from veto-authority specialist → plan FLAGGED. Present to user, require explicit override.
3. Advisory `CONCERN` only → plan PROCEEDS. Append findings to plan doc as known tradeoffs.
4. All `PASS` → plan approved, move to Execute.

## Output Format

```markdown
# Plan Review Fanout — <plan-name>

**Plan:** <file or inline>
**Run:** 2026-04-22T09:47:00Z

## Verdicts
- architect: PASS | CONCERN | VETO — <1-line reason>
- schema-guardian: ...
- security-reviewer: ...
- widget-specialist: N/A | PASS | CONCERN | VETO — ...
- tenant-isolation: ...
- perf-hunter: ...
- ui-reviewer: N/A | ...
- standards-keeper: ...

## Findings
### architect
- file:line — finding
### schema-guardian
- ...

## Aggregate
- BLOCKED | FLAGGED | APPROVED
- Next step: <explicit>
```

Save to `audits/plan-review-<feature>-YYYY-MM-DD.md` when plan is approved and moves to Execute.

## Integration with compound-engineering

Compound pipeline: `Brainstorm → Plan → Execute → Review → VerticalCheck`

With fanout: `Brainstorm → Plan → plan-review-fanout → Execute → code-reviewer → /ultrareview → VerticalCheck`

Fanout runs BEFORE Execute. `/ultrareview` runs AFTER Execute.

## Anti-patterns

- Never serialize the 8 specialists — Opus 4.7 under-delegates without explicit batch directive
- Never override a schema-guardian VETO without updating `.claude/rules/schema-discipline.md` first
- Never skip fanout on "small" plans that touch schema, auth, widget, or payments
- Never accept advisory CONCERN without logging it in the plan doc

## Cross-refs

- `.claude/rules/parallel-approaches.md` — fan-out phrasing
- `.claude/rules/opus-4-7-prompting.md` §4 — explicit fan-out directive
- `.claude/rules/daily-skills.md` — grill-me + write-prd upstream gates
- `.claude/skills/compound-engineering/SKILL.md` — insert point
- `.claude/rules/ultrareview.md` — post-execute review (different gate)
