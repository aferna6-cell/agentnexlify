# Idea 3: M8 Calendar/CRM Rollout Gate — Formal Pre-Flag-Flip Checklist

**Evidence:** Commit a36f97a (2026-08-30) ships os_calendar_crm.py (700 lines, Google Calendar + CRM bridge). Commits 47cda00/b786aeb (2026-08-31) show "Calendar/Gmail OAuth HOLD" and "service_role HOLD" flags explicitly. m8-next-actions-2026-08-31.md documents next actions. The M8 staging RLS was just re-enabled (47cda00). No formal subconscious-tracked rollout gate exists for M8's flag flip to production tenants.

**Action:** Recommend creating a formal M8 production rollout checklist issue in GH — covering: OAuth scopes verified, service_role RLS re-enabled in prod, smoke test against real tenant, calendar slot creation E2E verified, CRM sync idempotency confirmed. Tag as human-action-required.

**Impact:** Prevents premature M8 production flag flip that could expose half-integrated Calendar/CRM to paying tenants. The explicit HOLDs suggest the team is aware — a GH issue formalizes the gate.

**Category:** operational
