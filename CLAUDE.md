# AgentNexLiFy — CLAUDE.md

AI-powered business automation platform. Chat widget captures leads, books appointments, and automates follow-ups for small businesses.

## Critical Rules
- NEVER use `from __future__ import annotations` in any Python file — it breaks FastAPI
- NEVER use localStorage in React artifacts
- Always use `client_id` (not `tenant_id`) when querying the `leads` table
- Always use `status` (not `lead_stage`) for lead status in the `leads` table
- Widget JS must be identical in widget/ AND frontend/public/widget/
- All new pip packages need `--break-system-packages` flag
- NEVER commit .env files or log secret values
- Database schema changes ONLY via numbered migration files in migrations/

### Claude API Model IDs
Valid model IDs (March 2026): claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001. NEVER use a model ID not on this list. If Anthropic releases new models, update this list AFTER verifying the ID works.

### Migration Discipline
Migration SQL files do NOT auto-apply. After creating a migration, it must be manually run in the Supabase SQL editor. Always flag new migrations in commit messages.

## Tech Stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React, Vite, Tailwind-style CSS, Recharts
- Database: Supabase (PostgreSQL with RLS)
- AI: Anthropic Claude API (claude-sonnet-4-6)
- Email: Resend (noreply@agentnexlify.com)
- SMS: Twilio
- Payments: Stripe
- Hosting: Railway (backend), Vercel (frontend)

## Architecture

```
Browser → Chat Widget (embedded JS) → FastAPI /api/chat → Claude API
                                     → Supabase (messages, leads, appointments)
                                     → Twilio (SMS notifications)

Dashboard (React/Vite) → FastAPI /api/* → Supabase
```

Widget is tenant-scoped. Every request carries a tenant/client ID. Multi-tenant from day one.

## Key Directories
- `backend/` — FastAPI service (`main.py`, `routers/` with 25 files, `services/` for business logic)
- `frontend/` — React/Vite dashboard (`src/pages/`, `src/utils/api.js`)
- `widget/` + `frontend/public/widget/` — Embeddable chat widget (must be identical)
- `migrations/` — SQL migration files (001–031)
- `docs/dev-knowledge/` — Knowledge base (bug-patterns.md, schema-log.md, architecture-decisions.md)
- `_archive/`, `landing-page-v2/`, `public/` — Legacy (do not touch)

## Common Commands
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Backend dev: `uvicorn backend.main:app --reload --port 8000`
- Backend run: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Demo platform: `cd demo-platform && npm start`
- Install git hooks: `bash scripts/install-hooks.sh`

## Database Schema (Key Tables)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| tenants | Core accounts/billing | id, business_name, owner_email, plan, plan_status, stripe_customer_id, password_hash, owner_name, business_slug |
| widget_configs | Chat widget customization | tenant_id, api_key, bot_name, primary_color, greeting_message, position, branding (JSONB), booking_enabled, is_online |
| leads | Lead records | client_id (FK→tenants), name, email, phone, status, lead_score, lead_temperature, service_interest, tags (TEXT[]) |
| chat_messages | Canonical message store | tenant_id, session_id, role, content, created_at |
| conversations | Chat conversation container (legacy) | tenant_id, session_id, messages (JSONB), lead_id |
| appointments | Booked slots | tenant_id, lead_id, customer_name, start_time, end_time, status, google_event_id, recurrence_rule, recurrence_parent_id |
| business_hours | Availability config | tenant_id, timezone, hours (JSONB), slot_duration_minutes |
| automation_sequences | Multi-step email series | tenant_id, name, trigger_event, is_active |
| automation_steps | Steps in a sequence | sequence_id, step_order, delay_minutes, action_type |
| automation_executions | Lead progress through sequence | sequence_id, lead_id, tenant_id, current_step, status |
| automations | Simple automation rules | tenant_id, type, name, is_enabled, config (JSONB) |
| faq_entries | FAQ database | tenant_id, question, answer, category |
| activity_log | CRM interaction tracking | tenant_id, lead_id, activity_type, description |
| client_notes | Manual CRM notes | tenant_id, lead_id, content |
| integrations | OAuth tokens (Google Cal) | tenant_id, provider, access_token, refresh_token |
| team_members | Multi-user support | tenant_id, email, name, role, password_hash |
| webhooks | Outbound webhook defs | tenant_id, name, url, events, is_active |
| webhook_logs | Webhook audit trail | webhook_id, event, payload, success |
| email_templates | Reusable email template library | tenant_id, name, category, subject_template, body_template, is_shared |
| reviews | Reputation manager | tenant_id, platform, author_name, rating, review_text, ai_draft_response, owner_response, responded |
| support_messages | Contact form submissions | name, email, message |
| website_content | Crawled website data for AI | tenant_id, url, pages_json (JSONB), extracted_text, crawl_status, pages_found, crawled_at |
| content_items | Content Studio | tenant_id, title, source_text, platform_versions (JSONB), status, scheduled_for |
| email_events | Email open tracking | tenant_id, lead_id, event_type, execution_id |
| ai_feedback | Chat AI response ratings | tenant_id, session_id, message_index, rating, correction |
| menu_items | Restaurant menu | tenant_id, name, description, price, category, available, sort_order |
| orders | Restaurant orders | tenant_id, session_id, customer_name, items_json, total, order_type, status |
| jobs | Job board postings | tenant_id, title, description, pay_range, schedule, location, skills, is_active |
| job_applications | Job applicants | job_id, tenant_id, applicant_name, applicant_phone, message, status |
| tenant_tag_definitions | AI conversation auto-categorization tags | tenant_id, tag_name, tag_color, is_system, is_enabled |
| action_items | AI-extracted tasks from conversations | tenant_id, conversation_id, lead_id, description, due_date, priority, status, assigned_to |
| conversation_notes | Internal team notes on conversations | conversation_id, tenant_id, author_id, content |
| snippets | Quick reply templates for team conversations | tenant_id, title, content, shortcut, category, usage_count |
| response_metrics | Conversation response time tracking | tenant_id, conversation_id, response_time_seconds, channel, outcome |

