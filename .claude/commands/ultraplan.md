---
description: Native Claude Code CLI command — drafts a plan in a remote cloud session, reviewable via browser. Distinct from inline plan mode (Shift+Tab x2).
---

`/ultraplan` is a **native Claude Code CLI feature** — not a user-defined command, skill, or agent. Invoke it by typing `/ultraplan` at the prompt. The plan is drafted in a remote cloud session while the local terminal stays free; review happens asynchronously in a browser.

This file is reference-only. Do NOT attempt to implement the command — it ships with the CLI.

## When `/ultraplan` wins over plan mode

| Situation | Tool |
|---|---|
| 2+ files, review inline before code | plan mode (Shift+Tab x2) |
| 10+ files, cross-service, review async | `/ultraplan` |
| Spec → plan → issues pipeline | `/ultraplan` |
| Interactive iterative feature design | plan mode |
| Long-running planning while you do other work | `/ultraplan` |
| Blocker: need plan in <2 min for tight loop | plan mode |

See `.claude/rules/opus-4-7-prompting.md` § 5 for the governing rule.

## AgentNexLiFy integration

- **Compound engineering** (`.claude/skills/compound-engineering/SKILL.md`) — use `/ultraplan` for the Plan phase when the feature touches 10+ files or crosses backend/frontend/widget boundaries. Feed the browser-reviewed plan into the Execute phase. For smaller slices, keep plan mode inline.
- **write-prd → prd-to-issues pipeline** (`.claude/rules/daily-skills.md`) — after `write-prd` produces the spec, invoke `/ultraplan` to draft the phased implementation plan async, then hand off to `prd-to-issues`. Mirrors the `prd-to-plan` skill but offloads the drafting work from the local session.
- **Worktree orchestration** (`.claude/skills/worktree-orchestrator/SKILL.md`) — draft the multi-worktree dispatch plan in `/ultraplan`, review in browser, then execute locally with explicit fan-out phrasing per `opus-4-7-prompting.md` § 4.
- **After `/ultraplan` returns** — apply `/ultrareview` before merging any implementation that resulted from the plan. See `.claude/rules/ultrareview.md`.

## Limitations

- **CLI only** — no VS Code Claude extension support. If working inside VS Code, fall back to plan mode or switch to the CLI terminal.
- **Not synchronous** — do not use when you need the plan in the same turn. Use plan mode.
- **Browser review required** — the output lives in a cloud session; plan on checking the browser tab to approve/edit.
- **Not a substitute for grill-me** — `/ultraplan` drafts structure; it does not resolve ambiguity. Run `grill-me` (batch-mode per `opus-4-7-prompting.md` § 1) BEFORE invoking `/ultraplan` if the spec has open questions.

## Cross-refs

- `.claude/rules/opus-4-7-prompting.md` § 5 — governing rule, plan mode vs `/ultraplan`
- `.claude/rules/ultrareview.md` — post-implementation review gate
- `.claude/rules/opus-4-7.md` — canonical 4.7 feature matrix
- `.claude/skills/compound-engineering/SKILL.md` — Plan phase integration
- `.claude/skills/prd-to-plan/SKILL.md` — local alternative when `/ultraplan` isn't available
