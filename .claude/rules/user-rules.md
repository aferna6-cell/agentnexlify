# User Rules — AgentNexLiFy Session Discipline

Four rules the user set on 2026-04-15. Non-negotiable for this project. All four are either enforced by hooks or cross-link to existing rules for reinforcement.

## Rule 1 — Plan First, Build Last
Before ANY implementation: present a plan, get approval, then execute. Plans state files touched, rule mappings, edge cases, commit intent.

**Why:** prevents wasted work when the user's intent differs from mine. Also gates 2+-file changes through review.

**How to apply:**
- Non-trivial work (2+ files, schema change, new service, architectural shift) → plan in text, wait for explicit "yes" / "looks good" / equivalent
- Trivial work (one-line fix, rename, typo) → execute directly
- Plan format: bullet list of files, rule mappings where relevant, edge cases, commit intent
- Reinforced by `ultrathink.md` plan-mode gate and `no-assumptions.md` 80% threshold

## Rule 2 — Ask When Unsure
Confidence below 80% on interpretation → ASK. Never guess scope, target, env, or destructive action.

**Why:** one clarifying question saves hours of wrong-direction work. Session transcripts show many bugs originated from assumed intent.

**How to apply:**
- Use `AskUserQuestion` tool for 2-4 structured choices
- Plain-text question for open-ended clarification
- Show the ambiguity explicitly ("X could mean A or B")
- Full spec: `.claude/rules/no-assumptions.md`

## Rule 3 — Every 15 Messages, Generate a Handoff Summary
Counter hook fires at the 15th, 30th, 45th, … user prompt. Inject directive forcing a summary before responding.

**Why:** long sessions risk context loss, compaction, or model drift. 15-message summary lets user paste into a fresh session without starting over.

**How to apply:**
- Enforcement: `scripts/claude-hooks/message-counter.sh` — reads `.claude/state/message-count`, increments each turn, outputs hookSpecificOutput when `count % 15 == 0`
- Summary format:
  1. What we're working on
  2. Decisions made this session
  3. Files changed + key paths (file:line references)
  4. Open questions / blockers
  5. Concrete next step
- Reset counter: delete `.claude/state/message-count` to restart cadence

## Rule 4 — Short Tasks Use Sonnet or Haiku; Opus Only for Deep Multi-Step Work
Tasks under ~30s → Haiku or Sonnet. Opus reserved for planning, architecture, complex decomposition.

**Why:** Opus is ~5x Sonnet, ~15x Haiku per token. Codeburn 30-day snapshot showed 99% of spend going to Opus ($312.42 of $316.13). Most of that was mechanical work that Sonnet/Haiku could have handled.

**How to apply:**
- If running in an Opus session and the task is mechanical (rename, format, lookup, grep, one-file edit) → delegate via `Agent` with `subagent_type` that routes to Sonnet/Haiku
- Keep Opus turns for: plan generation, architecture review, security-critical code review, decomposing ambiguous requirements
- Cross-reference: `.claude/rules/model-routing.md` advisor-executor pattern (Opus plans → Sonnet executes → Haiku cleans)

## Enforcement Summary
| Rule | Enforcement |
|---|---|
| 1. Plan first | Self-discipline + `ultrathink.md` plan-mode gate |
| 2. Ask when unsure | Self-discipline + `no-assumptions.md` hook (existing) |
| 3. 15-msg summary | `message-counter.sh` hook (non-bypassable) |
| 4. Model routing | Self-discipline + `model-routing.md` cross-ref |

## Scope
These rules apply to AgentNexLiFy sessions only (this repo). They do not bind sessions in other projects.
