# M8 Confidence Gate — 20260831T215823Z

**Confidence: 76%** (PKCE fix live + staging healthy + fresh PKCE-free URLs; live Calendar+Gmail still missing — Google phone step-up not cleared)

**Verdict: HOLD** — not COMPLETE

## Re-check (20260831T215823Z UTC)

| Check | Result |
|-------|--------|
| Staging deploy | **SUCCESS** `a391e32b…` (commit `e277f78`, started 21:56:09Z) |
| Health | `ok` / supabase connected |
| `GET .../google/status` | `connected=false` |
| `GET .../gmail/status` | `connected=false` |
| DB `integrations` | **0** rows (calendar/gmail empty) |
| DB `tenant_integrations` | **0** rows |
| Railway HTTP since 21:55Z | **0** `/google/callback` or `/gmail/callback` hits |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T215823Z`, expire `2026-08-31T22:58:24+00:00`) |
| Prod M8 flags | all absent (OFF) |

## Why still HOLD

Owner may have approved the phone prompt since ~20:52Z, but staging shows **no callback** and **no integration rows** since 21:55Z. Without live Calendar+Gmail connected proof + passing `calendar,gmail,agent_os_e2e` smoke, M8 COMPLETE stays ~76%.

## Human next step

1. On a device that can pass Google verification for the harmless test account, open **Calendar** URL below (also in `audits/artifacts/m8-oauth-owner-urls.md`).
2. Finish consent **including any Google phone step-up** → staging **Connected** HTML.
3. Repeat for **Gmail**.
4. Reply `both connected`.

Then agent runs: `M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e`.

**Do not:** computerUse against same step-up · start M9 · enable prod M8 flags.

## Fresh URLs (minted 20260831T215823Z)

### Calendar
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgoogle%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTcxMDR9.6bDuMGscQ_ar0ypN8hCHVXyPfFwnk9_IIfdI_X5wo20&access_type=offline&include_granted_scopes=true&prompt=consent

### Gmail
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgmail%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTcxMDR9.6bDuMGscQ_ar0ypN8hCHVXyPfFwnk9_IIfdI_X5wo20&access_type=offline&include_granted_scopes=true&prompt=consent
