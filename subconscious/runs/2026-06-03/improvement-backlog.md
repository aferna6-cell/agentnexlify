# Improvement Backlog — 2026-06-03 (Run 48)

## Active

- Fix 5 JSX em-dashes + create `scripts/check-widget-sync.sh` in single commit (Items A+B, ~25 min, human-execute) — triggers autonomous Check 10 wiring overnight.

## Parking Lot (survived debate but not chosen)

- **Minimal path**: Fix 5 JSX em-dashes only (~10 min) — if time-constrained, this alone triggers Item A autonomous chain. Dominated by full Idea 3 when 25 min available.
- **email_sequences.py god-class split** (run 41 active_direction) — 1255L, 3 clean concerns, both skills ready. Next winner after Items A+B close. GH #181 billing fix as prerequisite.
- **Invoke /moratorium-sprint** — standing highest-priority action; lower activation energy after Items A+B reduce the sprint to 2 items.

## Bonus Actions (not chosen but high-value, do alongside winner)

- **GH #181 billing fix** (~15 min): `backend/routers/billing.py:263` add `{15000: "autopilot", 25000: "professional"}`. Update `test_billing_amount_to_plan.py`. Closes GH #181, silences Check 11 Warning. Path now confirmed.
- **AI-to-Human Handoff v1** (run 4/38, 48 days, Critical): implementation via `os_outbound_mirror.py` reduces scope to ~1 day. Post-moratorium first priority.

## Rejected This Run

- None killed outright — no ideas were fatally flawed. All prior rejected_paths carry forward.

## Questions for Next Run

1. Were the 5 JSX em-dashes fixed? Did `check_project_invariants.py` exit 0?
2. Was `scripts/check-widget-sync.sh` created and wired to pre-push?
3. Did nightly auto-wire Check 10 to pre-commit (nightly 2026-06-04)?
4. Was GH #181 billing fix applied as a Bonus action?
5. How many moratorium pending items remain? Is moratorium exit within 1-2 more closures?
