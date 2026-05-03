---
name: premortem
description: Stress-test a plan by assuming it already failed 6 months out. Forces failure-mode enumeration before execute. Load when user says "premortem this", "stress-test this plan", "what could kill this", or before merging architectural PRs / shipping multi-week features / locking pricing or schema changes.
origin: Klein 2007 "Performing a Project Premortem" (HBR); Kahneman endorsed in Thinking Fast and Slow
version: 1.0.0
triggers:
  - premortem this
  - premortem
  - stress-test this plan
  - kill this plan
  - what could kill this
  - assume this failed
  - 6 months from now this is dead
---

# Premortem — Failure-First Plan Stress Test

Flips confirmation bias. Default LLM behavior validates plans. Premise "plan already failed" turns off optimism, forces concrete failure enumeration. Maps to `claude-usage-patterns.md` Pattern 7 (Stress-Test Strategy) — sharper version.

## When to Use
- Plan exists (PRD, spec, architecture doc) AND execute hasn't started
- Multi-week feature about to enter compound-engineering Execute phase
- Architectural decision with hard-to-reverse blast radius (schema, pricing, auth)
- Pre-merge gate on >100-line PR touching tenant isolation / payments / migrations
- Pre-launch gate on customer-facing change (new pricing tier, plan rename, widget rework)
- User says "premortem this" + provides a plan or links a spec/PRD
- After grill-me + write-prd produced a draft plan, before prd-to-issues

## When NOT to Use
- No plan exists yet → use `grill-me` then `write-prd` first
- Trivial change (one-line, rename, doc fix)
- Plan already executed → run postmortem instead, not premortem
- Time-boxed exploration / spike — failure is acceptable, point is learning
- User explicitly says "just ship it"

## Where this fits in the workflow

```
Brainstorm → grill-me → write-prd → PREMORTEM → prd-to-issues → Execute → Review → /ultrareview → ship
```

Different from grill-me: grill-me resolves ambiguity BEFORE plan exists. Premortem stress-tests AFTER plan exists, before execute. Different gate.

## Step 0 — Plan ingestion
1. Read the plan/spec/PRD fully. Path or paste — both fine.
2. Echo back in 5 bullets: goal, scope, key technical bets, dependencies, success metric.
3. Confirm with user: "This is what I'm stress-testing. Right?"
4. Wait for confirm or correction. Then start Step 1.

Reason: premortem on misread plan = wasted cycles.

## Step 1 — Frame the failure
Open with the premise, literally:

> "It is [TODAY + 6 months]. The plan is dead. Users abandoned it / launch was rolled back / engineering team is rewriting it from scratch. I am writing the postmortem. Below are the ways it died."

Don't soften. Don't hedge. Don't "this could happen" — "this is what happened." Premise is failure. Job is forensics.

## Step 2 — Failure mode enumeration (batch, by category)

Generate 8-12 failure modes minimum, grouped by category. One category per message. Each failure gets:
- **Title** (one line, concrete)
- **Story** (3-5 sentences — what specifically happened, in order)
- **Early warning signs** (signals that would have predicted it 1-3 months out)
- **Severity** (LOW / MEDIUM / HIGH / CRITICAL)
- **Likelihood** (LOW / MEDIUM / HIGH)

Categories to cover (AgentNexLiFy-specific):

**Technical**
- Schema migration partial-applied → tenant data corrupt
- Widget byte-drift between `widget/` and `frontend/public/widget/`
- `client_id` vs `tenant_id` regression (3+ prior incidents)
- N+1 query under load → latency spike at 100+ tenants
- Anthropic API rate limit / outage with no fallback path
- Race condition between Stripe webhook + lead row creation

**Product / UX**
- Feature solves wrong problem (no tenant actually wanted it)
- Empty state breaks for tenants with 0 leads
- Mobile widget behavior diverges from desktop
- AI response quality regresses for vertical KB tenants
- Pricing tier confusion → churn or revenue loss

**Tenant / Multi-tenant**
- RLS policy gap → cross-tenant data leak
- One large tenant's load degrades small-tenant experience
- Plan rename breaks legacy contract enforcement
- Onboarding flow assumes US-only (Twilio E.164, timezone, currency)

**Operational**
- Migration #N applied to staging but not prod (or vice-versa)
- Dependency upgrade ships breaking change with no test coverage
- Hook bypass during rushed deploy → secret leaked
- Cron job silently fails for 3 weeks

**Adoption / Business**
- No tenant onboards within 30 days of ship
- Sales partner can't explain feature to prospect
- Competitor (GoHighLevel) ships same thing 2 weeks later, cheaper
- Hours-saved metric flat → churn uplift theory disproven

Don't generate every category. Pick the 3-5 most relevant to the specific plan. Quality > coverage.

## Step 3 — Synthesis

After all failure modes enumerated, output the synthesis block:

```
SYNTHESIS

Most likely failure
- <title> — <one-line why>

Most dangerous failure (highest blast radius)
- <title> — <one-line blast description>

Biggest hidden assumption
- <the load-bearing belief that, if wrong, the plan can't survive>
- Why it's hidden: <where in the plan it's implicit, never stated>
- How to test cheaply BEFORE execute: <concrete check>

Top 3 early warning signs to monitor
1. <signal> — measurable how, threshold what
2. <signal>
3. <signal>

Revised plan (gaps closed)
- <change 1>: <what + why>
- <change 2>
- <change 3>

Decision
- PROCEED with revised plan
- PAUSE — test hidden assumption first via <concrete check>
- KILL — premise is broken (rare; only when hidden assumption already disproven by evidence in the codebase / KB / past audit)
```

## Output rules

- Concrete failures with file paths / table names / endpoint names. No generic "tech debt" / "scope creep" filler.
- Stories in past tense, active voice. Subject + verb + consequence. "Migration 102 ran in staging, dropped in prod, two tenants lost lead history overnight."
- Early warning signs must be observable in our stack (logs, metrics, tests, KB articles, dashboards). No "vibes."
- Severity + likelihood not optional — forces ranking later.
- Synthesis section is the deliverable. Failure list is supporting evidence.

## Anti-patterns

- Generic risk lists ("scope creep", "team burnout") — useless
- Hedging language ("could", "might") — premise is past tense, plan is dead
- Premortem on a half-baked plan — go back to grill-me + write-prd
- Premortem AND execute in same session — split chats per `one-task-one-chat.md`
- Skipping synthesis — failure list without ranking is noise
- 50+ failure modes — diluted signal; cap at 12

## Cross-refs

- `.claude/rules/claude-usage-patterns.md` Pattern 7 (Stress-Test Strategy)
- `.claude/rules/claude-usage-patterns.md` Pattern 1 (Fight Me) — adjacent technique
- `.claude/skills/grill-me/SKILL.md` — pre-plan ambiguity resolution
- `.claude/skills/write-prd/SKILL.md` — produces the plan being stress-tested
- `.claude/skills/compound-engineering/SKILL.md` — slot premortem between Plan and Execute
- `.claude/rules/ultrareview.md` — post-execute review (different gate)
- `.claude/rules/no-assumptions.md` — surface hidden assumptions

## Source

Gary Klein, "Performing a Project Premortem", Harvard Business Review (2007). Endorsed by Daniel Kahneman in Thinking, Fast and Slow as single most valuable decision-making technique. Adopted by Google, Goldman Sachs, Procter & Gamble pre-launch.
