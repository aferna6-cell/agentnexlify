# Opus 4.7 Prompting Moves

Source: Suryansh Tiwari migration post (2026-04-17). Four moves not already covered by `opus-4-7.md`, `self-verification.md`, `ultrareview.md`, `task-budgets.md`, `vision-3x.md`.

## Why
4.7 takes instructions literally. 4.6 guessed. Prompts that relied on the model "filling gaps" now under-execute or over-execute. Fix the prompt, not the model.

---

## 1. Batch clarifying questions

**Rule:** When a skill or agent needs to clarify, ask all questions in ONE message. Do not drip-feed across turns.

**Why:** Each turn on 4.7 layers literal interpretations from prior turns. Multi-turn clarification compounds drift. Single-turn batch keeps intent coherent.

**Applies to:**
- `.claude/skills/grill-me/SKILL.md` — reframe "one question at a time" as "batch 5-8 questions per branch, wait for answers, branch, batch next 5-8"
- `.claude/skills/write-prd/SKILL.md` — interview phase
- `.claude/skills/triage-issue/SKILL.md` — repro questions
- Any agent that uses `AskUserQuestion` — prefer 4-option structured choice over 3-turn back-and-forth

**Counter-example:** True open-ended discovery still works turn-by-turn. Rule applies to known-domain clarification.

---

## 2. Positive examples beat negative rules

**Rule:** In agent system prompts and skill bodies, replace "don't do X / never do Y" with "like this: <example>". If a prompt has 3+ "never" lines, flip them.

**Why:** 4.7 treats negative rules as token cost without behavior lock-in. Positive examples anchor output shape. Faster, cheaper, more reliable.

**Audit targets:**
- `.claude/agents/*.md` — 57 agents; grep for "never", "don't", "do not", "avoid"
- `.claude/skills/*/SKILL.md` — especially `.claude/skills/caveman-mode`, `.claude/skills/karpathy-guidelines`
- Inline prompts in `backend/services/advisor_executor.py`, `backend/services/llm_runtime.py`, `backend/services/managed_agents_registry.py`

**Keep negative rules when:**
- Security invariant (never commit secrets, never skip webhook sig verify)
- Legal/compliance (never store PII in logs)
- Schema discipline (never use `tenant_id` on leads — already pinned in `schema-discipline.md`)

**Flip everything else** to positive examples.

---

## 3. Delete progress scaffolding

**Rule:** Remove "summarize every N tool calls", "explain plan then execute", "give status update before moving on" from agent prompts. 4.7 emits progress natively.

**Why:** Scaffolding wastes tokens and forces redundant structure on a model that already self-narrates well.

**Audit targets:**
- `.claude/skills/compound-engineering/SKILL.md` — check Review + VerticalCheck prompts
- `.claude/skills/issue-to-pr-loop/SKILL.md` — polling loop prompts
- `.claude/skills/autopilot-loop/SKILL.md` — legacy, still sourced
- `.claude/skills/nightly-commit-review/SKILL.md`
- Executor/advisor system prompts in `backend/services/advisor_executor.py`

**Keep scaffolding when:**
- Output is machine-parsed downstream (JSON shape must be stable)
- Compliance log requires explicit checkpoint markers
- User-facing chat UI needs discrete "thinking" / "done" events

---

## 4. Fan-out must be explicit

**Rule:** 4.7 spawns fewer subagents by default. Parallel execution phrasing must be explicit: "spawn subagents in the same turn to investigate X, Y, Z."

**Why:** Default delegation dropped. Compound-engineering, parallel-approaches, and worktree-orchestrator all need the directive spelled out.

**Applies to:**
- `.claude/rules/parallel-approaches.md` — add phrasing example
- `.claude/skills/compound-engineering/SKILL.md` — Brainstorm phase subagent spawn directive
- `.claude/skills/worktree-orchestrator/SKILL.md` — N-worktree dispatch
- `.claude/skills/delegate/SKILL.md`
- User prompts invoking `/delegate`, `/compound-engineering`

**Phrasing that works:**
- "Spawn subagents in the same turn to investigate X, Y, Z."
- "Fan out to 3 worktrees in parallel, each with strategy A/B/C."
- "Dispatch code-explorer + schema-guardian + security-reviewer concurrently."

**Phrasing that under-delegates on 4.7:**
- "Investigate X, Y, Z." (4.7 does sequentially)
- "Consider multiple angles." (4.7 picks one)

---

## 5. `/ultraplan` slash command

**Rule:** For multi-file plans reviewed async, use CLI `/ultraplan` (cloud plan-drafting, browser review). For inline same-session plans, use plan mode (Shift+Tab x2).

**Why:** Two distinct primitives. `/ultraplan` runs in a remote session while terminal stays free. Plan mode is synchronous.

**When each wins:**

| Situation | Tool |
|---|---|
| 2+ files, review before code | plan mode |
| 10+ files, cross-service, review async | `/ultraplan` |
| Spec → plan → issues pipeline | `/ultraplan` |
| Interactive feature design | plan mode |

**Not available in:** VS Code Claude extension (CLI only).

**Reference:** `.claude/commands/ultraplan.md` — full invocation guide, AgentNexLiFy integration notes (compound-engineering, write-prd pipeline, worktree-orchestrator), and limitations.

---

## Audit checklist (do this once)

```
# 1. Find negative-rule bloat
grep -rn "never\|don't\|do not\|avoid" .claude/agents/ .claude/skills/ | wc -l

# 2. Find progress scaffolding
grep -rn "summarize every\|status update\|explain your plan" .claude/ backend/services/

# 3. Find drip-feed clarification patterns
grep -rn "one question at a time\|ask one" .claude/skills/

# 4. Find sequential fan-out phrasing
grep -rn "investigate.*then\|consider multiple" .claude/skills/

# 5. Confirm no legacy budget_tokens in Python (already verified 2026-04-20: clean)
grep -rn "budget_tokens" backend/
```

---

## Anti-patterns
- Never flip a security "never" to a positive example (invariant must stay hard)
- Never batch clarifications when the first answer would branch the rest (then sequential wins)
- Never delete scaffolding that downstream parsers depend on
- Never assume 4.7 will fan out without the directive

## Cross-refs
- `rules/opus-4-7.md` — canonical feature matrix
- `rules/parallel-approaches.md` — worktree dispatch
- `rules/prompt-formula.md` — ROLE/TASK/CONTEXT/CONSTRAINTS/OUTPUT
- `.claude/skills/grill-me/SKILL.md` — needs batch-mode rewrite
- `.claude/skills/compound-engineering/SKILL.md` — needs explicit fan-out phrasing

## Source
Suryansh Tiwari, "The Ten Moves to Migrate Your 4.6 Prompts to 4.7" (2026-04-17). Aligns with Anthropic migration guide + Karpathy declarative-prompting post.
