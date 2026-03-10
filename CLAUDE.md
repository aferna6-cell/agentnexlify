# AgentNexLiFy — CLAUDE.md

## Project Overview
AgentNexLiFy is a SaaS AI business automation platform. Backend is FastAPI/Python on Railway, frontend is React/Vite on Vercel, database is Supabase (PostgreSQL).

## Critical Rules
- NEVER use `from __future__ import annotations` in any Python file — it breaks FastAPI
- NEVER use localStorage in React artifacts
- Always use `client_id` (not `tenant_id`) when querying the `leads` table
- Always use `status` (not `lead_stage`) for lead status in the `leads` table
- Widget JS must be identical in widget/ AND frontend/public/widget/
- All new pip packages need `--break-system-packages` flag

## Tech Stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React, Vite, Tailwind-style CSS, Recharts
- Database: Supabase (PostgreSQL with RLS)
- AI: Anthropic Claude API (claude-sonnet-4-5-20250514)
- Email: Resend (noreply@agentnexlify.com)
- SMS: Twilio
- Payments: Stripe
- Hosting: Railway (backend), Vercel (frontend)

## Database Schema (Key Tables)
- tenants: client_id=id, plan, plan_status, owner_email, notification_phone, sms_notifications_enabled
- leads: client_id (FK→tenants), name, email, phone, status, lead_score, lead_temperature
- chat_messages: tenant_id, session_id, role, content, created_at
- widget_configs: tenant_id, api_key, bot_name, primary_color, greeting_message, position, branding (JSONB)

## Plan Names
- free, growth ($199), professional ($399), enterprise ($799)
- Old names (DO NOT USE): foundation, operations

## Common Commands
- Frontend build: cd frontend && npm run build
- Backend run: uvicorn backend.main:app --host 0.0.0.0 --port 8000

## File Structure
- backend/routers/ — API endpoints (16 router files)
- backend/services/ — Business logic (automation, email, SMS, scoring)
- frontend/src/pages/ — React page components
- frontend/src/utils/api.js — All API call functions
- widget/ — Widget JS source
- migrations/ — SQL migration files
