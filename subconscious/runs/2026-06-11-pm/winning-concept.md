# Winning Concept — Run 2026-06-11-pm (Run 56)

## Title
Fix 10 em-dash violations → Check 10 auto-wires tonight

## Category
code_health

## Confidence
HIGH

## Status
AUTONOMOUS-EXECUTABLE (pending nightly 2:37 AM execution)

## Context
Run 55 winner was PARTIALLY implemented:
- `from __future__ import annotations` in channels_instagram.py: **FIXED** (confirmed by check_project_invariants PASS on that check; likely cleared in b736ca2/b8fdcd2)
- 10 em-dash violations: **STILL PRESENT** — check_project_invariants exits 1
- Check 10 (pre-commit wire): **NOT WIRED** — 55-day pending item

Set has shifted since run 55: Sidebar.jsx:386 is NEW (introduced by fc662b4 "Hide platform-admin pages from tenant sidebar", part of the high-velocity sprint), ComposerAttachments.jsx:1 is GONE (fixed as side-effect of recent PRs). Net: still 10 violations.

## Target violations (exact)

| File | Line(s) | Context |
|------|---------|---------|
| `frontend/src/pages/main.jsx` | 152 | UI copy |
| `frontend/src/components/CookieConsent.jsx` | 5, 31 | Cookie notice copy |
| `frontend/src/components/MarketingUpsell.jsx` | 3 | Marketing copy |
| `frontend/src/App.jsx` | 325 | UI copy |
| `frontend/src/components/Sidebar.test.jsx` | 27, 49 | Test fixture strings |
| `frontend/src/components/Sidebar.jsx` | 386 | NEW — platform-admin hide copy (fc662b4) |
| `frontend/src/components/ReferralCard.jsx` | 24, 45 | Referral copy |

## Implementation
Replace each em-dash character (U+2014, `—`) with a hyphen-minus (U+002D, `-`).

Nightly SKILL.md Item A block:
```bash
# Item A — inline patch applied by nightly-commit-review when autonomous_executable: true
sed -i 's/—/-/g' frontend/src/pages/main.jsx
sed -i 's/—/-/g' frontend/src/components/CookieConsent.jsx
sed -i 's/—/-/g' frontend/src/components/MarketingUpsell.jsx
sed -i 's/—/-/g' frontend/src/App.jsx
sed -i 's/—/-/g' frontend/src/components/Sidebar.test.jsx
sed -i 's/—/-/g' frontend/src/components/Sidebar.jsx
sed -i 's/—/-/g' frontend/src/components/ReferralCard.jsx
```

After fix, `python scripts/check_project_invariants.py` exits 0 → Item A auto-wires Check 10 into pre-commit tonight per nightly SKILL.md block.

## Why this is the winner
1. **Unblocks 55-day pending item** — Check 10 auto-wires the instant invariants exits 0. No other action this run achieves that.
2. **Self-healing loop** — Check 10 in pre-commit blocks future em-dash violations at commit time. The accumulation pattern (fc662b4 introduced a violation in a 17-line cosmetic diff) stops.
3. **S-effort** — 7 sed invocations, ~2 minutes.
4. **AUTONOMOUS-EXECUTABLE** — adds to pending_autonomous, not pending_approval; does not worsen moratorium count.
5. **Prior precedent** — 8db33df (run 49 nightly) fixed 5 em-dashes autonomously. Same class.

## Moratorium compliance
AUTONOMOUS-EXECUTABLE items do not increment pending_approvals. Moratorium threshold tracks human-required items only. This winner is compatible with moratorium-active state.

## Precedent chain
- Run 49 winner: nightly 8db33df fixed 5 em-dashes autonomously (2026-06-05)
- Run 55 winner: from __future__ FIXED; em-dashes carried forward
- Run 56 winner: clear remaining 10 em-dashes → Check 10 wires tonight

## Post-execution verification
```bash
python scripts/check_project_invariants.py  # must exit 0
grep -rn '—' frontend/src/  # must return 0 matches in target files
```
