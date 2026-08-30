# Milestone 8 — Calendar + CRM Business Actions

**Status (2026-08-30 finalization):** Offline slice **merged** on `main` via
PR #709. Migration **198 APPLIED** on production Supabase (#708). Production
data-plane wiring lands on `cursor/milestone8-finalize-a2c9`. Flags remain
**default OFF** until controlled live proof.

| State | Meaning |
|-------|---------|
| **Merged** | Code on `main` (offline tools, policy, evals, Collecting ports, docs) |
| **Live-proven** | Controlled staging smoke with real Google / leads completed |
| **Enabled** | Env flag `=1` on that environment |

Today: **merged** yes · **live-proven** no (auth-gated) · **enabled** nowhere by default.

## Architecture (locked)

See `planning/decisions/2026-08-30-m8-calendar-crm-architecture.md`, Phase 0
`audits/audit-m8-calendar-crm-phase0-2026-08-30.md`, and finalization map
`audits/audit-m8-finalization-path-2026-08-30.md`.

| Concern | Decision |
|---------|----------|
| Calendar provider | Google via `CalendarPort` → data plane (`os_calendar_crm` → `booking` / `google_calendar`) |
| CRM SoT | `leads` (`client_id`, `status`) via `CrmPort` → `apply_crm_mutations` |
| Entity resolution | `agents/_resolve.ts` (exact / unique / multiple / none) |
| Mutations | Action Executor only — no department → provider calls |
| L1 path | Collecting bundle → `persist_tool_executions` → apply + read-back |
| L2 calendar | Claim → `run_calendar_l2` (not engine Collecting) → verify |
| Flags | `CALENDAR_ACTIONS_ENABLED=0`, `CRM_ACTIONS_ENABLED=0` (default OFF) |

## Tools

| Tool | Risk | Notes |
|------|------|-------|
| `get_calendar_availability` | 0 | Seeded busy from SharedContext / freebusy; never invents |
| `create_calendar_event` | 1 → 2 | L2 when attendees / `send_invitations` |
| `reschedule_calendar_event` | 2 | Approval required |
| `cancel_calendar_event` | 2 | Explicit `event_id` only |
| `get_customer` | 0 | Tenant-scoped |
| `search_customers` | 0 | Never picks among multiple |
| `update_customer` | 1 | Field-level; preserves unspecified |
| `create_customer` | 1 | Duplicate-aware (email then phone) |
| `update_lead_stage` | 1 | Canonical / tenant stages only |
| `add_customer_note` | 1 | Reused; not gated by CRM flag |

## Guarantees (honest)

- **Idempotency:** claim-gated execute + search-before-create fingerprint /
  `idempotency_key`. Without Google idempotency tokens this is **best-effort**,
  not provider-native exactly-once.
- **Verification:** calendar GET after write; CRM field read-back. Status
  `verification_failed` is separate from `succeeded`. Unknown provider outcomes
  stay non-terminal (`running` + reason) — not auto-retried.
- **Availability:** never fabricated. Empty or provider error is returned as-is.
- **Ambiguity:** multiple name matches → clarification / `kind: multiple`.

## Current flag states

| Flag | Dev | Staging | Canary | Production |
|------|-----|---------|--------|------------|
| `CALENDAR_ACTIONS_ENABLED` | optional local | **OFF** until smoke | **OFF** | **OFF** |
| `CRM_ACTIONS_ENABLED` | optional local | **OFF** until smoke | **OFF** | **OFF** |
| `SEND_EMAIL_ENABLED` | optional local | **OFF** until Gmail live proof | **OFF** | **OFF** |
| `RAG_ENABLED` | optional local | candidate after holdout | candidate | **OFF** (198 applied; gated) |

Rollback for any flag: set `=0` / unset (fail-closed).

## Remaining production blockers

1. **Controlled Calendar staging smoke** — requires staging tenant + Google OAuth
   on a harmless calendar (owner authorization).
2. **Controlled CRM staging smoke** — staging lead/customer mutations +
   cross-tenant negative proof.
3. **Gmail live proof** — do not enable `SEND_EMAIL_ENABLED` globally until
   proposal → approve → one send → Message-ID read-back → redrive no-dup.
4. **RAG enablement** — migration 198 applied; enable staging/canary only with
   frozen `min_score=1.0` and fast disable path; broader prod after canary soak.

## Verification commands

```bash
# Offline M8 gate
python3 agent-service/evals/datasets/calendar-crm/build_calendar_crm_eval_v1.py
cd agent-service && npm run eval:calendar-crm:gate

# M6 / M7 regression
cd agent-service && npm run eval:actions:gate
# RAG validation + independent holdout (repo scripts)
npm run check:quick

# Backend Calendar/CRM unit tests
cd backend && python -m pytest tests/test_os_calendar_crm.py tests/test_os_tool_executions.py -q
```

## Live smoke (owner-gated)

Blocked until explicit environment authorization:

1. Staging tenant + test calendar
2. Availability from provider → internal create once → GET verify → cancel verify
3. Invite create parks → nothing external before approve → one event after approve → redrive no-dup
4. Wrong-tenant event ID fails
5. CRM: tenant search, ambiguous clarify, partial update + read-back, duplicate create blocked, stage validation, cross-tenant ID refused, audit complete

## Out of scope

SMS, computer use, browser automation, general multi-step planner (Milestone 9),
ten CRM vendors, RL/active learning.

## Status honesty

**Merged on main (#709):** offline Action Executor + policy + evals +
flag-gated department resolvers.

**This finalization branch:** production apply paths (`os_calendar_crm`),
SharedContext busy/CRM seed, L2 calendar claim-gated execute, docs/matrix.

**Not yet live-proven / not enabled:** production Calendar/CRM flags, Gmail
send, RAG beyond optional staging candidate.
