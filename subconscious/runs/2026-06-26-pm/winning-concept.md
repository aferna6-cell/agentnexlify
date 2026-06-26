# Winning Concept — Run 68 (2026-06-26-pm)

**Title:** Deliver 30-Second Terminal Command Block to Unblock Pre-Commit  
**Category:** code_health  
**Confidence:** HIGH  
**Requires Human:** YES — paste into terminal  
**Autonomous:** false  
**Effort:** 30 seconds (copy-paste execution)  
**Mandate:** Fires unconditionally from run 67 winning-concept.md §RUN 68 MANDATE

---

## Problem

`check_project_invariants.py` exits 1 for the **4th consecutive subconscious run** (65 → 66 → 67 → 68). Pre-commit Check 13 FAIL+BLOCK mode has blocked all git commits since 2026-06-23. The violations are mechanical — widget drift + em-dashes — introduced by referral sprint PRs #368-371.

**Live invariant output (run 68):**
```
FAIL widget assets are byte-identical across mirrors
  - drift: widget/agentnexlify-widget.js != landing-page-v2/widget/agentnexlify-widget.js
FAIL website source avoids em dashes
  - frontend/src/components/billing/ReferralCard.jsx:6
  - frontend/src/pages/SignupPage.jsx:40
  - frontend/src/pages/SignupPage.jsx:151
  - frontend/src/pages/AdminFunnelPage.jsx:15
  - frontend/src/pages/AdminFunnelPage.jsx:49
  - frontend/src/pages/AdminFunnelPage.jsx:87
  - frontend/src/pages/AdminFunnelPage.jsx:122
  - frontend/src/pages/AdminFunnelPage.jsx:267
  - frontend/src/pages/AdminFunnelPage.jsx:315
  - frontend/src/pages/AdminFunnelPage.jsx:440
2 invariant(s) failed.
```

---

## Delivery History (Why This Escalated to Mandate)

| Run | Delivery attempt | Outcome | Root cause |
|-----|-----------------|---------|-----------|
| 65 | Nightly 2026-06-24 | FAILED | `cp` not in nightly scope |
| 66 | Nightly 2026-06-25 (Step 9B) | FAILED | Editing existing SKILL.md not in nightly scope |
| 67 | Interactive human session prompt | NOT EXECUTED | Activation energy too high (~10 min of steps to follow) |
| 68 | **Push notification + 30-second command block** | **← THIS RUN** | — |

---

## FIX — PASTE THIS IN YOUR TERMINAL (30 seconds from repo root)

```bash
cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js && sed -i 's/—/-/g' frontend/src/components/billing/ReferralCard.jsx frontend/src/pages/SignupPage.jsx frontend/src/pages/AdminFunnelPage.jsx && python3 scripts/check_project_invariants.py && git add -A && git commit -m "fix: widget drift + em-dash violations (run 65 mandate — pre-commit blocked since 2026-06-23)"
```

**What it does:**
1. Syncs `landing-page-v2/widget/agentnexlify-widget.js` from `widget/` (the source of truth)
2. Replaces all em-dashes (`—`) with hyphens (`-`) in the 3 files with violations
3. Runs the invariant check — confirms it passes (exits 0)
4. Stages ALL changes and commits with the canonical message

**If the check still fails after step 3:** Stop. Do NOT commit. Paste the failing output into a new Claude session to investigate.

---

## After This Fix

Once the commit lands:
1. Pre-commit unblocked — all future commits go through normally
2. Run 65 + 66 active_directions → mark implemented
3. Run 69 winner: Plan-name guard Check 7 (AUTONOMOUS-EXECUTABLE, parking lot → active, ~20 lines, nightly delivers)
4. Moratorium exit path clears further: true_pending drops from ~6 to ~4 → cleanup sprint → ≤2 → exits

---

## Bonus Actions (run 69 candidates)

**Bonus A — Plan-Name Guard Check 7 (AUTONOMOUS-EXECUTABLE)**  
After check exits 0: add Check 7 to `check_project_invariants.py` validating canonical plan names in `ai_usage_guard.py`, `billing_reconciliation.py`, `sms_rate_limiter.py`, `api_key_auth.py`. Prevents next repricing half-migration. ~20 lines, same pattern as existing checks.

**Bonus B — SMS Compliance Dashboard Section**  
`GET /api/sms/compliance-stats` endpoint + Settings page section showing opt-out count/dates. Completes the TCPA compliance loop (backend suppresses, tenant sees). S-effort. Run 69 candidate after moratorium path clears.

---

## RUN 69 MANDATE

If `check_project_invariants.py` still exits 1 in run 69 (run 65 fix still unimplemented for the 5th consecutive run): escalate to a calendar reminder. The subconscious loop has exhausted its delivery toolkit. A scheduled calendar event that forces an interactive session is the only remaining lever.
