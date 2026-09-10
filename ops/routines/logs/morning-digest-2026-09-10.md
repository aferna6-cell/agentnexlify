# Morning Digest — 2026-09-10

Generated: 2026-09-10 UTC | Caveman-mode

---

## Commits (last 24h)

- `82ebd85` test: remove unnecessary invoice e2e future annotations (#838)
- `d673720` ops: nightly-commit-review 2026-09-10
- `77b2f03` Merge PR #837 — cleanup future-annotations invoice actions (#823)
- `eee887a` test: shrink future-annotations baseline for invoice actions
- `e430b33` test: remove future annotations from invoice action tests
- `7c957d3` test: remove future annotations from calendar CRM tests (#836)
- `307db14` ci: block new backend future-annotations violations (#834)

**Theme:** future-annotations cleanup sprint nearly done. CI gate now blocks new violations.

---

## Issues Updated (last 24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #823 | fix: remove `__future__` from 2 remaining backend test files | OPEN | bug, nightly-review, backend |
| #827 | P1 AI cost governance: triage and meter 45 unguarded call sites | OPEN | billing, risk:high, P1 |
| #829 | CI: isolate recurring backend coverage failure blocking PRs | OPEN | — |
| #801 | P0 M8: approve_send_once leaves execution running with no messageId | OPEN | P0, risk:high, agent-os |
| #832 | Morning digest 2026-09-09 | OPEN | digest |

---

## Open PRs Needing Action

No open PRs. All recent PRs merged. Clean slate.

---

## Subconscious Recommendation

**Run 117 (2026-09-06-pm):** Add Step 9L to `nightly-commit-review/SKILL.md` — automate AI usage guard sweep. Detector (`scripts/check_ai_metering.py`) is live and finds 30+ unguarded AI-calling functions across 16 router files + 14 service files. Without this step, every new AI route starts unguarded and accumulates billing exposure until a human notices. 3rd carry-forward → direct implementation precedent established.

---

## Top 3 Priorities Today

1. **Close #823** — 2 remaining backend test files still have `from __future__ import annotations`. Active sprint, commits landed today. Finish + close.

2. **Triage #827 (P1 billing)** — 45 unguarded AI call sites in production. Subconscious aligns: `check_ai_metering.py` is ready, Step 9L nightly sweep is the fix. Meter the remaining sites or implement Step 9L to catch them automatically going forward. Billing exposure is real.

3. **Diagnose #801 (P0)** — `approve_send_once` leaves execution running with no provider `messageId`. P0 + risk:high. No recent commits touching it. Needs eyes before it blocks agent-os feature work.

---

## Notes

- KB log last entry: 2026-08-26 (cron). No fresh KB compile today. Not a blocker.
- CI gate for `__future__` annotations is now enforced via PR #834. Good guard rail.
- No open PRs = no review backlog. Good position.
