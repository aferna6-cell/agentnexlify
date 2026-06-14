# Winning Concept — 2026-06-11

## Recommendation

AUTONOMOUS-EXECUTABLE: Remove `from __future__ import annotations` (line 1) from `backend/routers/channels_instagram.py`, then fix 10 em-dash violations across 7 JSX files — together these restore `check_project_invariants.py` exit 0 and trigger tonight's nightly auto-wire of Check 10 into pre-commit.

## Why This, Why Now

`channels_instagram.py` was introduced 1 day ago in PR #232 (7c8825c) with `from __future__ import annotations` on line 1. CLAUDE.md Critical Invariant #5 is unambiguous: this annotation makes Pydantic resolve every request body as strings, causing 422 validation errors on ALL Instagram integration endpoints. The connector is 444 lines with 12 endpoints and 172 tests — zero tenants have used it yet, but they will once the dashboard surfaces it. Removing line 1 is the fix.

The same PR (plus a5c65b5) also introduced 10 em-dash violations across 7 JSX files. Combined with the `from __future__` fix, removing these violations restores `check_project_invariants.py` exit 0. That exit 0 is the ONLY remaining blocker for Item A — the nightly SKILL.md already contains the pre-commit Check 10 inline patch, the governance.json entry is `pending_autonomous / autonomous_executable: true`, and the nightly channel is confirmed active (Check 12 wired autonomously on 2026-06-09). Tonight's nightly cycle will apply Check 10 as soon as it sees exit 0. After Check 10 is live, future `from __future__` and em-dash violations are caught at commit time — ending the recurrence loop that has driven the last 3 runs.

## Implementation Sketch

**Step 1 — Fix `channels_instagram.py` (1 line)**
```
backend/routers/channels_instagram.py line 1: DELETE `from __future__ import annotations`
```
Verify: `grep "from __future__" backend/routers/channels_instagram.py` → no output.

**Step 2 — Fix 10 em-dash violations (7 files)**
```
frontend/src/main.jsx:152              — → -
frontend/src/components/CookieConsent.jsx:5  — → -
frontend/src/components/CookieConsent.jsx:31 — → -
frontend/src/components/MarketingUpsell.jsx:3 — → -
frontend/src/components/App.jsx:328     — → -
frontend/src/components/Sidebar.test.jsx:27  — → -
frontend/src/components/Sidebar.test.jsx:49  — → -
frontend/src/components/billing/ReferralCard.jsx:24 — → -
frontend/src/components/billing/ReferralCard.jsx:45 — → -
frontend/src/components/os/ComposerAttachments.jsx:1 — → -
```

**Step 3 — Verify**
```bash
python3 scripts/check_project_invariants.py
# Expected: 0 invariant(s) failed. (All 6 checks PASS)
```

**Step 4 — Commit**
```
fix: remove from __future__ annotations in channels_instagram.py + clear 10 em-dash violations (check_project_invariants → exit 0, unblocks Item A Check 10 wire)
```

**Step 5 — Tonight nightly (2:37 AM)** auto-executes Item A:
- Adds `check_project_invariants.py` call as Check 10 to `scripts/hooks/pre-commit`
- Commits: `ci(pre-commit): wire check_project_invariants.py as Check 10`
- Updates governance.json Item A status → `implemented`

## What This Replaces

Previous active direction was run 54 winner (Fix 3 em-dash violations in Agent OS UI) — SUPERSEDED by a5c65b5/7c8825c which cleared the targeted violations via refactoring while introducing 10 new ones. Run 55 is the corrective pass.

## Confidence

HIGH — `channels_instagram.py` violation confirmed by 2 independent checks (check_project_invariants.py output + direct grep). em-dash fix class confirmed working (8db33df, 2026-06-05, 5 fixes in one autonomous commit). Check 10 auto-wire mechanism confirmed active (Check 12 wired by nightly 2026-06-09 via same path). Bounded scope: 2 invariant classes, 8 files total.

## Standing Actions (not this run's winner)

- **Merge PR #183** (~10 min): billing.py still missing 15000→autopilot + 25000→professional. Path confirmed (backend/routers/billing.py:263).
- **Item B (check-widget-sync.sh)**: MISSING 50+ days. pending_autonomous but never executed. Consider explicit inline implementation in next interactive session.
- **email_sequences.py split** (backend/routers/email_sequences.py, 1255L): unblocked once GH #181 resolved.
- **Home.jsx split** (1171L): god-class threshold exceeded, schedule via /god-class-splitter.
