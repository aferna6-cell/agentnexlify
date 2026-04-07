---
name: agentnexlify-surface-selector
description: "Choose the correct AgentNexLiFy surface before editing. Use when a task touches this repository and you need to decide which directory to work in."
version: 1.0.0
origin: codex
triggers: ["where should I put this", "which directory", "surface selector", "where does this belong"]
---

# AgentNexLiFy Surface Selector

Read [`CLAUDE.md`](/home/aidan/agentnexlify/CLAUDE.md) first, then classify the task.

## Surface map
- `backend/`: production API, widget backend, automations, billing, integrations, business-page API.
- `frontend/`: production React app for marketing pages, dashboard, and public `/biz/:slug` rendering.
- `widget/`: production embed asset served by FastAPI at `/widget`.
- `demo-platform/`: demo-only app and optional local AI backend.
- `landing-page-v2/`: legacy static marketing pages.
- `public/`: older widget artifact line, not the current production widget path.
- `_archive/`: retired code and scripts for reference only.
- `migrations/`: schema history and the best clue for column names.
- `prospects/`: outbound prospecting/import tooling, not customer-facing product logic.

## When NOT to Use
- Do not use for tasks that are clearly within a single already-known surface.
- Do not use for reading files or understanding code — only for deciding WHERE the work belongs.

## Decision rules
- If the user is changing production API behavior, start in `backend/`.
- If the user is changing dashboard UX, marketing routes, or hosted public business pages, start in `frontend/`.
- If the user is changing the live website embed, start in `widget/` and verify the mirrored file in `frontend/public/widget/`.
- If the user is changing a sales demo, stay in `demo-platform/` unless they explicitly ask to port the change to production.
- Do not default to `landing-page-v2/`, `public/`, or `_archive/`. Treat those as legacy until the request proves otherwise.

## Cross-surface pairings
- Widget behavior usually spans `widget/` + `backend/routers/widget.py`.
- Hosted business pages usually span `backend/routers/business_page.py` + `frontend/src/pages/BusinessPage.jsx`.
- Dashboard features usually span `frontend/src/` + a router in `backend/routers/` + direct Supabase queries.

## Fast repo scan
- Start with `backend/main.py`, `frontend/src/main.jsx`, and `README.md`.
- Ignore `dist/` and `node_modules/` unless the user explicitly asks about built artifacts.
