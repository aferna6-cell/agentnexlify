# Feature rollout matrix — Agent OS capabilities (2026-08-30 staging live)

| Flag | Development | Staging | Canary | Production | Merged? | Live-proven? | Staging enabled? | Canary eligible? | Production eligible? | Blocker | Rollback |
|------|-------------|---------|--------|------------|---------|--------------|------------------|------------------|----------------------|---------|----------|
| `RAG_ENABLED` | OK | **ON** | hold | **OFF** | yes | **yes** | **yes** | not yet | **no** | Need Calendar/Gmail complete for milestone COMPLETE | `RAG_ENABLED=0` |
| `CRM_ACTIONS_ENABLED` | OK | **ON** | hold | **OFF** | yes | **yes** | **yes** | not yet | **no** | Need Calendar/Gmail complete | `CRM_ACTIONS_ENABLED=0` |
| `CALENDAR_ACTIONS_ENABLED` | OK | **ON** | **OFF** | **OFF** | yes | **no** | **yes** (flag only) | **no** | **no** | No google_calendar OAuth; Google redirect URIs | `CALENDAR_ACTIONS_ENABLED=0` |
| `SEND_EMAIL_ENABLED` | OK | **ON** | **OFF** | **OFF** | yes | **no** | **yes** (flag only) | **no** | **no** | No gmail OAuth; Google redirect URIs | `SEND_EMAIL_ENABLED=0` |

## Staging identifiers

- Railway staging env: `5988ed51-6691-4497-825d-14fefff5f591`
- API: `https://agentnexlify-staging.up.railway.app`
- Supabase staging: `nohanoiugcbaxtxinttp`
- Smoke tenant: `7451537b-a694-4c31-83b0-1b804df3d757`

## Evidence

- `audits/artifacts/m8-staging-live-proof-report-2026-08-30.md`
- `audits/artifacts/m8-staging-live-proof-2026-08-30.json`
- `audits/artifacts/m8-live-smoke-20260830T230857Z.json`

## Verdict

**MILESTONE 8 HOLD** — RAG + CRM staging live-proven; Calendar + Gmail blocked on Google OAuth.
