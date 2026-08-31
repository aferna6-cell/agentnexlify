# M8 Confidence Gate — 20260831T204457Z

**Confidence: 76%** (PKCE fix live + staging healthy + OAuth URLs reach Google sign-in; live Calendar+Gmail proof still missing)

**Verdict: HOLD** — not COMPLETE

## Re-check (20260831T204457Z UTC)

| Check | Result |
|-------|--------|
| Staging deploy | **SUCCESS** `bb9e3e59…` on `beb1cb6` (PKCE fix `dfa358d` live since 20:21Z) |
| Health | `ok` / supabase connected |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T204357Z`, expire `2026-08-31T21:43:57+00:00`) |
| API status | `google/status.connected=False`, `gmail/status.connected=False` |
| DB `integrations` / `tenant_integrations` | **0 / 0** rows (entire staging DB) |
| Railway logs since 20:40Z | **0 callback hits** |
| Railway logs after PKCE deploy | **0 callback hits** (status + auth mint only) |
| Alternate connect path | **none** — Railway has `GOOGLE_CLIENT_ID`/`SECRET` names; no refresh token/password in env; no computerUse; prod integrations also 0 rows |

## Why still HOLD

Prior consent at **20:17Z** hit pre-PKCE deploy → both callbacks **400**. PKCE fix live since **20:21Z**, but owner has **not** completed a new consent (still zero `/google/callback` or `/gmail/callback`).

Without live Calendar+Gmail connected proof + passing `calendar,gmail,agent_os_e2e` smoke, M8 COMPLETE maxes ~76–80%.

## Human next step

1. Open Calendar URL in `audits/artifacts/m8-oauth-owner-urls.md` (also in agent final message).
2. Finish consent → staging **Connected** HTML.
3. Repeat for Gmail.
4. Reply `both connected`.

**Do not start M9.** Production M8 flags remain OFF.
