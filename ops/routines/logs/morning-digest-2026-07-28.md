# Morning Digest — 2026-07-28

Generated: 2026-07-28 UTC

---

## Commits (last 24h)

- `a72d14b` ops: nightly-commit-review 2026-07-28 [auto-nightly]
- `d64a5e4` fix(autonomy): stop the open_pr handoff contradicting the merge node (#603)
- `c624700` test(router): pin router-composition semantics ahead of the fastapi bump (#602)
- `d7259d4` feat(graph): agent graph runtime + autonomous engineering loop (#599)
- `6e032f8` fix(routes): version-stable route introspection (#265) (#600)
- `2cdd2da` chore: weekly skill discovery report 2026-07-27
- `e9701aa` ops: morning-digest 2026-07-27

7 commits. Heavy day — autonomy graph runtime shipped + router fixes + tests. Auto-nightly ran.

---

## Issues Updated (last 24h)

### NEW — #605 [OPEN] Crash mid-superstep strands autonomy run in `running` forever — no sweeper
- Opened: 2026-07-28
- Reproduced in the wild: cycle 7, verify node crash, run `a82c9f38` stuck as `running` forever
- No sweeper → orphans accumulate silently; `running` becomes a lie
- Fix needed: sweeper + node re-entry safety classification + heartbeat + `run_loop list`
- Cross-refs: #599, `backend/graph/checkpoint.py`, `migrations/189_graph_runs.sql`

### CLOSED — #601 Pin router-composition semantics with characterization tests (#265 prereq)
- Closed: 2026-07-28 (completed)
- PR #602 landed: `backend/tests/test_router_composition_semantics.py` + requirements.txt comment fix
- Unblocks #265 fastapi cap lift

### OPEN — #265 deps: re-raise fastapi <0.136 cap once starlette is bumped
- Updated: 2026-07-27
- Prereq (#601) now done. PR #604 opened today to lift the cap. Review needed.

### OPEN — #500 GH Actions down — all hosted-runner jobs fail in 3s [human-action-required]
- **Day 8** since 2026-07-20 12:21 UTC
- Still blocking ALL CI, PR validation, monitoring, nightly loops
- Fix: `github.com/settings/billing/summary` → spending limit or payment

---

## Open PRs Needing Action

### #606 DRAFT — subconscious: run 101 — feature-docs-trio SKILL.md
- Age: 0 days (opened today)
- New subconscious run — feature docs trio implementation

### #604 DRAFT — deps: lift the fastapi <0.136 cap — not a real incompatibility
- Age: 0 days (opened today)
- Prereq (#601) done. Router semantics pinned. Ready to review and merge.

### #575 DRAFT — Tenant-silence ops alert + Managed Agents Phase 0 prep
- Age: 5 days
- tenant_silence_watch.py + migration 188 (file only, not applied) + managed_agent_run_log.py
- CI red due to #500 (not PR's fault). Owner review needed.
- Do NOT apply migration 188 until Phase 0 start.

### #577 DRAFT — subconscious: Step 9G + 9H KB self-healing + Actions heartbeat
- Age: 4 days
- SKILL.md only: auto-trigger KB autopopulate when stale >7d (9G) + GH #500 ping (9H)
- CI red due to #500. Safe to merge.

### Dependabot PRs (no action needed yet — review after GH Actions restored)
- #596 OPEN: fastapi bump (conflicts with #604 — #604 takes priority)
- #597 OPEN: uvicorn 0.49→0.51
- #598 OPEN: stripe <12 → >=15.3.1
- #595 OPEN: python-dateutil update
- #594 OPEN: pywebpush update
- #593 OPEN: react-dom 18.3.1→19.2.8 (demo-platform only)

---

## Subconscious Recommendation

**Run 101 (2026-07-28, PR #606):** feature-docs-trio — likely adding docs/SKILL.md for 3 features. New run fired today.

**Run 100 (2026-07-23):** Step 9G — auto-trigger KB autopopulate when stale >7d; comment diagnostics on #403 if secrets fail. Shipped in PR #577 (pending merge).

**Run 99 (2026-07-20):** Step 9F — KB staleness check. Live in nightly. Confirmed firing.

Subconscious now at observe → alert → self-heal arc. Step 9G merge unblocks the repair loop.

---

## KB Health

- Last successful run: 2026-07-23 (5 days ago)
- Step 9F threshold: >7 days → alert on #403. Not triggered yet.
- Step 9G (PR #577): merge to enable auto-repair before it tips over threshold.

---

## Autonomy Loop Status

- Graph runtime shipped (#599 = d7259d4). Running.
- Bug found in the wild (#605): crash mid-verify strands run in `running` permanently.
- Handoff fix also landed (#603): open_pr→merge contradiction fixed.
- Router introspection fixed (#600): version-stable route counting.
- Characterization tests landed (#602): FastAPI router semantics pinned.
- FastAPI cap lift drafted (#604): ready to review once #604 CI clears (blocked by #500).

---

## Top 3 Priorities Today

### 1. FIX GH ACTIONS SPENDING LIMIT [BLOCKER — owner only, day 8]
- URL: `github.com/settings/billing/summary`
- Raise spending limit or fix payment method
- Unblocks: ALL CI, PR merges, monitoring, nightly loops, dependabot
- Issue: #500

### 2. IMPLEMENT AUTONOMY SWEEPER [#605 — new defect, reproduced today]
- Stranded `running` runs accumulate silently after any crash mid-verify
- Needs: sweeper + node re-entry safety enum + `run_loop list` command + regression test
- Fresh issue, high urgency — graph is now live and cycling daily

### 3. MERGE PR #577 (Step 9G + 9H) + REVIEW PR #604 (fastapi cap lift)
- #577: SKILL.md only, safe to merge, activates KB self-repair before 7-day stale trigger
- #604: prereq done (#601 closed), router tests confirm semantics, cap was based on a measurement artifact not a real incompatibility
- Both blocked on CI only by #500 — merge both manually if comfortable

---

_Log: `ops/routines/logs/morning-digest-2026-07-28.md`_
