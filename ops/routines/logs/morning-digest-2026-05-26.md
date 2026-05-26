# Morning Digest — 2026-05-26

Generated: 2026-05-26 UTC

---

## Commits (last 24h)

- `aea5fff` subconscious: run 34 — Fix GH #181 AMOUNT_TO_PLAN governance mandate
- `e848b87` ops: nightly-commit-review 2026-05-26
- `96bcdb7` subconscious: run 33 — Create god-class-splitter skill (autonomously implemented by nightly review)
- `0a59147` docs(agent-os): partner brief for Agent OS rehaul — done/todo status
- `b1e0ed0` ops: kb-drift sweep 2026-05-25 — no drift detected
- `9201af9` chore: weekly skill discovery report 2026-05-25
- `45397c2` ops: morning-digest 2026-05-25

**7 commits.** Nightly review autonomous: god-class-splitter SKILL.md created (run 33 winner). Subconscious run 34 governance mandate fired for GH #181.

---

## Issues — Open / Recently Updated

| # | Title | Status |
|---|-------|--------|
| #185 | CI: 21 pytest failures (pyo3/cryptography PanicException) — env, not code | OPEN — env bug, not regression |
| #184 | Morning digest 2026-05-25 | OPEN — digest |
| #181 | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) | OPEN — **P0 billing bug, governance mandate** |
| #178 | Morning digest 2026-05-22 | OPEN — digest |
| #176 | Morning digest 2026-05-21 | OPEN — digest |
| #169 | [subconscious] Moratorium active — 5 pending items, oldest 30 days | OPEN — moratorium day 21+ |
| #174–168 | Morning digests 2026-05-20 → 2026-05-15 | OPEN — digest backlog |

**Actionable:** #181 only. All others are tracking/digest.

---

## Open PRs Needing Action

| # | Title | Age | State | Action needed |
|---|-------|-----|-------|---------------|
| #177 | feat(agent-os): chat-first Agent OS — spec + P0 foundation | 5 days | Draft | Review — largest open PR |
| #182 | Split invoices.py god class into 4 service modules + router | 3 days | Draft | Review + merge or close |
| #183 | subconscious: run 33 — GH #181 billing fix (CI trap) | 2 days | Draft | Contains billing fix context — review |
| #186 | build(deps-dev): bump @typescript-eslint/parser 8.58→8.60 | 1 day | Open | Merge (Dependabot, safe) |
| #15 | chore(deps): bump actions/upload-artifact 4→7 | 42 days | Open | Merge (Dependabot, stale) |
| #14 | chore(deps): bump actions/setup-node 4→6 | 42 days | Open | Merge (Dependabot, stale) |
| #12 | chore(deps): bump actions/setup-python 5→6 | 42 days | Open | Merge (Dependabot, stale) |
| #13 | chore(deps): bump peter-evans/create-pull-request 6→8 | 42 days | Open | Merge (Dependabot, stale) |
| #11 | chore(deps): bump actions/cache 4→5 | 42 days | Open | Merge (Dependabot, stale) |
| #172 | chore(deps-dev): bump eslint 9.39→10.4 | 8 days | Open | Merge (Dependabot) |

**5 stale Dependabot PRs (42 days) need batch merge or close.**

---

## Subconscious Recommendation (Run 34)

**Winner: Fix GH #181** — governance mandate fired (4th consecutive run).

- `billing.py:~264` — add `15000: "autopilot"` + `25000: "professional"` to `AMOUNT_TO_PLAN`
- `test_billing_amount_to_plan.py:38-44` — remove backwards issue-#81-era assertions; add positive current-price tests
- CI actively certifying broken state. Two prior fix attempts (c72b535, 1eaaeec) failed — backwards tests blocked them.
- Effort: S (~15 min). Confidence: HIGH.
- **After fix:** invoke `/moratorium-sprint` — Items A+B+D (~40 min, drops moratorium pending toward exit).

---

## Top 3 Priorities Today

1. **Fix GH #181** — billing bug, 4-run governance mandate. `billing.py:~264` + `test_billing_amount_to_plan.py:38-44`. ~15 min. Closes the subconscious loop.
2. **Run `/moratorium-sprint`** — after #181 fix. Items A (pre-commit hook), B (widget-sync script), D (lead-qualifier eval CI). Moratorium at day 21+, 8 pending items.
3. **Batch-merge stale Dependabot PRs** (#11 #12 #13 #14 #15 #172 #186) — 7 open, oldest 42 days. Low risk, high hygiene.

---

## KB Status

Last compile: 2026-05-05 (no new entries since). Network sandbox blocked discover runs. No new articles today.

---

## Flags

- CI env broken: `pyo3/cryptography` PanicException on `.venv` — tracked in #185. Not a code regression.
- Moratorium: day 21+, 8 pending items. Exit condition: ≤2 pending.
- Zero production feature commits since PR #180 (2026-05-23).
