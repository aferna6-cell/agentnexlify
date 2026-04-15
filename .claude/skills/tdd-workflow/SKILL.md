---
name: tdd-workflow
description: Enforce test-driven development with 80%+ coverage for new features, bug fixes, and refactoring in backend/tests/ or frontend/src/. Load when user says 'tdd', 'test-driven', 'write tests first', 'unit test', 'integration test', or 'test coverage'.
version: 1.0.0
origin: agentnexlify
user-invocable: true
triggers:
  - tdd
  - test-driven
  - test driven development
  - write tests first
  - test coverage
  - unit test
  - integration test
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob]
effort: high
---

# TDD Workflow — Test-Driven Development

Write tests first, then implement. 80%+ coverage target (unit + integration + E2E).

## When to Use

- Writing new features or functionality
- Fixing bugs (write a test that reproduces it first)
- Refactoring existing code
- Adding API endpoints in backend/routers/
- Creating new React components in frontend/src/

## When NOT to Use

- Quick scripts or one-off utilities where tests add no value
- Prototyping or exploratory code to be thrown away
- Documentation-only or configuration-only changes
- When tests would take longer to write than the feature itself

## Core Principles

1. **Tests BEFORE Code** — always write tests first, then implement
2. **Coverage minimum: 80%** — unit + integration + E2E combined
3. **Test all edge cases** — empty, null, error paths, boundary conditions
4. **Independent tests** — each test sets up its own data, no order dependencies

## TDD Workflow Steps

### Step 1: Write User Journeys
```
As a [role], I want to [action], so that [benefit]
```

### Step 2: Generate Test Cases
For each journey, cover: happy path, empty/null inputs, error scenarios, boundary conditions.

### Step 3: Run Tests (They Should Fail)
```bash
# Backend
python3 -m pytest backend/tests/ -x --tb=short -q

# Frontend
cd frontend && npm run build
```
Tests should fail — you haven't implemented yet.

### Step 4: Implement Code
Write minimum code to make tests pass.

### Step 5: Run Tests Again — They Should Pass

### Step 6: Refactor
Improve code quality while keeping tests green. Remove duplication. Improve naming.

### Step 7: Verify Coverage
```bash
npm run test:coverage
# Target: 80%+ achieved
```

## Test Types

- **Unit Tests** — individual functions, component logic, pure functions
- **Integration Tests** — API endpoints, database ops, service interactions
- **E2E Tests (Playwright)** — critical user flows, complete workflows

## AgentNexLiFy Test Commands

```bash
# Backend unit tests
python3 -m pytest backend/tests/ -x --tb=short -q

# Frontend build (no separate test runner)
cd frontend && npm run build

# E2E (Playwright MCP)
# Use autonomous-webapp-test skill for full E2E runs
```

## Gotchas

- `python` command doesn't exist — always use `python3`
- Pytest hangs on `lifespan startup` — the project uses `SyncASGITestClient` in `backend/tests/conftest.py`. Don't switch to TestClient.
- Backend sits at ~45% coverage — aspirational, not a blocker. Block on test PASS/FAIL, not coverage number.
- `console.log` in widget is intentional for cross-origin debugging — don't strip.
- No bare `except:` in tests — always catch specific exceptions.

## Success Criteria

- All existing tests still pass
- New behavior has ≥1 test that would fail without the implementation
- No regressions in adjacent code paths

## Full Patterns Reference

For complete unit/integration/E2E code examples, mocking patterns (Supabase, Redis), flaky test strategies, and CI/CD integration — see:
`references/coverage-rubric.md`

## Cross-refs

- `.claude/skills/e2e-testing/SKILL.md` — Playwright-specific patterns
- `.claude/skills/verification-loop/SKILL.md` — build + test + lint gate
- `.claude/skills/autonomous-webapp-test/SKILL.md` — full app autonomous E2E
