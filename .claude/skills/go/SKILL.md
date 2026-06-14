---
name: go
description: Manual AgentNexLiFy verification and optional ship gate. Use only when the user explicitly invokes /go or asks to run the go gate; verifies changed code, simplifies the diff, and commits or pushes only when the current user request explicitly authorizes shipping to main.
version: 1.2.0
origin: aidan
disable-model-invocation: true
triggers:
- /go
- run the go gate
- verify and push
- commit and push
- ship to main
effort: xhigh
---

# /go - Verify, Simplify, Then Ship Only If Authorized

Manual safety gate for finishing AgentNexLiFy code work. This skill is intentionally not model-invoked because it can commit and push. Treat it as a controlled command, not an automatic end-of-task reflex.

## Operating Modes

Default mode is verification-only.

Ship mode is allowed only when the current user request explicitly says to commit, push, ship to main, or equivalent. Do not infer shipping permission from earlier turns, from a successful test run, or from the fact that work appears complete.

## Before Running

1. Read `git status --short --branch`.
2. Read `git diff --name-only` and `git diff --cached --name-only`.
3. Identify the changed surfaces: backend, frontend, widget, schema, infra, docs, or mixed.
4. Stop if unrelated dirty files make the requested scope ambiguous.

## Verification Path

Use the narrowest checks that cover the changed surfaces, then escalate to the full gate before shipping.

- General gate: `npm run check:quick`
- Full repo gate: `npm run check:full`
- Backend changes: targeted `python -m pytest ...` for touched tests, then backend suite if risk is high.
- Frontend changes: `npm --prefix frontend run build` and relevant Vitest/Playwright checks.
- Widget changes: verify `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` remain identical, then run widget-facing tests.
- Schema changes: inspect migrations and use schema guard patterns before running affected backend tests.
- Security-sensitive changes: run the relevant security skill/checker before shipping.

If any verification fails, stop before commit or push and report the failure with the exact command.

## Simplify Pass

After verification is green, review the diff for:

- accidental broad changes
- duplicated logic
- stale comments or misleading docs
- missing focused tests for changed behavior

Apply only small, clearly safe simplifications. Do not turn `/go` into a broad refactor.

## Ship Mode

Ship mode requires explicit current-turn authorization.

1. Stage only the files that belong to this task. Do not use `git add -A` unless the user explicitly asked to stage everything.
2. Commit with a concise conventional message.
3. Fetch/rebase if `origin/main` advanced.
4. Re-run the checks that could be invalidated by the rebase.
5. Push to `origin main`.

Never force-push `main`. Never bypass hooks with `--no-verify` unless the user explicitly authorizes that exact bypass.

## Report

Return:

- changed surfaces
- verification commands and pass/fail status
- simplify changes, if any
- commit hash and push result, only if ship mode ran
- remaining risks or follow-ups

## Related Skills

- `verify` for verification without commit or push
- `verification-loop` for broad quality gates
- `agentnexlify-task-loader` for selecting repo-local skills before editing
- `agentnexlify-schema-guard` for data/schema changes
- `agentnexlify-widget-integrity` for widget changes
