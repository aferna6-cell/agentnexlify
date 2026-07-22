---
title: "Google Drive KB Onboarding — Folder Sync into the Widget Knowledge Base"
category: integrations
tags: [drive-kb, google-drive, oauth, knowledge-base, sync, pii, tenant-integrations, multi-provider, onboarding]
sources: ["specs/drive-kb-onboarding_spec.md"]
created: 2026-07-22
updated: 2026-07-22
summary: "Drive-KB lets a tenant connect one Google Drive folder as a live source for their widget knowledge base, syncing changed docs daily through an OAuth-scoped read-only connection with regex PII flagging, tier-gated document limits, and a multi-provider schema that keeps the dashboard read-only while a folder is the source of truth."
---

# Google Drive KB Onboarding — Folder Sync into the Widget Knowledge Base

Drive-KB turns a shared Google Drive folder into a self-maintaining knowledge base for the tenant's widget. A contractor drops their price lists, service menus, warranty terms, and FAQs into one Drive folder, connects it once, and the platform keeps the widget's answers in sync with those documents — new and edited files flow into the knowledge base on a daily cadence without the owner re-uploading anything. This is the low-friction on-ramp to the same per-tenant knowledge moat the rest of AgentNexLiFy is built on: the widget answers from the tenant's real documents, not a generic model guess. It closes the gap where an owner has all their business knowledge sitting in Drive already and does not want to hand-upload it file by file.

The connection is OAuth-only, `drive.readonly`, and one folder per tenant. The dashboard "Connect Google Drive" button calls `GET /api/v1/kb/integrations/drive/auth`, which returns a Google consent URL; the tenant grants read-only access, and Google redirects to `GET /api/v1/kb/integrations/drive/callback`. The callback exchanges the code, stores the tokens, and bounces the browser to `/dashboard/knowledge?drive=connected`. The tenant then picks the folder to sync (`/folders` lists candidates, `/folder` selects one and runs the first sync immediately). Because the callback always lands on the Knowledge dashboard, the connect handoff is the same whether it starts from the Knowledge page or the onboarding wizard's optional final step — the wizard hands off to Google, the tenant finishes the folder pick on the Knowledge page. The whole surface (connect, folder picker, sync-now, sync log, disconnect) lives in `backend/routers/kb_integrations.py` over `backend/services/drive_kb_sync.py`.

Sync is daily, diff-based, and fail-open. On the automation loop's daily pass, `run_drive_kb_sync_due` walks every enabled integration, compares each Drive file's `modifiedTime` against the last sync, downloads only changed files, converts them to markdown, and rebuilds the tenant's merged knowledge-base document with per-source headers. A manual "Sync now" button triggers the same routine on demand. Every sync writes an `integration_sync_log` row with counters — files added, updated, skipped, and PII-flagged — that the dashboard renders as the recent sync history. A transient Google outage or a not-yet-migrated table never raises into the loop: the sync path is wrapped fail-open so one tenant's bad sync cannot stall the others.

PII handling is advisory, never blocking. A regex scanner flags likely sensitive content in synced documents — SSN patterns, Luhn-valid credit-card numbers, and email addresses outside the tenant's own domain — and records the hit count to `integration_sync_log.files_pii_flagged`. Flagged content is still synced; the flag surfaces on the dashboard ("2 sections flagged — review in Drive") so the owner can decide whether a document belongs in a customer-facing knowledge base. The platform deliberately does not silently drop flagged content, because a false positive that quietly removed a real price list would be worse than a visible warning the owner can act on.

Document limits are tier-gated and the dashboard goes read-only while a folder is the source of truth. Free tenants sync up to 10 documents, Growth up to 100, and Pro unlimited; files beyond the tier limit are skipped and logged rather than erroring. Once a Drive folder is actively syncing, the Knowledge dashboard disables manual upload and per-document removal and shows a banner ("Knowledge is synced from Google Drive. Disconnect sync to edit documents manually.") — a manual edit would be overwritten by the next sync, so the read-only guard prevents the owner from fighting their own automation. Disconnecting the folder re-enables manual editing and keeps every already-synced document in place.

The storage model is multi-provider from day one. Drive tokens and folder selection live on a `tenant_integrations` row keyed by `provider` (`drive` today), not on Drive-specific columns bolted onto the tenants table. This is a deliberate abstraction: the sync routine dispatches by provider, so adding Dropbox, OneDrive, or Box later (see [[photo-quote]] for the same "ship one vertical at a time" discipline) is a new provider client plus an enum value, not a schema migration or a parallel sync pipeline. Those additional providers are explicitly post-GA (v1.1), gated on Drive sync holding a low error rate in production before a second provider is added — the schema is ready, the providers ship on demand.

## Key Concepts

- **OAuth `drive.readonly`** — The connection requests read-only Drive access only; the platform can list and download files in the chosen folder but never modify the tenant's Drive. Tokens are stored server-side and refreshed automatically.
- **One folder per tenant** — A tenant selects a single Drive folder as the KB source via the folder picker; `/folder` both records the choice and runs the first sync immediately.
- **Diff-based daily sync** — `run_drive_kb_sync_due` compares Drive `modifiedTime` against the last sync and downloads only changed files, so re-embedding stays cost-efficient. Manual "Sync now" runs the same routine on demand.
- **Advisory PII flagging** — A regex scan (SSN, Luhn-valid card, non-tenant-domain email) records `files_pii_flagged` per sync and surfaces it on the dashboard; flagged content is synced, not blocked.
- **Read-only-when-synced** — While a Drive folder is the active source, the Knowledge dashboard disables manual upload/remove and shows a banner; disconnecting restores manual editing and keeps synced docs.
- **Multi-provider schema** — Connection state lives on `tenant_integrations` keyed by `provider`, so Dropbox/OneDrive/Box (post-GA) are a provider dispatch, not a schema change.

## Relevance to AgentNexLiFy

Drive-KB is the lowest-friction path to a populated per-tenant knowledge base, which is the platform's core moat: the widget answers from the tenant's real documents rather than a generic model. It plugs directly into the existing widget chat and photo-quote flows — every synced document is retrievable context for a chat reply — and into onboarding as an optional final step, so a new tenant can be answering customer questions from their own price lists within minutes of signup instead of hand-uploading files. Operationally it reuses the platform's daily automation loop, `client_id`/`tenant_id` scoping, and fail-open discipline, and its multi-provider schema means the "connect your docs" story extends to Dropbox and OneDrive without re-architecting. Against GoHighLevel and the other all-in-one platforms, "point us at your Drive folder and your AI learns your business" is a materially lower-friction onboarding than manual knowledge-base entry.

## Related Articles

- [[photo-quote]] — the other widget-first knowledge feature, and the same ship-one-vertical-at-a-time discipline the multi-provider roadmap follows.
