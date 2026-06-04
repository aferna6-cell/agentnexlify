# Morning Digest — 2026-06-04

> Generated: 2026-06-04T00:00:00Z | Run 49 subconscious active

---

## Commits (last 24h)

- `eedd859` subconscious: run 2026-06-04 (run 49) — Fix 5 JSX em-dashes (atomic, ~2 min)

**1 commit.** Subconscious ran. No code shipped yet today.

Yesterday context (run 48 / nightly):
- `b8852a7` subconscious run 48 — Fix 5 JSX em-dashes + widget sync guard (Items A+B)
- `42992fa` ops: nightly-commit-review 2026-06-03

---

## Issues Opened / Updated (last 24h)

| # | Title | Labels | Status |
|---|-------|--------|--------|
| #199 | Morning digest 2026-06-03 | digest | open (stale) |
| #194 | Em-dash violations blocking Item A | nightly-review, frontend | open — **35+ days unresolved** |
| #193 | Moratorium: 13 pending items | moratorium | open — ongoing |
| #185 | CI: 21 pytest failures (pyo3/cryptography) | bug, ci | open — 10d |
| #181 | billing: AMOUNT_TO_PLAN missing autopilot + professional | billing | open — 12d |

---

## Open PRs Needing Action

| # | Title | Age | Status | Action |
|---|-------|-----|--------|--------|
| #200 | subconscious run 49 — extend nightly SKILL.md | 0d | draft | review + merge |
| #198 | bump @typescript-eslint/parser 8.58→8.60 | 1d | open | merge or close |
| #197 | bump eslint 9.39→10.4 | 1d | open | merge or close |
| #190 | fix(os-workers): inject business profile into worker prompts | 7d | draft | review |
| #183 | subconscious run 33 — GH #181 billing fix | 11d | draft | merge or supersede |
| #182 | Split invoices.py god class into 4 service modules | 11d | draft | review |
| #15,14,13,12 | Dependabot GH Actions bumps | 50d | open | **batch close — stale** |

---

## Subconscious Recommendation (Run 49)

**Decouple em-dash fix from widget sync guard. Do Item A alone — ~2 min.**

Run 49 finding: the ~25-min bundled commitment (Items A+B) is the activation-energy barrier. Items requiring >15 min go undone; sub-5-min items land. Em-dash fix = 5 string literals, 1-char each, zero logic risk.

Fix → `check_project_invariants.py` exits 0 → nightly at 2:37 AM auto-wires Check 10 to pre-commit → Item A closes autonomously.

Exact locations (confirmed by invariants run):
- `frontend/src/pages/IntegrationsPage.jsx:1018`
- `frontend/src/pages/SettingsInboundChannels.jsx:220,221`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:263,276`

Replace `—` (U+2014) with `-` at each line.

---

## Top 3 Priorities Today

### 1. Fix 5 JSX em-dashes — 2 min — closes #194, unblocks autonomous chain
```
frontend/src/pages/IntegrationsPage.jsx:1018          → replace — with -
frontend/src/pages/SettingsInboundChannels.jsx:220    → replace — with -
frontend/src/pages/SettingsInboundChannels.jsx:221    → replace — with -
frontend/src/pages/settings/MessagingSettingsCards.jsx:263 → replace — with -
frontend/src/pages/settings/MessagingSettingsCards.jsx:276 → replace — with -
```
Verify: `python3 scripts/check_project_invariants.py` → all 6 checks PASS.

### 2. Fix GH #181 billing bug — 15 min — closes #181
File: `backend/routers/billing.py:263` AMOUNT_TO_PLAN dict.
Add:
```python
15000: "autopilot",    # $150/mo
25000: "professional", # $250/mo
```
Update `backend/tests/test_billing_amount_to_plan.py`: replace old assertions (lines 38-44) with `{9900, 15000, 25000, 89900}`. PR #183 has this fix — review and merge instead of re-implementing.

### 3. Close stale Dependabot PRs — 5 min
PRs #12,13,14,15 — 50 days stale, GH Actions bumps. Close with comment "superseded by current dep audit."

---

## Blockers Carrying Forward

- **CI still broken** — #185 pyo3/cryptography build failures. Affects pytest suite. Not blocking local dev.
- **Moratorium** — 13 items in #193, 35+ days. Top unresolved: Item A (em-dashes), Item B (widget sync guard), Item D (billing fix).
- **PR #182 (invoices.py split)** — 11d draft. God class still ~900 lines. Needs merge or abandon decision.

---

## KB Status

Last compile: 2026-05-05. No new articles since then (network sandbox blocks autodiscovery). VOYAGE_API_KEY absent in cron env — embeddings deferred. 98 wiki articles indexed.

---

*Next digest: tomorrow 8 AM. Nightly review: 2:37 AM. KB autopop: 6 AM / 6 PM.*
