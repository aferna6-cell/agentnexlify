# Nightly Commit Review — 2026-06-27

## Commits reviewed (last 24h)

| SHA | Message | Risk | Verdict |
|-----|---------|------|---------|
| `1737a33` | subconscious: run 2026-06-26-pm (68) — mandate fires, 30-second terminal block | LOW | Docs/state only. No code changes. |
| `77df8a3` | ops: morning-digest 2026-06-26 | LOW | Log file. No code changes. |

Both commits are operational docs/logs. No code bugs introduced.

## Pre-existing invariant failures found

Running `scripts/check_project_invariants.py` revealed 2 pre-existing failures (carried over from referral sprint PRs #368-371, unresolved since 2026-06-23):

### 1. Em-dash violations — FIXED (LOW)

10 em-dashes in JSX source detected across 6 files. Project invariant: "website source avoids em dashes". All in comments or admin-only display text.

**Files fixed:**
- `frontend/src/components/billing/ReferralCard.jsx` (1 violation — comment)
- `frontend/src/pages/SignupPage.jsx` (2 violations — comments)
- `frontend/src/pages/AdminFunnelPage.jsx` (8 violations — comments + display text)
- `frontend/src/pages/AdminReferralPage.jsx` (5 violations — comments)
- `frontend/src/pages/AdminTenantHealthPage.jsx` (9 violations — comments)
- `frontend/src/pages/ReferralPage.jsx` (1 violation — comment)
- `widget/agentnexlify-widget.js` + `frontend/public/widget/agentnexlify-widget.js` (1 violation each — comment only, byte-identical sync maintained)

All replaced `—` with `-`. Admin-only display text change is cosmetic (null value fallback dash).

**Verified:** `PASS website source avoids em dashes`

### 2. Widget drift (landing-page-v2) — GH ISSUE #377 (MEDIUM)

`landing-page-v2/widget/agentnexlify-widget.js` missing ~20 lines of referral click-tracking code from widget source. Invariant check: "widget assets are byte-identical across mirrors".

CLAUDE.md marks `landing-page-v2/` as "legacy, do not touch (confirmed 2026-06-23)". Conflict: invariant requires sync, CLAUDE.md prohibits touching archive. Escalated to human via GH issue #377.

**Status:** `FAIL widget assets are byte-identical across mirrors` — 1 invariant remaining.

## Actions taken

- Fixed 26 em-dash violations across 6 JSX files + widget comment (LOW, autonomous)
- Synced `widget/` em-dash fix to `frontend/public/widget/` (byte-identical rule maintained)
- Created GH issue #377 with label `nightly-review` for widget drift (MEDIUM, human required)

## No issues found in commits themselves

Both commits (subconscious run docs + morning digest) are clean operational logs with no code bugs.

## Next steps

- Human: run fix in GH issue #377 to fully clear `check_project_invariants.py`
- Run 69 subconscious (per governance): once check exits 0, add Plan-name guard Check 7 (autonomous-executable)
