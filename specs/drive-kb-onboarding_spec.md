# Google Drive KB Onboarding — PRD

**Status:** grilled 2026-04-20, ready for issue staging
**Owner:** Aidan
**Created:** 2026-04-20
**Target tier:** All paid tiers (Free tier limited to 10 docs)
**v1 provider:** Google Drive only. Schema built on `tenant_integrations` so Dropbox/OneDrive/Box can plug in without migration.

## Goal

Tenant drops brand/FAQ/playbook docs in shared Google Drive folder → daily routine auto-pulls + compiles per-tenant KB. Kills manual KB-build step; first-touch-to-live-widget time drops from ~30min to ~5min.

## Non-goals

- Real-time sync (daily polling fine — freshness not critical)
- Dropbox, OneDrive, Box v1 (Drive first, expand on demand)
- 2-way sync (read-only from Drive)
- Translation of non-English docs (v1 assumes EN)
- Docs >5MB (skip + flag to tenant)

## Target users

- **New tenants** during onboarding — primary user
- **Existing tenants** during ongoing KB refresh (quarterly playbook update, new service)

## User stories

1. New salon owner signs up → onboarding step 3 "Connect Google Drive (optional)" → OAuth → picks folder → dashboard confirms 7 docs found → widget goes live 5min later using real brand voice.
2. Plumber-tenant drops new "2026 pricing sheet" in Drive folder → next morning's sync pulls it → widget quotes updated prices same day.
3. Tenant admin sees `KB → Drive Sync` tab showing last sync timestamp + list of docs + diff log.

## Acceptance criteria

### Frontend
- New onboarding step "Connect Google Drive (optional)"
- Dashboard `KB → Drive Sync` page with:
  - OAuth connect button
  - Folder picker (via Drive API)
  - Last sync timestamp
  - Doc list with pull status
  - Manual "sync now" button
  - Disconnect button

### Backend
- OAuth flow: redirect → Google consent → store refresh token encrypted in `tenant_integrations.oauth_token_enc`
- New routine `integration-kb-sync` running daily 07:00 UTC (3am EDT)
- For each tenant with `tenant_integrations` row where `provider='drive'` AND `enabled=true`:
  - List files in folder via Drive API
  - Compare modifiedTime to `last_synced_at`
  - Pull changed docs (PDF/Docx/GDoc/TXT/Markdown) — skip `.pages` + scanned PDFs with skip reason logged
  - Convert to markdown (pandoc for PDF/Docx; Drive export for GDoc; passthrough for TXT/MD)
  - Run PII regex scan (SSN/CC/non-tenant-domain emails); flag counts to `integration_sync_log.files_pii_flagged`; do NOT block
  - Assemble merged `.md` per tenant with `<!-- source: ... | synced: ... -->` headers per section
  - Compute SHA256 per section; compare to `kb_section_hashes`; re-embed only changed
  - Write merged `.md` to `widget/knowledge-bases/<tenant-slug>_kb.md`
  - Log summary to `integration_sync_log`
- `POST /api/kb/integrations/sync-now` endpoint (manual trigger from dashboard)
- When `enabled=true` on a `tenant_integrations` row → dashboard KB edit UI becomes read-only (Q7 D)

### Schema
New table `tenant_integrations` (multi-provider ready per Q1 B):
- `id uuid pk`
- `client_id uuid` (FK tenants) — **client_id not tenant_id**
- `provider text` — enum: `drive`, `dropbox`, `onedrive`, `box` (v1 ships `drive` only)
- `config_jsonb` — provider-specific config (e.g. `{folder_id: "...", folder_name: "..."}`)
- `oauth_token_enc bytea` — encrypted via pgcrypto
- `oauth_refresh_token_enc bytea`
- `oauth_expires_at timestamptz`
- `enabled bool default true`
- `last_synced_at timestamptz`
- `last_sync_status text` — `ok`, `error`, `partial`
- `created_at timestamptz default now()`
- `updated_at timestamptz default now()`
- unique (client_id, provider) — one integration per provider per tenant

