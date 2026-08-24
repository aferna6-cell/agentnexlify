# GitHub Actions replacement substrate

Date: 2026-08-24 · Status: proposed · Related: GH #500, #399, #403, #394 ·
Supersedes nothing · Builds on `2026-07-27-autonomous-engineering-substrate.md`

## The finding that matters

**The migration already happened — for 4 of 20 workflows — and nobody turned the
old ones off.**

On 2026-07-23 four Actions workflows were replaced with live Claude Code
Routines, each named for what it replaced. They are firing today. But every
Actions workflow is still `state: "active"`, including those four. So the dead
half of the estate keeps firing and failing on a schedule.

## Verified state

Checked directly, not inferred:

- **20 workflows, every one `state: "active"`.** Not one disabled.
- **All dark since 2026-07-20** — GH #500, Actions spending limit. Already
  recorded in `scripts/autonomy/ROUTINE.md:196`: *"#500 — Actions spending
  limit. All CI dark since 2026-07-20."*
- **Jobs die before doing anything.** Run 32729384546 / job 97437915152:
  `started_at` 12:51:54, `completed_at` 12:51:55. One second — no checkout, no
  install. Infrastructure refusal, not a code failure.
- **Observed cadence ~150 failed runs/day on `main`** (from run timestamps
  between 08:58 and 12:52: KB Auto-Populate, Refresh Second Brain and Autopilot
  Issue Loop each firing every ~25-30 min, plus push-triggered runs).
- **10 Routines live and firing**, four explicitly labelled as Actions
  replacements: Autopilot Issue Loop, Prod Uptime Watch, KB Auto-Populate,
  Weekly brain connector refresh. Plus nightly-commit-review, morning-digest,
  kb-drift, subconscious ×2, weekly-skill-discovery.

### Why this is worse than "CI is off"

Uniform red is indistinguishable from real red. This already cost real time:
PR #677 showed two failed checks, and disproving them required checking out
`origin/main` in a clean worktree to show it failed identically. **A monitoring
estate that always fails monitors nothing** — it actively hides the next real
failure. That is the cost being paid right now, and it is larger than the
missing automation.

### The landmine: the parked workflows carry instructions to recreate a conflict

Four workflows have live Routine counterparts doing the same job, and both
halves write to the repo. But the risk is subtler than "they will both run",
and the precise version matters:

| Job | Actions cron on `main` | Routine (live) | Conflict today? |
|---|---|---|---|
| Uptime watch | `0 */6 * * *` — **live cron** | `56 * * * *` | **Yes**, the moment Actions work |
| KB auto-populate | `0 6 31 2 *` — Feb 31, parked | `0 6,18 * * *` | No — but see below |
| Autopilot issue loop | `0 6 31 2 *` — Feb 31, parked | `28 */6 * * *` | No — but see below |
| Brain refresh | `0 6 31 2 *` — Feb 31, parked | `0 9 * * 1` | No — but see below |

Only `public-uptime-watch` is a live duplicate. The other three are parked on an
impossible date — **and each one carries a comment telling the next maintainer
exactly how to un-park it**:

- `kb-autopopulate.yml:10-12` — *"Restore `0 6,18 * * *` after…"*
- `autopilot-issue-loop.yml:5-7` — *"restore…"*
- `refresh-brain.yml:10-11` — *"Restore `17 7 * * *` after fixing."*

Those restore instructions were written **2026-07-20**. The Routines that now do
the same jobs were created **2026-07-23** — three days later. So the
instructions are stale by construction: they predate their own replacements and
were never revisited. Whoever fixes the billing will read them, follow them in
good faith, and recreate the conflict believing they are restoring service.

Note the restore cron in `kb-autopopulate.yml` is `0 6,18 * * *` — **byte-identical
to the live KB Routine's schedule**. Un-parking it produces two agents compiling
the knowledge base and pushing to `main` on the same cron.

That is the actual landmine: not a race that fires today, but a documented,
inviting instruction to start one. Disabling the four (or at minimum correcting
those comments) defuses it.

