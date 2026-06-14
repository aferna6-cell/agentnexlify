---
title: "Opus 4.7 Prompting Migration — Five Moves to Unbreak Your 4.6 Prompts"
category: ai-llm
tags: ["claude", "opus-4-7", "prompting", "migration", "agent-design", "ultraplan", "fan-out"]
sources:
  - ".claude/rules/opus-4-7-prompting.md"
  - ".claude/rules/opus-4-7.md"
  - ".claude/rules/self-verification.md"
  - ".claude/rules/ultrareview.md"
  - ".claude/rules/task-budgets.md"
  - ".claude/rules/vision-3x.md"
  - ".claude/commands/ultraplan.md"
  - "Suryansh Tiwari, 'The Ten Moves to Migrate Your 4.6 Prompts to 4.7' (2026-04-17)"
  - "Andrej Karpathy, declarative-prompting post (2026-04)"
  - "Anthropic Opus 4.7 migration guide (2026-04-16)"
created: 2026-04-20
updated: 2026-04-20
summary: "Opus 4.7 reads prompts literally — 4.6 guessed. Five moves (batch clarify, positive examples, strip scaffolding, explicit fan-out, /ultraplan) fix the under- and over-execution that otherwise ships. First sweep applied to 7 rule + skill + agent files on 2026-04-20."
---

# Opus 4.7 Prompting Migration — Five Moves to Unbreak Your 4.6 Prompts

Opus 4.7 shipped on 2026-04-16 as a drop-in model-ID swap — same `$5/$25` pricing, same API surface, same SDK call signatures aside from a new `xhigh` effort level and the beta `task_budget` parameter. What it did not ship as a drop-in is the prompts that were tuned against Opus 4.6. The 4.7 release notes and Karpathy's declarative-prompting post both surface the same behavioral shift: 4.7 executes instructions literally, where 4.6 inferred optional-ness from context. Prompts that relied on the model "filling gaps" now either under-execute (skip the inference the old prompt assumed) or over-execute (run every instruction to the letter when some were meant as guidance). The fix is on the prompts, not the model.

The migration problem is concentrated in agent bodies, skill instructions, and system prompts — the text that tells a subagent or a Managed Agent how to behave across many turns. Inline user prompts fare better because they are written fresh against the current model. The recurring failure modes are four: clarifying questions that drip-feed across turns and compound literal drift, negative rules ("never do X") that cost tokens without locking behavior, progress scaffolding ("summarize every N tool calls") that collides with 4.7's native self-narration, and fan-out directives that 4.7 silently serializes because the phrasing lacks the `spawn in the same turn` signal. A fifth move — adopt the new CLI-native `/ultraplan` for async multi-file planning — rounds out the migration by separating drafting load from terminal availability.

This article captures the migration playbook, the AgentNexLiFy-specific changes already landed on 2026-04-20, the remaining audit targets in the repo, and the cross-refs to the governing rule files. It pairs with [[claude-opus-4-7-release]] for the model-capability baseline and with `.claude/rules/opus-4-7-prompting.md` as the canonical enforcement rule. The five moves are not optional — leaving 4.6-style prompts in place is how the 4.7 lift from `xhigh` effort and self-verification gets eaten by prompt drift.

## Why 4.7 breaks 4.6 prompts

Two tokenizer-and-reasoning-level changes drive the behavior shift. First, the updated tokenizer maps the same input to 1.0–1.35x more tokens depending on content, which silently inflates advisor-brief budgets and `max_tokens` ceilings written against 4.6 token counts. Second, and more consequential for prompt shape, 4.7 does substantially more thinking at higher effort — especially in later turns of agentic loops — and reads instructions as binding rather than advisory. The compound effect is that a 4.6 prompt with three "never do X" lines and an implicit "but you can skip step 4 if irrelevant" clause now either enumerates every forbidden action literally, or executes step 4 even when the context makes it redundant.

Karpathy's declarative-prompting post frames the same pattern from the opposite direction: the shift is toward models that respect the prompt as a specification, not a suggestion. Positive examples anchor output shape cheaper than negative rules constrain it, because the model has a concrete target to match rather than a forbidden region to avoid. Suryansh Tiwari's migration post operationalizes this into the five moves documented here. Anthropic's own migration guide aligns — explicit scope markers, tightened effort knobs, and literal fan-out phrasing are the three fixes Anthropic recommends before production rollout.

The practical test for whether a prompt needs migration is to re-read it and ask: "what did 4.6 silently skip here that 4.7 will now execute?" If the answer is non-empty, the prompt drifted. The second test: "where does this prompt say 'never' or 'don't' three or more times in a row?" If yes, those cost tokens without behavior lock-in on 4.7 and should flip to positive examples unless they encode a security or schema invariant.

