# M8 Confidence Gate — 20260831T203219Z

**Verdict: HOLD — not COMPLETE**  
**Confidence: 76%** (PKCE fix live + step3/local green; live Calendar+Gmail proof still missing)

## Verified this pass

| Check | Result |
|-------|--------|
| Step-3 `m8_verify_staging_step3.py` | **PASS** |
| Staging deploy | **SUCCESS** `4e92d059…` on `db5f04b` (includes `dfa358d` PKCE disable) |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T203055Z`) |
| API status | `google/status.connected=False`, `gmail/status.connected=False` |
| DB integrations for smoke tenant | **0 rows** |
| Railway logs after PKCE deploy | **0 callback hits** (only auth mint + status) |
| Local PKCE/oauth tests | **14 passed** |
| Production M8 flags | **OFF** |

## Why not COMPLETE

Prior consent at **20:17Z** hit pre-PKCE deploy (`a472c19`) → both callbacks **400**. PKCE fix has been live since **20:21Z**, but the owner has **not** completed a new consent against the fixed deploy (no callback traffic).

Credential/PKCE plumbing alone cannot reach ≥90% without live Calendar+Gmail suite proof.

## Owner unblock (required for ≥90% / COMPLETE)

1. Open the **Calendar** auth URL from the agent final message (or `/tmp/m8-oauth-auth-urls-private.json`).
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
