# Winning Concept — 2026-06-05-pm (Run 51)

## Recommendation

Verify PR #183 targets the correct file (backend/routers/billing.py, not services/) and includes both the billing dict fix AND the test assertion corrections, then merge it — closing GH #181, silencing Check 11 WARNING, and unblocking the email_sequences.py god-class split.

## Why This, Why Now

GH #181 has been recommended as a subconscious winner 5 times (runs 31/32/34/35 + critical escalation) without implementation — triggering rejected_paths governance. The prior recommendations all said "write the fix." This recommendation is different: the fix is already written. PR #183 (12-day draft) contains the billing.py + test changes. Path confirmed June 2 (run 47): backend/routers/billing.py:263 — two prior failed code commits (c72b535, 1eaaeec) targeted the wrong path. Morning digest (2026-06-05) explicitly labels PR #183 "merge — confirmed path." The action is 10 minutes of review + merge, not writing new code. Merged: Check 11 WARNING becomes PASS, email_sequences.py split (run 41, 1255L) immediately unblocked, oldest moratorium exit chain item moves.

## Implementation Sketch

**Time: ~10 min. Risk: LOW (CI gate prevents incorrect merge).**

### Step 0 — Merge PR #200 first (5 min, Bonus A)
IMPORTANT: Do this before tonight's nightly (2:37 AM).
```
gh pr ready 200 && gh pr merge 200 --squash
```
This ensures the nightly SKILL.md scope extension is on main so Item B (widget sync guard) executes tonight.

### Step 1 — Read the PR #183 diff

Verify the PR diff contains exactly:
1. **File: `backend/routers/billing.py`** (NOT services/billing.py or billing.py at root)
   - AMOUNT_TO_PLAN dict at or near line 263
   - Adds `15000: "autopilot"` entry
   - Adds `25000: "professional"` entry
2. **File: `backend/tests/test_billing_amount_to_plan.py`**
   - Removes or corrects lines 38-44 (backwards assertions that assert 15000 + 25000 should NOT exist)
   - Adds current-price assertions for 15000 ($150/mo autopilot) + 25000 ($250/mo professional)
   - Updates `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`

If either file is missing or targets wrong path → DO NOT MERGE. Create new GH issue with the correct fix sketch and label it `critical` + `ai-ready`.

### Step 2 — Verify CI status on PR #183

If CI is green → proceed to merge.
If CI is red → read the failure. If the failure is only the contradictory test assertions (test_no_wrong_15000_mapping / test_no_wrong_25000_mapping), the PR may be incomplete — flag to human before merging.

### Step 3 — Merge

```
gh pr ready 183 && gh pr merge 183 --squash
```

### Step 4 — Verify post-merge

```bash
grep -n "15000\|25000" backend/routers/billing.py | head -5
# Expected: both entries present in AMOUNT_TO_PLAN dict

# Run billing tests
python3 -m pytest backend/tests/test_billing_amount_to_plan.py -v 2>&1 | tail -10
# Expected: all pass, no assertions about 15000/25000 being absent
```

### Step 5 — Update active_directions status

Update governance.json: GH #181 critical_standing_action entry → status `implemented`.

## What This Replaces

Previous active direction (run 50 AM): "Extend nightly scope + mark Item B AUTONOMOUS-EXECUTABLE" — that recommendation governs tonight's nightly execution (autonomous, no human action needed). This PM recommendation governs what the HUMAN does NOW: close the billing gap that has been blocking email_sequences.py split for 10+ days.

## Confidence

**MEDIUM-HIGH** — Evidence: morning digest confirms "merge — confirmed path." Path verified in run 47. Morning digest routine reads current repo state, not cached state. CI gate prevents incorrect merge. Rejected_paths governance is addressed by "merge existing PR" framing vs "write new fix" framing. Risk: PR #183 may still have wrong path from before run 47's discovery — Step 1 verification is mandatory before merge.

## Bonus Actions (after PR #183 merge)

**Bonus A — Merge PR #200 (5 min, do FIRST — before tonight's nightly 2:37 AM)**
`gh pr ready 200 && gh pr merge 200 --squash`
Ensures Item B (check-widget-sync.sh + pre-push) fires tonight.

**Bonus B — email_sequences.py god-class split (unblocked by PR #183 merge)**
With GH #181 closed, the prerequisite for run 41 is met. Invoke /god-class-splitter on backend/routers/email_sequences.py. Split into email_crud.py + email_enrollment.py + email_processor.py. ~2h execution. Schedule for next human session.

**Bonus C — Zapier security GH issue (2 min, anytime)**
Create GH issue with ai-ready label: "fix(zapier): add plan_status IN ('active','trialing') filter to _get_api_key_client in backend/services/zapier_auth.py". Routes to issue-to-pr-loop for autonomous fix. GH #107, 36+ days.
