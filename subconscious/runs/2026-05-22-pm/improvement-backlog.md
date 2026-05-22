# Improvement Backlog — 2026-05-22-pm (Run 30)

## Active

### Winner (Run 30): Billing Constants Contract Tests
S-effort, ~20 min, code-only. Guard AMOUNT_TO_PLAN + PLAN_TO_STRIPE_PRICE after c72b535
live billing bug. Full sketch: `subconscious/runs/2026-05-22-pm/winning-concept.md §Steps 1-5`.

### Standing: Invoke /moratorium-sprint (unchanged from runs 28–29)
Items A+B+D, ~40 min. Moratorium exit: pending 6→2. moratorium-sprint SKILL.md ready (7985fbb).
Sprint sketch: `subconscious/runs/2026-05-21/winning-concept.md`.

---

## Parking Lot (survived debate but not chosen)

- **Test Patch Path Standard** — prevent stale mock churn across 54 god-class splits.
  Evidence: 5f2cd2b 908-line repointing. Deferred impact. Promote when first god-class split PR opens.
  Potentially already documented in testing-standards.md — verify before writing.

- **AI-to-Human Handoff GH Issue** — 5 min, moratorium-exempt, Critical gap 36+ days.
  Spec fully written in `subconscious/runs/2026-05-21-pm/winning-concept.md §Step 1`.
  DO NOT propose as winner again until moratorium exits. Mechanism has been recommended
  3x (runs 21, 29, 30-evaluated) without implementation. Information is present. Act directly.

- **email_sequences.py God-Class Split** — 1255 lines, ROI 2.3, closes GH #112/#113.
  M-effort. Promote to winner queue post-moratorium. Template exists from local_seo split.

- **models/schemas.py Domain Split** — 999 lines, unlocks clean future router splits.
  M/L-effort. Prerequisite work. Queue after email_sequences.py.

- **Merge safe dep PRs #102/#103/#104/#164/#171** — ~5 min, any time, independent.
  Already listed in morning digest. No subconscious winner needed — just do it.

---

## Rejected This Run

- **/moratorium-sprint as run 30 winner** — Same mechanism since run 25 (6 recs).
  Remains highest-leverage action. Not killed. Demoted from winner slot only.

- **AI-to-Human Handoff GH Issue as run 30 winner** — 3rd consecutive recommendation
  without implementation (runs 21, 29, 30-evaluated). Spec exists. No new information.
  Demoted to parking lot per run 29 Q1 guidance. Do NOT re-propose as winner.

---

## Questions for Next Run

1. **Was test_billing_constants.py created?** If yes: note which PR, confirm CI green.
   If no: run 31 should either implement it immediately (S-effort, still fresh) or
   investigate why the billing fix context has cooled.

2. **Has /moratorium-sprint been invoked?** If yes: moratorium exits, pending → 2.
   First post-moratorium winners should be: AI-to-Human Handoff (customer value) +
   Zapier plan_status enforcement (security, GH #107, ROI 2.5).
   If no: run 31 should not propose sprint again — evaluate redesigning the mechanism.

3. **God-class refactor momentum?** Today: local_seo done + plan created. What's the
   next target being worked on? If email_sequences.py PR is open, promote test patch
   path standard from parking lot immediately.

4. **Billing.py god-class plan?** billing.py is explicitly HARD-STOP (grill-me required).
   When is grill-me planned for billing refactor? The constants contract tests should run
   before that refactor begins.