### A discrepancy I could not resolve

GitHub recorded many `event: "schedule"` runs today for the three *parked*
workflows — KB Auto-Populate at 08:59, 09:51, 10:23, 10:58, 11:28, 11:54,
12:22, and similar cadences for Refresh Second Brain and Autopilot Issue Loop —
each with a real job record failing in 1-3 seconds (e.g. run 32726777439, job
97429733746: started 12:22:44, completed 12:22:46).

A `0 6 31 2 *` cron should never dispatch. I verified the cron values directly
in the files on `main`, so both observations are solid and they are in tension.
Plausible causes are stale scheduler state cached from before the 2026-07-20
parking, or GitHub retrying dispatches that the spending limit rejects. **I could
not determine which from here and am not guessing.**

It does not change the recommendation — disabling the workflows stops the runs
under either explanation — but it does mean the ~150 runs/day figure is
*observed*, not derived from the crons, and anyone reasoning from the cron
expressions alone will underestimate the noise.

## Substrates available

Four, all already present in this project. None is hypothetical.

| Substrate | Commits to repo? | Gates a merge? | Marginal cost | Proven here |
|---|---|---|---|---|
| **Claude Code Routine** | **Yes** — full session with a repo clone | No | Claude usage | 10 live, all firing |
| **Backend `_automation_loop`** | No — no repo, DB/API only | No | **Zero** — already running 24/7 | ~40 jobs on it |
| **Managed Agents deployment** | No — sandboxed, cannot push | No | API + $0.08/h runtime | Shipped 2026-08-24, none armed |
| **Local pre-push hook** | n/a — runs before the push | **Advisory only** | Zero | 10 checks live |

Notes that decide the routing:

- **Routines are the only substrate that can write to the repo.** That is the
  whole reason four jobs went there and not elsewhere.
- **The backend loop is free and already leased.** `backend/main.py:365`,
  60-second tick, `% 5` / `% 15` / `% 30` tiers, DB lease so exactly one of the
  four Uvicorn workers acts. A daily wall-clock job goes in the `% 30` tier and
  self-gates on the hour — the pattern `purge_photo_quote_images_30d` already
  uses (`main.py:548-553`, gated to 03:00 UTC, idempotent per row).
- **Managed Agents deployments** now exist
  (`backend/services/managed_agents_deployments.py`,
  `scripts/managed_agents/provision_deployments.py`) with cron, IANA timezone,
  per-run spend cap, run history and webhooks. They cannot `git push`, which is
  exactly why `field-monitor-weekly` could not migrate.

## Routing rule

The obvious question — "does this job write to the repo?" — is too coarse.
Eleven scheduled jobs "write back", but they split three ways, and only the
first needs a Routine:

| What it actually needs | Count | Jobs |
|---|---|---|
| **git commit + push** (working tree) | 3 | `field-monitor-weekly`, `refresh-brain`, `kb-autopopulate` |
| **PR creation** | 2 | `ai-auto-improve`, `autopilot-issue-loop` |
| **Issues API only** — no working tree | 6 | `daily-business-digest`, `health-check`, `dead-code-sweep`, `dependency-audit`, `schema-sync-check`, `public-uptime-watch` |

That last row is the useful discovery: **six of eleven need nothing but an HTTP
call to the Issues API.** They do not need a runner, a checkout, or a Routine.
Several already embed their whole implementation as a heredoc in the YAML and
only check out the repo vestigially (`daily-business-digest` does this in five
of its six jobs).

So the rule is:

```
needs a git working tree (commit/push/PR)?
├── yes ─→ Claude Code Routine        (the only substrate that can push)
└── no  ── is it agent/LLM work? ── yes ─→ Managed Agents scheduled deployment
                                  └─ no ──→ backend _automation_loop tick   ← free
```

For the six Issues-API jobs the backend loop is the right home: it is already
running, already leased, and posting an issue is a plain HTTPS call it can make
as easily as any other. That is six runners' worth of work absorbed at zero
marginal cost.

