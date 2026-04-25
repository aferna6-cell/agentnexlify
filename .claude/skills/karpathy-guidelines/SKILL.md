---
name: karpathy-guidelines
description: "Load when writing, reviewing, or refactoring code in backend/ or frontend/ to keep changes surgical, surface assumptions, avoid overcomplication. Bias: caution over speed on non-trivial work."
version: 1.0.0
origin: forrestchang/andrej-karpathy-skills
license: MIT
triggers: ["think before coding", "simplicity first", "surgical changes", "goal-driven", "avoid overcomplication", "karpathy guidelines", "reduce llm mistakes"]
paths: backend/**.py,frontend/src/**.jsx,frontend/src/**.js,frontend/src/**.tsx,widget/**.js
user-invocable: false
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## Why — Karpathy verbatim (failure modes this skill prevents)

> **Blind assumptions:** "The models make wrong assumptions on your behalf and just run along with them without checking. They don't manage their confusion, don't seek clarifications, don't surface inconsistencies, don't present tradeoffs, don't push back when they should."

> **Overcomplication:** "They really like to overcomplicate code and APIs, bloat abstractions, don't clean up dead code... implement a bloated construction over 1000 lines when 100 would do."

> **Unwarranted changes:** "They still sometimes change/remove comments and code they don't sufficiently understand as side effects, even if orthogonal to the task."

> **Loops are the lever:** "LLMs are exceptionally good at looping until they meet specific goals... Don't tell it what to do, give it success criteria and watch it go."

If a diff smells like one of the first three, stop and re-apply the matching principle below. The fourth is the positive frame for principle #4 (Goal-Driven Execution).

## When to Use

- Writing new code in any language
- Refactoring or modifying existing code
- Reviewing PRs or diffs
- Planning multi-step implementation tasks
- Any time the user's request has ambiguity you'd normally paper over

## When NOT to Use

- Trivial typo fixes or obvious one-liners
- Pure mechanical renames (use Haiku + find-replace)
- Tasks the user explicitly scoped as "just do it, don't overthink"

## 1. Think Before Coding

**State assumptions. Surface confusion. Name tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- When multiple interpretations exist, present them, like this: "This could mean A (reset user session) or B (reset DB row) — which?"
- When a simpler approach exists, propose it. Push back when warranted.
- When something is unclear, stop. Name what's confusing. Ask.

**Pairs with:** `.claude/rules/no-assumptions.md` (existing rule — confidence <80% → ask).

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- Ship exactly what was asked — no extra features.
- Inline single-use code instead of abstracting it.
- Add "flexibility" or "configurability" only when requested, like this: wait for a second caller before extracting a helper.
- Handle only errors that can actually happen on the call path.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

**Enforcement in this project:** Pre-commit hook flags bare except, dead imports. Compound-engineering reviewer agent catches bloated abstractions.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Leave adjacent code, comments, and formatting as-is.
- Refactor only code the task requires — leave working code intact.
- Match existing style, even if you'd do it differently.
- When you notice unrelated dead code, mention it in the report, like this: "Noticed: `helpers.py:42` unused since #812 — leaving for follow-up."

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Leave pre-existing dead code for a dedicated cleanup pass.

**The test:** Every changed line should trace directly to the user's request.

**Enforcement:** `dead-code-sweep` skill for intentional cleanup passes. Drive-by deletions forbidden.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

| Instead of       | Transform to                                                |
| ---------------- | ----------------------------------------------------------- |
| "Add validation" | "Write tests for invalid inputs, then make them pass"       |
| "Fix the bug"    | "Write a test that reproduces it, then make it pass"        |
| "Refactor X"     | "Ensure tests pass before and after"                        |

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

**Pairs with:** `.claude/skills/tdd-workflow/SKILL.md`, `.claude/skills/verification-loop/SKILL.md`.

## Checklist

```
- [ ] Read the request carefully — multiple interpretations? ask
- [ ] State assumptions in plain text before editing
- [ ] Define success criteria (what test/command proves it works)
- [ ] Write minimum viable code — no speculative flexibility
- [ ] Touch only files tied directly to the request
- [ ] Run verification commands — loop until green
- [ ] Review diff line-by-line — every line traces to request
```

## Signals It's Working

- Fewer unnecessary changes in diffs
- Fewer rewrites due to overcomplication
- Clarifying questions come before implementation, not after mistakes
- Clean, minimal PRs — no drive-by refactoring

## Gotchas

- **"Simple" vs "simplistic".** Three similar lines is better than a premature abstraction, but don't copy-paste the same 50-line block five times to avoid a helper function. Use judgment — the line is around 3-4 repeats of non-trivial logic.
- **Surgical changes conflict with formatters.** If a file has trailing whitespace or missing newlines on lines you didn't touch, leave them alone. The auto-formatter will catch them later. Keep formatter edits out of logic PRs — a 500-line whitespace diff hides the real change.
- **Goal-driven execution needs a real goal.** "Make it work" is not a goal. "Tests in X file pass" is. When the user hasn't given you a success criterion, ASK for one before writing code.
- **Push-back has a limit.** You can disagree with a user's approach once, with evidence. If they re-state the direction, implement what they asked — one round of push-back, then execute.
- **Adjacent dead code temptation.** Seeing unused imports while editing a file is not permission to clean them. Note them in the response, let the user decide.
- **Overlap with project rules.** This skill's principle #1 overlaps with `.claude/rules/no-assumptions.md`. Treat them as reinforcing — follow both.
- **Skip the checklist on small fixes.** For a 5-line bug fix, use the principles and skip the ritual.
