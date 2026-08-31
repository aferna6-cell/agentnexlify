# M8 Confidence Gate — 2026-08-31T20:27Z

**Verdict: HOLD — not COMPLETE**  
**Confidence: 74%** (credential/PKCE plumbing verified; live Calendar+Gmail proof missing)

## Verified this pass

| Check | Result |
|-------|--------|
| Step-3 `m8_verify_staging_step3.py` | **PASS** (service_role JWT, `/health`, anon RLS `[]`, smoke chunks n=5, login 200) |
| Staging deploy | **SUCCESS** `edf77734…` on `dfa358d` (PKCE disabled) |
| Fresh auth URLs (post-deploy) | **no `code_challenge`** for Calendar + Gmail |
| API status | `google/status.connected=false`, `gmail/status.connected=false` |
| DB `tenant_integrations` / `integrations` for smoke tenant | **0 rows** |
| Live smoke `calendar,gmail` | **blocked** at `provider_gate` (`m8-live-smoke-20260831T202725Z.json`) |
| Local PKCE/oauth tests | **14 passed** |

## Why not COMPLETE

Owner completed Google consent at **20:17Z**, but callbacks hit deploy **`a472c19`** (TTL fix only; PKCE still on):

- `GET …/google/callback` → **400** `Failed to exchange authorization code`
- `GET …/gmail/callback` → **400** same

Redirect URIs are confirmed working (callbacks reached staging). Token exchange failed; PKCE fix (`dfa358d`) landed at **20:21Z**. No successful post-fix consent yet.

## Owner unblock (required for ≥90% / COMPLETE)

1. Open the **fresh** PKCE-free auth URLs minted after `dfa358d` (private path `/tmp/m8-oauth-auth-urls-private.json` on the agent host, or re-mint via authenticated `GET /api/v1/integrations/google/auth` + `…/gmail/connect`).
2. Complete consent; expect Connected HTML (not 400).
3. Re-run:

```bash
set -a && source /workspace/.env.staging && set +a
export M8_SMOKE_API_BASE=https://agentnexlify-staging.up.railway.app
export M8_SMOKE_CLIENT_ID=7451537b-a694-4c31-83b0-1b804df3d757
M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e PYTHONPATH=/workspace \
  python3 scripts/m8_live_smoke.py
```

## Production

M8 flags remain **OFF**. Do **not** start Milestone 9.

## Artifacts

- `audits/artifacts/m8-confidence-gate-20260831T202724Z.json`
- `audits/artifacts/m8-live-smoke-20260831T202725Z.json`
