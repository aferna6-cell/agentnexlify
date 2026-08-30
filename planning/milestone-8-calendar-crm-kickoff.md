# Milestone 8 kickoff — Calendar + CRM Business Actions

**Status:** Phase 0 complete; implementation starting on `cursor/milestone8-calendar-crm-a2c9`  
**Prerequisite:** M7 on main (#707). Migration 198 optional for M8.  
**Flags:** `CALENDAR_ACTIONS_ENABLED` / `CRM_ACTIONS_ENABLED` default **OFF**

## North star

Owner can ask to find a customer, check availability, and schedule — with approval, verification, and audit — without a general multi-step planner.

## Docs

| Doc | Role |
|-----|------|
| `audits/audit-m8-calendar-crm-phase0-2026-08-30.md` | Phase 0 inventory |
| `planning/decisions/2026-08-30-m8-calendar-crm-architecture.md` | Locked architecture |
| This file | Execution checklist |

## Explicitly out of scope

SMS, computer use, browser automation, general planner, RL, personalization, broad finance, ten CRM vendors.

## Acceptance (tracking)

See user Milestone 8 acceptance criteria 1–22. Phase 0 covers (1). Implementation PRs must keep (17)–(18) green and flags OFF for (21).

## Verification commands (target)

```bash
cd agent-service && npm test
cd agent-service && npm run eval:actions:gate          # M6
cd agent-service && npm run eval:rag                   # M7 validation
cd agent-service && npm run eval:rag:holdout           # M7 holdout
# later:
# npm run eval:calendar-crm
npm run check
```
