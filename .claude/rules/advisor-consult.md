---
paths:
  - "**/*"
---

# Advisor Consult — Opus 4.7 Intelligence Boost on Doubt

## Rule
When running as **Sonnet 4.6** or **Haiku 4.5** and confidence drops below **80%** on a non-trivial decision, invoke the `opus-advisor` agent for a short written brief before acting. Near-Opus intelligence at ~1.3x Sonnet cost, not 5x.

## Trigger conditions (any one → consult)
1. **Ambiguous decomposition** — request maps to 2+ valid architectures and user hasn't chosen
2. **Schema-touching change** — migration, Pydantic model, RLS-sensitive query
3. **Security-critical code** — auth, payments, tenant isolation, webhook signature, CORS
4. **Cross-file refactor** — 3+ files, unclear blast radius
5. **Regression fear** — change near a recently-fixed bug (check `docs/dev-knowledge/bug-patterns.md`)
6. **Novel pattern** — no prior example in the codebase to mirror
7. **Self-check fail** — user corrected the same mistake 2+ times this session

## Trigger conditions (DON'T consult)
- Confident rename, grammar fix, doc tweak
- Task explicitly scoped by an existing plan doc
- Task under 5 minutes (consult overhead > benefit)
- Mechanical cleanup with no semantic choice

## How to consult

### Dev-time (subagents)
```
Agent({
  subagent_type: "opus-advisor",
  prompt: "Task: <1-sentence>. Context: <3-5 bullet facts + file:line cites>. Ambiguity: <explicit list of 2+ interpretations>. Need: brief with files/constraints/gotchas/plan/test-gates/risks. Read-only."
})
```
Brief saved to `.claude/agent-comms/advisor-brief-{timestamp}.md`. Sonnet executor reads brief, executes, runs test gates.

### Product-runtime (Managed Agents)
`backend/services/advisor_executor.py` → `AdvisorExecutorRunner`. Opus 4.7 advises, Sonnet/Haiku Managed Agent executes. Opt-in via `advised_lead_qualifier()`, `advised_document_drafter()`, `advised_codebase_reviewer()` in `managed_agents_registry.py`.

## Cost model (keep spend near Sonnet)
- Advisor pass: ~300-500 Opus 4.7 output tokens ≈ **$0.05-0.15 per brief** ($25/MTok output)
- Executor pass: ~20-50k Sonnet tokens ≈ **$0.30-0.75 per execution**
- Net: ~1.15-1.3x pure-Sonnet cost
- Pure Opus baseline (no advisor): ~$2-5 per task
- **Savings: 65-80% vs pure Opus**

Advisor's `max_tokens` must stay tight (≤1200) or cost model breaks. New tokenizer on 4.7 is up to 1.35x prior count — old 800 budget became 600 effective, bumped to 1200 for headroom.

## Confidence signaling (when to escalate)
| Confidence | Action |
|------------|--------|
| 95%+ | Execute directly as Sonnet/Haiku |
| 80-95% | Execute with assumption stated in output |
| 60-80% | **Consult advisor first** |
| <60% | Consult advisor + `AskUserQuestion` |
| <40% | Stop, full context request from user |

## Failure semantics
- Advisor call fails (rate limit, JSON parse, timeout) → log warning, **fall back to pure executor**. Never block user-facing work on advisor.
- Executor failure bubbles up normally.
- Pattern already enforced in `backend/services/advisor_executor.py:297-312`.

## Opus 4.7 specifics (critical)
- Model ID: `claude-opus-4-7`
- **Do not pass** `temperature`, `top_p`, `top_k` — returns 400 error
- **Do not prefill assistant messages** — returns 400 error
- Extended thinking `thinking: {type: enabled, budget_tokens}` removed → use `thinking: {type: adaptive}` + `output_config.effort` when SDK supports it
- Advisor default is adaptive OFF (matches prior behavior, no extra latency)
- Tokenizer: up to 1.35x tokens for same text vs 4.6 — budget accordingly
- Literal instruction following: write prompts explicitly, don't rely on inference

## Pointers
- Rule: this file
- Subagents: `.claude/agents/opus-advisor.md`, `.claude/agents/sonnet-executor.md`
- Runtime: `backend/services/advisor_executor.py`
- Registry: `backend/services/managed_agents_registry.py`
- Model routing: `.claude/rules/model-routing.md`
- Project convention: Opus plans → Sonnet executes → Haiku cleans
