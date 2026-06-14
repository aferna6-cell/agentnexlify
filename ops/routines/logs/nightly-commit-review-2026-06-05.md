# Nightly Commit Review — 2026-06-05

**Run time:** 2026-06-05 UTC  
**Commits reviewed:** 2 (last 24 hours)

---

## Commits Reviewed

### 1. `829d741` — ops: morning-digest 2026-06-04
- **Risk:** LOW
- **Files:** `ops/routines/logs/morning-digest-2026-06-04.md` (1 file, +102 lines)
- **Assessment:** Log/docs only. No code changes. No issues.

### 2. `eedd859` — subconscious: run 2026-06-04 (run 49) — Fix 5 JSX em-dashes
- **Risk:** LOW
- **Files:** `subconscious/runs/2026-06-04/` (7 files, metadata and planning docs only)
- **Assessment:** Subconscious run recorded a recommendation to fix 5 em-dash violations but did NOT implement the fix. The actual JSX files were untouched. Invariants check confirmed `check_project_invariants.py` was exiting 1 on the em-dash check.

---

## Actions Taken

### LOW-risk fix applied: em-dash violations in 5 JSX UI strings

The subconscious run 49 winning concept called for replacing U+2014 em dashes with hyphens in 5 UI string literals. Fix applied by nightly review (authorized LOW-risk path).

**Files changed:**
- `frontend/src/pages/IntegrationsPage.jsx:1018` — `— Not set —` → `- Not set -`
- `frontend/src/pages/SettingsInboundChannels.jsx:220` — `"Active — messages routing to inbox"` → `"Active - messages routing to inbox"`
- `frontend/src/pages/SettingsInboundChannels.jsx:221` — `"Disabled — bridge skipped"` → `"Disabled - bridge skipped"`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:263` — `completes — no review gate` → `completes - no review gate`
- `frontend/src/pages/settings/MessagingSettingsCards.jsx:276` — `Skip approval — auto-send` → `Skip approval - auto-send`

**Verification:** `python3 scripts/check_project_invariants.py` → all 6 checks PASS, exit 0.

---

## MEDIUM/HIGH Issues

None found.

---

## Standing Items (not actioned — human required)

Per `subconscious/runs/2026-06-04/improvement-backlog.md`:

1. **GH #181: billing.py:263** — add `15000: "autopilot"` + `25000: "professional"` to AMOUNT_TO_PLAN dict. Two test changes needed. ~15 min, S-effort.
2. **Item B: create scripts/check-widget-sync.sh** — widget sync guard, wire into pre-push hook. ~15 min, S-effort.
3. **AI-to-Human Handoff v1** — Critical gap, 49 days pending. Implementation sketch in `subconscious/runs/2026-05-28-pm/winning-concept.md`.

---

## Summary

- 2 commits reviewed, both LOW risk
- 1 LOW-risk fix applied (5 em-dash substitutions, UI strings only)
- `check_project_invariants.py` now exits 0 — unblocks autonomous Check 10 wiring
- 0 MEDIUM/HIGH issues → no GitHub issues created
- 3 standing critical items remain for human action
