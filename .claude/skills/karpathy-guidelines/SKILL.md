---
name: karpathy-guidelines
description: "Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria. Derived from Andrej Karpathy's observations on LLM coding pitfalls."
version: 1.0.0
origin: forrestchang/andrej-karpathy-skills
license: MIT
triggers: ["think before coding", "simplicity first", "surgical changes", "goal-driven", "avoid overcomplication", "karpathy guidelines", "reduce llm mistakes"]
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

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

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

**Pairs with:** `.claude/rules/no-assumptions.md` (existing rule — confidence <80% → ask).

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

**Enforcement in this project:** Pre-commit hook flags bare except, dead imports. Compound-engineering reviewer agent catches bloated abstractions.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

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
- **Surgical changes conflict with formatters.** If a file has trailing whitespace or missing newlines on lines you didn't touch, leave them alone. The auto-formatter will catch them later. Don't let Prettier/Black drag you into a 500-line whitespace diff.
- **Goal-driven execution needs a real goal.** "Make it work" is not a goal. "Tests in X file pass" is. If the user hasn't given you a success criterion, ASK for one before writing code.
- **Push-back has a limit.** You can disagree with a user's approach once, with evidence. If they re-state the direction, implement what they asked. Don't re-litigate twice.
- **Adjacent dead code temptation.** Seeing unused imports while editing a file is not permission to clean them. Note them in the response, let the user decide.
- **Overlap with project rules.** This skill's principle #1 overlaps with `.claude/rules/no-assumptions.md`. They reinforce each other — don't treat them as redundant.
- **Don't cargo-cult the checklist.** For a 5-line bug fix the full checklist is overhead. Use the principles, skip the ritual.
