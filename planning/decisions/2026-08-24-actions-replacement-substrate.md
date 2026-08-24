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

### The landmine: restoring billing would create duplicate writers

This is the strongest argument for disabling the replaced workflows *now*,
independent of the noise.

Four workflows have live Routine counterparts doing the same job. Both halves
write to the repository. Today only one half runs, because Actions are dark —
so the conflict is invisible. **The moment Actions billing is restored, all four
pairs start running concurrently**, each committing to `main` or opening PRs:

| Job | Actions (dark, still `active`) | Routine (live, firing) |
|---|---|---|
| KB auto-populate | `kb-autopopulate.yml` | `0 6,18 * * *` — last fired 06:02 today |
| Autopilot issue loop | `autopilot-issue-loop.yml` | `28 */6 * * *` — last fired 12:33 today |
| Uptime watch | `public-uptime-watch.yml` | `56 * * * *` — last fired 12:56 today |
| Brain refresh | `refresh-brain.yml` | `0 9 * * 1` — last fired 09:00 today |

Two agents independently compiling the knowledge base and pushing, or two
autopilot loops both claiming the same `ai-ready` issue and opening competing
PRs, is a worse failure than either being off. Fixing billing would look like a
recovery and behave like a regression.

Disabling the four is therefore not just noise cleanup — it defuses a conflict
that is currently masked by the outage.

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

Ask one question first: **does this job write to the repository?**

```
writes to repo?
├── yes ── needs judgment/codegen? ── yes ─→ Claude Code Routine
│                                  └─ no ──→ Routine (still: only substrate that can push)
└── no  ── is it agent/LLM work? ─── yes ─→ Managed Agents scheduled deployment
                                   └─ no ──→ backend _automation_loop tick   ← free
```

Merge gating is a separate axis and is addressed below, because none of the
three scheduled substrates can do it.

## The honest gap: automation vs enforcement

Everything above restores **automation**. None of it restores **enforcement**.

- A Routine cannot block a merge. It runs on a clock, not on a pull request.
- The pre-push hook (`scripts/hooks/pre-push`, 10 checks: JS/TS + Python test
  quality, fast pytest subset, frontend build, `__future__` scan, `.env`
  gitignore, semgrep, plan drift, migration schema-log, widget sync) is real
  coverage — but it is **opt-in** (`scripts/install-hooks.sh` must be run) and
  **bypassable** (`git push --no-verify`). It encourages; it does not enforce.

So for anything that must be *enforced* rather than *encouraged* — tenant
isolation on a payments PR, the widget 3-mirror byte-identity invariant — there
is no substitute while Actions are dark. The only real answers are restoring
Actions billing or attaching a self-hosted runner. **This document does not
pretend otherwise**, and a plan that quietly downgrades enforcement to a
bypassable local hook without saying so would be the wrong outcome.

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
