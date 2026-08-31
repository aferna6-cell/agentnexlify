# M8 Confidence Gate — 20260831T205413Z

**Confidence: 76%** (PKCE fix live + staging healthy + fresh PKCE-free URLs + browser session found but Google step-up blocked consent; live Calendar+Gmail proof still missing)

**Verdict: HOLD** — not COMPLETE

## Re-check (20260831T205413Z UTC)

| Check | Result |
|-------|--------|
| Staging deploy | **SUCCESS** `b4810ef4…` (PKCE fix `dfa358d` lineage still live) |
| Health | `ok` / supabase connected |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T205034Z`, expire `2026-08-31T21:50:34+00:00`) |
| API status | `google/status.connected=False`, `gmail/status.connected=False` |
| DB `integrations` / `tenant_integrations` | **0 / 0** rows (entire staging DB) |
| Railway HTTP after PKCE deploy | **0** `/google/callback` or `/gmail/callback` hits |
| Credential hunt | No Google password / refresh token in `.env.staging`, env, Railway variable *values* (names only via MCP), or audits |
| Browser OAuth attempt | Chrome Profile session for `aidanfernandes31@gmail.com` found; Calendar consent hit **device step-up** (“Open the Gmail app on Apple iPhone 17”, code 28). Clemson account shows **Signed out**. Cannot complete without human phone approve or password. |

## Why still HOLD

Prior consent at **20:17Z** hit pre-PKCE deploy → both callbacks **400**. PKCE fix live since **20:21Z**. Agent reminted URLs and attempted interactive consent via logged-in Chrome session; Google required phone confirmation. Still zero successful callbacks / integration rows.

Without live Calendar+Gmail connected proof + passing `calendar,gmail,agent_os_e2e` smoke, M8 COMPLETE maxes ~76–80%.

## Human next step

1. On a device that can pass Google verification for the harmless test account, open Calendar URL in `audits/artifacts/m8-oauth-owner-urls.md` (also below).
2. Finish consent → staging **Connected** HTML.
3. Repeat for Gmail.
4. Reply `both connected`.

**Do not start M9.** Production M8 flags remain OFF.

## Fresh URLs (minted 20260831T205034Z)

### Calendar
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgoogle%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTMwMzR9.SFQX59ZKUXjCSKUzsCTw_JhStpvzaEVtMYyzIXkpZIY&access_type=offline&include_granted_scopes=true&prompt=consent

### Gmail
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgmail%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTMwMzR9.SFQX59ZKUXjCSKUzsCTw_JhStpvzaEVtMYyzIXkpZIY&access_type=offline&include_granted_scopes=true&prompt=consent