Merge gating is a separate axis and is addressed below, because none of the
three scheduled substrates can do it.

## The honest gap: automation vs enforcement

Everything above restores **automation**. None of it restores **enforcement**.

- A Routine cannot block a merge. It runs on a clock, not on a pull request.
- The pre-push hook (`scripts/hooks/pre-push`, 10 checks) is real coverage on
  paper — but it is **opt-in** (`scripts/install-hooks.sh` must be run) and
  **bypassable** (`git push --no-verify`). It encourages; it does not enforce.
- **And it is not currently installed.** `.git/hooks/` in this checkout contains
  only `*.sample`. So the fallback everyone assumes is catching things is, right
  now, catching nothing. Any plan that leans on it must start with running
  `install-hooks.sh`.

So for anything that must be *enforced* rather than *encouraged* — tenant
isolation on a payments PR, the widget 3-mirror byte-identity invariant — there
is no substitute while Actions are dark. The only real answers are restoring
Actions billing or attaching a self-hosted runner. **This document does not
pretend otherwise**, and a plan that quietly downgrades enforcement to a
bypassable, uninstalled local hook without saying so would be the wrong outcome.

### If you do lean on `ci_local.sh`, know the five gaps

`scripts/ci_local.sh` claims gate parity with `pr-check.yml` and gets close —
it even runs three gates `pr-check` does not. Five real gaps remain:

1. Root `npm audit` — not covered.
2. `demo-platform` `npm ci` / audit / coverage — not covered.
3. **pytest scope differs**: `pr-check` runs `tests` plus an explicit ~90-file
   list; `ci_local` runs `backend/tests/` wholesale and **omits the root
   `tests/` directory**. Each covers files the other misses — this is the gap
   most likely to let a real regression through.
4. Semgrep is **blocking** in CI but **optional** locally.
5. `check_migration_schema_log.py` is in `pre-push` (blocking) but not in
   `ci_local.sh` — so it is only enforced if the hook is installed, which it
   isn't.

Two PR gates *are* fully redundant with `ci_local.sh` today and could be
retired outright: `agent-config-security.yml` (identical command at
`ci_local.sh:114`) and the PR path of `lead-qualifier-eval.yml` (its only
blocking step is collected by `pytest backend/tests/`).

## Recommended sequence

**1. Stop the noise first (hours, not days).** Disable the workflows that are
already replaced or superseded. This is not a migration — it is turning off
things that only produce false failures. Highest value per unit effort in this
whole document, because it makes the next real failure visible.

**2. Route the unreplaced scheduled jobs** by the rule above. Prefer the backend
loop wherever the job is pure DB/API — it is free and already running, so it
adds no new operational surface.

**3. Decide enforcement deliberately.** Either restore Actions billing for the
handful of genuinely merge-gating checks, or accept the pre-push hook and say
out loud that those invariants are now advisory. Both are defensible. Drifting
into the second by accident is not.

**4. Only then consider Managed Agents deployments** for the agent-driven jobs
that do not write back. Lowest urgency: it is new surface, and the backend loop
or a Routine already covers most cases.

## Not done here

**Nothing was armed.** No Routine was created, no workflow disabled, no
deployment provisioned. Creating live recurring jobs that commit to the
repository is consequential and outward-facing, and the routing above changes
which substrate owns production automation — that is the owner's call, not a
side effect of an audit.

The mechanism exists and is proven; what remains is a decision about which jobs
matter enough to keep.

## Cross-refs

- `planning/decisions/2026-07-27-autonomous-engineering-substrate.md` — chose
  Routines over Actions/cron; this extends that decision to the whole estate
- `scripts/autonomy/ROUTINE.md:196` — the #500 record
- `backend/main.py:365` — the in-process leased scheduler
- `backend/services/managed_agents_deployments.py` — deployment support
- `scripts/hooks/pre-push` — the 10 local checks
- `scripts/ci_local.sh` — the full local gate
