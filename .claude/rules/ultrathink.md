---
paths:
  - "**/*"
---

# UltraPlan + UltraThink — Extended Thinking Always

## Rule
Every question or task → use extended thinking. No exceptions for "simple" tasks.

## Process
1. Break complex problems into subproblems
2. Consider 2-3 approaches before picking one
3. Think about edge cases, failure modes, second-order effects
4. Plan before acting
5. If task touches 2+ files → enter plan mode FIRST

## Never skip
- The thinking step
- Plan mode for non-trivial work
- The "what can go wrong" question
- Edge case enumeration

## Dynamic gate
`scripts/claude-hooks/ultrathink-trigger.sh` fires on UserPromptSubmit when complexity keywords detected (architect, refactor, migrate, debug deep, etc.).

## Effort config
- Project `.claude/settings.json`: `"effortLevel": "high"`
- Global `~/.claude/settings.json`: `"effortLevel": "high"` + `"alwaysThinkingEnabled": true`

## Thinking vs acting balance
- Short question → think, then 1-3 sentence answer
- Multi-step task → think, plan mode, execute, verify
- Never sacrifice thinking for speed — bad code is slower than slow code
