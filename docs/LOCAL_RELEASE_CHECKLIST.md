# Local Release Checklist

Use this checklist when GitHub Actions minutes are unavailable or when you want
one local pass before pushing. It assumes Windows PowerShell from the repo root,
but the same npm commands work on macOS/Linux when Python 3.12 is available.

## One-Time Local Setup

1. Confirm the preferred backend Python:

   ```powershell
   python scripts/run_python.py
   ```

   Expected on this workstation: `.venv312\Scripts\python.exe`.

2. Install backend dependencies if the environment is missing packages:

   ```powershell
   .venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```

3. Install frontend dependencies:

   ```powershell
   npm install
   npm --prefix frontend install
   ```

4. Copy and fill local environment variables:

   ```powershell
   Copy-Item .env.example .env
   ```

## Pre-Release Gate

Run the local release gate before a local release or direct push:

```powershell
npm run check:local-release
```

That expands to:

```powershell
npm run check:quick
npm run build
npm run test:backend:focused
npm run test:frontend
```

If time is tight, `npm run check:quick` is the minimum gate. It validates the
agent system, skill metadata, canonical skill sync, widget mirrors, project
invariants, and Codex orchestration configuration.

The quick gate also validates the agent-routing eval catalog with:

```powershell
npm run eval:agent-routing
```

The full backend suite remains available:

```powershell
npm run test:backend
```

As of April 28, 2026, the full backend suite runs through `.venv312` but still
has known test drift in auth, onboarding, and local SEO mocks. Use the focused
backend gate for local release confidence until those stale tests are repaired.

## Manual Smoke Test

1. Start the backend:

   ```powershell
   npm run dev:backend
   ```

2. In another terminal, start the frontend:

   ```powershell
   npm run dev:frontend
   ```

3. Visit the local frontend and check:

   - Sign up or login flow renders.
   - Onboarding wizard advances through each step.
   - Widget configuration page loads.
   - Public widget preview opens and can send a test message when API keys are configured.

4. Run the public smoke helper when local environment variables are ready:

   ```powershell
   npm run smoke
   ```

## No-Actions Autopilot Dry Run

Use local dry-run mode while Actions are paused. It classifies issues but does
not label, dispatch Codex, push, comment, or open pull requests.

```powershell
npm run autopilot:dry-run
npm run autopilot:dry-run:issue -- 123
```

Requirements:

- `gh` installed and authenticated.
- `ANTHROPIC_API_KEY` available in the environment.
- The target issue is visible to the authenticated GitHub account.

## Release Notes Template

```markdown
## Summary
-

## Verification
- `npm run check:local-release`

## Manual Checks
-

## Risks / Follow-up
-
```

## Troubleshooting

- If Python imports fail, run commands through `python scripts/run_python.py ...`
  or set `AGENTNEXLIFY_PYTHON` to the correct Python 3.12 executable.
- If generated browser artifacts appear, they should remain ignored:
  `.playwright-cli/` and `output/`.
- If Git prints stale worktree metadata warnings, inspect with
  `git worktree list` and prune only after confirming the old paths are gone.
