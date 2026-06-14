# Improvement Backlog — 2026-06-04 (Run 49)

## Active

- Fix exactly 5 JSX em-dash violations (~2 min) — unblocks autonomous Check 10 wiring at 2:37 AM tonight (run 49 winner)

## Parking Lot (survived debate, not chosen)

- **AI-to-Human Handoff v1** — WEAKENED this run. Critical gap, 49 days, os_outbound_mirror.py reduces scope. First post-moratorium winner candidate once pending drops to ≤ 2.
- **Zapier API key plan_status enforcement (GH #107)** — WEAKENED. ROI 2.5, security gap, 49 days. Moratorium-exempt on security grounds but strictly lower priority than Item A. Promote if GH #107 confirmed still open.
- **email_sequences.py god-class split** — KILLED this run. Valid, all prerequisites met (god-class-splitter + post-split-test-repair SKILLs ready), but M-effort during active moratorium with 13 pending items. Promote after moratorium exits.

## Rejected This Run

- **Items A+B combined (~25 min)** — superseded by atomic Idea 1. Run 48 was the combined rec; run 49 de-couples to remove activation energy barrier.
- **email_sequences.py split** — KILLED. M-effort, moratorium active, would add to pending not reduce it.

## Standing Critical Actions (not subconscious winners — human required)

- **GH #181: billing.py:263 add 15000→autopilot + 25000→professional** (~15 min, S-effort). Path confirmed: `backend/routers/billing.py`. Two test changes needed. PR #183 path reference wrong — update to `backend/routers/billing.py`.
- **Item B: create scripts/check-widget-sync.sh** (~15 min, S-effort). Script template in `subconscious/runs/2026-06-03/winning-concept.md §Step 2`.
- **AI-to-Human Handoff v1** (run 4, 49 days, Critical). Implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.

## Questions for Next Run

1. Was the em-dash fix committed? Did `check_project_invariants.py` exit 0?
2. Did nightly 2026-06-04 auto-wire Check 10 (look for bash block in `scripts/hooks/pre-commit`)?
3. Was Bonus A (widget sync guard) done in the same session?
4. Was GH #181 billing fix done?
5. What is the true pending count after any implementations?
