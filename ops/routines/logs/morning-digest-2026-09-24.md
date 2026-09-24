# Morning Digest — 2026-09-24

Generated: 2026-09-24 (automated routine)

---

## ⚠️ CRITICAL — Act Today

**AUTOPILOT_GH_TOKEN expires 2026-10-02 — 8 days.** GH #399 open. Nightly loop and issue-to-pr-loop break on expiry. Rotate now.

---

## Commits (last 24h)

- `bcba89b` subconscious: run 2026-09-24 — Step 9J priority queue fix (sort:created-asc + perPage=5)
- `7af7013` ops: nightly-commit-review 2026-09-24
- `bd65562` subconscious: run 2026-09-23 — Step 9E P0 credential expiry tier (7th carry)

3 commits. Nightly + subconscious loops active and firing.

---

## Issues (updated last 24h)

| # | Title | State | Labels | Updated |
|---|-------|-------|--------|---------|
| [#399](https://github.com/aferna6-cell/agentnexlify/issues/399) | P0: Rotate AUTOPILOT_GH_TOKEN before 2026-10-02 | OPEN | P0, human-action-required | 2026-09-24 |
| [#892](https://github.com/aferna6-cell/agentnexlify/issues/892) | [CI][Safety] staging credential rejection test escapes to network | OPEN | bug, p1, ci, blocker | 2026-09-23 |
| [#897](https://github.com/aferna6-cell/agentnexlify/issues/897) | Morning digest 2026-09-23 | OPEN | digest | 2026-09-23 |
| [#895](https://github.com/aferna6-cell/agentnexlify/issues/895) | [Ops][P2] Step 9G KB self-heal depends on unavailable gh CLI in CCR | OPEN | bug, p2, ops | 2026-09-23 |
| [#769](https://github.com/aferna6-cell/agentnexlify/issues/769) | M9.4 follow-up — analyze live bakeoff misses before more spend | OPEN | p1, diagnostic, agent-os | 2026-09-23 |

---

## Open PRs

All 6 are Dependabot, opened 2026-09-21 (3 days old). No human-authored open PRs.

| # | Title | Age |
|---|-------|-----|
| [#891](https://github.com/aferna6-cell/agentnexlify/pull/891) | chore(deps): update bcrypt ≥5,<6 in /backend | 3d |
| [#890](https://github.com/aferna6-cell/agentnexlify/pull/890) | chore(deps): bump supabase 2.28.3→2.31.0 in /backend | 3d |
| [#889](https://github.com/aferna6-cell/agentnexlify/pull/889) | chore(deps): update google-api-python-client ≥2.200.0,<3 in /backend | 3d |
| [#888](https://github.com/aferna6-cell/agentnexlify/pull/888) | chore(deps): bump uvicorn 0.52.4→0.53.0 in /backend | 3d |
| [#887](https://github.com/aferna6-cell/agentnexlify/pull/887) | chore(deps-dev): bump vitest group in /demo-platform | 3d |
| [#885](https://github.com/aferna6-cell/agentnexlify/pull/885) | chore(deps-dev): bump jsdom 30.0.1→30.1.0 in /frontend | 3d |

Step 9J fix (Run 128) targets these — sort:created-asc + perPage=5 will process oldest first in tonight's nightly.

---

## Subconscious Recommendation (Run 128)

**Step 9J — Dependabot PR queue should use `sort:created-asc`, `perPage=5`**

7+ consecutive nightly runs skip 17/19 Dependabot PRs (token budget depletes before processing). Fix: oldest PRs processed first, 5 per run. ~3-line SKILL.md edit. Run 127 winner (Step 9E P0 escalation tier) was implemented by yesterday's nightly. Run 128 winner is Step 9J — autonomous-executable tonight.

Confidence: HIGH.

---

## Knowledge Base

Last compile: 2026-08-26 (29 days ago). Stale — compile blocked by missing ANTHROPIC_API_KEY (GH #403) and VOYAGE_API_KEY (GH #618). No new articles in last 24h.

---

## Top 3 Priorities Today

1. **ROTATE AUTOPILOT_GH_TOKEN** — GH #399, expires 2026-10-02 (8 days). Hard deadline. Nightly loop, issue-to-pr-loop, all autonomous ops break if missed. Human action only — no code can fix this.

2. **Fix CI blocker #892** — staging credential rejection test escaping to network. P1 blocker. Blocks clean CI on all PRs. Needs investigation: test isolation or credential stub leak.

3. **Merge or review Dependabot PRs** — 6 open (supabase, bcrypt, uvicorn, google-api-python-client, vitest, jsdom). All 3 days old. bcrypt and supabase are security-adjacent. Step 9J nightly fix will auto-process oldest tonight — but manual merge of bcrypt #891 now is safe and immediate.

---

## Carry-forward Watch

- GH #769 (M9.4 bakeoff miss analysis) — P1, diagnostic, agent-os. Open 21 days. No recent movement.
- GH #895 (Step 9G gh CLI unavailable in CCR) — P2 ops. Will persist until CCR environment gets gh CLI or Step 9G is patched to skip gracefully.
- KB staleness — resolves when #403 (ANTHROPIC_API_KEY) is rotated/added to CCR env.
