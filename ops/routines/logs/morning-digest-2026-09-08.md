# Morning Digest — 2026-09-08

Generated: 2026-09-08T00:00:00Z (automated routine)

---

## Commits (last 24h) — 14 total

- `6219d4a` fix(os-workflows): remove `__future__` annotations from 2 service files; add nightly review log 2026-09-08
- `4c8a1bf` chore(deps): bump recharts 3.9.2 → 3.10.1 in /frontend
- `89b9e01` chore(deps-dev): bump jsdom 29.1.1 → 30.0.1 in /frontend
- `f8ba92b` chore(deps): bump uvicorn 0.49.0 → 0.52.4 in /backend (#815)
- `891dcbf` chore(deps-dev): bump @vitejs/plugin-react to 6.1.1 (#816)
- `776387d` chore(deps-dev): bump vitest group (2 pkgs) (#813)
- `bee0ef1` Merge PR #817 — bump @testing-library/jest-dom in /frontend
- `ae15d43` Merge PR #812 — bump eslint 10.9.1 → 10.10.0
- `c155ef1` chore(deps-dev): bump @testing-library/jest-dom in /frontend
- `3896222` chore(deps-dev): bump eslint 10.9.1 → 10.10.0
- `0d86584` ci(dependabot): group demo Vitest updates
- `ab458db` chore(deps-dev): bump @playwright/test 1.61.1 → 1.62.1
- `3cc5be7` ops: kb drift sweep 2026-09-07 — no drift detected
- `74792ea` chore: weekly skill discovery report 2026-09-07

**Signal**: Heavy dep maintenance day. One real fix: `__future__` annotations partially remediated in 2 os_workflow files. Issue #823 filed for the remaining 5 test files — not done yet.

---

## Issues — opened / updated (last 24h)

| # | Title | Status | Labels |
|---|-------|--------|--------|
| #823 | `fix: remove __future__ annotations from 5 backend test files` | OPEN (new) | bug, nightly-review, backend |
| #808 | Morning digest 2026-09-07 | OPEN (stale) | digest |

**Existing critical open issues (not new, still unresolved):**

| # | Title | Age | Labels |
|---|-------|-----|--------|
| #805 | nightly-review: os_workflows spreading `__future__` pattern | 1d | risk:medium, backend |
| #801 | P0 M8: approve_send_once leaves execution running with no provider messageId | 3d | P0, bug, risk:high, agent-os |
| #767 | Website Connect v1 — one-click chatbot onboarding | 5d | P0, security, customer-value |
| #800 | Brain connector 44 days stale | 3d | human-action-required |
| #403 | Set ANTHROPIC_API_KEY in GH Actions (blocks autopilot+KB) | 61d | critical, human-action-required |
| #684 | Brain connector 33 days stale (duplicate signal) | 14d | human-action-required |

**82 open issues total.**

---

## Open PRs needing action

| # | Title | Age | Notes |
|---|-------|-----|-------|
| #824 | docs(skills): add AI endpoint metering workflow | <1d | **Not draft. Needs review/merge.** Branch: chatgpt/meter-ai-endpoint-skill |
| #825 | subconscious: run 118 — recommend meter-ai-endpoint skill creation | <1d | Draft. Subconscious output. |
| #821 | subconscious: run 2026-09-07-pm — Create meter-ai-endpoint skill | 1d | Draft. Overlaps with #824/#825 — consolidate? |
| #819 | chore(deps): update stripe >=15.6.1,<16 in /backend | 1d | Ready to merge |
| #818 | chore(deps): update pywebpush >=2.5.0,<3 in /backend | 1d | Ready to merge |
| #595 | chore(deps): update python-dateutil in /backend | 43d | Stale Dependabot — review or close |
| #586 | chore(deps): bump react 18.3.1 → 19.2.8 in /frontend | 43d | React 19 upgrade — **major version, intentional hold?** |
| #591 | chore(deps): bump react 18.3.1 → 19.2.8 in /demo-platform | 43d | Same |
| #593 | chore(deps): bump react-dom 18.3.1 → 19.2.8 in /demo-platform | 43d | Same |
| #580 | chore(deps): bump actions/checkout from 4 to 7 | 43d | GH Actions — skipping CI per #500 dark mode |

**10 open PRs. 3 dupes on meter-ai-endpoint skill (#821, #824, #825) — consolidation needed.**

---

## Subconscious recommendation

**Run 117 (2026-09-06-pm):** Add Step 9L to `nightly-commit-review/SKILL.md` — automated AI Usage Guard Coverage Sweep using `check_ai_metering.py`. Detector finds 30+ unguarded AI-calling functions across 16 router + 14 service files. Without this step, every new AI route starts unguarded and accumulates billing debt until a human notices.

**Run 118 in progress:** Implementing `meter-ai-endpoint` skill (PRs #824/#825 are the output).

---

## Top 3 Priorities for Today

### 1. Close issue #823 — `__future__` annotations in 5 backend test files
- **Why**: Critical invariant #5 in CLAUDE.md. 2 service files fixed yesterday; 5 test files remain. Nightly review filed #823 this morning.
- **Action**: Fix `from __future__ import annotations` in the 5 files named in #823. Confirm pre-commit hook catches any future regressions.

### 2. Consolidate meter-ai-endpoint PRs (#821, #824, #825) → decide + merge one
- **Why**: Subconscious ran twice on this concept. Three separate PRs exist for the same deliverable. Merge #824 (not draft, docs) or supersede with a clean implementation PR.
- **Action**: Review #824 content, close #821 and #825 as superseded, merge or iterate on #824.

### 3. Unblock P0 #801 — approve_send_once execution leak
- **Why**: P0 bug. Execution continues running with no provider messageId — potential runaway spend and state corruption. Stale 3 days.
- **Action**: Read issue + M8 code. Implement guard or stop condition. Issue #767 (Website Connect) is also P0 but longer horizon — #801 is more acute.

---

## Blockers / Human Action Required

- **#403**: `ANTHROPIC_API_KEY` missing from GH Actions secrets → autopilot loop + KB autopopulate completely blocked in CI. Has been open 61 days. Add the secret in GitHub repo settings.
- **Brain connector**: 44 days stale (#800). Re-run `brain/_tools/refresh_connectors.py` or reconnect the data source.

---

*Digest under 200 lines. Caveman-mode: facts, no prose.*
