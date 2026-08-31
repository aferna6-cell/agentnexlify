# M8 OAuth owner URLs (staging smoke tenant)

Minted: `20260831T203909Z`  
Tenant: `7451537b-a694-4c31-83b0-1b804df3d757`  
PKCE: calendar=`False` gmail=`False`  
State expires: `2026-08-31T21:39:09+00:00` (≈60 minutes from mint)  
Google probe: both URLs redirect to Google sign-in (redirect_uri accepted)

## Do this now (order matters)

1. Open **Calendar** URL below in a browser already signed into the **harmless Google test account**.
2. Click Allow / Continue until you land on staging **Connected** HTML (not a 400 "Failed to exchange authorization code").
3. Open **Gmail** URL below and complete consent the same way.
4. Reply in the agent thread: `both connected` (or paste status). Agent will run:
   `M8_SMOKE_SUITES=calendar,gmail,agent_os_e2e`.

**Success check (optional, before reply):** after consent, staging APIs should show `connected=true` for both google and gmail status endpoints.

**Do not** use production. **Do not** start M9.

## Calendar (Google Calendar)

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgoogle%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.events+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTIzNDl9.BwiKNH387oTFwieziG3oegoo2EiODTMzJ9fguHTBsHg&access_type=offline&include_granted_scopes=true&prompt=consent

## Gmail

https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=1031969590686-ipmp1e4ob8463gv1pvnu0u98b6urm3ra.apps.googleusercontent.com&redirect_uri=https%3A%2F%2Fagentnexlify-staging.up.railway.app%2Fapi%2Fv1%2Fintegrations%2Fgmail%2Fcallback&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.modify&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiI3NDUxNTM3Yi1hNjk0LTRjMzEtODNiMC0xYjgwNGRmM2Q3NTciLCJleHAiOjE3ODgyMTIzNDl9.BwiKNH387oTFwieziG3oegoo2EiODTMzJ9fguHTBsHg&access_type=offline&include_granted_scopes=true&prompt=consent
