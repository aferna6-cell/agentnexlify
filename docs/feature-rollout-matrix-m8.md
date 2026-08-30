# Feature rollout matrix — Agent OS capabilities (2026-08-30 live-proof update)

Distinguish **merged**, **live-proven**, and **enabled**. Do not flip all capabilities globally.

| Flag | Development | Staging | Canary | Production | Merged? | Migration ready? | Live-proven? | Staging enabled? | Canary eligible? | Production eligible? | Blocker | Rollback |
|------|-------------|---------|--------|------------|---------|------------------|--------------|------------------|------------------|----------------------|---------|----------|
| `RAG_ENABLED` | OK local | Candidate after KB compile | After staging soak | **OFF** | yes (#707) | **198 APPLIED** | holdout yes; live tenant **no** (0 chunks) | **no** (Railway prod-only; flag not flipped) | not yet | **no** | Empty `tenant_kb_chunks`; no staging Railway env; need compiled KB + staging deploy | `RAG_ENABLED=0` |
| `SEND_EMAIL_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes | n/a | **no** | **no** | **no** | **no** | No gmail connector in DB; no service key in agent; owner live procedure pending | `SEND_EMAIL_ENABLED=0` |
| `CALENDAR_ACTIONS_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes (#709/#710) | n/a | **no** | **no** | **no** | **no** | Zero `google_calendar` OAuth integrations; no service key in agent | `CALENDAR_ACTIONS_ENABLED=0` |
| `CRM_ACTIONS_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes (#709/#710) | n/a | partial DB-plane only; Action Executor path **no** | **no** | **no** | **no** | Service key unavailable to agent runner; need Action Executor + `os_tool_executions` live audit | `CRM_ACTIONS_ENABLED=0` |

## Recommended progression

1. Provision **staging Railway environment** (or confirm smoke-tenant-only local runner with service key secrets injected).
2. Connect **Google Calendar + Gmail** OAuth on smoke tenant `7451537b-…`.
3. Compile/index approved KB → non-zero `tenant_kb_chunks`.
4. Run `scripts/m8_live_smoke.py` with auth env → capture artifact.
5. staging → internal/canary tenant → broader production — one flag family at a time.

## Evidence

- `audits/artifacts/m8-live-proof-report-2026-08-30.md`
- `audits/artifacts/m8-live-smoke-20260830T165228Z.json`
- Runner: `scripts/m8_live_smoke.py`