> Always verify against live schema — this table may be outdated.

## Plan Names
- free, growth ($199), professional ($399), enterprise ($799)
- Old names (DO NOT USE): foundation, operations

## Schema Discipline
ALWAYS check the actual Supabase schema before writing queries. Known past issues:
- `client_id` is correct for leads table (NOT `tenant_id`)
- `status` is correct for lead status (NOT `lead_stage`)
- Foreign keys pointing to renamed/dropped tables
- `password_hash` and `owner_name` added in migration 002

Before writing any database query, verify the column exists. When creating a migration, check it doesn't conflict with existing schema.

## Python/FastAPI Gotchas
- Never use `from __future__ import annotations` in files with FastAPI route handlers — breaks Pydantic model resolution, causes 422 errors
- Always use explicit Pydantic model classes for request bodies, not inline parameters
- CORS is configured in main.py — if widget stops working on external sites, check CORS first
- Production runs with 4 Uvicorn workers — in-memory state is per-process only

## Frontend Patterns
- Dashboard uses a dark theme — match it for any new components
- Plan/subscription data must come from live API calls, never stale JWT claims
- Empty states should be helpful with CTAs, not just "0" or "No data"

## Skills & Agents

Skills in `.claude/skills/`: **schema-guard**, **debug-api**, **feature-build**, **widget-test**, **team-orchestration**. Also `.codex/skills/` for repo-native skills.

Agents in `.claude/agents/`: **schema-guardian**, **backend-dev**, **frontend-dev**, **widget-specialist**, **qa-tester**, **devops**. Use `/delegate` to plan delegation. Agents communicate via `.claude/agent-comms/`.

**Delegation order:** schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester. Before deploy: qa-tester + devops in parallel.

## Workflow Commands

High-level commands that orchestrate the full agent pipeline:

| Command | What It Does |
|---------|-------------|
| `/new-feature` | Schema → Backend → Frontend → QA → Commit (chains all relevant agents) |
| `/fix-bug` | Check known patterns → Diagnose → Fix → Verify → Document → Commit |
| `/deploy` | QA + DevOps in parallel → Fix blockers → Final gate |
| `/refactor` | Analyze → Plan → Execute incrementally → Verify → Commit |
| `/checkpoint` | Save current session state to disk (survives compaction) |
| `/recover` | Restore context after compaction or session restart |
| `/summary` | Generate a comprehensive change summary with metrics and health check |
| `/script` | Generate a client-ready demo script based on what's actually built |

## Context Management

Long sessions lose context when compaction happens. To prevent this:

1. **Run `/checkpoint` before big tasks** — saves state to disk
2. **Run `/checkpoint` when context feels heavy** — saves state before auto-compaction triggers
3. **If context was lost, run `/recover`** — reads checkpoint + agent outputs + git state
4. **Delegate heavy work to agents** — they use their own context windows, keeping yours clean
5. **Use `/compact` manually at natural breakpoints** with specific instructions: `/compact preserve the feature we're building and the agent outputs`
6. **Run `/clear` between unrelated tasks** — don't let old context pollute new work

## Automation

This repo has automated safety checks:
- **Pre-commit hook** — blocks commits containing secrets, dangerous imports, or bare except blocks
- **Pre-push hook** — runs frontend build check and schema consistency check before pushing
- **GitHub Actions** — daily health check, PR validation, auto bug logging on fix commits, daily AI auto-improve
- **Claude Code hooks** — pre-edit warns on sensitive files, post-edit scans for dangerous patterns, notification on agent completion, auto-checkpoint before compaction

See docs/ai-development.md for full details.

## Daily Routine

Automated via Task Scheduler: 8 AM morning (`scripts/daily/morning-auto.sh`), 8 PM evening (`scripts/daily/evening-auto.sh`). Both write to `docs/` only. Interactive: `/morning`, `/evening`. Details: `docs/scheduled-routines.md`.

## Workflows

**New API endpoint:** Check existing routers → schema-guard → Pydantic model → route → register in main.py
**New dashboard page:** Create in `frontend/src/pages/` → dark theme → live API data → helpful empty states → sidebar link
**Database migration:** Next numbered file in `migrations/` (after 037) → test in Supabase SQL editor → run on prod → update Pydantic models

## Knowledge Base

`docs/dev-knowledge/`: bug-patterns.md, schema-log.md, architecture-decisions.md. Always update after fixing bugs or changing schema.
