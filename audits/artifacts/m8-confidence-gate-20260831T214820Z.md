# M8 Confidence Gate — 20260831T214820Z

**Score:** 76%  
**Verdict:** HOLD  
**Reason:** Google device step-up still blocks consent; Calendar+Gmail disconnected; zero `/callback` hits since 21:45Z

## Recheck since 21:45Z

| Check | Result |
|-------|--------|
| Staging health | ok (deployment `79766e46-06a6-45e4-b595-96dbe781bbe5` / `55f0ff2`) |
| `GET .../google/status` | `connected=false` |
| `GET .../gmail/status` | `connected=false` |
| `integrations` rows (tenant) | **0** |
| `tenant_integrations` rows | **0** |
| Railway HTTP `/google/callback` + `/gmail/callback` since 21:45Z | **0** |
| Fresh auth URLs | **no `code_challenge`** (minted `20260831T214820Z`, expire `2026-08-31T22:48:20+00:00`) |
| Prod M8 flags | all absent (OFF) |

## Owner action (required)

1. On a device that can pass Google verification for the harmless test account, open **Calendar** URL below (also in `audits/artifacts/m8-oauth-owner-urls.md`).
2. Complete consent **including phone step-up** until staging shows Connected HTML.
3. Open **Gmail** URL and complete consent the same way.
4. Reply: `both connected`

Then agent runs: `M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e`.

**Do not:** computerUse against same step-up · start M9 · enable prod M8 flags.

## Calendar

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgoogle%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTY1MDB9.ZRV3m_qvtbkfFyMkZBlBBnh5usTIlJ6vkVFrAdnmHrg&access_type=offline&include_granted_scopes=true&prompt=consent

## Gmail

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgmail%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTY1MDF9.LtkicLWla7sY22_2j6kWmuZyBXjotVkOhLbM91ByyMc&access_type=offline&include_granted_scopes=true&prompt=consent
