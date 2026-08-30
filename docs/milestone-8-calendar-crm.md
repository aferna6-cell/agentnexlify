# Milestone 8 — Calendar + CRM Business Actions

**Status (2026-08-30 deploy-proof):** Offline + data-plane **merged** (#709/#710/#711).
Migration **198 APPLIED**. Smoke-tenant RAG indexed (**6** active chunks) + retrieval
proof pass; Railway still **production-only** (no staging env). Calendar/CRM/Gmail
Action Executor live smokes **blocked** on OAuth + service credentials. Flags
**default OFF**. Evidence: `audits/artifacts/m8-deploy-proof-report-2026-08-30.md`.
Owner staging steps: `docs/ops/m8-staging-setup.md`.

| State | Meaning |
|-------|---------|
| **Merged** | Code on `main` (offline tools, policy, evals, Collecting ports, docs) |
| **Live-proven** | Controlled staging smoke with real Google / leads completed |
| **Enabled** | Env flag `=1` on that environment |

Today: **merged** yes · **live-proven** partial RAG only · **enabled** nowhere · **HOLD**.

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

Use the real runner (not a guard-only stub):

```bash
export M8_SMOKE_AUTHORIZED=1
export M8_SMOKE_CLIENT_ID=<smoke-tenant-uuid>
export M8_SMOKE_ENV=staging
export M8_SMOKE_CONFIRM_ENV=staging
export M8_SMOKE_SUITES=rag,calendar,crm,gmail
# Also: SUPABASE_URL + SUPABASE_SERVICE_KEY
# Calendar needs google_calendar OAuth on that tenant
# Gmail needs gmail connector + SEND_EMAIL_ENABLED=1 + M8_SMOKE_ALLOW_EXTERNAL_SEND=1
python3 scripts/m8_controlled_smoke.py   # delegates to scripts/m8_live_smoke.py
```

Exit codes: `2` auth · `3` credentials/provider missing · `4` assertion fail · `0` pass.

Evidence: `audits/artifacts/m8-live-smoke-*.json`.

**2026-08-30 cloud-agent attempt:** RAG process soak passed; Calendar/CRM Action
Executor/Gmail blocked (no service key in agent env; zero Google/Gmail
integrations; empty `tenant_kb_chunks`). Report:
`audits/artifacts/m8-live-proof-report-2026-08-30.md`.

## Out of scope

SMS, computer use, browser automation, general multi-step planner (Milestone 9),
ten CRM vendors, RL/active learning.

## Status honesty

**Merged on main (#709 + #710):** offline Action Executor + production apply
paths + L2 calendar claim gate + docs/matrix.

**Not live-proven / not enabled:** production Calendar/CRM/Gmail/RAG flags.
Live smoke still needs staging secrets + OAuth on a smoke tenant.
