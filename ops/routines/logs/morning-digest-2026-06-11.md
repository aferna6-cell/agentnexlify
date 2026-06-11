# Morning Digest — 2026-06-11

> Generated: 2026-06-11 UTC | Subconscious run 2026-06-11 active

---

## Commits (last 24h) — 10 total

- `c932350` docs: auto-log bug fix from ad4f83f
- `ad4f83f` subconscious: run 2026-06-11 — Fix channels_instagram.py from __future__ + 10 em-dashes → Check 10 auto-wires tonight
- `7a5fb98` docs: auto-log bug fix from 7c8825c
- `7c8825c` Home redo + Agent OS uploads/image-gen + Instagram connector (PR #232)
- `11c229a` Security: escape HTML in approval-notification email (PR #231)
- `364a1cc` Record migration 137 applied (marketing_addon columns dropped) + sync drift manifest (PR #230)
- `247834b` docs: auto-log bug fix from 66aac38
- `66aac38` Hotfix: remove orphaned @xyflow/react manualChunks entry breaking prod frontend build (PR #229)
- `a5c65b5` Retire marketing add-on into Agent OS, schema-drift guard, gap analysis + approval notifications (PR #228)
- `e653563` Close all code-shaped launch-rubric items: 221/262, dims 2/3/5 complete (PR #227)

**Nightly verdict:** PR #232 (Instagram connector + Home redo) landed. Subconscious run 55 already opened PR #233 (DRAFT) targeting the 2 invariant violations it introduced: `from __future__` in channels_instagram.py + 10 em-dash violations in 7 JSX files. Tonight's nightly should auto-wire Check 10 to pre-commit once those land.

---

## Issues (opened/updated)

| # | Title | State | Labels |
|---|-------|-------|--------|
| **#206** | security: use timingSafeEqual for X-Agent-Token comparison | OPEN | security, high |
| **#213** | Emit activity_log rows for all 4 automations (dashboard parity) | OPEN | -- |
| **#217** | Stripe Connect: self-serve own-payments — BLOCKED on billing-arch | OPEN | backend |
| **#216** | Vertical agent presets + lead-qualifier control UI (the moat) | OPEN | backend, frontend |
| **#215** | Integration health dashboard + "is my widget live?" probe | OPEN | backend, frontend |
| **#214** | WordPress plugin for one-click widget install (no-code embed) | OPEN | frontend, widget |
| **#194** | Em-dash violations blocking Item A (check_project_invariants) | OPEN | nightly-review, medium |
| **#193** | [subconscious] Moratorium: 13 pending items, oldest 44 days | OPEN | moratorium |

---

## Open PRs Needing Action

| PR | Age | State | Title |
|----|-----|-------|-------|
| **#233** | 0d | DRAFT | subconscious run 55 — fix channels_instagram.py from __future__ + 10 em-dashes ← **MERGE THIS TODAY** |
| **#212** | 3d | DRAFT | feat(os): web-grounded research worker for Agent OS |
| **#211** | 3d | DRAFT | Agent OS north-star: gap #1 Act hardening + gap #2 learning loop |
| **#209** | 4d | DRAFT | subconscious run 52 — Fix timing-safe token comparison in auth.ts (GH #206) ← **MERGE: fixes security issue** |
| **#200** | 8d | DRAFT | subconscious run 49 — Extend nightly SKILL.md + 5 JSX em-dash patch |
| **#32** | 58d | open | chore: bump react-dom 18→19 in /frontend |
| **#30** | 58d | open | chore: bump react-helmet-async 2→3 in /frontend |
| **#27** | 58d | open | chore: bump dompurify 3.3→3.4 in /frontend |
| **#25** | 58d | open | chore: bump @vitejs/plugin-react 4→6 in /frontend |
| **#21** | 58d | open | chore: bump @vitest/coverage-v8 3→4 in /frontend |

**Oldest actionable:** Dependabot PRs (58d) all stale — dep bumps, low risk, could batch-merge.

---

## Subconscious Recommendation (run 55)

**Fix `channels_instagram.py` line 1 (`from __future__ import annotations`) + clear 10 em-dash violations across 7 JSX files → `check_project_invariants.py` exits 0 → nightly auto-wires Check 10 to pre-commit tonight.**

PR #233 (DRAFT) already exists for this — just review and merge.

Standing actions still live:
- Merge PR #183 (~10 min): billing.py missing 15000→autopilot + 25000→professional price mappings
- Item B (check-widget-sync.sh): MISSING 50+ days — consider explicit inline impl in next session
- email_sequences.py (1255L): split blocked on GH #181
- Home.jsx (1171L): god-class, schedule via /god-class-splitter

---

## Top 3 Priorities Today

1. **Merge PR #233** — subconscious run 55. Clears `from __future__` in Instagram connector (critical: causes 422 on ALL 12 endpoints) + 10 em-dashes. Unblocks Check 10 nightly wire tonight. ~15 min review.

2. **Merge PR #209** — timing-safe token comparison (security, `high`). Fixes GH #206, been open 4 days. Low-risk 1-file change in auth.ts.

3. **Merge PR #183** (billing plan price fix) — 15000→autopilot + 25000→professional mapping wrong. Revenue impact. Confirmed 10 min job per subconscious run notes.

---

## KB Status

Last log entry: 2026-05-05. KB auto-populate cron is stale — likely blocked by network sandbox or missing Supabase token. No new articles since ~5 weeks ago (87→98 articles). **Backlog:** 4 wiki articles compiled but embeddings not upserted (Supabase MCP unauthorized in cron env).

---

> Rubric: 221/262 (84%). Dims 2/3/5 complete. Moratorium active: 13 items.
