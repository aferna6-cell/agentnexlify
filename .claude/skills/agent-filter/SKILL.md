---
name: agent-filter
description: 5-test signal-vs-noise filter for AI agent ecosystem adoption. Load when user proposes adopting a new agent framework, library, protocol, model, or tool. Triggers on "should we use X", "thinking about adopting X", "X just launched, should we look at it", "is X worth it", "evaluate X", or any framework/library/tool name not already in the project stack.
origin: knowledge-base/raw/ai-llm/agent-field-filter-2026-04-30.md
version: 1.0.0
triggers:
  - should we use
  - should we adopt
  - thinking about adopting
  - is X worth it
  - just launched
  - evaluate this framework
  - new agent framework
  - run agent-filter
  - /agent-filter
---

# Agent Filter — 5-Test Signal vs Noise

Forces a structured adoption decision BEFORE the project takes on a new dependency, framework, model, or pattern. The agent space ships 10 launches a week; 90% are noise. This skill rejects noise cheaply.

Maps to `knowledge-base/raw/ai-llm/agent-field-filter-2026-04-30.md` (KB source) and complements `.claude/rules/fill-instructions-before-guessing.md` (pre-flight discipline).

## When to Use
- User proposes adopting a new agent framework (LangGraph, AutoGen, CrewAI, Mastra, etc.)
- User proposes a new model swap or provider change
- User proposes a new MCP server, sandbox vendor, eval tool, memory store
- User asks "should we look at X" or "X just launched, are we behind?"
- Adoption decision involves >1 day of integration work
- Decision touches the model layer, orchestration layer, or tool boundary

## When NOT to Use
- Bug fix, doc tweak, rename — adoption filter not relevant
- Internal-only refactor — no external dependency change
- Already in the stack (LangGraph, MCP, Anthropic SDK, Supabase, Anthropic Managed Agents) — re-eval quarterly, not per-prompt
- Trivially reversible (small npm dep) — just try it

## The 5 Tests

Run all five. Score each PASS / FAIL / UNKNOWN. Adopt only on >=3 PASS + zero hard FAIL on tests 3 or 4.

### Test 1 — Will it matter in 2 years?
- PASS: durable primitive (protocol, memory pattern, sandbox layer, orchestration shape)
- FAIL: wrapper, CLI flag, this-week's-HN-framework
- UNKNOWN: too new to tell — default FAIL

Examples:
- MCP → PASS (Linux Foundation steward, "USB-C of AI")
- Naive parallel multi-agent on shared memory → FAIL
- AutoGPT-style autonomous agent → FAIL (already dead in product form)

### Test 2 — Has someone respected built real on it + written honestly?
- PASS: a postmortem, a "we tried X in prod and here's what broke" essay, an Anthropic engineering blog
- FAIL: 10 launch posts and zero failure analysis
- UNKNOWN: only marketing material → default FAIL

Source priority: postmortems > vendor blog > launch posts > Twitter hype.

### Test 3 — Adoption requires throwing away tracing/auth/retries? (HARD FAIL)
- PASS: slots into existing tracing (Langfuse), auth (Supabase RLS), retries (httpx + tenacity)
- FAIL: framework-trying-to-be-platform — replaces our existing infra
- UNKNOWN → treat as FAIL

If FAIL here, stop. 90% mortality on platforms-disguised-as-frameworks.

### Test 4 — Cost of skipping for 6 months? (HARD FAIL ONLY IF EVIDENCE OF REAL COST)
- PASS: skipping costs nothing measurable — just delayed exposure
- FAIL: real customer asked for it OR competitor shipped it OR our agents fail without it
- UNKNOWN → default PASS (skipping is cheap by default)

The "falling behind" feeling is almost always the trap. Demand evidence of real cost.

### Test 5 — Can I measure if it helps my agents?
- PASS: golden dataset exists OR can be built in <1 day, A/B comparison feasible
- FAIL: no eval harness, would ship on vibes
- UNKNOWN: gap — build the eval first, then re-run filter

For AgentNexLiFy: Lead Qualifier golden set lives at `backend/tests/evals/lead_qualifier_golden.json` (10 examples). Use it.

## Output Shape

When invoked, produce:

```
# Filter: <thing under consideration>

| Test | Result | Evidence |
|------|--------|----------|
| 1. Matters in 2yr | PASS/FAIL/UNK | <citation> |
| 2. Real-world postmortem | PASS/FAIL/UNK | <link or "none found"> |
| 3. No re-platform | PASS/FAIL/UNK | <what it replaces> |
| 4. Skip-cost | PASS/FAIL/UNK | <real cost or "none"> |
| 5. Measurable | PASS/FAIL/UNK | <eval harness path or "build first"> |

Verdict: ADOPT / DEFER / SKIP
Re-evaluate: <date or trigger>
```

## Adoption Habits (apply on every PASS verdict)

1. Pin the version. Don't track HEAD.
2. Add to `.claude/rules/model-routing.md` or `.claude/rules/plugins.md` as appropriate.
3. Add a smoke test to `backend/tests/` or a build-time check.
4. Set a 90-day re-eval calendar entry.
5. If it touches a Managed Agent, add a row to `backend/tests/evals/lead_qualifier_golden.json` covering the new behavior.

## Skip List Reminder (April 2026)

Already filtered out — do not re-relitigate without new evidence:

- AutoGen / AG2 production builds
- CrewAI new builds
- Microsoft Semantic Kernel (unless MS-locked)
- DSPy as general framework
- Standalone code-as-action architectures
- "Autonomous agent" pitches (AutoGPT/BabyAGI dead in product form)
- Agent app stores
- Horizontal "build any agent" enterprise platforms
- SWE-bench/OSWorld leaderboard chasing
- Naive parallel multi-agent (5 agents on shared memory)
- Per-seat SaaS pricing (market on outcome/usage)
- Kimi K2.6 / GPT-5.5 cross-provider auto-routing — vendor-blog claims, no postmortem, no cross-model eval harness in repo. Re-eval trigger: monthly LLM spend exceeds $200 in `logs/llm_traces/` aggregated by month.

## Production Picks (April 2026, treat as reference, re-evaluate quarterly)

| Layer | Pick |
|-------|------|
| Orchestration | LangGraph (default), Mastra (TS), Pydantic AI (Python type-safe) |
| Provider SDK | Anthropic SDK direct, or Claude Managed Agents for tenant agents |
| Protocol | MCP, full stop |
| Memory | Mem0 (chat), Zep (entity), Letta (multi-day) |
| Tracing/evals | Langfuse OSS, LangSmith, Braintrust |
| Sandbox | E2B (code), Browserbase + Stagehand (browser), Modal (bursts) |
| Models | Sonnet 4.6, Opus 4.7, Haiku 4.5 |

Models are swappable. If our agent only works with one, that's a smell, not a moat.

## Anti-patterns

- Running this filter on a tool already in the stack → just trust the prior verdict, re-eval quarterly
- Skipping Test 5 because "evals are hard" → that's the test failing. Build the eval first.
- Adopting on Test 4 alone — "we'll fall behind" is the trap, not the signal
- Running the filter then adopting anyway because the framework is shiny — at that point delete the filter, save the time

## Cross-refs

- `knowledge-base/raw/ai-llm/agent-field-filter-2026-04-30.md` — source article + AgentNexLiFy gap analysis
- `.claude/rules/fill-instructions-before-guessing.md` — pre-flight discipline
- `.claude/rules/model-routing.md` — model picks already filtered
- `.claude/rules/plugins.md` — plugin picks already filtered
- `backend/tests/evals/lead_qualifier_golden.json` — measurability harness for Test 5
