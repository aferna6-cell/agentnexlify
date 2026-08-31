# M8 Confidence Gate — 20260831T203611Z

**Verdict: HOLD — not COMPLETE**  
**Confidence: 76%** (PKCE fix live + staging healthy; live Calendar+Gmail proof still missing)

## Verified this pass (20260831T203611Z)

| Check | Result |
|-------|--------|
| Staging deploy | **SUCCESS** `0cac82cf…` on `86309f7` (includes `dfa358d` PKCE disable) |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T203534Z`, expire `2026-08-31T21:35:34Z`) |
| API status | `google/status.connected=False`, `gmail/status.connected=False` |
| DB `tenant_integrations` for smoke tenant | **0 rows** (table total also 0) |
| Railway logs after PKCE deploy | **0 callback hits** (only status + auth mint) |
| Production M8 flags | **OFF** |

## Why not COMPLETE

Prior consent at **20:17Z** hit pre-PKCE deploy (`a472c19`) → both callbacks **400**. PKCE fix has been live since **20:21Z**, but the owner has **not** completed a new consent against the fixed deploy (still zero `/google/callback` or `/gmail/callback` traffic).

Credential/PKCE plumbing alone cannot reach ≥90% without live Calendar+Gmail suite proof.

## Owner unblock (required for ≥90% / COMPLETE)

1. Open the **Calendar** auth URL below (also in `audits/artifacts/m8-oauth-owner-urls.md`).
2. Complete Google consent → expect Connected page (not 400).
3. Repeat for **Gmail**.
4. Tell the agent to re-run:

```bash
set -a && source /workspace/.env.staging && set +a
export M8_SMOKE_API_BASE=https://agentnexlify-staging.up.railway.app
export M8_SMOKE_CLIENT_ID=7451537b-a694-4c31-83b0-1b804df3d757
M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e PYTHONPATH=/workspace \
  python3 scripts/m8_live_smoke.py
```

## Production

M8 flags remain **OFF**. Do **not** start Milestone 9.
