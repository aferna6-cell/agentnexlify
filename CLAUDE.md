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

## Tech Stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React, Vite, Tailwind-style CSS, Recharts
- Database: Supabase (PostgreSQL with RLS)
- AI: Anthropic Claude API (claude-sonnet-4-5-20250514)
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
- `backend/` — FastAPI service. Main app in `backend/main.py`
- `backend/routers/` — API endpoints (16 router files: analytics, appointments, auth, automations, billing, business_page, clients, integrations, leads, sequences, sms, stripe_webhooks, support, team, webhooks, widget)
- `backend/services/` — Business logic (automation, email, SMS, scoring, booking, conversation)
- `frontend/` — React/Vite app (dashboard + public pages)
- `frontend/src/pages/` — React page components
- `frontend/src/utils/api.js` — All API call functions
- `widget/` — Production widget bundle (embeddable JS)
- `frontend/public/widget/` — Widget mirror (must match widget/)
- `migrations/` — SQL migration files (001–013)
- `ai/` — Autonomous development runtime (skill engine, memory, auto-improve)
- `skills/` — Generated skills workspace
- `.codex/skills/` — Repository-native skills (schema-guard, surface-selector, widget-integrity, runtime-constraints)
- `demo-platform/` — Separate demo/sales app (isolated from production)
- `landing-page-v2/`, `public/` — Older frontend lines (do not touch unless explicitly requested)
- `_archive/` — Retired code (reference only)
- `prospects/` — Prospecting/import utilities (not runtime code)
- `docs/` — Documentation and AI development system docs
- `docs/dev-knowledge/` — Persistent knowledge base (bug patterns, schema log, architecture decisions)

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
| widget_configs | Chat widget customization | tenant_id, api_key, bot_name, primary_color, greeting_message, position, branding (JSONB), booking_enabled |
| leads | Lead records | client_id (FK→tenants), name, email, phone, status, lead_score, lead_temperature, service_interest |
| chat_messages | Canonical message store | tenant_id, session_id, role, content, created_at |
| conversations | Chat conversation container (legacy) | tenant_id, session_id, messages (JSONB), lead_id |
| appointments | Booked slots | tenant_id, lead_id, customer_name, start_time, end_time, status, google_event_id |
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
| support_messages | Contact form submissions | name, email, message |

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

## What NOT to Touch
- .env files — never commit, never log values
- Stripe webhook secret — only set via Railway env vars
- API_SECRET_KEY — must be persistent on Railway, not regenerated per deploy
- Database schema — only modify via numbered migration files in migrations/

## Skills

Claude Code has project-specific skills in .claude/skills/. Use them:
- **schema-guard** — before any database work
- **debug-api** — when diagnosing API errors
- **feature-build** — when building new features
- **widget-test** — when testing or modifying the chat widget
- **team-orchestration** — when delegating complex tasks to the agent team

Repository-native skills also exist in .codex/skills/ (surface-selector, schema-guard, widget-integrity, runtime-constraints).

## Agent Team

This repo has a team of specialized agents in `.claude/agents/`. For complex tasks, use the team-orchestration skill or `/delegate` command to plan delegation.

| Agent | Purpose |
|-------|---------|
| schema-guardian | Database schema validation and migration design |
| backend-dev | FastAPI endpoints, Pydantic models, backend logic |
| frontend-dev | React/Vite dashboard pages and components |
| widget-specialist | Embeddable chat widget, CORS, embedding |
| qa-tester | Testing, validation, bug detection |
| devops | Deployment, CI/CD, infrastructure |

### Delegation Rules
1. **Database work** → Always run schema-guardian BEFORE backend-dev
2. **After any code changes** → Run qa-tester to validate
3. **Full-stack features** → schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester
4. **Before deploy** → Run qa-tester + devops in parallel
5. **Simple tasks** → Just do them directly, don't over-delegate

Agents communicate via `.claude/agent-comms/`. When chaining agents, read prior output and pass context in the delegation prompt.

## Automation

This repo has automated safety checks:
- **Pre-commit hook** — blocks commits containing secrets, dangerous imports, or bare except blocks
- **Pre-push hook** — runs frontend build check and schema consistency check before pushing
- **GitHub Actions** — daily health check, PR validation, auto bug logging on fix commits, daily AI auto-improve
- **Claude Code hooks** — pre-edit warns on sensitive files, post-edit scans for dangerous patterns

See docs/ai-development.md for full details.

## Daily Routine (Automated)

Morning and evening routines run automatically via Windows Task Scheduler using `claude -p` (headless mode).

| Time | Script | What It Does |
|------|--------|-------------|
| 8 AM weekdays | `scripts/daily/morning-auto.sh` | Health check, activity analysis, task generation, safe doc fixes, daily log |
| 8 PM weekdays | `scripts/daily/evening-auto.sh` | Commit review, knowledge base updates, task backlog update, tomorrow prep |

Both routines can ONLY write to `docs/` — they cannot modify application code, run package managers, delete files, or push to remote. Interactive versions available via `/morning` and `/evening` commands.

Setup: `powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1`
Details: See docs/scheduled-routines.md

## Workflows

### Adding a New API Endpoint
1. Check if a similar endpoint exists in backend/routers/
2. Verify all referenced DB columns exist (use schema-guard skill)
3. Create Pydantic model for request/response
4. Add route in appropriate router file
5. Register router in main.py if new file
6. Test with curl or the frontend

### Adding a New Dashboard Page
1. Create page in frontend/src/pages/
2. Match existing dark theme and component patterns
3. Use live API data, never JWT claims for display
4. Include helpful empty states
5. Add navigation link in sidebar component

### Database Migration
1. Create numbered SQL file in migrations/ (next number after 013)
2. Test in Supabase SQL editor on a test project first
3. Run on production Supabase
4. Update any Pydantic models that reference changed columns
5. Update this CLAUDE.md if table structure changes

## Memory

Development knowledge lives in docs/dev-knowledge/:
- bug-patterns.md — recurring bugs and their fixes
- schema-log.md — schema change history
- architecture-decisions.md — why things are the way they are

After fixing a non-trivial bug, append it to bug-patterns.md.
After any schema change, append it to schema-log.md.
