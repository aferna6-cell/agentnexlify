---
paths:
  - "**/*"
---

# Model Routing — Right Model for Right Task

## Models

| Model | ID | Use for |
|-------|-----|---------|
| **Haiku** | `claude-haiku-4-5-20251001` | grammar, formatting, lookups, bullet lists, renames, translations, quick classification, hook scanners |
| **Sonnet** | `claude-sonnet-4-6` | code, debug, API calls, multi-file edits, most Agent executions, default implementation |
| **Opus 4.7** | `claude-opus-4-7` | **NEW DEFAULT FOR OPUS** - planning, architecture, security design, critical review, ambiguous decomposition, advisor passes. Self-verifies outputs. Default effort: `xhigh` in Claude Code. See `rules/opus-4-7.md`. |

## Opus 4.7 feature invoke-regularly rules
- **Self-verification** required on every task completion (`rules/self-verification.md`)
- **/ultrareview** required before merging >20 LOC changes (`rules/ultrareview.md`)
- **Task budgets** required on any long-running/cron agent (`rules/task-budgets.md`)
- **3x vision** for screenshot/diagram/design inputs (`rules/vision-3x.md`)

## Pattern for non-trivial tasks
**Opus 4.7 plans + self-verifies → Sonnet executes → Haiku cleans up.**

## Advisor-on-uncertainty rule

When a Sonnet or Haiku executor is unsure, it must not spend retries guessing.
If confidence is below 80%, evidence conflicts, the contract is ambiguous, two
implementations look similarly plausible, or the path touches security/data
integrity/cost, route through Opus 4.7 as an advisor first. Keep costs near
Sonnet levels by asking Opus for a compact plan/risks/test-gates brief, then
let the Sonnet or Haiku executor perform the work.

## Advisor-Executor Pattern (dev-time)

Claude Platform launched the advisor pattern: pair Opus as an advisor with Sonnet or Haiku as an executor. Near-Opus intelligence at ~1.3x pure-Sonnet cost instead of 5x pure-Opus.

**Two subagents (ship 2026-04-10):**
- `.claude/agents/opus-advisor.md` — Opus, read-only (Read/Grep/Glob). Produces a written brief.
- `.claude/agents/sonnet-executor.md` — Sonnet, full tools. Consumes the brief, executes, runs test gates.

**Flow:**
1. Main session receives complex task → invokes `opus-advisor` with task description
2. Advisor reads relevant files (≤15 tool calls), outputs brief: `{files, constraints, gotchas, plan, test gates, risks}`
3. Main session saves brief to `.claude/agent-comms/advisor-brief-{timestamp}.md`
4. Main session invokes `sonnet-executor` with brief path
5. Executor reads brief, executes in order, runs test gates, writes Executor Report

**When to use the advisor-executor pair:**
- Task touches 3+ files
- Task involves schema changes
- Task touches security-critical code (auth, payments, tenant isolation)
- Task requires architectural decisions
- User prefixes request with `advisor:`

**When NOT to use:**
- Renames, grammar, lookups (Haiku direct)
- Single-file bug fixes under 20 lines (Sonnet direct)
- Tasks already scoped by a plan doc (Sonnet executes the plan doc itself)
- Tasks under 5 minutes (overhead > benefit)

**Cost model:**
- Advisor: ~2-5k Opus output tokens ≈ $0.15-0.40 per brief
- Executor: ~20-50k Sonnet tokens ≈ $0.30-0.75 per execution
- Net: ~1.3x pure-Sonnet cost, ~25% pure-Opus cost
- Opus-only baseline: ~$2.00-5.00 per task
- Savings: 65-80% vs pure Opus on complex tasks

**Product-runtime mirror:** Same pattern ships for tenant-facing agents in `backend/services/advisor_executor.py` (A2). Opt-in per call site via `advised_*()` helpers in `managed_agents_registry.py`.

## Never
- Never Opus for mechanical work (rename, format, lookup)
- Never Haiku for architecture or security design
- Never default to Opus execution when Sonnet fits - use Opus 4.7 as the advisor boost for uncertainty

## Hook agent model delegation
- Security scanner on auth/payment file edit → Haiku
- Pre-push code review → Haiku
- Plan/architecture review → Opus 4.7
- Bulk refactor execution → Sonnet

## Cost awareness
Opus is 5x Sonnet, 15x Haiku per token. Every Opus call should justify the depth.
