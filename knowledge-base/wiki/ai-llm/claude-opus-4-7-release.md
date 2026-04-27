---
title: "Claude Opus 4.7 — Self-Verifying Agentic Intelligence at Opus 4.6 Pricing"
category: ai-llm
tags: ["claude", "opus-4-7", "self-verification", "xhigh-effort", "task-budgets", "agentic-coding"]
sources: ["raw/ai-llm/anthropic-claude-opus-4-7.md"]
created: 2026-04-17
updated: 2026-04-27
summary: "Opus 4.7 (claude-opus-4-7) lifts CursorBench to 70% vs 58%, resolves 3x more Rakuten-SWE-Bench production tasks than 4.6, and verifies its own outputs — same $5/$25 pricing."
---

# Claude Opus 4.7 — Self-Verifying Agentic Intelligence at Opus 4.6 Pricing

Anthropic shipped Claude Opus 4.7 on 2026-04-16 as a drop-in upgrade to Opus 4.6 — same $5/M input and $25/M output pricing, identical API surface aside from a new `xhigh` effort level and a public-beta `task_budget` parameter. The core advance is reliability on long-running agentic work: the model catches its own logical faults during the planning phase, reports missing data instead of fabricating plausible fallbacks, and runs proofs on systems code before starting implementation (Vercel's observation). Early-access partners report a pattern of step-change jumps — CursorBench from 58% to 70%, Rakuten-SWE-Bench 3x production-task resolution, XBOW visual-acuity from 54.5% to 98.5% — concentrated on the hardest class of multi-step coding work that previously required human supervision.

The model's behavioral shift matters more than the benchmark lift for anyone operating agents in production. Opus 4.7 pushes back in technical discussions rather than agreeing with the user (Replit), keeps executing through tool failures that stopped Opus 4.6 cold (Notion), and demonstrates loop resistance that Genspark flags as the single most critical production differentiator. Hex reports low-effort Opus 4.7 roughly matches medium-effort Opus 4.6, which compounds into real cost savings when task budgets and the `effort` parameter are tuned. For AgentNexLiFy, this changes the calculus on when to use Opus as an [[advisor-consult|advisor]] versus executor — see [[claude-opus-4-6-capabilities]] for the baseline being replaced.

Two changes affect token accounting and must be planned for. First, the tokenizer was updated; the same input can map to 1.0–1.35x more tokens depending on content, which invalidates existing `max_tokens` budgets and advisor brief ceilings. Second, at higher effort the model does substantially more thinking, especially in later turns of agentic loops, producing more output tokens in exchange for better reliability. Prompts tuned against Opus 4.6's looser instruction-following now execute to the letter — previously-loose interpretations that relied on the model skipping optional steps will over-scope. The mitigation is explicit scope marking in prompts plus the new `output_config.effort` parameter to dial depth up or down per call.

The beta `task_budget` lives under `output_config` with a 20k-token minimum and requires the `anthropic-beta: task-budgets-2026-03-13` header. Unlike `max_tokens`, which is a hard per-request cap the model cannot see, `task_budget` is an advisory budget the model prioritizes work against and paces itself toward. This is the right knob for nightly commit review, KB compile loops, and the issue-to-PR autopilot — places where a multi-hour agentic run needs to finish gracefully under a fixed spend. It is the wrong knob for interactive chat widget replies, where user-facing correctness beats cost pacing. See [[anthropic-managed-agents-architecture]] for the runtime decoupling that makes budget-aware long runs durable across session failures.

Two new operational disciplines ship alongside the model. Opus 4.7 performs **self-verification** automatically — it devises a verification step (unit tests, round-tripping outputs through a recognizer, proof sketches) before reporting completion — but the discipline rule in `.claude/rules/self-verification.md` forces an explicit `Verified: <check> — PASS/FAIL` line in every task-done message to make verification legible. The `/ultrareview` slash command launches a dedicated review session that flags bugs and design issues a careful human reviewer would catch; Pro and Max Claude Code users get three free reviews. CodeRabbit measured 10%+ recall improvement on difficult-to-detect bugs with no precision regression, which puts `/ultrareview` alongside the existing `code-reviewer` agent as a mandatory gate before merging anything over 20 LOC.

Vision capability also tripled — images up to 2,576 pixels on the long edge (~3.75MP), three times prior Claude models. This is model-level, not an API parameter; images are simply processed at higher fidelity. For AgentNexLiFy that unlocks pixel-perfect screenshot debugging of widget embeds, readable dense UI elements in dashboard renders, and viable computer-use workflows against OAuth dialogs and Stripe portals. The tradeoff is token cost per image scales with resolution, so batch workloads should still Haiku-triage first and reserve Opus 4.7 for screenshots where the detail actually matters.

## Key Concepts

- **xhigh effort** — New level between `high` and `max` introduced with Opus 4.7. Default in Claude Code on 4.7. Controls how much thinking the model does before responding; maps to the `effort` field in `output_config`.
- **Self-verification** — Built-in behavior where the model generates and runs a check against its own output before declaring done. Catches logical faults during planning, not just after execution.
- **Task budget** — Advisory token budget the model can see and pace against across a long agentic loop. Public beta; 20k minimum; requires beta header. Distinct from `max_tokens`, which is a hard per-request cap the model does not see.
- **Literal instruction following** — 4.7 executes prompts to the letter rather than inferring optional-ness from context. Requires explicit "this step is optional" markings where 4.6 would infer skip-ability.
- **Loop resistance** — Ability to recover from tool failures, ambiguous state, and repeated errors without entering an infinite retry loop. Genspark reports this as the single most critical production differentiator.

## Related Articles

- [[claude-opus-4-6-capabilities]] — The baseline model Opus 4.7 replaces; benchmark and pricing comparison.
- [[claude-sonnet-4-6-capabilities]] — Sonnet stays the default executor under the advisor-executor pattern; Opus 4.7 is the advisor.
- [[anthropic-managed-agents-architecture]] — Session durability + sandbox isolation that make long task-budget runs viable.
- [[anthropic-building-effective-agents]] — Pattern catalog for when agent autonomy actually pays off vs. simple workflows.

## Relevance to AgentNexLiFy

Opus 4.7 is the new default for planning, architecture review, and advisor-consult passes in the `backend/services/advisor_executor.py` runtime — swap the model ID from `claude-opus-4-6` to `claude-opus-4-7`, bump advisor `max_tokens` from 800 to 1200 to absorb the 1.35x tokenizer expansion, and leave Sonnet 4.6 as the executor. The real wins ship at the workflow layer: enable `task_budget` on the nightly commit review (20k-50k), KB compile loop (20k per article), and issue-to-PR autopilot (80k per issue) so those runs finish gracefully under budget instead of running hot. Mandate `/ultrareview` on every PR over 20 LOC and on every auth/payments/tenant-isolation touch — the 10% recall lift CodeRabbit measured is the kind of difference that catches the client_id-vs-tenant_id class of bug before it ships. **As of 2026-04-26 (PR #96), `.claude/rules/effort-per-prompt.md` codifies the per-prompt effort tuning discipline**: default `xhigh` is correct for agentic coding loops, but mechanical edits, renames, and single-file fixes should drop to `medium` (~1x baseline cost) or `low` (~0.5x). The rule also confirms that `/effort` is a per-turn output-config knob that does NOT invalidate the cached prefix — safe to dial without restarting the session. Avoid the trap of using Opus 4.7 for mechanical work: rename, grammar, and formatting still route to Haiku 4.5 per `.claude/rules/model-routing.md`; Opus 4.7's depth only pays off on ambiguous decomposition, security-critical review, and multi-step agentic loops.

Updated 2026-04-27 due to #96
