# Environment Blockers Audit — 2026-04-15

Tracks tooling unavailable from current Windows session that gates verification of code changes.

## Blocker B1 — npm broken on host
**Severity:** HIGH (blocks all frontend verification)
**Diagnosis:**
```
npm --version
> Error: Cannot find module 'nopt'
> Require stack: C:\Users\aidan\AppData\Local\Programs\nodejs\node_modules\npm\node_modules\@npmcli\config\lib\index.js
```
- Node v24.14.1 installed at `C:\Users\aidan\AppData\Local\Programs\nodejs\`
- `node_modules/nopt` missing inside npm's bundled deps
- `frontend/node_modules` does NOT exist (deps never installed in this env)

**Impact:**
- Cannot run `npm run build`
- Cannot run `npm run dev`
- Cannot run `npm run test` (vitest)
- Cannot install new dependencies
- Cannot run `npm audit`

**Recommended fix (user action):**
```powershell
# Option A — reinstall npm via PowerShell as Admin
cd "C:\Users\aidan\AppData\Local\Programs\nodejs\node_modules\npm"
node ./bin/npm-cli.js install --no-save

# Option B — reinstall Node.js entirely (cleanest)
# Download Node 22 LTS from nodejs.org, run installer, restart terminal

# Option C — use nvm-windows
# Install nvm-windows, then:
nvm install 22.11.0
nvm use 22.11.0
```

**Verify after fix:**
```bash
npm --version       # should print 10.x or 11.x
cd frontend && npm install
npm run build       # should produce frontend/dist/
```

## Blocker B2 — gh CLI not installed
**Severity:** MEDIUM (blocks GitHub automation tracks)
**Diagnosis:**
```
gh auth status
> bash: gh: command not found
```

**Impact:**
- Cannot run `issue-to-pr-loop` skill (needs `gh issue list`, `gh pr create`, etc.)
- Cannot file/triage GitHub issues from CLI
- Cannot create test issues to validate autonomous loops
- Manual GitHub interaction only via web UI

**Recommended fix (user action):**
```powershell
# Windows installer
winget install --id GitHub.cli

# Or via Scoop
scoop install gh

# After install, authenticate
gh auth login
```

**Verify:**
```bash
gh auth status
gh issue list --limit 3
```

## Blocker B3 — backend pytest needs env
**Severity:** MEDIUM (blocks backend test verification)
**Diagnosis:** `.env` file gitignored + security rules block reading credentials. No env vars exported in this session for `SUPABASE_URL`, `SUPABASE_KEY`, `ANTHROPIC_API_KEY`, etc.

**Impact:**
- Cannot run `pytest backend/tests/`
- Cannot verify backend changes locally
- All verification deferred to CI (GitHub Actions)

**Recommended fix:** none required — CI handles it. If local pytest desired, copy production env to `backend/.env.test` (gitignored).

## What we can verify locally despite blockers
- ✅ Python AST parse / syntax check (`python -m compileall backend/`)
- ✅ Static antipattern grep scans
- ✅ File system byte comparisons (widget sync)
- ✅ Git operations (commit, push, log, diff)
- ✅ File reads + edits

## What requires fix-then-rerun
- ❌ Frontend build (B1)
- ❌ Frontend test suite (B1)
- ❌ Backend test suite (B3)
- ❌ Dependency audit (B1 + missing pip-audit)
- ❌ GitHub issue automation (B2)
- ❌ Live Supabase queries (B3)

## Workaround pattern used in this session
For frontend changes (e.g. toast component replacing alert calls):
1. Make changes in source
2. Commit + push
3. CI runs build on push (`.github/workflows/`)
4. Verify in CI logs OR Vercel preview deploy
5. If broken: revert via `git revert <sha>` and re-attempt

This is acceptable for additive, mechanical changes (low cognitive risk). Higher-risk changes (architectural, schema) MUST wait for working local verification.

## Action items for next session
1. Fix B1 (npm) — 15 min user action, unblocks everything frontend
2. Install gh CLI (B2) — 5 min user action, unblocks autonomous loops
3. Re-run frontend build to verify toast util change works
4. Re-run this audit to confirm blockers cleared

## Cross-refs
- `audit-codebase-debug-2026-04-15.md` — companion code-side audit (0 active bugs)
- `.claude/rules/claude-code-security.md` — why credential reads are blocked
- `.claude/skills/dependency-auditor/SKILL.md` — uses pip-audit + npm audit (both blocked)
