# Effort Per Prompt — Set Effort on the Prompt, Not the Session

## Rule
Set `/effort` per prompt that needs the headroom. Default xhigh on Opus 4.7 burns ~2x the tokens of medium for many prompts that don't need the depth. Pick the level for the task at hand.

## Levels (Opus 4.7)

| Effort | When to use | Cost vs medium |
|--------|-------------|----------------|
| `low` | Quick fix, mechanical edit, lookup | ~0.5x |
| `medium` | Most prompts — code edits, simple debug, doc tweaks | 1x baseline |
| `high` | Demanding reasoning, multi-file refactor planning | ~1.5x |
| `xhigh` | Default for agentic coding loops on 4.7 | ~2x |
| `max` | Diminishing returns, rarely worth it | ~3-4x |

## Pattern
- `/effort medium` for the next prompt → run prompt → effort returns to session default after that turn
- Combine with self-verification (`rules/self-verification.md`) — short prompts with `medium` + verify line beat long prompts with `xhigh`

## When `xhigh` is right
- Spec → plan → code, single shot, real architectural choice
- Ambiguous decomposition where Opus must explore branches
- Security/payment/tenant-isolation reasoning
- Compound-engineering Brainstorm or Plan phase

## When to drop to `medium` or `low`
- Editing a known file with a known intent
- Renaming, formatting, doc fixes
- Running a one-shot tool invocation
- Bug fix with regression test already written
- Caveman summary turns

## Cache interaction
Do NOT change `/model` mid-session — invalidates the cached prefix (see `claude-usage-patterns.md` and source: Thariq, "Lessons from Building Claude Code"). `/effort` is a per-turn output-config knob and does NOT invalidate cache.

## Anti-patterns
- Never default to `xhigh` for a session of 80% mechanical edits
- Never use `max` "to be safe" — it costs 3-4x medium with marginal lift
- Never raise effort to compensate for vague prompts — fix the prompt instead (`prompt-formula.md`)

## Cross-refs
- `rules/opus-4-7.md` — xhigh is new default; pricing
- `rules/model-routing.md` — model picks come first, effort is the second knob
- `rules/task-budgets.md` — effort + budget combine for long agentic loops
- Source: SolarXpander cost-optimization writeup (2026-04-26)
