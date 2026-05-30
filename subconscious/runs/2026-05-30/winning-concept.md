# Winning Concept — 2026-05-30 (Run 41)

## Recommendation

Invoke `/god-class-splitter` on `backend/routers/email_sequences.py` — split the 1255-line module into `email_crud.py`, `email_enrollment.py`, and `email_processor.py`.

---

## Why This, Why Now

Today's nightly review (d481799, 2026-05-30) created `.claude/skills/post-split-test-repair/SKILL.md` — the final prerequisite that has blocked this recommendation since run 35. For the first time in this system's 41-run history, ALL tooling is simultaneously available: the god-class-splitter SKILL.md (e848b87), the post-split-test-repair checklist (d481799), and the confirmed pattern from PR #180 (2174732, 135 new tests, 5 files split successfully). The email_sequences.py split is the run 35 active_direction (14+ days in pending queue) and was identified in run 40's own recommended sequence as the direct next step after SKILL.md creation. Execution now resolves a pending item rather than adding one, moving the moratorium exit math in the right direction.

---

## Implementation Sketch

### Step 0 — Prerequisite check
```bash
wc -l backend/routers/email_sequences.py        # confirm 1255L
ls .claude/skills/god-class-splitter/SKILL.md   # confirm exists
ls .claude/skills/post-split-test-repair/SKILL.md  # confirm exists (d481799)
```

### Step 1 — Invoke /god-class-splitter
```
/god-class-splitter
```
Supply target: `backend/routers/email_sequences.py`

The skill will:
- Identify 3 clean concerns: CRUD (sequence CRUD, template CRUD), Enrollment (lead enrollment, unenrollment, status), Processor (_process_pending_sends, run_sequence_processor)
- Propose module names: `email_crud.py`, `email_enrollment.py`, `email_processor.py`
- Extract each concern into its own file under `backend/routers/` or `backend/services/`
- Update `backend/main.py` router registrations

### Step 2 — Critical standing action (do first, ~15 min)
Before executing the split, fix GH #181:
```python
# backend/services/billing.py — AMOUNT_TO_PLAN dict
# Add: 15000: "autopilot", 25000: "professional"
# test_billing_amount_to_plan.py:38-44 — remove backwards assertions
```
Check 11 will stop firing WARNING once done.

### Step 3 — Invoke /post-split-test-repair immediately after split
```
/post-split-test-repair
```
Run the 8-step checklist:
1. grep stale `from backend.routers.email_sequences import` in `backend/tests/`
2. Repoint @patch targets to new module paths
3. Fix any ImportError in test files
4. Run `python -m pytest backend/tests/ -x -q` — must pass
5. Verify no 500 errors in Railway logs for email sequence endpoints

### Step 4 — Wire GH #112/#113 as follow-on issues
After split, the N+1 query fix (GH #112) and process duplication fix (GH #113) become scoped to single modules. Tag both issues with the new module names for executor clarity.

### Step 5 — Commit
```bash
git add backend/routers/email_crud.py backend/routers/email_enrollment.py \
        backend/routers/email_processor.py backend/main.py backend/tests/
git commit -m "refactor(email): split email_sequences.py (1255L) → crud+enrollment+processor"
```

---

## What This Replaces

Run 35 active_direction (pending_approval, "Invoke /god-class-splitter on email_sequences.py"). Run 41 is the escalation with all prerequisites now met. Previous winner (run 40) fixed the nightly autonomous channel for SKILL.md creation, which enabled d481799 to create the post-split-test-repair SKILL.md — making this split actionable.

---

## Standing Actions (Unchanged)

In priority order:

1. **GH #181 billing fix (~15 min, HUMAN REQUIRED, do BEFORE split):** `billing.py` add `15000: "autopilot"`, `25000: "professional"` to `AMOUNT_TO_PLAN`; remove backwards test assertions `test_billing_amount_to_plan.py:38-44`. Check 11 fires WARNING on every commit as reminder.
2. **Invoke /moratorium-sprint (~40 min):** Items A (check_project_invariants pre-commit), B (check-widget-sync.sh), D (lead-qualifier-eval.yml). Exits moratorium. Tool ready (7985fbb).
3. **AI-to-Human Handoff v1 (~1 day):** Run 38 winner, 44+ days. Agent OS plumbing ready (os_outbound_mirror.py, PR #188 merged).
4. **GH #112/#113 N+1 fix:** After email_sequences split simplifies scope.

---

## Governance Corrections Applied This Run

- **Run 39** (post-split-test-repair SKILL.md): `pending_approval` → `implemented` (d481799, nightly 2026-05-30)
- **Run 40** (fix nightly-commit-review SKILL.md): `pending_approval` → `implemented` (d481799, nightly 2026-05-30)
- **ccf0c8e** (god-class cross-ref): additional implementation artifact from nightly 2026-05-30

---

## Confidence

**MEDIUM** — all tooling prerequisites met for first time (HIGH evidence). Risk: first production use of god-class-splitter on a complex 1255L module. /post-split-test-repair reduces risk but doesn't eliminate it. email_sequences.py has 17 functions and is adjacent to billing logic (enrollment costs). Confidence would be HIGH if a dry-run split pass were verified first.
