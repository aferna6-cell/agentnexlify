---
name: go
description: Auto-invoke at the END of any implementation/bug-fix/refactor task — runs end-to-end verification, simplifies changed code, opens a PR to main, and enables auto-merge on green CI. Trigger when user suffixes a prompt with "/go", says "ship it", "verify and PR", "open a PR when done", "verify end-to-end", or when Claude has just finished writing code and no verification has run yet. Do NOT invoke for pure research, docs, or read-only exploration.
version: 1.0.0
origin: aidan
triggers:
- /go
- ship it
- verify and PR
- verify end-to-end
- open a PR when done
- finish the task
- wrap it up
effort: xhigh
---

# /go — Verify → Simplify → PR → Auto-Merge

Claude-facing skill. Fires at task completion to guarantee working code lands cleanly on `main`.

## When to invoke
- User ends a coding prompt with `/go`
- User says any variant: "ship it", "verify and PR", "wrap it up", "finish the task"
- Claude finished implementation in current session and hasn't verified E2E yet
- `PostToolUse` loop quiet for >30s after last Edit/Write (instructed elsewhere, not enforced here)

## When NOT to invoke
- Pure research, KB ingest, docs-only changes (no behavior risk)
- Read-only exploration (`Read`/`Grep`/`Glob` only, zero writes)
- User is mid-debate / still choosing approach
- Uncommitted work on multiple unrelated task surfaces (ask user to split first)

## Surface detection
Classify changed files before verifying. Use `git diff --name-only origin/main...HEAD` + working tree.

| Surface | Signals | Verification |
|---|---|---|
| **Backend** | `backend/**/*.py`, `migrations/*.sql` | uvicorn boot + pytest fast + curl smoke |
| **Frontend** | `frontend/src/**/*.{jsx,tsx,css}` | `vite build` + Playwright MCP browser session + chrome-devtools-mcp console/network check |
| **Widget** | `widget/*`, `frontend/public/widget/*` | widget-test skill (cross-origin embed check) |
| **Schema** | `migrations/*.sql`, Pydantic model edits | schema-guardian agent check |
| **Infra/CI** | `.github/workflows/*`, `railway.json`, `vercel.json` | config lint + dry-run |
| **Mixed** | 2+ of above | run all applicable in parallel |

## Flow

### Step 1 — Surface detect
```bash
git diff --name-only origin/main...HEAD
git status --short
```
Map files → surfaces. If zero changes, abort with "nothing to ship."

### Step 2 — Start services (if backend/frontend touched)
```bash
# Backend (if Python changed)
.venv/bin/python -m uvicorn backend.main:app --reload --port 8000 &
# Frontend (if React changed)
cd frontend && npm run dev &
```
Run in background. Wait for `http://localhost:8000/health` + `http://localhost:5173` to respond before test step.

### Step 3 — E2E verification per surface

**Backend:**
```bash
.venv/bin/python -m pytest tests/ -q -x --timeout=30
# smoke
curl -sf http://localhost:8000/health
# hit a few real endpoints with test tenant creds
```

**Frontend:** use **all three** browser tools (user choice 3):
1. `mcp__playwright__*` — scripted flow of primary user journey
2. `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*` — DevTools console errors, network 4xx/5xx, Lighthouse audit
3. `autonomous-webapp-test` skill — exploratory pass across UI

Capture screenshots on each. Abort if any:
- Console error (`level=error`)
- Network request `>=400` on non-auth route
- Playwright assertion fails
- Visible layout break vs baseline

**Widget:** run `widget-test` skill. Must pass: load on external origin, open, send msg, receive response, lead captured in DB.

**Schema:** if any `migrations/*.sql` new/changed, invoke schema-guardian agent to check applied state vs file.

### Step 4 — /simplify changed code
```
Skill("simplify")
```
Reviews diff for reuse/duplication/quality. Apply suggestions only if staff-eng approves. Don't over-refactor.

### Step 5 — Full verification gate
```
Skill("verification-loop")
```
Runs build + types + lint + fast tests + secret scan. Must be green.

### Step 6 — Commit (if dirty), push, PR
```bash
# commit anything outstanding
git add <explicit files>
git commit -m "<conventional msg>"
git push origin HEAD:<branch>

# open PR to main
gh pr create --base main --head <branch> --title "<title>" --body "<summary + test plan + verification evidence>"
```

**Never** bypass pre-push hooks (`--no-verify`) unless user explicitly authorizes.
**Never** force-push to main.

### Step 7 — Auto-merge on green
```bash
PR=$(gh pr view --json number -q .number)
gh pr merge "$PR" --auto --squash --delete-branch
```
GitHub auto-merges when all required checks pass. If repo has no branch protection, fail loudly with fix suggestion instead of direct-merging.

### Step 8 — Report
Output to user:
- PR URL
- Verification summary (✓/✗ per surface)
- Simplify deltas (lines cut, dupes removed)
- Auto-merge enabled: yes/no (+ required checks list)
- What's next (if follow-ups surfaced)

## Failure policy
Any verification fails → **halt before PR**. Report exact failure (file, line, error). Do NOT auto-patch — let user decide fix approach.

## Edge cases
- **No branch protection on main** → skip auto-merge flag, warn user to add branch rules
- **Pre-push hook blocks on unrelated lint** → halt, surface blocker, ask user (per no-assumptions rule)
- **Remote advanced during session** → rebase commits onto new `origin/main`, re-run verification
- **Detached HEAD** → checkout a named branch first (`gh pr create` requires branch)
- **Sandbox blocks SSH push** → retry with `dangerouslyDisableSandbox: true` on git push only
- **Chrome-devtools-mcp not running** → fall back to Playwright MCP only
- **Dev server already on port** → detect + reuse, don't spawn duplicate

## Cost/time budget
- Full /go run: 3–8 min (build 30s, E2E 60–180s, simplify 30–60s, CI wait 60–300s)
- Opus advisor pass on failure analysis: ~$0.15
- Parallel browser tools: run concurrently, not sequentially

## Invocation examples
```
User: "Add a dark mode toggle to settings page /go"
→ Claude implements + auto-fires /go at completion
```
```
User: "Fix the 500 in /api/leads and ship it"
→ "ship it" triggers /go
```
```
User: "/go"  (alone, after prior work)
→ verifies current branch state, simplifies, PRs
```

## Pointers
- Verification: `.claude/skills/verification-loop/SKILL.md`
- Simplify: `.claude/skills/simplify/SKILL.md`
- Webapp test: `.claude/skills/webapp-testing/SKILL.md`
- Widget test: `.claude/skills/widget-test/SKILL.md`
- Autonomous UI: `.claude/skills/autonomous-webapp-test/SKILL.md`
- PR skill: `commit-commands:commit-push-pr`
- Confidence gate: `scripts/claude-hooks/confidence-gate.sh` (must pass ≥90%)
