# Feature rollout matrix — Agent OS capabilities (2026-08-30 deploy-proof)

Distinguish **merged**, **live-proven**, and **enabled**. Do not flip all capabilities globally.

| Flag | Development | Staging | Canary | Production | Merged? | Migration ready? | Live-proven? | Staging enabled? | Canary eligible? | Production eligible? | Blocker | Rollback |
|------|-------------|---------|--------|------------|---------|------------------|--------------|------------------|------------------|----------------------|---------|----------|
| `RAG_ENABLED` | OK local | Candidate after staging env + KB | After staging soak | **OFF** | yes (#707) | **198 APPLIED** | partial (holdout + smoke-tenant retrieval; no staging HTTP) | **no** (Railway staging env missing) | **no** | **no** | No staging Railway env; Agent OS HTTP not proven | `RAG_ENABLED=0` |
| `SEND_EMAIL_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes | n/a | **no** | **no** | **no** | **no** | No gmail connector; no staging; no service key in agent | `SEND_EMAIL_ENABLED=0` |
| `CALENDAR_ACTIONS_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes (#709/#710) | n/a | **no** | **no** | **no** | **no** | Zero `google_calendar` OAuth; no staging | `CALENDAR_ACTIONS_ENABLED=0` |
| `CRM_ACTIONS_ENABLED` | optional | **OFF** | **OFF** | **OFF** | yes (#709/#710) | n/a | **no** (Action Executor) | **no** | **no** | **no** | Service key unavailable; need Action Executor + `os_tool_executions` live audit | `CRM_ACTIONS_ENABLED=0` |

## Recommended progression

1. Owner creates **Railway staging** per `docs/ops/m8-staging-setup.md` (agents cannot).
2. Connect **Google Calendar + Gmail** OAuth on smoke tenant `7451537b-…`.
3. Confirm `tenant_kb_chunks` active > 0 (currently **6** on smoke tenant).
4. Enable flags **staging-only**, run `scripts/m8_live_smoke.py` with `M8_SMOKE_API_BASE`.
5. staging → canary → production — one flag family at a time. **Not in this task.**

## Evidence

- `audits/artifacts/m8-deploy-proof-report-2026-08-30.md`
- `audits/artifacts/m8-deploy-proof-2026-08-30.json`
- `audits/artifacts/m8-live-smoke-20260830T171155Z.json`
- `audits/artifacts/m8-rag-smoke-tenant-proof.json`
- Runner: `scripts/m8_live_smoke.py`
- Staging runbook: `docs/ops/m8-staging-setup.md`

## Verdict

**MILESTONE 8 HOLD** — architecture merged; staging deploy + OAuth + Action Executor live proofs remain.
