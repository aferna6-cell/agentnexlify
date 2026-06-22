---
type: project
name: "Autonomous Dev Operation"
tags:
  - project
  - automation
source_status: source-backed
sensitivity: normal
status: active
last_verified: 2026-06-22
---

# Autonomous Dev Operation

## Summary
[[AgentNexLiFy]] is built largely by an **agent-assisted, partly-autonomous development
operation** layered on the repo. Scheduled routines file issues, review commits, and land
low-risk fixes; a human (the owner) approves the rest.

## Components (observed in GitHub)
- **Morning digest** — daily summary issue: commits landed, open issues, top-3 priorities.
- **Nightly commit review** — triages last 24h commits; auto-fixes LOW-risk, files MEDIUM/HIGH.
- **Subconscious loop** — numbered improvement runs that pick one high-value fix per cycle
  (e.g. runs 58–64 drove the #308/#292/#293 fixes).
- **Issue → PR autopilot** — issues become worktree PRs.

## Why it matters
- It is how a solo founder ships at high volume (often 10–30 commits/day).
- It also produces the open-loop backlog tracked in [[Open Loops]].
- Reflects the owner's "[[User Engineering Rules|build the system, not the answer]]" philosophy.

## Recurring themes (from history)
- **Plan-name drift** after every repricing — billing dicts/gates miss live plan names
  (#81/#181/#292/#293), caught repeatedly by the subconscious loop.
- **Silent-failure bug class** — swallowed exceptions found by nightly review (#97/#99/#109/#94).
- **Stripe webhook idempotency/race** hardening recurs (#295/#301/#308).
- **Launch-readiness grind** (191→208→221/262).

## Current friction
- KB embeddings broken since ~2026-04-30 (missing `VOYAGE_API_KEY` in cron).
- GitHub Actions minutes exhaustion → crons throttled, local CI mirror added.
- Container-expiry risk: large unpushed batches (e.g. PR #333, 51 commits).
- ~50 open PRs (many stale Dependabot + feature branches) — review/merge backlog.

## Related
- [[AgentNexLiFy]] · [[Daily Skills Gate]] · [[Open Loops]] · [[GitHub Activity]] · [[Claude Model Routing]]

## Provenance
- [[connector-github-issues]] · [[connector-github-history]] · [[repo-agentnexlify-claude-md]]
