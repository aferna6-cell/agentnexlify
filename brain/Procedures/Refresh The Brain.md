---
type: procedure
name: "Refresh The Brain"
tags:
  - procedure
  - maintenance
source_status: source-backed
sensitivity: normal
last_verified: 2026-06-22
---

# Refresh The Brain

## When to use
To keep this vault current as GitHub and Supabase change. There is **no always-on daemon** —
this container is ephemeral — so the brain re-syncs by running a deterministic refresh, on
demand or on a schedule.

## The update model (honest)
The vault updates when `_tools/refresh_connectors.py` runs. Three ways to run it:
1. **On a schedule where the vault lives** — once the vault is in its own repo (persistence
   decision pending), add a cron or **GitHub Action** that runs the script daily and commits
   the refreshed `Sources/connector-*.md` + `state.json` + `INGESTION-LOG.md`.
2. **Manually** — run it locally with creds set (below).
3. **In a Claude session** — ask Claude to re-run the connector smoke pass + re-validate; Claude
   regenerates the connector traces and any affected canonical notes.

## Steps (script)
```bash
export GITHUB_TOKEN=...            # repo:read on aferna6-cell/agentnexlify
export SUPABASE_ACCESS_TOKEN=...   # Supabase Management API token (sbp_...)
export SUPABASE_PROJECT_REF=pxserpybmajixqrmzaly
python3 _tools/refresh_connectors.py   # rewrites connector source traces + stamps state
python3 _tools/run_all.py              # re-validate all gates
```
The script is **read-only** against GitHub/Supabase and **never writes secret values** into the
vault — only counts, titles, and metadata. Missing creds → that connector is skipped cleanly.

## What it refreshes vs what needs Claude
- **Automatic** (script): `Sources/connector-github-issues.md`, `Sources/connector-supabase-schema.md`,
  `state.json` `last_refresh`, `INGESTION-LOG.md`.
- **Needs a Claude pass**: turning new history into canonical Decisions/Topics/Commitments
  (synthesis + entity resolution). Re-run the deep-history digest when major changes land.

## Related
- [[Autonomous Dev Operation]] · [[GitHub Activity]] · [[Local Release Gate]]

## Provenance
- [[connector-github-issues]] · [[connector-supabase-schema]]
