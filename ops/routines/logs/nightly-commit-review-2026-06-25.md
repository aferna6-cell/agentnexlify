# Nightly Commit Review — 2026-06-25

## Commits reviewed (last 24h)

| SHA | Message | Risk |
|-----|---------|------|
| a9407d3 | subconscious: run 2026-06-24-pm — Fix widget drift + em-dash violations (docs/state) | LOW |
| 58a0954 | docs(CLAUDE.md): correct stale website/deploy note | LOW |
| 6ece987 | docs(brain): website surface map; revert wrong-target legacy greeting edit | LOW |
| b97efbc | Update site support-widget greeting to Nexi intro (landing-page-v2 — legacy, reverted by 6ece987) | LOW |
| 4a80f40 | ops: nightly-commit-review 2026-06-24 | LOW |

## Issues found

### FIXED — Widget drift + em-dash violations (pre-commit Check 13 blocked)

**Source:** Subconscious run 65 (a9407d3) flagged this as AUTONOMOUS-EXECUTABLE.

**Root cause:** Referral sprint PRs #368-371 (2026-06-22/23) introduced:
1. Widget drift — `landing-page-v2/widget/` not synced to match `widget/` + `frontend/public/widget/`
2. Em-dash violations (U+2014) in JSX/JS files — blocked `check_project_invariants.py` Check 13

**Files fixed:**
- `widget/agentnexlify-widget.js` — 1 em-dash in comment (line 2044)
- `frontend/public/widget/agentnexlify-widget.js` — synced from source
- `landing-page-v2/widget/agentnexlify-widget.js` — synced from source
- `frontend/src/components/billing/ReferralCard.jsx` — 1 em-dash
- `frontend/src/pages/SignupPage.jsx` — 2 em-dashes
- `frontend/src/pages/AdminFunnelPage.jsx` — 8 em-dashes
- `frontend/src/pages/ReferralPage.jsx` — 1 em-dash
- `frontend/src/pages/AdminTenantHealthPage.jsx` — 12 em-dashes
- `frontend/src/pages/AdminReferralPage.jsx` — 5 em-dashes

Total: 30 em-dashes replaced with `-`, widget drift resolved.

**Verification:** `python3 scripts/check_project_invariants.py` — All 6 checks PASS. Exit 0.

## MEDIUM/HIGH issues

None found.

## Summary

5 commits reviewed — all LOW risk (docs, state, revert). Pre-commit Check 13 was blocked since PRs #368-371 merged. Fix implemented and committed. All invariants green.
