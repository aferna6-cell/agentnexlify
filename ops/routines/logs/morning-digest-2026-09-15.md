# Morning Digest — 2026-09-15

Generated: 2026-09-15 UTC

---

## Commits (last 24h)

- `ef7796b` docs(nightly): review 2026-09-15 [auto-nightly]
- `cca06f8` chore(deps): update pydantic-settings >=2.15.0,<3 in /backend (#868)
- `370073e` chore(deps): update cryptography >=50.0.1,<51 (#866)
- `e20d541` chore(deps-dev): bump vite 8.1.5→8.3.0 in /frontend
- `203b21a` chore(deps-dev): bump vite 8.2.2→8.3.0 in /demo-platform (#862)
- `9c1b806` chore(deps-dev): bump @playwright/test 1.62.1→1.63.0 (#855)
- `60e8120` chore(deps): update pyyaml in /backend (#865)
- `00d5aa1` chore(deps-dev): bump @testing-library/react in /frontend (#856)
- `6613e73` chore(deps): bump python-dotenv 1.2.2→1.2.3 in /backend (#867)
- `ed0068e` chore(deps): bump dompurify 3.4.14→3.4.15 in /frontend (#857)
- `0d1628f` chore(deps-dev): bump @typescript-eslint/parser 8.69.0→8.70.0 (#854)
- `580fe0a` fix(m9): fail live bakeoff CLI on promotion failure (#853)

12 commits. Heavy dependency churn. One real fix (m9 bakeoff CLI).

---

## Issues opened/updated (last 24h)

| # | Title | State | Labels |
|---|-------|-------|--------|
| #871 | fix(billing): 20 functions call AI without metering guard | OPEN 🆕 | ai-ready, nightly-review, billing |
| #870 | [security] 90+ backend/routers/ files missing `Depends(block_demo_role)` | OPEN 🆕 | ai-ready, nightly-review, security |
| #827 | P1 AI cost governance: 45 unguarded production call sites | OPEN | priority/p1, billing, risk:high |
| #823 | fix: remove `from __future__ import annotations` from 2 backend test files | CLOSED ✅ | nightly-review, backend |
| #800 | Brain connector 44 days stale — last run 2026-07-23 | OPEN 🔴 | human-action-required |
| #769 | M9.4 follow-up — analyze live bakeoff misses before more spend | OPEN | priority/p1, diagnostic |
| #768 | Billing Automation v1 PR3 — Agent OS end-to-end proof | CLOSED ✅ | priority/p1, revenue |
| #767 | Website Connect v1 — one-click chatbot onboarding | OPEN | priority/p0, security, risk:high |
| #403 | Set ANTHROPIC_API_KEY in GitHub Actions — blocks autopilot + KB | OPEN 🔴 | critical, human-action-required |

**Nightly filed 2 new issues** (#870, #871). Both ai-ready. #823 + #768 closed — good.

---

## Open PRs needing action

| # | Title | Age | Notes |
|---|-------|-----|-------|
| #872 | subconscious: run 121 — Step 9E credential expiry (2nd carry-forward) | 0d | DRAFT. Token expiry fix. Review + merge. |
| #860 | bump react 18.3.1→**19.3.0** in /frontend | 1d | ⚠️ MAJOR version. Test widget + dashboard. |
| #861 | bump react 18.3.1→**19.3.0** in /demo-platform | 1d | ⚠️ MAJOR version. Pair with #860. |
| #863 | bump react-dom 18.3.1→**19.3.0** in /demo-platform | 1d | ⚠️ MAJOR version. Pair with #861. |
| #859 | bump vitest 4.1.10→**5.0.0** in /frontend | 1d | ⚠️ MAJOR version. Run test suite first. |
| #864 | update mcp requirement >=2.2.0,<3 in /backend | 1d | Minor. Low risk. |

4 major-version bumps landed at once. Do NOT auto-merge. Run full suite.

---

## Subconscious recommendation

**Run 121 (today, PR #872) — AUTOPILOT_GH_TOKEN expiry is CRITICAL.**

- Token flagged since Sep 9 (3 consecutive runs). Expires ~**2026-09-18** (3 days from now).
- Powers nightly-commit-review, issue-to-pr-loop, autonomous engineering loop.
- If it expires: all automated review/fix/escalation stops. CVE window stays open.
- PR #872 improves Step 9E to file a GH issue earlier — but **the rotation itself is a human action**.
- Action: rotate `AUTOPILOT_GH_TOKEN` in GitHub repo secrets today.

---

## Top 3 priorities today

1. 🔴 **Rotate AUTOPILOT_GH_TOKEN** — expires Sep 18, 3 days. Human action, repo secrets.
   Powers the entire autonomous loop. Non-negotiable.

2. 🔴 **Triage #870 (security)** — 90+ mutating endpoints missing `block_demo_role`.
   `ai-ready` so issue-to-pr-loop can tackle it, but scope is systemic.
   Decide: let autopilot batch-fix, or do it manually to control blast radius.

3. ⚠️ **Review React 19 PRs (#860, #861, #863) + vitest 5 (#859)** — major version bumps.
   Run full frontend test suite + widget embed smoke before merging any of these.

---

## Also on radar

- **#403** (critical, 68d stale) — `ANTHROPIC_API_KEY` missing from GitHub Actions secrets.
  Blocks KB autopopulate + autopilot loop in CI. Long-standing blocker.
- **#767** (priority/p0) — Website Connect v1. Active dev. No blocker visible.
- **#827** (priority/p1) — AI cost governance. 45 unguarded call sites. Ongoing.
- KB log last entry: 2026-08-26 (20 days ago). Next autopopulate may be stale.
