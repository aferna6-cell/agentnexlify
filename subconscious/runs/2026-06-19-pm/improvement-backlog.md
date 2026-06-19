# Improvement Backlog — 2026-06-19-pm (Run 62)

## Active

- **Fix GH #292/#293 — Wire chatbot/agent_os into plan-name dicts** (sms_rate_limiter +
  api_key_auth + billing_reconciliation). ~20 min, 3 files, ~12 lines. Run 62 mandate.
  All new paid tenants broken since billing repricing 2026-06-16. HIGH confidence.

## Parking Lot (survived debate, not chosen)

- **Fix GH #308 — Webhook Idempotency Early-Write** (Bonus A — implement after main fix).
  Full sketch: `subconscious/runs/2026-06-19/winning-concept.md`. delete_key() +
  stripe_webhooks exception handler + regression test. ~20 min. Revenue bug (dunning-lock).
  RUN 63 MANDATE: if #292/#293 unimplemented, switch to this as winner.

- **Add Plan-Name Guard Check 7 to check_project_invariants.py** (Bonus B — AUTONOMOUS-
  EXECUTABLE after GH #292/#293 fix). ~15 lines Python. Systemic guard vs future plan-name
  drift.

- **Investigate GH #263 — 24 pending migrations** (CRITICAL flag, 5 days). Needs triage
  before fix. Determine: applied-but-not-tracked vs genuinely pending. File GH issue
  with disposition.

- **AI-to-Human Handoff v1** (run 4, ~75 days, oldest pending). Implementation via
  os_outbound_mirror.py (Agent OS delivery layer). Scope ~1 day. Post-moratorium priority.

- **email_sequences.py god-class split** (1143L, run 41/35). god-class-splitter SKILL.md
  ready. Post-moratorium, M-effort.

- **Home.jsx god-class split** (1006L). Post-moratorium, M-effort.

## Rejected This Run

- **Idea 3 (GH #263 investigate) as winner** — insufficient triage to formulate atomic
  action. Parking lot candidate. Not enough evidence to know what "fix" looks like.

## Questions for Next Run

1. Was GH #292/#293 implemented? Check sms_rate_limiter.py:10 for "chatbot" and "agent_os".
2. Was GH #308 implemented? Check idempotency.py for delete_key method.
3. Was PR #333 (51-commit batch) reviewed and merged?
4. What are the 24 pending migrations in GH #263 — applied or genuinely pending?
5. Was Plan-Name Guard Check 7 added to check_project_invariants.py?
