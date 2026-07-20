---
paths:
  - "**/*"
---

# No Assumptions — Ask When Uncertain

## Rule
Confidence <80% on correct interpretation → ASK before proceeding. One question now saves hours of wrong-direction work.

## Never guess at
- Which files to delete
- Which branch to target (main vs feature)
- Which env to deploy to (prod vs staging)
- What user meant by vague instructions
- Schema changes that could break production
- Scope ("refactor this" — refactor what, how far)
- Whether to commit/push

## How to ask
- Use `AskUserQuestion` for structured choices (2-4 options with header + multiSelect)
- Plain text question for open-ended clarification
- Show the ambiguity explicitly — "X could mean A or B"
- Offer your best guess + why you're unsure

## When safe to proceed without asking
- Read-only operations (Read, Grep, Glob)
- Reversible local edits in obvious scope
- Task is explicitly scoped in the request
- User said "just do it" or "your call"
- A cross-provider team issue supplies acceptance criteria and the team resolves ambiguity with repository evidence plus the quorum in `docs/TEAM_OPERATING_CONTRACT.md`

For Tier C team decisions, find a safe substitute and continue independent lanes. Ask only when the owner's intrinsic authority is required and no substitute exists.

## Confidence calibration
- 95%+ → proceed confidently
- 80-95% → proceed, state assumption
- 60-80% → proceed with caveat + commit reviewable
- <60% → STOP, ask
- <40% → definitely stop, full context request
