# 2026-07-27 — Autonomous engineering: pick one loop, run it on Routines

Status: proposed · Supersedes nothing · Related: GH #500, #399, #403, #394

## Context

The goal is an engineering loop that runs AgentNexLiFy with minimal owner input.
The repo already contains most of the parts. Almost none of them execute.

Verified state, 2026-07-27:

**Exactly one autonomous loop runs today.** `nightly-commit-review`, and it runs
because it was *migrated off local cron onto a cloud Claude Routine*
(`trig_014nVaJAnhKSaXEDDsYuddJ9`, `37 6 * * *` UTC). The local script
self-disables to avoid double runs — `scripts/daily/nightly-commit-review.sh:28-35`.
Unbroken daily commits 07-23 → 07-27 confirm it. `morning-digest` also fires
cloud-side but skipped 07-25 and 07-26.

**Everything else is parked, unwired, or laptop-bound:**

| Loop | Trigger | Why it does not run |
|---|---|---|
| `autopilot-loop` | GH Actions | cron set to `0 6 31 2 *` — Feb 31, never fires (`.github/workflows/autopilot-issue-loop.yml:4-9`). Parked 2026-07-20: expired `AUTOPILOT_GH_TOKEN` (#399) + exhausted minutes (#500). Also needs `codex` on PATH. |
| `issue-to-pr-loop` | local crontab | Never wired. No installer. Needs `gh` + `crontab`, neither present. |
| `kb-autopopulate`, `refresh-brain` | GH Actions | Same Feb-31 park. #403 (missing `ANTHROPIC_API_KEY` in Actions), #394 (brain creds). |
| `build-loop` | manual | Reads four files in `.claude/agent-comms/` that were never created. |
| `kairos` | manual daemon | Hardcodes `/home/aidan/...`; no supervisor, dies with the container. |
| daily `morning`/`evening` | local cron | `setup-cron.sh` calls `crontab`, which is absent in cloud containers. |

**The pattern that works is the one nightly-commit-review used.** Cloud Routines
need no PAT, no Actions minutes, no API-key secret, and no laptop. Local cron
and GitHub Actions are both dead paths right now.

## Two competing issue→PR loops

`autopilot-loop` (labels `ai-ready` / `wip-autopilot`, has real CI plumbing,
parked) and `issue-to-pr-loop` (labels `auto-ready` / `wip-auto`, declares itself
the successor, never wired). Disjoint label vocabularies, so they cannot collide —
and cannot cooperate either. Building a third before resolving this fork
compounds the problem.

## Decision

1. **Routines are the scheduler.** Every autonomous loop is a Routine, not a
   crontab entry and not an Actions schedule. Actions stays for PR-triggered
   checks only, and the team contract already bans it for team branches
   (`.ai/team-contract.json` → `github_actions.allowed_for_team_work: false`).
2. **One loop, not three.** `autopilot-loop` is the survivor — it has the state
   machine, the concurrency mutex, the caps, and the no-auto-merge invariant.
   `issue-to-pr-loop` and `build-loop` get archived rather than repaired.
3. **The loop body runs on `backend/graph/`.** Select work → plan → implement →
   verify → land or escalate is a cyclic graph with budgets and one human gate.
   That is exactly what the graph runtime was built for, and it replaces the
   hand-rolled bash state machine with something that checkpoints, resumes, and
   cannot spend past its budget.

## Why this and not "restore GitHub Actions"

Restoring Actions is cheaper — the parked workflows name the exact cron to put
back. Do it anyway (see owner actions). But it does not deliver the goal on its
own: Actions minutes are a metered resource that the 2026-06-23 session proved
can be exhausted in a day, and #500 has been open a week with every run failing.
A loop whose liveness depends on a billing state that has already failed once is
not an autonomous loop. Routines have no such meter.

## The real bottleneck is work supply, not scheduling

`brain/Maps/Open Loops.md` records the loop's own conclusion after 15 PRs in one
session:

> "the autonomous loop has exhausted the high-value buildable backlog … Continuing
> the loop now would mean manufacturing low-value niche work, against the
> 'highest value' intent."

Scheduling was never what stopped it. It ran out of work it could justify, and
the remaining items were owner-gated decisions. Any loop we arm needs a
**stop condition** — when the ranked backlog has no item above a value
threshold, the loop reports and idles instead of manufacturing work. Without
that it burns quota producing niche verticals.

## Guardrails to fix before arming anything

The current routine safety model is the weakest link:
`claude -p --dangerously-skip-permissions`, with writes confined to `docs/` by
*prompt convention only* — `docs/scheduled-routines.md` concedes this. An
engineering loop writes code, so it needs real limits:

- Verification is `bash scripts/ci_local.sh origin/main` (20 gates, zero Actions
  minutes) — the loop may not open a PR without a green local run pasted as
  evidence.
- No auto-merge. Preserve the `autopilot-loop` invariant.
- Deploy-quota awareness: cap PRs per day. The 2026-06-23 session blew the Vercel
  free-tier 100-deploys/day cap with 11 merged PRs and blocked all frontend
  deploys for 24h.
- Budget per run via `RunBudget`, so a stuck loop fails with a named node instead
  of spending.

## Owner actions (only the account owner can do these)

1. **#500** — raise the Actions spending limit at
   `github.com/settings/billing/summary`. Every hosted run has failed in 3-5s
   since 2026-07-20.
2. **#399** — rotate `AUTOPILOT_GH_TOKEN`, then restore `0 */4 * * *` in
   `autopilot-issue-loop.yml`.
3. **#403** — set `ANTHROPIC_API_KEY` in Actions secrets; restore the
   `kb-autopopulate.yml` cron.
4. **#394** — fix brain-refresh credentials; restore `refresh-brain.yml`.
5. Approve Routine creation — the MCP `create_trigger`/`list_triggers` calls
   require interactive approval, so a headless session cannot arm a Routine
   itself.

Items 1-4 are not required for the Routine path. They are required to get CI and
the KB back, which the loop wants for verification breadth.

## Consequences

- One loop to reason about instead of three, with one label vocabulary.
- Loop liveness stops depending on a laptop being awake or a bill being paid.
- The graph runtime gets its first real consumer, which is the honest test of
  whether it was worth building.
- `issue-to-pr-loop` and `build-loop` get archived — sunk design work discarded
  deliberately rather than left as decoys for future sessions.