## The five moves

### 1. Batch clarifying questions
Ask all questions in one message. Drip-feeding one question per turn compounds literal interpretations across turns — each turn layers 4.7's pinned reading of the prior turn onto the next. A single-turn batch of five to eight questions per design branch keeps intent coherent and cuts round-trips by 3-5x. The counter-example is open-ended discovery where the first answer genuinely branches the rest; there, sequential still wins. Applied to `.claude/skills/grill-me/SKILL.md`, `.claude/skills/write-prd/SKILL.md`, and `.claude/skills/triage-issue/SKILL.md` on 2026-04-20.

### 2. Positive examples beat negative rules
Replace "don't do X / never do Y" with "like this: <example>". Three-or-more negative rules in a row is the audit threshold — flip to positive examples anchored on the desired output shape. The model latches faster onto an exemplar than onto a forbidden region. The exceptions are invariants: security ("never commit secrets"), schema discipline ("never use `tenant_id` on `leads`"), and legal/compliance ("never log PII"). Those stay as hard negatives because they encode non-negotiable constraints, not style preferences. Applied on 2026-04-20 to `opus-advisor.md`, `sonnet-executor.md`, `karpathy-guidelines/SKILL.md`, `feature-build/SKILL.md`, and `ai-feature-pattern/SKILL.md`.

### 3. Delete progress scaffolding
Remove "summarize every N tool calls", "explain your plan then execute", "give a status update before moving on" from agent prompts. 4.7 emits progress natively — adding scaffolding wastes tokens and forces redundant structure on a model that already self-narrates cleanly. Keep scaffolding only when a downstream parser depends on a stable JSON shape, a compliance log requires explicit checkpoint markers, or a user-facing chat UI needs discrete "thinking" / "done" events. Audit targets: `compound-engineering/SKILL.md`, `issue-to-pr-loop/SKILL.md`, `nightly-commit-review/SKILL.md`, `autopilot-loop/SKILL.md`, and inline executor/advisor prompts in `backend/services/advisor_executor.py` and `managed_agents_registry.py`.

### 4. Fan-out must be explicit
4.7 spawns fewer subagents by default. Parallel execution needs the directive spelled out literally, or the model serializes. Phrasings that work: "Spawn subagents in the same turn to investigate X, Y, Z", "Fan out to 3 worktrees in parallel, each with strategy A/B/C", "Dispatch agent1 + agent2 + agent3 concurrently". Phrasings that under-delegate on 4.7: "Investigate X, Y, Z" (done sequentially), "Consider multiple angles" (picks one). Applied to `.claude/rules/parallel-approaches.md` and `.claude/skills/compound-engineering/SKILL.md` on 2026-04-20. Remaining audit targets: `worktree-orchestrator/SKILL.md`, `delegate/SKILL.md`, and inline prompts invoking `/compound-engineering`.

### 5. Adopt `/ultraplan` for async multi-file planning
`/ultraplan` is a native Claude Code CLI command — not a user-defined slash command — that drafts a plan in a remote cloud session while the local terminal stays free. Review happens in a browser. The decision matrix: 2+ files reviewed inline → plan mode (Shift+Tab x2); 10+ files cross-service reviewed async → `/ultraplan`; spec → plan → issues pipeline → `/ultraplan`; interactive iterative design → plan mode. Not available in the VS Code Claude extension — CLI only. Documented in `.claude/commands/ultraplan.md` and cross-linked from `opus-4-7-prompting.md` § 5 on 2026-04-20.

## AgentNexLiFy changes already applied

Two commits on 2026-04-20 landed the first sweep:

- **ee2cfe3** (batch mode + positive examples): `grill-me/SKILL.md` drip-feed reframed as batch 5-8 per branch; `daily-skills.md` grill-me pattern updated; `opus-advisor.md`, `sonnet-executor.md`, `karpathy-guidelines/SKILL.md` — 16 style negatives flipped to positive examples; all security/schema invariants (`client_id`, `from __future__ import annotations` ban, `.env` discipline, webhook signature verification, `localStorage` ban) kept verbatim.
- **4362424** (migration sweep): `feature-build/SKILL.md` — 3 style negatives flipped, 4 security/schema kept; `ai-feature-pattern/SKILL.md` — 3 style negatives flipped, 8 secret/API compliance kept; `parallel-approaches.md` — explicit fan-out phrasing section with 5 working examples and 2 anti-phrasings; `compound-engineering/SKILL.md` — fan-out note cross-linking `parallel-approaches.md`; `.claude/commands/ultraplan.md` — new reference file; `opus-4-7-prompting.md` § 5 cross-ref to ultraplan.

