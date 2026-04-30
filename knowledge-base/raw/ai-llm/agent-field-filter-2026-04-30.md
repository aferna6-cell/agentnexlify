# Agent Field Filter — What to Adopt, What to Skip

**Source:** community essay 2026-04-30 ("what's signal, what's noise wearing the costume of urgency")
**Captured:** 2026-04-30
**Status:** raw — pending /kb-compile

## Core thesis
Field has no destination yet. Frameworks obsolete in a quarter. Don't chase launches — pick durable primitives, skip wrappers, build evals.

## The 5-test filter (use before adopting anything)

1. **Will it matter in 2 years?** Wrappers/CLI flags = no. Primitives (protocols, memory patterns, sandboxing) = often yes.
2. **Has someone respected built real on it + written honestly?** Postmortems > marketing. "We tried X in prod and here's what broke" > 10 launch posts.
3. **Adoption requires throwing away tracing/auth/retries?** Framework-trying-to-be-platform = 90% mortality. Good primitives slot in.
4. **Cost of skipping for 6 months?** Usually nothing. Skips 90% of launches. Pretending this is "falling behind" is the trap.
5. **Can I measure if it helps my agents?** Without evals, you ship on vibes. With evals, the data picks the model.

## Habit
On every launch: write down what you'd need to see in 6 months to believe it matters. Come back. Most questions answer themselves.

## Durable primitives (these compound)

- **Context engineering** — context = state. Every irrelevant token costs reasoning quality. Active summarization, compression, pruning. Read: Anthropic "Effective Context Engineering for AI Agents" + multi-agent research postmortem.
- **Tool design** — 5-10 well-named tools beat 20 mediocre. Names = English verb phrases. Descriptions include when-not-to-use. Error messages = feedback model can act on. "Max tokens 500 exceeded, summarize first" beats "400 Bad Request" — 40% retry reduction reported.
- **Orchestrator-subagent pattern** — single-agent default. Reach for orchestrator-subagent only when single hits real wall (context pressure, sequential latency, task heterogeneity). Subagents read-only with focused contexts. Orchestrator owns writes. Anthropic research system + Claude Code subagents = canonical shape.
- **Evals + golden dataset** — harvest production traces, label failures, regression set. LLM-as-judge for subjective, exact-match for rest. 50 hand-labeled examples is enough to start. Day-one investment, 10x cheaper than retrofitting.
- **File-system-as-state** — think/act/observe/repeat. FS or structured store as truth. Every action logged + replayable. Claude Code, Cursor, Devin, Aider — all converged.
- **MCP (conceptually)** — agent capabilities + tools + resources, extensible auth/transport. Linux Foundation steward. "USB-C of AI."
- **Sandboxing as primitive** — process isolation, network egress, secret scoping, auth boundaries. Bolt-on after security review = lose deal. Build in week one.

## What to skip (April 2026)

- AutoGen/AG2 production
- CrewAI new builds
- Microsoft Semantic Kernel (unless MS-locked)
- DSPy as general framework
- Standalone code-as-action architecture
- "Autonomous agent" pitches (AutoGPT/BabyAGI dead in product form)
- Agent app stores
- Horizontal "build any agent" enterprise platforms
- SWE-bench/OSWorld leaderboard chasing
- Naive parallel multi-agent (5 agents on shared memory = fail)
- Per-seat SaaS pricing (market moved to outcome/usage-based)
- This week's HN framework — wait 6 months

## Production picks (April 2026)

| Layer | Pick |
|---|---|
| Orchestration | LangGraph (default), Mastra (TS), Pydantic AI (Python type-safe) |
| Provider SDK | Claude Agent SDK / OpenAI Agents SDK *inside* LangGraph nodes |
| Protocol | MCP, full stop |
| Memory | Mem0 (chat), Zep (entity-tracking convos), Letta (multi-day agents) |
| Tracing/evals | Langfuse (OSS), LangSmith (LangChain shops), Braintrust (research evals) |
| Sandbox | E2B (code), Browserbase + Stagehand (browser), Anthropic Computer Use (OS), Modal (bursts) |
| Models | Sonnet 4.6 (cost-perf), Opus 4.7 (reliable tools/multi-step), GPT-5.4/5.5 (CLI/terminal), Gemini 2.5/3 (long-context/multimodal), DeepSeek-V3.2/Qwen 3.6 (cost) |

Treat models as swappable. If agent only works with one = smell, not moat. Re-evaluate quarterly.

## Move sequence

1. Pick ONE measurable outcome (not platform). Evals target = day one.
2. Tracing + evals BEFORE shipping. 50 hand-labeled = enough to start.
3. Single-agent loop. LangGraph or Pydantic AI. 3-7 well-designed tools. FS as state.
4. Treat agent as product not project. Failures = roadmap.
5. Add scope only when failure modes pull it in (subagents, memory, computer-use).
6. Boring infra (MCP, E2B/Browserbase, existing Postgres + auth + obs).
7. Watch unit economics from day one. PoC $0.50/run = $50K/month at scale.
8. Re-evaluate models quarterly, not weekly.

## Watch list (next 2 quarters)

- Replit Agent 4 parallel forking
- Outcome-based pricing maturity (Sierra, Harvey)
- Skills as packaging layer (AGENTS.md proliferation)
- Claude Code 47% regression postmortem → online eval discipline
- Voice surpassing text for support (Sierra Q4 2025)
- Open-model agent capability closing gap (DeepSeek-V3.2 native thinking-into-tool, Qwen 3.6)

## Mapping to AgentNexLiFy

| Primitive | Project state |
|---|---|
| Context engineering | Partial — `one-task-one-chat.md` covers it. No active context pruning in agent loops. |
| Tool design | Strong — managed_agents_registry.py + advisor-executor pattern |
| Orchestrator-subagent | Strong — compound-engineering skill, 5-agent pipeline |
| Evals + golden dataset | **Gap** — no golden dataset for Lead Qualifier or any managed agent |
| File-system-as-state | Strong — plans/, audits/, specs/, memory/ |
| MCP | Strong — Supabase + Playwright + Chrome DevTools wired |
| Sandboxing | **Gap** — widget runs untrusted JS, no E2B layer |
| Tracing | **Partial** — logger.info on llm_runtime; no JSONL trace file or eval pipeline |

## Action items

1. **Golden dataset for Lead Qualifier** — 50 inbound leads → expected (intent_score, fit_score, recommendation). Pytest harness. CI flag.
2. **JSONL trace on llm_runtime** — every Claude call → `logs/llm_traces/*.jsonl`. Foundation for #1 + cost dashboard.
3. **`/agent-filter` skill** — codify 5-test filter as gate when user proposes adoption.
4. **Friday reading routine** — scheduled agent: Anthropic eng blog + Simon Willison + Latent Space → weekly digest.
5. **Sandbox eval** — investigate E2B for widget JS execution path.

## Cross-refs
- `.claude/rules/model-routing.md` — advisor-executor pattern
- `.claude/skills/compound-engineering/SKILL.md` — 5-agent pipeline
- `.claude/rules/one-task-one-chat.md` — context hygiene
- `backend/services/llm_runtime.py` — tracing extension target
- `backend/services/lead_qualification.py` — golden dataset target
