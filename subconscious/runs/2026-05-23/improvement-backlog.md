# Improvement Backlog — 2026-05-23 (Run 31)

## Active

### Winner (Run 31): Fix GH #181 — AMOUNT_TO_PLAN current-price entries + test
S-effort, ~15 min. Add `15000: "autopilot"` and `25000: "professional"` to billing.py AMOUNT_TO_PLAN.
Update test_billing_amount_to_plan.py: remove contradictory assertions (lines 38-44), add
current-price assertions, update `test_all_four_current_tiers_present` to use current prices.
Full sketch: `subconscious/runs/2026-05-23/winning-concept.md §Steps 1-5`.

### Standing: Invoke /moratorium-sprint (unchanged from runs 28–30)
Items A+B+D, ~40 min. Pending 6→2 = moratorium exits. moratorium-sprint SKILL.md ready (7985fbb).
Sprint sketch: `subconscious/runs/2026-05-21/winning-concept.md`.

---

## Parking Lot (survived debate but not chosen)

- **Zapier plan_status enforcement (GH #107)** — S-effort, ROI 2.5, 23+ days.
  Fix: add `plan_status IN ('active','trialing')` to zapier_auth.py::_get_api_key_client.
  Promote to winner in run 32 if moratorium exits. First post-moratorium security winner candidate.

- **email_sequences.py god-class split** — 1255 lines, ROI 2.3, M-effort.
  Closes GH #112 (N+1 queries) + GH #113 (120-line duplication). Local_seo template ready.
  Promote to winner queue post-moratorium.

- **AI-to-Human Handoff GH Issue** — Spec fully written in runs/2026-05-21-pm/winning-concept.md.
  Do NOT propose as winner until moratorium exits. First customer-value winner after exit.

- **Test Patch Path Standard** — prevent stale mock churn across 54 god-class splits.
  Evidence: 5f2cd2b 908-line repointing. Promote when first post-local_seo split PR opens.

- **models/schemas.py domain split** — 999 lines. Queue after email_sequences.py.

- **Merge safe dep PRs** — ~5 min, any time, independent. No subconscious winner needed.

---

## Rejected This Run

- **/moratorium-sprint as run 31 winner** — 8+ consecutive recs without invocation. Remains
  the standing highest-leverage action and active direction. Not killed. Demoted from winner
  slot because Idea 1 has higher urgency (live billing gap, CI certifying wrong state).
  Run 32 escalation: if sprint still not invoked and Idea 1 implemented, evaluate mechanism
  redesign (not another repeat winner).

---

## Questions for Next Run (Run 32)

1. **Was GH #181 fixed?** If yes: confirm CI green with new test assertions.
   If no: run 32 should implement directly (S-effort, zero ambiguity, implementation sketch complete).

2. **Has /moratorium-sprint been invoked?** If yes: pending → 2, moratorium exits.
   Post-moratorium first winners: Zapier plan_status (security, ROI 2.5) + AI-to-Human Handoff
   (customer value, Critical, 37+ days).
   If no: evaluate mechanism redesign — 9+ consecutive sprint recs without invocation is a
   systemic signal, not just information lag.

3. **God-class split momentum?** After local_seo, what's next in queue? email_sequences.py
   (1255 lines, template ready) is the clear next target if production commits continue.
