# Morning Digest — 2026-04-27

> Period: last 24h | 13 commits | 3 new bugs filed | 10 open PRs | subconscious run completed

---

## Commits (last 24h) — 13

- `734cef0` subconscious: run 2026-04-27 — JS + Python Silent Catch Guard
- `402a44a` Merge branch 'main' (remote sync)
- `7c1c0b3` ops: nightly-commit-review 2026-04-27
- `50123a4` Merge feature/steal-list-1-6 into main
- `a9a677e` test(rate-limit): lock _chat_rate_limit signature contract
- `ee4bc16` fix(widget-chat): correct _chat_rate_limit signature for slowapi
- `752819c` Merge PR #96 — feature/steal-list-1-6
- `841b987` chore(claude): cost-optimization moves — effort/session hygiene/observability
- `041b7f0` chore(claude): subagent spawn discipline + dedicated tools index
- `cf0fd7f` Merge PR #95 — feature/steal-list-1-6
- `fb57995` fix(idempotency,rate-limit): close race + RLS + XFF spoofing
- `b0b1fb4` feat(steal-list 1-6): idempotency, rate-limit, contextual reindex, MCP tooling
- `b50e198` chore(ai): auto-commit Claude edits [main 2026-04-26 11:18]

---

## Issues opened/updated — nightly filed 2026-04-27

| # | Title | Severity | Status |
|---|-------|----------|--------|
| #99 | bug(stripe): SignatureVerificationError catch anti-pattern | MEDIUM | OPEN |
| #98 | perf(twilio): _find_tenant_by_phone O(N) full scan on every SMS | MEDIUM | OPEN |
| #97 | bug(rate-limit): _chat_rate_limit swallows exceptions silently | MEDIUM | OPEN |
| #94 | bug(billing): IndexError crash when charges.data is empty list | MEDIUM | OPEN |
| #93 | bug(billing): guard_checkout_for_fraud flags no_payment_required | **HIGH** | OPEN |

**#93 is revenue-impacting** — coupon/trial signups get paused immediately. 2-line fix: `fraud_guard.py:121-123`.

---

## Open PRs needing action — 10 total

| # | Title | Age | State | Action |
|---|-------|-----|-------|--------|
| #91 | feat(zapier): backend auth middleware + API key CRUD | 2d | open | **merge** (awaiting Hermes approval note — all 21 tests pass) |
| #89 | test(billing): regression tests for AMOUNT_TO_PLAN | 2d | open | **merge** — closes #81, 19 tests pass |
| #90 | test(scheduled-jobs): import chain verification | 2d | open | **merge** — closes #82, 8 tests pass |
| #86 | fix(hooks): 4 missing post-edit checks | 2d | DRAFT | review → undraft → merge |
| #85 | feat: intent engineering layer | 3d | DRAFT | needs migration applied + test plan |
| #80 | feat(onboarding-v2): Week 1 foundation | 4d | DRAFT | Week 2 backend still pending |
| #73 | [memory-hygiene] widget conversation memory tier | 7d | open | **stale — merge or close** |
| #72 | [memory-hygiene] KB article provenance | 7d | open | **stale — merge or close** |
| #66 | bump eslint 9.39→10.2 | 7d | open | check breaking changes → merge |
| #65 | bump cross-env 7.0→10.1 | 7d | open | merge (ESM-only, Node ≥20 ok) |

---

## KB Status

- Last successful run logged: **2026-04-21 18:12** (cron, commits=5, raw=10, wiki=4)
- **6 days no new articles** — kb-autopopulate silently failing (errors=3 across all categories)
- Action: check `scripts/daily/kb-autopopulate.sh` + search-tool availability

---

## Subconscious recommendation — 2026-04-27

**JS + Python Silent Catch Guard** (Run 3 winner, 16+ days pending)

Patch `widget_chat.py:295` bare `except Exception` — add `logger.warning(...)`. Add Check 9 to `scripts/hooks/pre-commit` blocking `.catch(() => null/{})`  patterns. Fix 3 known JS violations first:
- `MarketingDashboardPage.jsx:96`
- `LocalSEOPage.jsx:262`
- `AuthContext.jsx:89`

S-effort. Lifts moratorium (4 pending → 3 → moratorium off). Also closes #97 as a side-effect.

**Urgent side-note (not moratorium):** Issue #93 fraud_guard HIGH billing bug — fix independently today, don't wait for subconscious cycle.

---

## Top 3 priorities today

1. **Fix #93 HIGH billing bug** — `fraud_guard.py:121-123`: add `"no_payment_required"` to expected statuses. Coupon/trial signups actively broken. 2-line fix.

2. **Implement JS+Python Silent Catch Guard** — subconscious run 3 winner (16+ days pending). Patch `widget_chat.py:295` + add pre-commit Check 9 + fix 3 known JS violations. Also resolves #97.

3. **Batch-merge ready PRs** — #89, #90, #91 all non-draft with passing tests. #73 + #72 (7d stale memory-hygiene) — merge or close today.

---

*Full digest: `ops/routines/logs/morning-digest-2026-04-27.md`*
*Future: replace GH issue step with post to #dev-standup when Slack connector attached.*
