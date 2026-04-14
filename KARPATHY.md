# KARPATHY.md — Four Principles for LLM Coding

Drop-in behavioral rules. Derived from Andrej Karpathy's observations on where LLM coding assistants fail. Loaded alongside `CLAUDE.md` for every session.

Full enforcement spec: `.claude/skills/karpathy-guidelines/SKILL.md`.

---

## 1. Think Before Coding

**Don't assume. Don't hide confusion. State ambiguity explicitly.**

- State assumptions in plain text before editing.
- Present multiple interpretations rather than silently picking one.
- Push back if a simpler approach exists.
- Stop and ask rather than guess. Confidence <80% → ask.

> *Karpathy: "The models make wrong assumptions on your behalf and just run along with them without checking. They don't manage their confusion, don't seek clarifications, don't surface inconsistencies, don't present tradeoffs, don't push back when they should."*

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- Would a senior engineer say this is overcomplicated? If yes, rewrite.

> *Karpathy: "They really like to overcomplicate code and APIs, bloat abstractions, don't clean up dead code... implement a bloated construction over 1000 lines when 100 would do."*

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code.
- Don't refactor things that aren't broken.
- Match existing style even if you'd do it differently.
- Notice unrelated dead code → mention it, don't delete it.
- Every changed line traces directly to the request.

> *Karpathy: "They still sometimes change/remove comments and code they don't sufficiently understand as side effects, even if orthogonal to the task."*

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

| Instead of       | Transform to                                          |
| ---------------- | ----------------------------------------------------- |
| "Fix the bug"    | "Write a test that reproduces it, then make it pass"  |
| "Add validation" | "Write tests for invalid inputs, then make them pass" |
| "Refactor X"     | "Ensure tests pass before and after"                  |

> *Karpathy: "LLMs are exceptionally good at looping until they meet specific goals... Don't tell it what to do, give it success criteria and watch it go."*

---

## Checklist (non-trivial tasks)

```
- [ ] Request read carefully — multiple interpretations? ask
- [ ] Assumptions stated in plain text before editing
- [ ] Success criteria defined (what test/command proves it works)
- [ ] Minimum viable code — no speculative flexibility
- [ ] Only files tied directly to the request touched
- [ ] Verification commands run — loop until green
- [ ] Diff reviewed line-by-line — every line traces to request
```

## Signals It's Working

- Fewer unnecessary changes in diffs
- Fewer rewrites from overcomplication
- Clarifying questions come before implementation, not after mistakes
- Clean, minimal PRs — no drive-by refactoring

## Pairs With

- `.claude/rules/no-assumptions.md` — confidence <80% → ask (principle #1)
- `.claude/rules/ultrathink.md` — extended thinking always (principle #1)
- `.claude/skills/karpathy-guidelines/SKILL.md` — full spec + gotchas
- `.claude/skills/tdd-workflow/SKILL.md` — goal-driven loops (principle #4)
- `.claude/skills/dead-code-sweep/SKILL.md` — intentional cleanup only (principle #3)
