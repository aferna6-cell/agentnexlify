---
type: preference
name: "User Engineering Rules"
tags:
  - preference
  - working-style
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# User Engineering Rules

How [[Aidan Fernandes]] wants engineering work done (the 12 user rules + agent discipline).

## Process
- **Plan first, build last** — present a plan, get approval, then execute (2+ files / schema /
  architecture). Trivial fixes: just do them.
- **Ask when unsure** — confidence <80% on interpretation → ask, don't guess.
- **Opus only for deep work** — mechanical tasks go to Sonnet/Haiku (see [[Claude Model Routing]]).
- **Don't speed toward "working"; stop mid-task to rethink** if the design is wrong.

## Discipline
- No half-done migrations. Factor god classes (>600 lines) before extending.
- Never change a test to match assumed intent — code is wrong until the test author proves
  otherwise.
- New files over bloating existing ones; ship small additive wins.
- Deterministic-first: don't use an LLM for what a script can do.
- Smallest concrete change; no speculative abstraction/fallbacks/catch-all try-except.

## Voice
- See [[Builder Writing Voice]] and [[Caveman Mode]].

## Related
- [[Aidan Fernandes]] · [[Claude Model Routing]] · [[Daily Skills Gate]] · [[Caveman Mode]] · [[Builder Writing Voice]]

## Provenance
- [[repo-agentnexlify-claude-md]] (user-rules) · [[repo-agentnexlify-agents-md]]