New table `integration_sync_log`:
- `id uuid pk`
- `client_id uuid` (FK) — **client_id not tenant_id**
- `integration_id uuid` (FK tenant_integrations)
- `provider text`
- `synced_at timestamptz`
- `files_added int`
- `files_updated int`
- `files_skipped int`
- `files_pii_flagged int` — per Q9 D (regex PII scan)
- `sections_reembedded int` — per Q8 B (diff-based)
- `sections_skipped int` — unchanged sections
- `error text nullable`

New table `kb_section_hashes`:
- `client_id uuid` (FK)
- `section_id text` — stable ID per section (file_name + section_anchor)
- `content_sha256 text` — drives re-embed decision (Q8 B)
- `embedded_at timestamptz`
- pk (client_id, section_id)

### Security
- OAuth tokens encrypted via Supabase `pgcrypto`
- Service account NOT used (each tenant = own OAuth) — prevents cross-tenant leak
- RLS: tenant only sees own sync log
- Refresh token rotation handled via Google API refresh cycle
- Per-tenant scope limited: `drive.readonly` on picked folder ONLY

## Success metrics

- 40% new paid tenants connect Drive during onboarding
- Time-to-first-complete-KB: 30min → 5min
- KB freshness: avg age of KB entries drops 30 days → 3 days
- Zero cross-tenant doc leaks (security invariant)

## Risks

| Risk | Mitigation |
|---|---|
| OAuth token expiry breaks sync silently | Alerting on 3 consecutive sync failures |
| Private doc shared accidentally | OAuth scope limited to picked folder + tenant owns consent |
| Folder size blows up (500+ docs) | Per-tenant limit by tier (Free: 10, Growth: 100, Pro: unlimited) |
| Google API rate limits | Exponential backoff + batch requests |
| Doc format edge cases (scanned PDFs, images) | Skip + log; OCR v2 |
| Encryption key rotation breaks reads | Document key-rotation runbook |

## Dependencies

- Migration NNN for 3 new tables (`tenant_integrations`, `integration_sync_log`, `kb_section_hashes`)
- Supabase `pgcrypto` extension (check already enabled)
- Google Cloud project with OAuth app + client_id/secret
- Environment vars: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, `KB_ENCRYPTION_KEY` (for pgcrypto)
- New backend routine `integration-kb-sync` — daily 07:00 UTC
- Doc conversion: `pypandoc` (PDF/Docx) + Drive API export (GDoc) + passthrough (TXT/MD)
- KB compile skill already exists: `.claude/skills/kb-compile/SKILL.md`

## Resolved decisions (grill-me 2026-04-20)

1. **Provider strategy:** v1 Drive only, `tenant_integrations` multi-provider schema ready for Dropbox/OneDrive/Box without migration (option B)
2. **Free tier:** 10-doc limit preserved (option B) — acquisition hook
3. **Sync cadence:** daily 07:00 UTC fixed + manual "sync now" button (option C)
4. **Doc format v1:** PDF + Docx + GDoc + TXT + Markdown; `.pages` + scanned-image PDF → OCR v2 (option D)
5. **KB format:** single merged `.md` per tenant + per-section source header (`<!-- source: drive/foo.pdf | synced: YYYY-MM-DD -->`) (option C)
6. **Auth:** OAuth-only, no service-account fallback (option A) — per-tenant isolation, no cross-tenant leak risk
7. **Sync conflict:** dashboard KB locked read-only when Drive sync enabled (option D) — Drive is source of truth
8. **Embeddings cost:** diff-based, SHA256 per section, re-embed only changed (option B) — ~10x cost savings at 100+ tenants
9. **PII handling:** regex pre-filter (SSN/CC/non-tenant-domain emails) + dashboard flag, don't block (option D)

## Rollout

1. Migration + schema + encryption
2. Google OAuth app registered + credentials stored
3. Backend OAuth callback + token exchange
4. Drive API client + file listing + download
5. Doc conversion pipeline
6. Routine creation via `/schedule`
7. Manual sync endpoint
8. Dashboard UI (connect flow + sync log + manual trigger)
9. Pilot: 5 tenants, 2 weeks, monitor failures
10. Onboarding integration (step 3)
11. GA

## Skipped scope

- OCR of scanned PDFs (v2)
- Translation / multi-language (v2)
- Dropbox / Box / OneDrive (v1.1+)
- Real-time webhooks (Drive pushes on change) — v2 if polling costs get high
- Sharing diff notifications to tenant email (v1.1)
