---
name: grill-me
description: Socratic clarifying questions before any new feature, refactor, or risky migration. Load when user says "grill me", "interview me", "clarify this feature", "what am I missing", or proposes new work touching 2+ files in backend/, frontend/, widget/, or migrations/.
origin: https://github.com/mattpocock/skills/tree/main/grill-me
version: 1.0.0
triggers:
  - grill me
  - interview me on
  - clarify this feature
  - what am I missing
  - help me think through
  - before I build
---

# Grill Me — Socratic Pre-Build Interview

Forces decision-tree resolution BEFORE code. Batch 5-8 questions per branch in ONE message. Maps to `claude-usage-patterns.md` Pattern 2 (Interview First).

Opus 4.7 follows instructions literally and each turn layers interpretations from prior turns. Drip-feed questioning compounds drift. Batch mode keeps context flat. See `rules/opus-4-7-prompting.md` section 1.

## When to Use
- New feature spec (any file in `specs/`)
- Refactor touching 3+ files
- Schema change (any `migrations/NNN_*.sql`)
- New tenant onboarding pattern
- New widget capability
- Pricing/plan change
- Any task where user said "build X" without spec

## When NOT to Use
- One-line fix
- Typo/rename
- User already wrote PRD (use `write-prd` to extend, not interview from scratch)
- User explicitly says "just do it"

## Loop (batch mode)
1. Read user request
2. Identify ambiguities by branch (data model, edges, failures, existing, scope, success)
3. Batch 5-8 numbered questions for ONE branch in ONE message
4. Wait for ALL answers
5. Update mental model from aggregated answers, branch next bucket based on what changed
6. Batch next 5-8 questions for next branch
7. Repeat until every branch resolved. Target 40+ total questions across branches.
8. Output: structured summary of resolved decisions → hand off to `write-prd` or `compound-engineering`

Never drip one question at a time. Never mix branches in one batch — one branch per message keeps answers aligned.

## AgentNexLiFy question buckets

**Data model:**
- Which table(s)? Does this touch `leads`, `conversations`, `appointments`, `tenants`, `subscriptions`?
- Tenant scope: `client_id` only, or cross-tenant?
- Column to add/change/remove? Migration number assigned?
- RLS policy needed? Public read or service-role only?

**Edge cases:**
- What if tenant has 0 leads? 100k leads?
- What if conversation has no messages?
- What if Stripe webhook fires before lead row exists?
- Mobile vs desktop widget behavior?

**Failure modes:**
- Anthropic API down → fallback?
- Resend rate limit → queue or drop?
- Twilio E.164 invalid → user feedback?
- Migration partial-applied → rollback strategy?

**Existing systems:**
- Does an endpoint already exist? Grep `backend/routers/`
- Does a similar dashboard page exist? Look in `frontend/src/pages/`
- Is there a knowledge-base article? Check `knowledge-base/wiki/`
- Schema-guard skill needed? Yes if touching `leads` or `conversations`

**Scope:**
- Backend only? Frontend only? Widget too?
- One tenant or all tenants?
- Behind feature flag?
- Reversible if it goes wrong?

**Success criteria:**
- How do we know it works?
- What metric moves?
- What test proves it?
- What does the user see?

## Output format
After grilling complete:
```
RESOLVED DECISIONS
- Data: <table.column, RLS, tenant scope>
- Edges: <covered cases + chosen behavior>
- Failures: <fallback per dependency>
- Existing: <reused vs new>
- Scope: <files, layers, flag, reversible y/n>
- Success: <metric, test, UX>

OPEN QUESTIONS (escalate to user)
- <question> — blocks <next step>

NEXT
→ Hand off to: write-prd | compound-engineering | direct execution
```

## Cross-refs
- `.claude/rules/opus-4-7-prompting.md` §1 — batch-mode clarification
- `.claude/rules/no-assumptions.md` — confidence <80% → ask
- `.claude/rules/user-rules.md` Rule 2 — ask when unsure
- `.claude/rules/claude-usage-patterns.md` Pattern 2 — Interview First
- `PROMPTLIBRARY.md` — REASON Implementation Plan prompt
- Companion skill: `write-prd`
