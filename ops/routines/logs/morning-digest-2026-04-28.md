# Morning Digest — 2026-04-28

> Period: last 24h | 3 commits | 5 open bugs | 10 open PRs | subconscious run 2026-04-27

---

## Commits (last 24h) — 3

- `677b52c` docs: auto-log bug fix from e68677a
- `e68677a` fix(silent-errors): add logging to 4 bare-exception/silent-catch handlers
- `549f1f1` ops: morning-digest 2026-04-27

**Note:** `e68677a` likely closes #97 (widget_chat.py silent catch). Issue still shows OPEN — close it.

---

## Issues — active bugs (all open)

| # | Title | Severity | Age |
|---|-------|----------|-----|
| #99 | bug(stripe): SignatureVerificationError catch anti-pattern | MEDIUM | 1d |
| #98 | perf(twilio): _find_tenant_by_phone O(N) full scan every SMS | MEDIUM | 1d |
| #97 | bug(rate-limit): _chat_rate_limit swallows exceptions silently | MEDIUM | 1d |
| #94 | bug(billing): IndexError crash when charges.data is empty list | MEDIUM | 2d |
| **#93** | **bug(billing): guard_checkout_for_fraud flags no_payment_required** | **HIGH** | 2d |

**#93 is revenue-impacting** — coupon/trial signups paused immediately on checkout. 2-line fix: `fraud_guard.py:121-123`.

**#97 likely fixed** by `e68677a` — verify and close.

---

## Open PRs — 10 total

| # | Title | Age | State | Action |
|---|-------|-----|-------|--------|
| #104 | chore(deps): bump uvicorn 0.34→0.46.0 | 1d | open | **merge** (replaces stale #26) |
| #103 | chore(deps): bump python-multipart 0.0.26→0.0.27 | 1d | open | **merge** (security) |
| #102 | chore(deps): update youtube-transcript-api >=1.2.4 | 1d | open | merge |
| #101 | chore(deps-dev): bump @typescript-eslint/parser 8.58→8.59 | 1d | open | merge |
| #91 | feat(zapier): backend auth middleware + API key CRUD | 3d | open | **merge** (21 tests pass) |
| #90 | test(scheduled-jobs): import chain verification | 3d | open | **merge** — closes #82 |
| #89 | test(billing): regression tests for AMOUNT_TO_PLAN | 3d | open | **merge** — closes #81 |
| #86 | fix(hooks): 4 missing post-edit checks | 3d | DRAFT | review → undraft → merge |
| #85 | feat: intent engineering layer | 4d | DRAFT | needs migration applied |
| #80 | feat(onboarding-v2): Week 1 foundation | 5d | DRAFT | Week 2 backend still pending |

**Batch-mergeable today:** #89 + #90 + #91 + #101 + #102 + #103 + #104 (7 PRs)

---

## KB Status

- Last successful run: **2026-04-21 18:12** — 7 days silent
- Autopopulate still failing (errors=3 in last known run)
- Action needed: check `scripts/daily/kb-autopopulate.sh` + search-tool availability

---

## Subconscious recommendation — run 2026-04-27

**JS + Python Silent Catch Guard** (Run 3 winner, 16+ days pending)

Python side (`widget_chat.py:295`) **likely done** by `e68677a` yesterday.

Remaining work:
- Add pre-commit Check 9 — block `.catch(() => null)` + `.catch(() => {})` in JS
- Fix 3 known JS violations before adding the check:
  - `MarketingDashboardPage.jsx:96`
  - `LocalSEOPage.jsx:262`
  - `AuthContext.jsx:89`
- Update subconscious governance: Run 2 + Run 3 → `implemented`. Pending count 5→3. Moratorium condition recalculated.

S-effort. Lifts subconscious moratorium (≥2 pending unimplemented = moratorium active).

---

## Top 3 priorities today

1. **Fix #93** — `fraud_guard.py:121-123`: add `"no_payment_required"` to allowed statuses. HIGH billing bug. Coupon/trial signups actively broken. 2-line fix.

2. **Close JS Silent Catch Guard** — pre-commit Check 9 + 3 JS violation fixes (`MarketingDashboardPage.jsx:96`, `LocalSEOPage.jsx:262`, `AuthContext.jsx:89`). Python side done. Lifts moratorium.

3. **Batch-merge 7 PRs** — #89 + #90 + #91 (feature/fixes) + #101 + #102 + #103 + #104 (dependabot). All green. Also: verify `e68677a` closed #97 → close the issue.

---

*Full digest: `ops/routines/logs/morning-digest-2026-04-28.md`*
*Future: replace GH issue step with post to #dev-standup when Slack connector attached.*
