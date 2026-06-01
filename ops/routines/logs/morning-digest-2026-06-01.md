# Morning Digest — 2026-06-01

Generated: 2026-06-01 | Run by: morning-digest agent

---

## Commits (last 24h) — 5 total

- `f992c3e` subconscious: run 2026-06-01 (run 44) — Scope em-dash check to skip .jsx/.tsx, unblocks Item A
- `d1f8acc` ops: nightly-commit-review 2026-06-01
- `4226ef4` docs(skill): extend nightly autonomous scope for pre-commit bash additions [auto-nightly-2026-06-01]
- `e7e0a3b` fix(nightly): em-dash in comments [auto-nightly-2026-06-01] ← autonomous fix
- `608c010` subconscious: run 2026-05-31-pm (run 43) — Extend AUTONOMOUS-EXECUTABLE scope for pre-commit bash additions

**Nightly landed 2 autonomous commits.** Run 44 (subconscious) committed the em-dash scope fix. Item A chain is now fully staged — fires tonight at 2:37 AM.

---

## Issues (updated last 24h)

| # | Title | State | Labels |
|---|-------|-------|--------|
| #194 | Em-dash violations in UI copy blocking Item A (check_project_invariants pre-commit) | OPEN | nightly-review, medium-risk, frontend |
| #193 | Moratorium active: 13 pending items, oldest 44 days | OPEN (updated) | subconscious, moratorium |

**#194 decision needed:** 5 JSX em-dash violations remain (UI labels, intentional copy). Subconscious run 44 already committed the scope fix (`f992c3e`) — `check_project_invariants.py` now skips `.jsx/.tsx`. Issue #194 may be auto-closed by tonight's nightly confirming Item A wired.

**#193 moratorium:** Still active. 13 pending human items. 3 are ≤15 min each (see priorities below).

---

## Open PRs needing action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #190 | fix(os-workers): inject business profile into worker prompts | 4d | Draft — needs review/merge |
| #183 | subconscious run 33 — GH #181 billing fix, CI trap | 8d | Draft — blocked on #181 manual fix |
| #182 | Split invoices.py god class into 4 service modules | 9d | Draft — awaiting god-class-splitter pass |
| #186 | bump @typescript-eslint/parser 8.58→8.60 | 7d | Open — Dependabot, safe to merge |
| #172 | bump eslint 9.39→10.4 | 14d | Open — Dependabot, check for breaking changes |
| #15/#14/#13/#12/#11 | CI action bumps (upload-artifact, setup-node, setup-python, create-pr, cache) | 48d | Open — Dependabot, low risk |

**Oldest stale:** Dependabot bumps #11–#15 at 48 days. Batch-merge or close the safe ones.

---

## Subconscious Recommendation (Run 44)

**Scope em-dash check to skip `.jsx`/`.tsx` in `check_project_invariants.py` — committed `f992c3e`.** This unblocks Item A (pre-commit Check 10, 30-day pending). Tonight's nightly (2026-06-02 2:37 AM) should auto-wire the 3-line bash block, update `governance.json` Item A → `implemented`, and close #194.

Run 43 note: SKILL.md extension for autonomous bash hook scope already committed (`4226ef4`). Full 3-run Item A chain: run 42 (governance.json) → run 43 (SKILL.md) → run 44 (scope fix) → tonight (execution). No human action needed for Item A.

---

## Top 3 Priorities Today

### 1. GH #181 — billing.py fix (~15 min, HUMAN REQUIRED)
- Add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN` in `backend/services/billing.py`
- Fix backwards assertions in `backend/tests/test_billing_amount_to_plan.py:38-44`
- Check 11 fires WARNING on every commit until resolved
- Unblocks PR #183

### 2. email_sequences.py god class split (~2h, HUMAN REQUIRED)
- File: `backend/routers/email_sequences.py` (1255L)
- Invoke `/god-class-splitter` → split into email_crud + email_enrollment + email_processor
- Do after #181 is merged (unblocks clean PR baseline)
- Run 41 winner, 10+ days pending

### 3. Item B — check-widget-sync.sh (~15 min, HUMAN REQUIRED)
- Create `scripts/check-widget-sync.sh` to verify widget byte-identity (2→3 copy check)
- Wire into pre-push hook
- Fix CLAUDE.md Invariant #4 reference (currently says 2 copies, should say 3)
- Last moratorium sprint item requiring human touch before moratorium exits

---

## Autonomous Loop Status

| Item | Status | ETA |
|------|--------|-----|
| Item A — check_project_invariants pre-commit | `pending_autonomous` → executes tonight | 2026-06-02 nightly |
| Item D — lead-qualifier-eval.yml workflow | Queued for run 45 (after Item A confirms) | 2026-06-03 |
| Moratorium | Active — 3 human items remain before exit | After #1-3 above |

---

## Health Signals

- KB log: last successful compile 2026-05-05 (87→98 articles). Embedding backfill blocked by Supabase MCP auth errors — 4 slugs pending reindex when token refreshed.
- Nightly autonomous: 5/5 success rate on correctly-scoped items. Running clean.
- Pre-commit: em-dash check now scoped. All 6 checks should PASS after `f992c3e`.
