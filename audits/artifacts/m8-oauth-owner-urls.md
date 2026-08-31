# M8 OAuth owner URLs (staging smoke tenant)

Minted: `20260831T215117Z`  
Tenant: `7451537b-a694-4c31-83b0-1b804df3d757`  
PKCE: calendar=`False` gmail=`False`  
State expires: `2026-08-31T22:51:36+00:00` (≈60 minutes from mint)  
Google probe: calendar={'status': 200, 'final_host': 'accounts.google.com'} gmail={'status': 200, 'final_host': 'accounts.google.com'}

## Do this now (order matters)

1. Open the **Calendar** URL below in a browser already signed into the **harmless Google test account**.
2. Complete consent **including Google phone step-up on your device** until you land on staging **Connected** HTML (not a 400 "Failed to exchange authorization code").
3. Open the **Gmail** URL below and complete consent the same way.
4. Reply in the agent thread: `both connected` (or paste status). Agent will run:
   `M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e`.

**Success check (optional, before reply):** after consent, staging APIs should show `connected=true` for both google and gmail status endpoints.

**Do not** use production. **Do not** start M9. **Do not** ask the agent to burn another long computerUse session on the same device step-up unless step-up is already cleared.

## Calendar (Google Calendar)

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgoogle%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTY2OTZ9.8x1lFNBGFXSRAJufVj0qFwXGVTQhmlBL9V0prf0WSF4&access_type=offline&include_granted_scopes=true&prompt=consent

## Gmail

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgmail%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTY2OTZ9.8x1lFNBGFXSRAJufVj0qFwXGVTQhmlBL9V0prf0WSF4&access_type=offline&include_granted_scopes=true&prompt=consent
