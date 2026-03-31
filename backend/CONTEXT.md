# Backend Workspace
<!-- Last updated: 2026-03-31 -->

FastAPI/Python service for the AgentNexLiFy platform. Lives in `backend/`.

## Stack

- Framework: FastAPI (Python 3.11) on Railway (project "cheerful-freedom", service "agentnexlify")
- Database: Supabase (PostgreSQL with RLS)
- Integrations: Stripe (billing), Resend (email), Twilio (SMS), Anthropic Claude API (chat AI)
- Patterns: snake_case, type hints, Pydantic models, tenant-isolated data, API keys prefixed `anx_`

## Structure

- `backend/main.py` — FastAPI app, CORS, router registration
- `backend/routers/` — 53 route files, one per feature area
- `backend/services/` — Business logic, third-party integration wrappers
- `backend/models/` — Pydantic request/response models (schemas.py)

## Critical Rules

- NEVER use `from __future__ import annotations` — breaks Pydantic model resolution in FastAPI
- ALL tenant-specific queries MUST use RLS or explicit `tenant_id` / `client_id` filtering
- Leads table uses `client_id` (not `tenant_id`), status field is `status` (not `lead_stage`)
- Conversations table uses `client_id` (not `tenant_id`)
- Always use explicit Pydantic model classes for request bodies, not inline parameters
- Production runs with 4 Uvicorn workers — in-memory state is per-process only
- Widget config + chat data uses 5-min TTL in-memory cache (per-worker)

## Workflow: New API Endpoint

1. Check existing routers — does one already exist for this feature?
2. Run `schema-guard` skill — verify columns exist before writing queries
3. Create Pydantic request/response models in `backend/models/schemas.py`
4. Add route to appropriate router file
5. Register router in `backend/main.py` if it's new
6. All endpoints must have input validation and proper error responses

## Testing

- Backend tests: `test_feature_name.py` in `tests/`
- Run `pytest` before committing
- NEVER skip security review on auth or payment endpoints

## What to Avoid

- Hardcoding tenant-specific data in shared endpoints
- Raw SQL where Supabase client methods work
- Skipping error handling on third-party API calls (Stripe, Resend, Twilio, Claude API)
- Business logic that belongs in `services/` landing in route handlers

## Known Issues

- `lead_captured` flag hardcoded to `false` — needs dynamic detection (Phase A)
- Dashboard stats showing 0 conversations — tenant_id lookup mismatch in analytics router
- `response_metrics` UUID casting error on some queries
- CORS configured in `main.py` — if widget stops working on external sites, check CORS first
