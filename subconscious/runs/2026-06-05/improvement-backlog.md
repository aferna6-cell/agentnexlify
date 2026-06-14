# Improvement Backlog — 2026-06-05 (Run 50)

## Active

- **Item B: Create scripts/check-widget-sync.sh + wire pre-push + fix CLAUDE.md Invariant #4** — AUTONOMOUS-EXECUTABLE via nightly scope extension (run 50 winner, 43-day gap, 3 widget copies). Expected close: nightly 2026-06-06 at 2:37 AM.
- **Item A: Wire check_project_invariants.py as pre-commit Check 10** — AUTONOMOUS-EXECUTABLE, auto-wires TONIGHT (pre-condition met: check_project_invariants.py exits 0 as of 2026-06-05).

## Parking Lot (survived debate but not chosen)

- **Zapier API key plan_status security fix** — GH #107, 36+ days. Route via `issue-to-pr-loop`: create GH issue with `ai-ready` label for `backend/services/zapier_auth.py::_get_api_key_client`. ~10-line fix + regression test. Security gap: cancelled tenants bypass tier gate via un-revoked keys. ROI 2.5. Do NOT use as subconscious winner per governance note — route to issue-to-pr-loop.
- **email_sequences.py god-class split** — 1255L, 3 clean concerns, all tooling ready. GH #181 prerequisite (~15 min). M-effort (~2h), moratorium active. Active_direction runs 35/41. First post-moratorium candidate.
- **AI-to-Human Handoff v1** — Run 4, 50 days oldest pending, CRITICAL gap all 7 industries. Agent OS (os_outbound_mirror.py) reduces scope to ~1 day. Do not re-propose as winner until moratorium exits. Implementation sketch: `subconscious/runs/2026-05-28-pm/winning-concept.md`.

## Rejected This Run

- **email_sequences.py split as winner** — KILLED: moratorium active day 35, M-effort, GH #181 prerequisite unresolved, zero production velocity in 4 days. Parking lot: correct queue.
- **GH #181 as winner** — KILLED by governance: in `rejected_paths`, 5-consecutive-run threshold. Remains `critical_standing_action`. Do first before email split.

## Standing Critical Actions (not subconscious winners — do independently)

1. **GH #181: billing.py:263** — add `{15000: "autopilot", 25000: "professional"}` to AMOUNT_TO_PLAN. Update `test_billing_amount_to_plan.py`: remove backwards assertions (lines 38-44), add current-price assertions. ~15 min, human required. Silences Check 11 WARNING. Closes GH #181. Path confirmed: `backend/routers/billing.py`.
2. **AI-to-Human Handoff v1** — Critical gap, route to human sprint or issue-to-pr-loop with `ai-ready` tag once moratorium exits.

## Questions for Next Run

1. Was Item B (check-widget-sync.sh) created by nightly 2026-06-06? Check: `ls scripts/check-widget-sync.sh`, grep pre-push for widget-sync line.
2. Was Item A (Check 10) wired by nightly 2026-06-05/06? Check: `grep check_project_invariants scripts/hooks/pre-commit`.
3. Was GH #181 implemented? Check: `grep 15000 backend/routers/billing.py` — should show autopilot entry.
4. Are Items A+B now closed? If yes: pending count drops, moratorium exit threshold review required.
5. Has the issue-to-pr-loop been confirmed running? If yes: promote Zapier fix to `ai-ready` GH issue creation.