Both commits are phrasing-and-reference-only — zero behavior change. The value is that future 4.7 sessions read prompts that match 4.7's literal-execution semantics, not 4.6's inference-driven ones.

## Remaining audit targets

The sweep is not finished. These files still need review against the five moves:

- `.claude/skills/worktree-orchestrator/SKILL.md` — N-worktree dispatch needs explicit fan-out phrasing per move 4.
- `.claude/skills/delegate/SKILL.md` — multi-agent dispatch same issue.
- `.claude/skills/issue-to-pr-loop/SKILL.md` — polling loop prompts; audit for progress scaffolding (move 3).
- `.claude/skills/autopilot-loop/SKILL.md` — legacy but still sourced; same scaffolding audit.
- `.claude/skills/nightly-commit-review/SKILL.md` — batch triage prompts; audit for scaffolding and fan-out.
- `.claude/skills/compound-engineering/SKILL.md` — Review + VerticalCheck phases; audit for progress scaffolding.
- `backend/services/advisor_executor.py` system prompts — inline 4.6-era advisor/executor prompts; audit for negatives + scaffolding.
- `backend/services/llm_runtime.py` inline prompts — same.
- `backend/services/managed_agents_registry.py` — Managed Agent instructions for Lead Qualifier, Document Drafter, Codebase Reviewer.
- 57 agents in `.claude/agents/*.md` — run the negative-rule grep audit from `opus-4-7-prompting.md` audit checklist; flip non-invariant negatives.

Audit commands captured verbatim in `.claude/rules/opus-4-7-prompting.md` § Audit checklist. Run `grep -rn "never\|don't\|do not\|avoid" .claude/agents/ .claude/skills/ | wc -l` for the size of the remaining negative-rule surface.

## Anti-patterns

- Flipping a security negative to a positive example — invariants stay hard ("never commit secrets" does not become "like this: redacted-env.example").
- Batching clarifications when the first answer would branch the rest — then sequential wins and batching poisons downstream questions.
- Deleting scaffolding that a downstream JSON parser depends on — scaffolding collides with 4.7's self-narration only when the output is free-form text.
- Assuming 4.7 will fan out without the directive — silently serializes and the parallel-approaches budget gets wasted on sequential exploration.
- Using `/ultraplan` when you need the plan in the same turn — use plan mode instead; `/ultraplan` is async by design.

## Key Concepts

- **Literal instruction following** — 4.7 executes prompts as binding specifications rather than inferring skip-ability from context. Every instruction runs unless marked optional explicitly.
- **Batch clarification** — asking all clarifying questions in one turn to prevent compound literal drift across turns. Replaces the 4.6-era "one question at a time" pattern in `grill-me`, `write-prd`, `triage-issue`.
- **Positive-example anchoring** — specifying desired output shape via exemplars ("like this: <example>") rather than forbidden regions ("never do X"). Cheaper tokens, stronger behavior lock-in.
- **Explicit fan-out** — directive phrasing that forces 4.7 to spawn subagents in the same turn. Without it, 4.7 serializes and the parallel-approaches pattern degrades into sequential exploration.
- **`/ultraplan`** — CLI-native slash command introduced with 4.7; drafts plans in a remote cloud session while the local terminal stays free. Distinct from inline plan mode (Shift+Tab x2). Not available in the VS Code Claude extension.

## Related Articles

- [[claude-opus-4-7-release]] — Model-capability baseline, benchmark lift, tokenizer expansion, xhigh effort, task budgets, 3x vision.
- [[claude-opus-4-6-capabilities]] — The 4.6 baseline these prompts were originally tuned against.
- [[anthropic-building-effective-agents]] — Pattern catalog for when agent autonomy pays off; informs which prompts need migration first.
- [[effective-context-engineering]] — Broader prompt-design principles Karpathy's declarative-prompting post extends.

## Relevance to AgentNexLiFy

This migration is load-bearing for every agent, skill, and system prompt that ships in the repo. The runtime advisor-executor pair (`backend/services/advisor_executor.py`), the nightly commit review, the issue-to-PR autopilot, the compound-engineering 5-agent pipeline, and the 57 agent bodies in `.claude/agents/` all route through Opus 4.7 when reasoning depth matters. Leaving 4.6-style prompts in place means 4.7's reliability lift from self-verification, `xhigh` effort, and task budgets gets eaten by prompt drift — the model does more thinking against a worse specification, producing slower and costlier output than 4.6 would have with its own tuned prompts. The two commits landed on 2026-04-20 close the first and largest phrasing-debt slice; the remaining audit targets above are tracked as the follow-on sweep. The governing rule is `.claude/rules/opus-4-7-prompting.md` — treat it as the canonical enforcement for any new agent or skill written against 4.7.
