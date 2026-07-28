# Autonomous engineering loop — Routine prompt + arming runbook

The loop is driven by a **Claude Code cloud Routine**, not cron and not GitHub
Actions. Rationale in `planning/decisions/2026-07-27-autonomous-engineering-substrate.md`:
Routines are the only substrate in this project that currently survives without
a laptop, a PAT, or Actions minutes — `nightly-commit-review` has run unbroken
on one since 2026-07-20 while every Actions-scheduled loop sat parked.

## How the pieces fit

```
Routine fires  ──▶  Claude Code session  ──▶  run_loop CLI  ──▶  graph
   (the clock)        (the capability)         (the policy)      (the state)
```

The session can edit files, run git, and reach GitHub. The graph decides what
gets built, whether it passed, and whether it may ship. Neither can do the
other's job, and the gates are code, so the session cannot talk its way past a
failing check.

## Arming it (owner, one time)

Routine creation needs interactive approval, so this cannot be done from a
headless session. In an interactive Claude Code session:

1. Confirm the driver runs here at all:
   ```bash
   python3 -m scripts.autonomy.run_loop start --backlog /dev/null --help
   ```
2. Create the Routine with the prompt in the next section. Suggested schedule:
   **every 6 hours** (`0 */6 * * *`), matching the cadence the parked autopilot
   loop used. Start daily (`0 13 * * *`) if you want to watch a few cycles first.
3. Mode: **fresh session per fire**. Each run should start from a clean context;
   the loop's memory lives in `.autonomy/` and on GitHub, not in a conversation.
4. Record the returned `trig_...` id at the bottom of this file, the way
   `scripts/daily/nightly-commit-review.sh:28` records its own.

To pause: disable the Routine. There is no other switch to find.

## The Routine prompt

Copy everything between the fences.

```
Run one cycle of the AgentNexLiFy autonomous engineering loop.

Read first, in this order:
- CLAUDE.md (project rules — they bind you)
- brain/Maps/Home.md, then brain/Maps/Open Loops.md
- planning/decisions/2026-07-27-autonomous-engineering-substrate.md

## 1. Build a scored backlog

Fetch open GitHub issues from aferna6-cell/agentnexlify. For each, judge and
score it honestly:

  value       0..1  how much shipping this is worth
  effort      0..1  1 = multi-day
  confidence  0..1  how sure you are it can be done unattended, correctly
  risk        low | medium | high
  blocked     true if something outside this repo must happen first
  owner_gated true if it needs a decision only the owner can make
              (pricing, incentives, spend, anything with an external
              side effect that cannot be reverted from the repo)
  touches_frontend  true if it changes frontend/ or landing-page-v2/

Score conservatively. An inflated score is how this loop ends up shipping
niche work nobody asked for — the exact failure recorded in Open Loops after
the 2026-06-23 session. If you are unsure it can be done unattended, that is
low confidence, and low confidence is the correct answer.

Write the list to `/tmp/backlog.json` as `{"items": [...]}`.

## 2. Start the loop

Check out a working branch first (`claude/auto-<short-slug>`), and leave the
tree clean. The driver refuses to start otherwise.

    python3 -m scripts.autonomy.run_loop start \
      --backlog /tmp/backlog.json \
      --prs-opened-today <PRs THE LOOP opened in the last 24h> \
      --total-prs-today <PRs opened by ANYONE in the last 24h, bots included>

The two counts are different guards and conflating them is a real bug that has
already happened once. `--prs-opened-today` is the loop's own allowance (4/day).
`--total-prs-today` only trips a much higher deploy-pressure ceiling (60). On
2026-07-27 the first real run stood down because 20 PRs existed that day — 18 of
them Dependabot — which would have made "blocked" the loop's normal state.

It prints one JSON object. Obey `status`:

- `blocked` → a precondition failed (on `main`, dirty tree, or the daily PR
  budget is spent). `blockers` says exactly what to fix. Fix it and rerun, or
  stop and report if you cannot. Do NOT pass `--skip-preflight` to get past
  this — that flag is for diagnostics, and using it to silence a guardrail is
  the failure mode the guardrail exists to prevent.


- `awaiting_action` → do the action in `payload.instructions`, then resume:

      python3 -m scripts.autonomy.run_loop resume \
        --run-id <run_id> --result '<json>'

  Repeat until a terminal status. The actions are:
    implement → write the change on a NEW branch (never main), tests first,
                commit with [skip ci]. Do not push, do not open a PR.
    open_pr   → push and open a DRAFT PR, pasting the gate summary as merge
                evidence.
    merge     → confirm the PR's checks are green on GitHub, mark it ready,
                and merge it. ONLY the PR this run opened. If anything is red
                or unmergeable, resume with {"merged": false, "reason": "..."}
                and leave it open.
    escalate  → comment on the issue with what you tried, the failing gate
                output, and the specific decision needed. Then stop.

- `completed` → read `outcome`:
    merged     → shipped to production. Done for this cycle. Stop.
    pr_opened  → PR is open but not merged (merge declined, or the run
                 stopped before it). Stop.
    parked     → verified but the daily PR budget is spent. Stop.
    escalated  → handed to the owner. Stop.
    idle       → nothing cleared the value floor. Stop. Do NOT lower the bar
                 and do NOT invent work.
    dry        → the backlog is genuinely dry. Post ONE issue comment saying
                 so, and say in your final message that the Routine should be
                 paused until new work is filed.

- `failed` / `budget_exhausted` → do not retry. Report what happened.

## 3. Rules that override anything above

- Merge ONLY the PR this run opened. Auto-merge on green is owner-granted
  (2026-07-28); it does not extend to anyone else's PR, and never to a red one.
- Never work directly on main. Branch first.
- Never lower the value floor, edit scripts/autonomy/backlog.py, or hand-edit
  a checkpoint to get a different decision out of the loop. If the policy is
  wrong, say so in your final message and stop — changing the guardrail to
  clear the guardrail is the one thing that makes this system untrustworthy.
- Never change a test to make a gate pass (CLAUDE.md user-rules Rule 10).
- One task per cycle. Stop when the loop says stop.
- GitHub Actions is down (#500); `scripts/ci_local.sh` is the only real
  verification. The loop runs it for you — do not skip ahead of it.

Finish with: what you did, the outcome, and anything a human must decide.
```

