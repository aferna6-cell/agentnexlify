# Daily Skills — Mandatory Workflow Gates

Five skills enforced as gates in the development loop. Not optional. Not invokable only when asked. These fire based on what type of work is happening.

---

## 1. GRILL-ME — Before Writing Any Code

**Rule: Zero code before zero ambiguity.**

Invoke `.claude/skills/grill-me/SKILL.md` at the start of EVERY non-trivial implementation task. Walk the full design tree: 40+ questions minimum across all branches before writing a single line.

### Branches to cover every time
1. **Goal** — What exact user problem does this solve? What does success look like in measurable terms?
2. **Scope** — What is explicitly OUT of scope? What adjacent problems are we NOT solving?
3. **Data model** — Which tables? Which columns? Which tenant isolation pattern? Any new migrations needed?
4. **API contract** — Endpoint shape, request/response schema, auth requirements, rate limits?
5. **UI/UX** — Which pages? Which states (empty, loading, error, success)? Mobile behavior?
6. **Edge cases** — What happens when X is null? What if the tenant has 0 records? What if the API is down?
7. **Failure modes** — What fails silently vs loudly? What's the fallback?
8. **Dependencies** — What existing code does this touch? What breaks if this changes?
9. **Performance** — Any N+1 risks? Any missing indexes? Any sync calls in async paths?
10. **Security** — Any new input vectors? Any new auth surfaces? Any PII handled?
11. **Tests** — What test cases prove this works? What test cases prove it DOESN'T break?
12. **Rollout** — Feature flag? All tenants? Specific plan tier? Migration order?

### Mandatory triggers
- User says "build X", "add X", "implement X", "create X", "write X"
- Task touches 2+ files
- Any new API endpoint
- Any database migration
- Any change to widget behavior
- Any change to billing/plan logic

### Hard stops (grill-me required, no exceptions)
- Schema changes
- Auth/permissions changes
- Widget JS changes (byte-identical rule)
- Billing / Stripe webhook changes
- New AI agent definitions

### Skip only when
- One-line fix (typo, rename, formatting)
- User has already provided a full spec/PRD
- Continuing work on a task already grilled this session

**Pattern: Ask one question at a time. Wait for answer. Branch based on answer. Minimum 40 questions total before declaring "zero ambiguity".**

---

## 2. WRITE-PRD — Idea → Spec Before Any Planning

**Rule: No planning or issues before a spec exists.**

Invoke `.claude/skills/write-prd/SKILL.md` when a new feature is proposed but no `specs/<feature>_spec.md` exists.

### Mandatory triggers
- User describes a new feature in natural language without referencing a spec
- User says "I want to build X" or "we need X"
- Task is multi-session (won't fit in one chat)
- Feature touches multiple layers (backend + frontend + widget)

### Output
`specs/<feature-name>_spec.md` — Goals, non-goals, user stories, acceptance criteria, open questions, success metrics.

### Sequence
`WRITE-PRD → GRILL-ME → PRD-TO-ISSUES → TDD → build`

---

## 3. PRD-TO-ISSUES — Spec → GitHub Issues

**Rule: No manual issue creation. Every approved spec becomes issues automatically.**

Invoke `.claude/skills/prd-to-issues/SKILL.md` immediately after a PRD is approved.

### Mandatory triggers
- PRD approved (user says "looks good", "ship it", "let's go")
- User says "issues from PRD", "create tickets", "backlog from spec"
- Multi-week feature (needs to be parallelizable)

### Output
GitHub issues via `gh issue create` — each issue is independently grabbable, has acceptance criteria, labels (`backend`/`frontend`/`widget`/`migration`), and explicit blocking relationships.

### Issue quality bar
- Title: imperative verb phrase ("Add lead enrichment source column")
- Body: user story + acceptance criteria + test cases + files expected to change
- Labels: layer + priority
- Blocking: explicit `Blocked by #N` references

---

## 4. TDD-WORKFLOW — Tests Before Code

**Rule: No implementation without failing tests first.**

Invoke `.claude/skills/tdd-workflow/SKILL.md` at the start of any implementation after grill-me completes.

### Mandatory triggers
- Any new function, endpoint, or component
- Any bug fix (regression test first)
- Any refactor (characterization tests first)
- User says "fix bug in X", "add function X", "build endpoint X"

### Sequence
1. Write failing test that describes the contract
2. Run test → confirm it fails for the right reason
3. Write minimal code to make it pass
4. Refactor
5. Run full test suite to catch regressions

### Coverage bar
- Backend: 80%+ for new modules, 100% for security/auth paths
- Frontend: critical user flows covered (happy path + error states)
- Widget: cross-origin embed tested per `widget-test` skill

### Hard rule
Never change a test to make it pass. If a test fails, the code is wrong, not the test. See `user-rules.md` Rule 10.

---

## 5. IMPROVE-ARCHITECTURE — Weekly Structural Review

**Rule: Ship features AND keep the foundation clean.**

Invoke `.claude/skills/improve-architecture/SKILL.md` on the following cadence:

### Mandatory triggers
- Every Monday (or start of work week) — weekly health check
- Before any major feature branch starts (catch problems before they compound)
- After any large refactor completes
- When any file hits 600+ lines (god class threshold)
- User says "improve architecture", "architecture review", "codebase health", "/improve"
- After 10+ commits land without a review pass

### What it checks
Six passes: file bloat, layer violations, dead code, schema drift, dependency rot, performance hotspots.

### Output
`audits/audit-architecture-YYYY-MM-DD.md` — ranked fix list (CRITICAL / HIGH / MEDIUM / LOW) with severity + effort scores.

### Rule: don't fix and audit in the same session
Audit produces a report. Fixes happen in a separate session using compound-engineering. Mixing them causes half-finished refactors.

---

## Daily Loop

```
New idea arrives
    ↓
WRITE-PRD (if no spec exists)
    ↓
GRILL-ME (40+ questions, zero ambiguity)
    ↓
PRD-TO-ISSUES (spec → GitHub issues)
    ↓
TDD-WORKFLOW (failing tests first)
    ↓
Build (compound-engineering pipeline)
    ↓
Monday: IMPROVE-ARCHITECTURE (health check)
```

---

## Anti-patterns (never do)

- Writing code before grill-me completes ("I'll figure it out as I go")
- Creating GitHub issues by hand instead of prd-to-issues
- Writing implementation before tests (especially for bug fixes)
- Skipping the architecture review because "we're in a rush"
- Treating these as optional when the user doesn't explicitly ask

---

## Cross-refs
- `.claude/skills/grill-me/SKILL.md`
- `.claude/skills/write-prd/SKILL.md`
- `.claude/skills/prd-to-issues/SKILL.md`
- `.claude/skills/tdd-workflow/SKILL.md`
- `.claude/skills/improve-architecture/SKILL.md`
- `.claude/rules/user-rules.md` (Rule 1: Plan first, Rule 10: never change tests)
- `.claude/rules/ultrathink.md` (plan mode gate)
- `.claude/rules/no-assumptions.md` (80% confidence threshold)
