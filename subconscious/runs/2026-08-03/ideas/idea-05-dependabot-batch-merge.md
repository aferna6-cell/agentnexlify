# Idea 05 — Batch-Merge Safe Dependabot PRs

**Evidence:**
- `ops/routines/logs/morning-digest-2026-08-03.md`: "batch-merge safe Dependabot PRs (#580, #582–585, #589) to clear the 7-day backlog."
- 6 safe PRs: #580 (actions/checkout 4→7), #582 (@playwright/test 1.61.1→1.62.0), #583 (eslint 10.7→10.8), #584 (@typescript-eslint/parser 8.64→8.65), #585 (@vitejs/plugin-react 6.0.3→6.0.4), #589 (recharts 3.9.2→3.10.1).
- All 7+ days old. All minor/patch bumps. No behavioral changes expected.
- 3 held PRs: #586 (React 18→19, MAJOR), #587 (jsdom 29→30, major), #588 (@testing-library/jest-dom 6→7, major).
- Morning digest already recommended this — subconscious adding no new signal here.

**Idea:** Merge PRs #580, #582, #583, #584, #585, #589 via `mcp__github__merge_pull_request`.

**Expected impact:** Clears 7-day backlog. Keeps dependency graph current. Prevents safe deps from aging further.

**Effort:** XS (6 GitHub MCP merge calls)
**Confidence:** HIGH
**Autonomous:** YES (fully executable via GitHub MCP)
**Novelty:** LOW — morning digest already flagged this. No new subconscious value-add vs digest.
**Note:** This idea is executable but not subconscious-worthy as the winner — morning digest already recommended it. Better as a bonus action than a winner.
