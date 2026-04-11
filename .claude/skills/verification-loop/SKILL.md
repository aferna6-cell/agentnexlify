---
name: verification-loop
description: "Run a comprehensive verification system for Claude Code sessions covering build, types, lint, tests, security, and diff review."
version: 1.0.0
origin: claude
triggers: ["verification loop", "verify changes", "quality gate", "pre-PR check", "verify build", "run verification"]
effort: high
---

# Verification Loop Skill

A comprehensive verification system for Claude Code sessions.

## When to Use
- After completing a feature or significant code change
- Before creating a PR
- When you want to ensure quality gates pass
- After refactoring

## When NOT to Use
- During active development mid-task (wait until a milestone)
- For trivial one-line changes (overkill for tiny fixes)
- When the project has no build/test infrastructure (adapt the checks instead)

## Verification Phases

### Phase 1: Build Verification
```bash
# Check if project builds
npm run build 2>&1 | tail -20
# OR
pnpm build 2>&1 | tail -20
```

If build fails, STOP and fix before continuing.

### Phase 2: Type Check
```bash
# TypeScript projects
npx tsc --noEmit 2>&1 | head -30

# Python projects
pyright . 2>&1 | head -30
```

Report all type errors. Fix critical ones before continuing.

### Phase 3: Lint Check
```bash
# JavaScript/TypeScript
npm run lint 2>&1 | head -30

# Python
ruff check . 2>&1 | head -30
```

### Phase 4: Test Suite
```bash
# Run tests with coverage
npm run test -- --coverage 2>&1 | tail -50

# Check coverage threshold
# Target: 80% minimum
```

Report:
- Total tests: X
- Passed: X
- Failed: X
- Coverage: X%

### Phase 5: Security Scan
```bash
# Check for secrets
grep -rn "sk-" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
grep -rn "api_key" --include="*.ts" --include="*.js" . 2>/dev/null | head -10

# Check for console.log
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10
```

### Phase 6: Diff Review
```bash
# Show what changed
git diff --stat
git diff HEAD~1 --name-only
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Potential edge cases

## Output Format

After running all phases, produce a verification report:

```
VERIFICATION REPORT
==================

Build:     [PASS/FAIL]
Types:     [PASS/FAIL] (X errors)
Lint:      [PASS/FAIL] (X warnings)
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL] (X issues)
Diff:      [X files changed]

Overall:   [READY/NOT READY] for PR

Issues to Fix:
1. ...
2. ...
```

## Continuous Mode

For long sessions, run verification every 15 minutes or after major changes:

```markdown
Set a mental checkpoint:
- After completing each function
- After finishing a component
- Before moving to next task

Run: /verify
```

## Integration with Hooks

This skill complements PostToolUse hooks but provides deeper verification.
Hooks catch issues immediately; this skill provides comprehensive review.

## Gotchas
- **Agentnexlify doesn't use `npm test` at the root.** Frontend uses `cd frontend && npm run build`. Backend uses `python3 -m pytest backend/tests/`. No combined runner.
- **`pyright` is not installed.** Use `python3 -m py_compile` or `ruff check` for Python. Skip the Phase 2 pyright step entirely.
- **Ruff warnings ≠ blockers.** The project has intentional `# noqa: BLE001` on broad exception catches. Don't auto-fix them.
- **Pytest hangs on `lifespan startup`.** Starlette TestClient deadlocks — the project uses a custom `SyncASGITestClient` in `backend/tests/conftest.py`. Don't "fix" by switching back to TestClient.
- **`python` command doesn't exist.** Always use `python3`. The hook runs `python3 -m pytest ...`.
- **Secret scan false-positives on `.env.example`.** These are template files with placeholder keys. Don't flag them.
- **`console.log` in widget is intentional** for cross-origin debugging. Don't strip without reading context.
- **Coverage target 80% is aspirational.** The backend sits at ~45% currently. Don't block a PR on coverage alone — block on `PASS/FAIL` of the tests that exist.
- **Diff review before push.** `git log origin/main..HEAD --stat` is the real "what's about to ship". `git diff HEAD~1` misses multi-commit branches.
- **Phase 5 `grep -rn "sk-"`** catches legitimate strings like "sk-" in comments. Prefer `grep -rn "sk-ant-\|sk-live-\|rk_live_"` for real key prefixes.
