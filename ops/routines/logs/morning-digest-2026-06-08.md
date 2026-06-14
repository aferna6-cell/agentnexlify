# Morning Digest — 2026-06-08

> Generated: 2026-06-08 UTC | Subconscious run 51 (2026-06-05-pm) active

---

## Commits (last 24h) — 3 total

- `1d7aa4a` ops: nightly-commit-review 2026-06-08 — all clean, 0 bugs filed
- `d20284f` Agent OS phase-3 polish: routing chip, legacy-draft reject, slot extraction (#208) ← MEDIUM, clean
- `617b667` Render v2 Agent OS response shape in the dashboard (#207) ← LOW, clean

**Nightly verdict:** All 3 commits clean. No issues filed. Agent OS v2 shipping fast.

---

## Issues (open, actionable)

| # | Title | Labels | Age | Priority |
|---|-------|--------|-----|----------|
| **#206** | security: use timingSafeEqual for X-Agent-Token in agent-service | security, HIGH | 1d | **P1 — PR #209 ready** |
| **#181** | billing: AMOUNT_TO_PLAN missing autopilot ($150) + professional ($250) | billing, medium-risk | 16d | P1 — subconscious run 51 |
| **#193** | Moratorium active: 13 pending items | moratorium | 9d | ongoing |
| **#185** | CI: 21 pytest failures (pyo3/cryptography PanicException) | bug, ci | 14d | env bug, not regression |
| **#194** | Em-dash violations blocking Item A | nightly-review, frontend | 7d | carry-forward |

---

## Open PRs Needing Action

| # | Title | Age | Draft | Action |
|---|-------|-----|-------|--------|
| **#209** | subconscious run 52 — Fix timingSafeEqual in agent-service/src/auth.ts | 1d | no | **review + merge — security HIGH** |
| **#200** | subconscious run 49 — Extend nightly SKILL.md scope | 3d | no | **merge — nightly needs scope for Item B tonight** |
| **#183** | subconscious run 33 — GH #181 billing fix | 15d | yes | **review + merge — confirmed path per run 51** |
| **#190** | fix(os-workers): inject business profile into worker prompts | 10d | yes | review after #183 |
| **#182** | Split invoices.py god class into 4 service modules | 16d | yes | blocked on #183 merge |
| **#198** | bump @typescript-eslint/parser 8.58→8.60 | 3d | no | safe merge |
| **#197** | bump eslint 9.39→10.4 | 3d | no | MAJOR — check breaking changes |
| **#15 #14 #12** | Dependabot GH Actions bumps | 50d+ | no | **batch close — stale** |

---

## Subconscious Recommendation (Run 51 — 2026-06-05-pm)

**Merge PR #200 first. Then verify + merge PR #183.**

- PR #183 path confirmed: `backend/routers/billing.py:263` (NOT services/). Fix exists. CI gate prevents bad merge.
- Step 1: `gh pr ready 200 && gh pr merge 200 --squash` → ensures Item B fires in tonight's nightly
- Step 2: verify PR #183 diff — must contain `15000: "autopilot"` + `25000: "professional"` in `backend/routers/billing.py`. If confirmed, merge.
- Post-merge: email_sequences.py god-class split (1255L → 3 modules) immediately unblocked.
- Confidence: MEDIUM-HIGH. Risk: LOW (CI gate active).

---

## Top 3 Priorities Today

### 1. Review + merge PR #209 — 10 min — security
- `agent-service/src/auth.ts`: swap `===` for `timingSafeEqual` (node:crypto)
- Filed yesterday as HIGH by nightly. PR already open. No complex logic.
- Command: `gh pr review 209 --approve && gh pr merge 209 --squash`

### 2. Merge PR #200 — 5 min — unblocks autonomous nightly chain
- SKILL.md scope extension for widget sync guard (Item B)
- Tonight's nightly (2:37 AM) needs this on main to execute Item B autonomously
- PR was draft; confirm it's ready, then merge

### 3. Verify + merge PR #183 — 10 min — closes 16-day billing bug
- GH #181: Stripe webhook silent-downgrades autopilot/professional customers without `metadata.plan`
- Check: PR diff must target `backend/routers/billing.py` (NOT services/)
- Check: test file removes backwards assertions lines 38-44, adds correct assertions
- If verified: `gh pr ready 183 && gh pr merge 183 --squash`
- Unblocks: email_sequences.py god-class split (run 41, #182)

---

## Autonomous Loop Status

| Item | Status | ETA |
|------|--------|-----|
| Item A — check_project_invariants pre-commit | status unknown (PR #200 not merged) | tonight if #200 merged |
| Item B — widget 3-copy sync guard | pending_autonomous (needs PR #200 on main) | tonight if #200 merged |
| email_sequences.py split | blocked on PR #183 merge | after today's actions |
| Moratorium | active — 3 human actions remain (PRs #209/#200/#183) | today |

---

## Agent OS Shipping Status

Strong last 48h:
- PR #205 agent-service auth hardening ✓
- PR #207 v2 response shape rendering ✓
- PR #208 routing chip + slot extraction ✓

PR #190 (business profile injection for OS workers) is next in the queue — review when above merges are done.

---

## Flags

- **CI broken** — pyo3/cryptography env bug (#185). Not a code regression. Doesn't block local dev.
- **KB stale** — last compile 2026-05-05 (34 days). Embeddings blocked (no VOYAGE_API_KEY in cron).
- **Nightly clean** — 0 bugs found in last 3 nightly runs. Agent OS quality holding.

---

*Nightly review: 2:37 AM. KB autopop: 6 AM / 6 PM.*
*Log: `ops/routines/logs/morning-digest-2026-06-08.md`*
