---
type: topic
name: "Claude Model Routing"
tags:
  - topic
  - ai
  - cost
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Claude Model Routing

## Definition
The rule for which [[Anthropic]] Claude model to use per task:
- `claude-haiku-4-5-20251001` — mechanical (grammar, formatting, renames, classification).
- `claude-sonnet-4-6` — code, debug, multi-file edits, most execution.
- `claude-opus-4-7` — planning, architecture, security design, critical review (xhigh effort
  default; $5/$25 per MTok).

## Why it matters
- A Codeburn snapshot showed ~99% of spend going to Opus, mostly on mechanical work Sonnet/Haiku
  could handle → route deliberately. Pairs with the [[Advisor-Executor Pattern]].

## Related
- [[Advisor-Executor Pattern]] · [[Anthropic]] · [[User Engineering Rules]]

## Provenance
- [[repo-agentnexlify-claude-md]] (model-routing + user rule 4)
