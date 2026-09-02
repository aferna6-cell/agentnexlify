# Transition record — 2026-09-02

**M8 COMPLETE → merge completion evidence → restore mandatory green CI → close demo-role security gap → M9 planner.**

## Done

1. **M8 formal completion** — canonical six-suite PASS @ runtime SHA `962da79b`; evidence commit `ac80a1bd`.
2. **#748 MERGED** — `1f36818f` into `main` (input preservation + OAuth state TTL 60m + evidence). Ready-for-review + merge completed; no six-suite rerun needed for docs-only head advance.

## In progress

3. **#747** — rebased onto post-#748 `main`, `[skip ci]` removed, marked ready.
   - Change remains one-file `package-lock.json` (brace-expansion high → 0).
   - **Blocked on GitHub Actions PR Validation not enqueueing** for this PR (no run after push / ready / reopen). Agent cannot `workflow_dispatch` (403).
   - Owner: Actions → PR Validation → Run workflow on `cursor/brace-expansion-audit-fix-a2c9`, confirm full gate passes end-to-end, then merge.

## Next (owner / subsequent agent)

4. Enable **branch protection** on `main`: require PR Validation; block direct pushes except defined break-glass.
5. **#669** — central demo-role mutation guard (middleware + allowlist + CI route audit + tests). Not ~100 route-level Depends.
6. **M9** — only after #669: durable planner state machine (`goal → plan → steps → execute via Action Executor → verify → approve → resume`). Planner never gains independent tool authority.
