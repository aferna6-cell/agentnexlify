---
name: triage-issue
description: Investigate a bug by exploring the codebase, identify root cause, and file a GitHub issue with TDD-based fix plan. Load when user says "triage this bug", "investigate this issue", "what's causing X", "root cause this", or pastes a bug report.
origin: https://github.com/mattpocock/skills/tree/main/triage-issue
version: 1.0.0
triggers:
  - triage this bug
  - investigate this issue
  - what is causing
  - root cause this
  - diagnose this
  - find the bug
---

# Triage Issue — Detective Work + TDD Fix Plan

Investigation FIRST, fix LATER. Output: GH issue with reproduction + root cause + failing test + fix plan.

## When to Use
- Bug reported with vague description
- Production error with stack trace
- Reproducible-but-unexplained behavior
- Regression after recent deploy
- Customer report ("X stopped working")
- Sentry alert needing classification

## When NOT to Use
- Bug already triaged, just needs fix → use `fix-bug` command
- One-line typo fix obvious from error
- Feature request (not a bug) → use `write-prd`
- "How does X work?" research → use RESEARCH prompt from PROMPTLIBRARY

## Process (4 phases — Superpowers methodology)

### Phase 1 — Reproduce
- Get exact reproduction steps
- Identify minimum input that triggers bug
- Confirm bug exists in current `main` (not stale)
- Note: tenant context, environment, browser if applicable
- If can't reproduce → STOP, escalate to user with what was tried

### Phase 2 — Narrow
- Read the failing code path top-to-bottom
- Trace data flow — where does input enter, where does it diverge from expected?
- Check git log for recent changes to that path: `git log --oneline -10 -- <file>`
- Check `docs/dev-knowledge/bug-patterns.md` — known similar bug?
- Use `gitnexus_query({query: "<error keyword>"})` if available
- Check tests — does an existing test cover this path? Why didn't it catch?

### Phase 3 — Diagnose
- State the root cause in one sentence: "X happens because Y"
- Identify the smallest possible fix
- Identify what regressed (commit that introduced bug, if any)
- Check if known anti-pattern: `client_id` vs `tenant_id`, `from __future__ import annotations`, missing widget byte-sync, RLS missing `client_id` filter

### Phase 4 — File Issue
- Open GH issue with reproduction + root cause + fix plan + test plan
- Tag `bug`, severity (`severity/critical|high|medium|low`), `ai-ready` if scoped tightly enough for `issue-to-pr-loop`
- DO NOT FIX in this skill — handoff to fix-bug or issue-to-pr-loop

## Issue Template
```markdown
## Bug
<one-sentence description>

## Reproduction
1. <step>
2. <step>
3. Observed: <wrong behavior>
4. Expected: <right behavior>

## Environment
- Tenant: <client_id or "any">
- Env: <prod|staging|local>
- Browser: <chrome 120|n/a>
- Version/commit: <sha>

## Root Cause
<one sentence>: X happens because Y at <file:line>

## Evidence
- Stack trace: <paste relevant frames>
- Logs: <paste relevant lines>
- Related code: <file:line> with quote
- Last touched by commit: <sha> on <date>

## Fix Plan (TDD)
1. **Failing test first**: write `<test_name>` in `<test_path>` that reproduces bug. Verify it FAILS on current main.
2. **Minimal fix**: change `<file:line>` from `<old>` to `<new>`.
3. **Verify**: test now PASSES. Run full suite — no regressions.
4. **Add to bug-patterns.md**: capture the antipattern so it doesn't recur.

## Risk
- Blast radius: <files touched + downstream callers>
- Reversibility: <revert is safe / migration involved>
- Tenant impact: <single | all | none>

## Labels
bug, severity/<level>, layer/<backend|frontend|widget>, ai-ready (if scoped)
```

## Antipattern checklist (AgentNexLiFy)
Before filing root cause, check if bug is one of these known patterns:
- [ ] Used `tenant_id` instead of `client_id` on leads/conversations
- [ ] Used `lead_stage` or `service_interest` (columns that don't exist)
- [ ] Has `from __future__ import annotations` in FastAPI router file
- [ ] Widget JS in `widget/` doesn't match `frontend/public/widget/` byte-for-byte
- [ ] Used `localStorage` in React artifact code
- [ ] Schema change not in numbered migration file
- [ ] Query missing `client_id` filter (cross-tenant leak)
- [ ] Webhook handler not verifying signature
- [ ] Pydantic model defined with deferred annotations causing 422

## Cross-refs
- Companion: `fix-bug` command, `issue-to-pr-loop` skill, `tdd-workflow` skill
- `docs/dev-knowledge/bug-patterns.md` — known patterns to check first
- `.claude/rules/workflow-orchestration.md` — anti-desperation rule
- `PROMPTLIBRARY.md` — DEBUG Bug Triage prompt