## Watching it

```bash
python3 -m scripts.autonomy.run_loop status --run-id <id>   # where a run stopped
python3 -m scripts.autonomy.run_loop list                   # every run, stranded flagged
python3 -m scripts.autonomy.run_loop sweep --dry-run        # what a sweep would resolve
python3 -m scripts.autonomy.run_loop sweep                  # resolve crash-stranded runs to failed
ls .autonomy/                                               # every run's state
cat .autonomy/<run_id>/history.jsonl                        # superstep-by-superstep
cat .autonomy/<run_id>/steps.jsonl                          # per-node timing + errors
```

A run stuck in `running` with no activity for an hour has no process behind it
(a crash mid-superstep — GH #605). `sweep` resolves it to `failed` with the
reason recorded, and never re-runs a node: whether the dead run's work may be
redone is reported (`safe_to_retry`, from the per-node re-enterability marking
in `loop_graph.py`), not acted on. Runs paused at a handoff (`awaiting_input`)
are live no matter how old, and are never swept.

`.autonomy/` is local state, not history worth committing — it is gitignored.

## Guardrails, and where each one lives

| Guardrail | Enforced by |
|---|---|
| Never starts on main, or over a dirty tree | `gates.preflight` in `run_loop start` |
| The loop's own PR output is capped per day | `gates.deploy_budget_remaining` (4/day) |
| Stands down when the day's deploys are near the cap | `gates.deploy_pressure_exceeded` (60 total) |
| Only worthwhile work gets built | `backlog.VALUE_FLOOR` + `select()` |
| Loop stops instead of manufacturing work | `Selection.dry` → outcome `dry` |
| High-risk work is escalated, never done unattended | `backlog.ACTIONABLE_RISK` |
| Owner-gated decisions never get guessed | `WorkItem.owner_gated` |
| Nothing ships unverified | `verify` node runs `scripts/ci_local.sh` in-process |
| Bounded retry, not infinite | `MAX_IMPLEMENT_ATTEMPTS` + `RunBudget.max_node_visits` |
| Deploy quota is respected | `gates.deploy_budget_remaining` → outcome `parked` |
| Merges only its own PR, only after a green gate | `merge` node, reachable only downstream of `verify` |
| Merge rate is capped with the PR rate | `land` charges the 4/day allowance before `open_pr`/`merge` |
| A crash cannot lose the run | `FileCheckpointer` under `.autonomy/` |
| A crash cannot strand a run forever | `run_loop sweep` — resolves, never re-runs (#605) |

The reason `verify` runs the gate in-process rather than asking the session
whether its own work passed is the same reason the value floor is code: the
component being judged should not be the one reporting the verdict.

## What this does NOT fix

Four blockers stay owner-only. The loop works without them; the repo is worse
off until they are cleared.

- **#500** — Actions spending limit. All CI dark since 2026-07-20.
- **#399** — expired `AUTOPILOT_GH_TOKEN`.
- **#403** — `ANTHROPIC_API_KEY` missing from Actions secrets; KB autopopulate parked.
- **#394** — brain-refresh credentials; the brain goes stale without them.

## Routine registry

| Routine | Schedule | Trigger id |
|---|---|---|
| nightly-commit-review | `37 6 * * *` UTC | `trig_014nVaJAnhKSaXEDDsYuddJ9` |
| autonomous-engineering-loop | _not yet armed_ | _record the `trig_...` here_ |
