# M8 Confidence Gate — 20260831T204049Z

**Verdict: HOLD — not COMPLETE**  
**Confidence: 76%** (PKCE fix live + staging healthy + OAuth URLs reach Google sign-in; live Calendar+Gmail proof still missing)

## Verified this pass (20260831T204049Z)

| Check | Result |
|-------|--------|
| Staging deploy | **SUCCESS** `343e2cea…` on `088036d` (PKCE fix `dfa358d` live since 20:21Z) |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T203909Z`, expire `2026-08-31T21:39:09+00:00`) |
| Google URL probe | Both URLs → Google sign-in identifier page (redirect_uri OK) |
| API status | `google/status.connected=False`, `gmail/status.connected=False` |
| DB `tenant_integrations` for smoke tenant | **0 rows** (table total also 0) |
| Railway logs after PKCE deploy | **0 callback hits** (status + auth mint only through 20:39Z) |
| Alternate connect path | **None** — no Google refresh token / smoke Google password in `.env.staging`; computerUse MCP unavailable |
| Production M8 flags | **OFF** (flag vars absent on production service) |

## Why not COMPLETE

Prior consent at **20:17Z** hit pre-PKCE deploy (`a472c19`) → both callbacks **400**. PKCE fix live since **20:21Z**, but owner has **not** completed a new consent (still zero `/google/callback` or `/gmail/callback`).

Live provider proof is required for ≥90% / COMPLETE. Credential plumbing alone is not enough.

## Owner unblock (required)

1. Open **Calendar** auth URL in `audits/artifacts/m8-oauth-owner-urls.md` (also in agent final message).
2. Complete Google consent → expect Connected page (not 400).
3. Repeat for **Gmail**.
4. Reply `both connected` so the agent can run:

```bash
set -a && source /workspace/.env.staging && set +a
export M8_SMOKE_API_BASE=https://agentnexlify-staging.up.railway.app
export M8_SMOKE_CLIENT_ID=7451537b-a694-4c31-83b0-1b804df3d757
M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e PYTHONPATH=/workspace \
  python3 scripts/m8_live_smoke.py
```

## Production

M8 flags remain **OFF**. Do **not** start Milestone 9.
