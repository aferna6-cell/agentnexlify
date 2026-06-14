---
name: systematic-debugging
effort: high
description: 4-phase debugging methodology — reproduce, narrow, diagnose, verify. Forbids random "just try changing stuff" edits. Load when user says "debug systematically", "this is broken", error message pasted, stack trace shared, or when fix-bug needs depth.
origin: https://github.com/obra/superpowers/tree/main/skills/systematic-debugging
version: 1.0.0
triggers:
  - debug systematically
  - this is broken
  - debug this
  - figure out why
  - cannot reproduce
  - flaky test
---

# Systematic Debugging — 4-Phase Discipline

NO random changes. NO "let me try this". Each phase has an exit criterion. If criterion fails, return to previous phase.

## When to Use
- Bug not understood after first read of error
- Flaky test that passes 80% of the time
- Production behavior different from local
- Stack trace points to working code (real cause is upstream)
- Regression after a recent commit
- "It worked yesterday"

## When NOT to Use
- Obvious typo from error message (just fix it)
- Hot-path performance work (use `performance-optimizer` agent)
- Security incident requiring immediate containment (escalate first)
- Bug already triaged with fix plan (skip to execution)

## Anti-patterns this skill forbids
- "Let me just try X and see"
- Adding `console.log` everywhere then forgetting them
- Bumping retry counts to mask the real failure
- Catching exceptions to silence them without understanding
- Asking the LLM "fix this" without showing what was tried
- Reverting commits without first knowing if they CAUSED the bug
- Re-running tests until they pass (flaky != fixed)

## Phase 1 — Reproduce
**Exit criterion:** I can trigger the bug at will, with the smallest input.

Steps:
1. Get exact reproduction from reporter (what they did, what they saw)
2. Reproduce locally with same input
3. If can't reproduce → list 3 differences (env, data, version) → control for each
4. Once reproduced, REDUCE input to minimum that still triggers
5. Write a failing test that captures it (red bar = reproduction proof)

If you can't reproduce after 30 min → STOP. Escalate with: what was tried, what was different, what you need from reporter.

## Phase 2 — Narrow
**Exit criterion:** I know the smallest code region that contains the bug.

Steps:
1. Read the failing code path top-to-bottom
2. `git log --oneline -10 -- <file>` — recent changes?
3. `git bisect` if regression — find first bad commit
4. Trace data flow: input → mutation → output. Where does observed diverge from expected?
5. Add `print` at boundary, NOT inside loop. Confirm data matches expectation at each boundary.
6. Eliminate sections that behave correctly (binary search the call graph)
7. Use `gitnexus_query({query: "<error keyword>"})` if available

Forbidden: changing code in Phase 2. ONLY observation.

## Phase 3 — Diagnose
**Exit criterion:** I can state root cause in one sentence: "X happens because Y at file:line."

Steps:
1. Write the root cause sentence
2. Identify the smallest possible fix
3. Identify why existing tests didn't catch (new test gap → backlog)
4. Identify if this is a known antipattern (check `docs/dev-knowledge/bug-patterns.md`)
5. Identify blast radius — who else depends on this code path
6. Decide: fix here, fix upstream, or fix both

If diagnosis is "looks like X is broken" without precision → return to Phase 2.

## Phase 4 — Verify
**Exit criterion:** failing test now passes, nothing else broke, root cause documented.

Steps:
1. Apply the minimal fix
2. Re-run the failing test from Phase 1 — must PASS
3. Run full test suite — must show no new failures
4. Run linter / type checker
5. Manual smoke test of related functionality (regression check)
6. Update `docs/dev-knowledge/bug-patterns.md` with the antipattern
7. Commit with message: "fix: <one-line root cause>"

If any step fails → return to Phase 3 (wrong diagnosis) or Phase 2 (wrong region).

## AgentNexLiFy specifics
Phase 2/3 checklist — is this one of these?
- `client_id` vs `tenant_id` mismatch on leads/conversations
- `from __future__ import annotations` in FastAPI router → 422 on every request
- Widget JS drifted between `widget/` and `frontend/public/widget/` → breaks tenant embeds
- Missing `client_id` filter in query → cross-tenant data leak
- Pydantic deferred annotation → string body resolution failure
- Plan name typo (`foundation`/`operations` retired)
- Stripe webhook signature not verified → spoof risk
- Resend rate limit hit silently → email queue corruption

## Output (per debugging session)
```markdown
## Bug
<one sentence>

## Phase 1 — Reproduction
- Minimum input: <X>
- Failing test: <path>::<name>
- Reproducible: <yes/no, %>

## Phase 2 — Narrowing
- Code region: <file:line-range>
- Recent changes: <commits>
- Data flow boundary where divergence appears: <description>

## Phase 3 — Diagnosis
- Root cause: <X happens because Y at file:line>
- Smallest fix: <change>
- Blast radius: <files + callers>
- Antipattern match: <yes/no, which>

## Phase 4 — Verification
- Failing test now passes: yes
- Full suite: <N passing, M failing — none new>
- Linter/types: clean
- Manual smoke: <covered behaviors>
- bug-patterns.md updated: yes
- Commit: <sha + message>
```

## Cross-refs
- Companion: `triage-issue` (for filing the bug), `fix-bug` command (for execution after diagnosis)
- `.claude/rules/workflow-orchestration.md` — Anti-Desperation rule
- `docs/dev-knowledge/bug-patterns.md` — known patterns
- `PROMPTLIBRARY.md` — DEBUG Bug Triage prompt
