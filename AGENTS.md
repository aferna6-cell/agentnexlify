# AgentNexLiFy Repository Guide

## Purpose
- Use this file to orient quickly before editing code in this repository.
- Read [`CLAUDE.md`](/home/aidan/agentnexlify/CLAUDE.md) first for project rules, then load the repo-local skills in `.codex/skills/` that match the task.

## Repo Shape
- `backend/`: the production FastAPI service. One app in [`backend/main.py`](/home/aidan/agentnexlify/backend/main.py) serves the API, mounts `/widget`, and starts the automation loop.
- `frontend/`: the primary Vite/React app. It contains public marketing routes, public business pages, and the authenticated dashboard.
- `widget/`: the production widget bundle served by the backend. This is the live embed surface.
- `demo-platform/`: a separate demo/sales app with its own optional FastAPI server. Treat it as isolated from production unless the task explicitly targets demos.
- `landing-page-v2/` and `public/`: older parallel frontend/widget lines. Do not touch them unless the request is explicitly about those surfaces or a migration away from them.
- `_archive/`: retired code and old scripts kept for reference only.
- `migrations/`: the clearest record of the live schema, but numbering is not perfectly tidy.
- `prospects/`: prospecting/import utilities and data, not product runtime code.

## Main Subsystems
- Widget chat runtime: [`backend/routers/widget.py`](/home/aidan/agentnexlify/backend/routers/widget.py) plus [`widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/widget/agentnexlify-widget.js).
- Tenant auth and dashboard API: [`backend/routers/auth.py`](/home/aidan/agentnexlify/backend/routers/auth.py).
- CRM and lead operations: [`backend/routers/clients.py`](/home/aidan/agentnexlify/backend/routers/clients.py), [`backend/routers/leads.py`](/home/aidan/agentnexlify/backend/routers/leads.py), [`backend/routers/analytics.py`](/home/aidan/agentnexlify/backend/routers/analytics.py).
- Scheduling and Google Calendar: [`backend/routers/appointments.py`](/home/aidan/agentnexlify/backend/routers/appointments.py), [`backend/routers/integrations.py`](/home/aidan/agentnexlify/backend/routers/integrations.py), [`backend/services/booking.py`](/home/aidan/agentnexlify/backend/services/booking.py).
- Automations, SMS, email: [`backend/routers/sequences.py`](/home/aidan/agentnexlify/backend/routers/sequences.py), [`backend/routers/automations.py`](/home/aidan/agentnexlify/backend/routers/automations.py), [`backend/services/automation_engine.py`](/home/aidan/agentnexlify/backend/services/automation_engine.py).
- Billing and outbound webhooks: [`backend/routers/billing.py`](/home/aidan/agentnexlify/backend/routers/billing.py), [`backend/routers/stripe_webhooks.py`](/home/aidan/agentnexlify/backend/routers/stripe_webhooks.py), [`backend/routers/webhooks.py`](/home/aidan/agentnexlify/backend/routers/webhooks.py).
- Hosted business pages: [`backend/routers/business_page.py`](/home/aidan/agentnexlify/backend/routers/business_page.py) and [`frontend/src/pages/BusinessPage.jsx`](/home/aidan/agentnexlify/frontend/src/pages/BusinessPage.jsx).

## High-Risk Invariants
- Do not add `from __future__ import annotations` to FastAPI router files. This repo already documents that it breaks request model handling.
- Auth, JWTs, and most tables use `tenant_id`; the `leads` table still uses `client_id`. Check the existing query pattern before changing lead-related code.
- Lead stage is stored in `status`, not `lead_stage`.
- The current production widget contract uses `data-api-key` and optional `data-brand-color` / `data-api-base`.
- [`widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/widget/agentnexlify-widget.js) and [`frontend/public/widget/agentnexlify-widget.js`](/home/aidan/agentnexlify/frontend/public/widget/agentnexlify-widget.js) must stay identical.
- Active chat history is stored in `chat_messages`. [`backend/services/conversation.py`](/home/aidan/agentnexlify/backend/services/conversation.py) reflects an older conversation-storage approach and should be treated as stale unless the task is explicitly reviving it.
- Current plan names are `free`, `growth`, `professional`, `enterprise`. Do not introduce older plan labels.
- Production backend runs with 4 Uvicorn workers. In-memory counters, caches, and loops are per-process only; do not treat them as globally authoritative.

## Working Rules
- Prefer source files over committed build output. Ignore `dist/` and `node_modules/` unless the task is explicitly about shipped artifacts.
- Treat audit documents (`FULL_AUDIT.md`, `PRE_LAUNCH_AUDIT.md`, `CLEANUP_REPORT.md`, `AUDIT_RESULTS.md`) as hints. Re-verify every claim in the live code before acting on it.
- When a task touches widget behavior, check both the backend widget API and the frontend/business-page embed path.
- When a task touches schema, migrations, or lead handling, load the schema guard skill before editing.
- When a task is demo-only, keep production code untouched unless the user asks for shared fixes.
- Avoid routing new work into `landing-page-v2/`, `public/`, or `_archive/` unless the task is explicitly about legacy cleanup or migration.

## Repo-Local Skills
- `agentnexlify-surface-selector`: choose the right surface or subsystem before editing.
- `agentnexlify-schema-guard`: protect live schema conventions and backend data/query invariants.
- `agentnexlify-widget-integrity`: keep the current production widget contract and mirrored assets consistent.
- `agentnexlify-runtime-constraints`: account for multi-worker runtime behavior, background jobs, and in-memory limits.

## Autonomous AI Runtime
- The autonomous development runtime lives in `ai/`.
- Generated reusable skills live in `skills/generated/`.
- The skill index lives in `skills/index.json`.
- Task memory lives in `ai/memory/`.
- For autonomous task preparation, resolution, recording, and self-improvement, use:
  - `python -m ai.skill_engine prepare "..."`
  - `python -m ai.skill_engine complete "..."`
  - `python -m ai.auto_improve --create-skills --write-report docs/ai-auto-improve-report.md --refresh-docs`

## Common Commands
- Backend dev server: `uvicorn backend.main:app --reload --port 8000`
- Frontend dev server: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Demo platform: `cd demo-platform && npm start`
- Docker stack: `docker compose up --build`
