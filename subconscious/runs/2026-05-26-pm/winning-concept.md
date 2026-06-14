# Winning Concept — 2026-05-26-pm (Run 35)

## Recommendation

Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` (1255L) — split into three focused modules: `email_crud.py`, `email_enrollment.py`, and `email_processor.py`.

---

## Why This, Why Now

**GH #181 governance mandate fires CRITICAL — mechanism change required.** Five consecutive subconscious runs recommended the same billing fix with zero implementation. The recommendation loop is broken. Governance mandates a pivot per the 5-consecutive-run escalation rule. GH #181 remains a **critical standing action** (see below) — it is not abandoned, but it is no longer the winner.

**email_sequences.py is the highest-leverage remaining god-class target.** At 1255L with three independent concerns (CRUD, enrollment, processor), it exceeds the 600-line threshold by 2x. GH #112 (list_enrollments N+1) and GH #113 (duplicate processor loop) have been open since 2026-05-02 — both are easier to fix post-split in isolated modules.

**The god-class-splitter skill was just created and is ready for its first production use.** e848b87 (yesterday's nightly review) implemented the SKILL.md. PR #182 (invoices.py split, 3 days, Draft) shows the pattern is already in use. email_sequences.py is the next highest-priority target per `plans/god-class-refactor_plan.md`.

**This is an interactive session.** Human is present. ~2 hours is executable now.

---

## Implementation Sketch

### Step 0: Pre-flight

```bash
wc -l backend/routers/email_sequences.py   # confirm 1255L
grep -n "^def \|^async def \|^class " backend/routers/email_sequences.py
```

### Step 1: Identify and name concerns

Three independent concerns from top-level inspection:

1. **CRUD** — sequence + step management endpoints (create, update, delete, list for sequences and steps): `create_sequence`, `get_sequence`, `update_sequence`, `delete_sequence`, `list_sequences`, `add_step`, `update_step`, `delete_step` + Pydantic models (StepCreate, StepUpdate, SequenceCreate, SequenceUpdate)
2. **Enrollment** — lead enrollment logic: `_enroll_lead`, `enroll_lead_in_sequences`, `list_enrollments`, `enroll_lead`, `EnrollRequest`, `_maybe_complete_enrollment`
3. **Processor** — sequence execution engine: `process_sequences`, `run_sequence_processor`, `_update_send_status`, `_increment_runs_total`

### Step 2: Extract to new modules

```
backend/routers/email_sequences.py (thin router, re-exports or delegates)
backend/services/email_sequences/
  __init__.py
  email_crud.py        (~400L: Pydantic models + CRUD endpoints)
  email_enrollment.py  (~300L: enroll_lead, auto-enroll, list_enrollments)
  email_processor.py   (~300L: process_sequences, run_sequence_processor)
```

Alternatively, if keeping as router files:
```
backend/routers/email_sequences_crud.py
backend/routers/email_sequences_enrollment.py
backend/routers/email_sequences_processor.py
```

Use the existing pattern from PR #180 and PR #182 — check how invoices.py was organized for consistency.

### Step 3: Run god-class-splitter 12-step checklist

Invoke the skill: `/god-class-splitter email_sequences.py`

The SKILL.md at `.claude/skills/god-class-splitter/SKILL.md` walks through all 12 steps including:
- Step 6: grep all importers and update every call site
- Step 9: pytest pass count unchanged from baseline
- Step 10: no stale `backend.routers.email_sequences` references remain
- Step 11: write `tests/test_extracted_email_sequences.py` smoke tests

### Step 4: Resolve GH #112/#113 in new modules

After split, apply N+1 fix in `email_enrollment.py`:
- `list_enrollments`: replace per-enrollment DB calls with bulk `.in_()` query
- In `email_crud.py`: `list_sequences` — bulk fetch, not 2 calls per sequence

### Step 5: Commit

```
refactor(email-sequences): split 1255L router into 3 modules (Rule 9)

Concerns: email_crud.py (CRUD endpoints + models), email_enrollment.py
(enroll logic + auto-enroll), email_processor.py (sequence runner +
send status). First production use of /god-class-splitter SKILL.md.
```

---

## Critical Standing Action: GH #181 (Do This First — ~15 min)

**Before starting the email_sequences.py split, apply GH #181 fix.** It's 15 min and removes a live billing gap:

1. `backend/routers/billing.py` — add to AMOUNT_TO_PLAN:
   ```python
   15000: "autopilot",    # $150/mo
   25000: "professional", # $250/mo
   ```
2. `backend/tests/test_billing_amount_to_plan.py` — remove `test_no_wrong_15000_mapping` + `test_no_wrong_25000_mapping` (lines 38-44); add `test_current_autopilot_pricing_150` + `test_current_professional_pricing_250`; update `test_all_four_current_tiers_present` to use `{9900, 15000, 25000, 89900}`.
3. Run `pytest backend/tests/test_billing_amount_to_plan.py -v` — confirm all green.

Full sketch: `subconscious/runs/2026-05-26/winning-concept.md` (run 34).

---

## What This Replaces

Run 34 winner (GH #181 fix) is moved from winner to critical_standing_action. GH #181 governance mandate is recorded as "recommendation_exhausted_5_consecutive" — future runs will not re-surface GH #181 as a winner unless new evidence emerges or human explicitly unblocks it. The recommendation loop is broken by design.

---

## Confidence

**MEDIUM** — Evidence is strong (1255L confirmed, clear split axis, skill ready, interactive session). Two factors reduce from HIGH: (1) ~2 hours of human execution required (vs 15-min for GH #181); (2) first production use of the new skill introduces unknown edge cases. The god-class-splitter 12-step checklist mitigates risk #2. Risk #1 is acknowledged — if the session doesn't complete the split, the recommendation stands for run 36 with higher confidence.
