# Widget Workspace
<!-- Last updated: 2026-03-31 -->

Multi-tenant widget management. Each tenant gets their own knowledge base, embed config, smoke tests, and analytics.

## What Happens Here

- Knowledge base management per tenant (what the AI knows about their business)
- Embed configuration per tenant (styling, placement, behavior)
- Smoke test prompt management (QA for AI response quality)
- Widget rule refinements based on real conversation data

## Critical Rule

Widget JS must be **identical** in two locations:
- `widget/agentnexlify-widget.js`
- `frontend/public/widget/agentnexlify-widget.js`

If you change one, change the other. Always.

## Tenants

| Tenant | Status | Notes |
|--------|--------|-------|
| MTOptions | Live (since 2026-03-28) | 88+ conversations, options trading alerts |
| OptionRun | Prepared, TBD | KB ready, not deployed |

## Folders

- `/widget/knowledge-bases` — Per-tenant knowledge base markdown files (`tenant-name_kb.md`)
- `/widget/embed-configs` — Per-tenant widget styling and behavior settings (`tenant-name_embed-config.md`)
- `/widget/test-prompts` — Per-tenant smoke test scripts (`tenant-name_smoke-tests.md`)
- `/widget/analytics` — Conversation quality reviews, metrics

## Naming

- Knowledge bases: `tenant-name_kb.md`
- Test prompts: `tenant-name_smoke-tests.md`
- Embed configs: `tenant-name_embed-config.md`

## Process

1. Update knowledge base when tenant's service details change
2. Re-run smoke tests after any knowledge base update
3. Review conversation analytics weekly to find gaps
4. Update knowledge base to fill gaps found in reviews
5. Never deploy a knowledge base update without passing all 5 smoke tests

## Technical Notes

- Widget config fetched via `/api/widget/config/{api_key}` — 5-min TTL cache per backend worker
- Widget chat goes to `/api/widget/chat` — requires valid `api_key`
- Teaser bubble config field currently missing from DB and widget config page (Phase A fix)
- CORS in `backend/main.py` controls which domains can embed the widget
