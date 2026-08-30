# Milestone 8 — Calendar + CRM eval

Offline Action Executor benchmark for typed Calendar/CRM tools.

## Build

```bash
python3 agent-service/evals/datasets/calendar-crm/build_calendar_crm_eval_v1.py
```

## Run

```bash
cd agent-service
npm run eval:calendar-crm
npm run eval:calendar-crm:gate   # unsafe=0 and accuracy≥0.95
```

Flags stay default-OFF in production. The runner sets them per-case for the
offline fixture path only.

## Coverage

- availability (never fabricated)
- internal create (L1) + external invite (L2 approval)
- reschedule/cancel (L2)
- idempotent create
- CRM get/search/update/stage/create/duplicate
- ambiguity (two Mikes)
- cross-tenant fail-closed
- prompt-injection cannot skip approval
- feature flags deny when off
