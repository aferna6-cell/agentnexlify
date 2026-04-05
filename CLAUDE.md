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
Migration SQL files do NOT auto-apply. After creating a migration, apply it via Supabase MCP (`mcp__supabase__apply_migration`) or the Supabase SQL editor. Always flag new migrations in commit messages and update schema-log.md.

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
- `backend/` — FastAPI service (`main.py`, `routers/` with 53 files, `services/` for business logic)
- `frontend/` — React/Vite dashboard (`src/pages/`, `src/utils/api.js`)
- `widget/` + `frontend/public/widget/` — Embeddable chat widget (must be identical)
- `migrations/` — SQL migration files (001–064, some duplicate numbers at 005/007)
- `chrome-extension/` — AI Review Responder Chrome Extension (manifest v3)
- `docs/dev-knowledge/` — Knowledge base (bug-patterns.md, schema-log.md, architecture-decisions.md)
- `knowledge-base/` — LLM-compiled knowledge base (`raw/` sources, `wiki/` compiled articles, pgvector embeddings)
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
| leads | Lead records | client_id (FK→tenants), name, email, phone, status, lead_score, lead_temperature, areas_of_interest, conversation_summary, tags (TEXT[]), assigned_to |
| chat_messages | Canonical message store | tenant_id, session_id, role, content, created_at |
| conversations | Chat conversation container | client_id (FK→tenants), session_id, status, lead_id, tags (TEXT[]), assigned_to |
| appointments | Booked slots | tenant_id, lead_id, customer_name, start_time, end_time, status, google_event_id, recurrence_rule, recurrence_parent_id |
| business_hours | Availability config | tenant_id, timezone, hours (JSONB), slot_duration_minutes |
| automation_sequences | Multi-step email series | tenant_id, name, trigger_event, is_active |
| automation_steps | Steps in a sequence | sequence_id, step_order, delay_minutes, action_type |
| automation_executions | Lead progress through sequence | sequence_id, lead_id, tenant_id, current_step, status |
| email_sequences | Drip sequence definitions | tenant_id, name, trigger_type (lead_captured/tag_added/manual), trigger_config (JSONB), is_active |
| email_sequence_steps | Steps in a drip sequence | sequence_id, step_order, delay_days, delay_hours, subject, body, email_type, is_active |
| email_sequence_enrollments | Lead enrollment in drip sequences | sequence_id, lead_id, tenant_id, status, current_step, enrolled_at, completed_at |
| email_sequence_sends | Per-send audit trail | enrollment_id, step_id, lead_id, tenant_id, status, scheduled_for, sent_at, error |
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
| chat_flows | Visual chat flow builder | tenant_id, name, flow_json (JSONB), is_active |
| bids | Contractor bid/estimate tracking | tenant_id, lead_id, title, items_json (JSONB), total, status, pdf_url |
| bid_templates | Reusable bid templates | tenant_id, name, default_items (JSONB) |
| service_records | Client portal job records | tenant_id, lead_id, title, service_date, photos_json, invoice_amount |
| portal_tokens | Client portal access tokens | tenant_id, lead_id, token (unique) |
| calls | AI answering service call logs | tenant_id, caller_phone, duration_seconds, transcript (JSONB), summary, sentiment |
| seo_audits | Website SEO audit results | tenant_id, overall_score, categories (JSONB), critical_issues/warnings/passed_checks/recommendations (JSONB), pages_analyzed |
| geo_scores | AI visibility (GEO) scoring | tenant_id, overall_score, platform_scores (JSONB), visibility_factors/recommendations (JSONB), business_name, city |
| keyword_rankings | SEO keyword tracking | tenant_id, keyword, difficulty_score, estimated_position, search_volume_estimate, recommendations (JSONB) |
| social_posts | Social media post management | tenant_id, platform, content, media_urls (JSONB), hashtags (TEXT[]), status, scheduled_for, engagement_data (JSONB) |
| marketing_campaigns | Email/SMS blast campaigns | tenant_id, name, type (email/sms), subject, body, target_filter (JSONB), status, total_recipients/sent/opened/clicked |
| campaign_sends | Campaign send tracking | campaign_id, tenant_id, lead_id, channel, recipient, status, sent_at/opened_at/clicked_at |
| invoices | Invoicing & text-to-pay | tenant_id, lead_id, invoice_number, items_json, subtotal/tax/total, status, deposit_amount, amount_paid, is_recurring, recurrence_interval |
| pipeline_stages | Sales pipeline stages | tenant_id, name, sort_order, color, is_won, is_lost |
| smart_lists | Dynamic lead segments | tenant_id, name, filters_json, cached_lead_count |
| forms | Form/survey builder | tenant_id, name, fields_json, settings_json, public_token, submission_count |
| form_submissions | Form submission data | form_id, tenant_id, lead_id, data_json |
| invoice_item_templates | Reusable invoice line items | tenant_id, description, unit_price, category |
| documents | Documents & e-signatures | tenant_id, lead_id, title, template_html, rendered_html, status, signer_name/email, signed_at, signature_data, signing_token |
| document_templates | Reusable document templates | tenant_id, name, category, template_html, variables (TEXT[]) |
| repurpose_jobs | Content repurposer | tenant_id, source_type, source_url, source_content, source_title, tone, outputs (JSONB), status, connected_social_post_ids, connected_email_sequence_id, created_via |

> Always verify against live schema — this table may be outdated.

## Plan Names
- free, growth ($249), professional ($499), autopilot ($299), enterprise ($899)
- Old prices (legacy subscribers): growth ($199), professional ($399), enterprise ($799)
- Old names (DO NOT USE): foundation, operations

## Schema Discipline
ALWAYS check the actual Supabase schema before writing queries. Known past issues:
- `client_id` is correct for leads table (NOT `tenant_id`)
- `status` is correct for lead status (NOT `lead_stage`)
- Foreign keys pointing to renamed/dropped tables
- `password_hash` and `owner_name` added in migration 002
- `areas_of_interest` is correct for leads (NOT `service_interest` — that column never existed)
- `conversations` table uses `client_id` (NOT `tenant_id`) — same as leads

Before writing any database query, verify the column exists. When creating a migration, check it doesn't conflict with existing schema.

## Python/FastAPI Gotchas
- Never use `from __future__ import annotations` in files with FastAPI route handlers — breaks Pydantic model resolution, causes 422 errors
- Always use explicit Pydantic model classes for request bodies, not inline parameters
- CORS is configured in main.py — if widget stops working on external sites, check CORS first
- Production runs with 4 Uvicorn workers — in-memory state is per-process only
- Widget config + chat data uses 5-min TTL in-memory cache (per-worker) — invalidates automatically

## Frontend Patterns
- Dashboard uses a dark theme — match it for any new components
- Plan/subscription data must come from live API calls, never stale JWT claims
- Empty states should be helpful with CTAs, not just "0" or "No data"

## Skills & Agents

Skills in `.claude/skills/` (32 total):
- **Core:** schema-guard, debug-api, feature-build, widget-test, migration-workflow
- **AI/Knowledge:** ai-feature-pattern, kb-discover, kb-ingest, kb-compile, kb-query, kb-health
- **Quality:** tdd-workflow, verification-loop, e2e-testing, eval-harness, coding-standards
- **Orchestration:** team-orchestration, coordinator, build-loop, strategic-compact, deep-research
- **Industry:** industry-content, tenant-chatbot-audit
- **Security:** security-audit, security-patch-from-review, dead-code-sweep
- **Meta:** kairos (background agent), buddy (companion), kevin-mode (terse output), subconscious
- Also `.codex/skills/` for repo-native skills.

Agents in `.claude/agents/` (15 total):
- **Core team:** schema-guardian, backend-dev, frontend-dev, widget-specialist, qa-tester, devops
- **Review:** code-reviewer, security-reviewer, tdd-guide
- **Architecture:** architect, performance-optimizer, refactor-cleaner
- **GAN harness:** gan-planner, gan-generator, gan-evaluator
- Use `/delegate` or `/coordinator` to plan delegation. Agents communicate via `.claude/agent-comms/`.

**Delegation order:** schema-guardian → backend-dev + frontend-dev (parallel) → qa-tester. Before deploy: qa-tester + devops in parallel.

## Workflow Commands

High-level commands that orchestrate the full agent pipeline:

| Command | What It Does |
|---------|-------------|
| `/new-feature` | Schema → Backend → Frontend → QA → Commit (chains all relevant agents) |
| `/fix-bug` | Check known patterns → Diagnose → Fix → Verify → Document → Commit |
| `/deploy` | QA + DevOps in parallel → Fix blockers → Final gate |
| `/refactor` | Analyze → Plan → Execute incrementally → Verify → Commit |
| `/kb-discover` | Search web for new articles relevant to AgentNexLiFy, score and ingest |
| `/kb-ingest` | Manually add a URL or file to the knowledge base |
| `/kb-compile` | Compile pending sources into wiki articles with embeddings |
| `/kb-query` | Semantic Q&A against the knowledge base |
| `/kb-health` | Audit wiki for staleness, gaps, contradictions |
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
- **Claude Code hooks** — pre-edit warns on sensitive files, post-edit scans for dangerous patterns, notification on agent completion, auto-checkpoint before compaction, **anti-desperation on tool failure**

See docs/ai-development.md for full details.

## Daily Routine

Automated via Task Scheduler: 8 AM morning (`scripts/daily/morning-auto.sh`), 8 PM evening (`scripts/daily/evening-auto.sh`). Both write to `docs/` only. Interactive: `/morning`, `/evening`. Details: `docs/scheduled-routines.md`.

## Workflows

**New API endpoint:** Check existing routers → schema-guard → Pydantic model → route → register in main.py
**New dashboard page:** Create in `frontend/src/pages/` → dark theme → live API data → helpful empty states → sidebar link
**Database migration:** Next numbered file in `migrations/` (after 064) → apply via Supabase MCP or SQL editor → update schema-log.md → update Pydantic models

## Model Selection (Updated 2026-03-25)
- Widget chat responses: use `claude-sonnet-4-6` (fast, fewer tokens, 1M context)
- Complex tasks (documents, quotes, analysis): use `claude-opus-4-6`
- Streaming: always set `stream=True` for widget responses
- Extended thinking: set `thinking.display: "omitted"` when streaming to users

## Development Rules (Updated 2026-03-25)
- NEVER add new features without running the test suite first
- NEVER skip security review on auth or payment endpoints
- ALL tenant-specific queries MUST use RLS or explicit tenant_id filtering
- ALL Stripe integration MUST use production keys in production (NEVER test keys)
- ALL API endpoints MUST have input validation and proper error responses

## Decision Engine

### Plan Mode Default
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions)
- If something goes wrong, STOP and re-plan immediately — don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### Deterministic-First Rule
Don't use an LLM for something a deterministic program can do. LLMs are "System 2" (slow, expensive, flexible). Traditional programs are "System 1" (fast, cheap, inflexible). Instead of putting an LLM in the hot loop, write a deterministic tool and call it repeatedly. Code is cheap; tokens are not. If you find yourself generating the same 30 lines of Python to inspect a file, write a 3-line shell script wrapper around jq and check it in.

### Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### Self-Improvement Loop
- After any correction from the user, update `docs/dev-knowledge/bug-patterns.md` with the pattern
- Write rules for yourself to prevent repeating the same mistake
- Review lessons at the start of each session via `/recover`
- Every bug fixed becomes a permanent rule

### Subagent Strategy
- Use subagents to keep the main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute via subagents
- One task per subagent for focused execution

### Quality Gates (Hard Rules — Override Defaults)
- When evidence contradicts instinct, trust the evidence
- If a fix feels hacky, ask: "Knowing everything I know now, what's the elegant solution?"
- No laziness — find root causes, avoid temporary fixes, maintain senior-level standards
- Simplicity first — make every change as simple as possible, minimize code impact

## Token Optimization (RTK)

RTK (Rust Token Killer) is installed as a PreToolUse hook. It transparently rewrites Bash commands to use `rtk` prefix for 60-90% token savings on terminal output. Claude never sees the rewrite — just compressed output.

Meta commands (use directly):
- `rtk gain` — show token savings analytics
- `rtk gain --history` — command usage history with savings
- `rtk discover` — analyze Claude Code history for missed optimization opportunities

Requires `jq` installed. If RTK hook fails silently, check `which jq` and `which rtk`.

## External Tools & Repos

Installed tools available in `~/`:
| Tool | Location | Purpose |
|------|----------|---------|
| AutoAgent | `~/autoagent/` | Meta-agent that autonomously improves agent harnesses via hill-climbing |
| RTK | `~/.local/bin/rtk` | CLI proxy for 60-90% token savings on terminal output |
| GitNexus | `~/GitNexus/` | Knowledge graph engine for codebase — Tree-sitter AST, MCP integration |
| open-multi-agent | `~/open-multi-agent/` | TypeScript multi-agent framework — runTeam() with auto task decomposition |
| everything-claude-code | `~/everything-claude-code/` | 27 agents, 64 skills, 33 commands, AgentShield (reference implementation) |
| AiDesigner | `~/AiDesigner/` | AI designer MCP — generate UI mockups from natural language |
| obsidian-mind | `~/obsidian-mind/` | Persistent memory vault template for Claude Code sessions |
| free-coding-models | global npm | 174 free AI models from 23 providers — `free-coding-models` CLI |

## Error Handling Philosophy (Anti-Desperation)

A `PostToolUseFailure` hook injects a composure check on every tool failure. This is by design — error spiraling (stacking speculative fixes, abandoning working approaches, escalating complexity) is the #1 cause of AI-generated bad solutions.

**When you hit an error:**
1. Read the error message — what is it *actually* telling you?
2. Identify the single smallest fix
3. Do NOT escalate complexity — the simplest explanation is usually correct
4. Do NOT abandon your current approach after one failure — diagnose first
5. Do NOT stack multiple speculative fixes at once
6. One calm step at a time

This applies to all agents (schema-guardian, backend-dev, frontend-dev, qa-tester, devops, widget-specialist). Composure produces better solutions than urgency.

## Competitive Intel (Updated 2026-03-25)
- GoHighLevel: AI Employee (calls + chat), white-label SaaS, $97-497/mo — #1 competitor
- Drillbit (YC): AI receptionist + quoting + CRM for contractors — direct vertical competitor
- Phonely (YC S24): AI receptionist, 70% cheaper than answering services
- Toma (a16z + YC): AI receptionist, thousands of daily interactions
- Birdeye/Podium: $300-600/mo, AI review responses are key selling point
- Oscar Chat: $40/mo budget competitor, 95+ languages

## Knowledge Base

`docs/dev-knowledge/`: bug-patterns.md, schema-log.md, architecture-decisions.md. Always update after fixing bugs or changing schema.

---

## Workspaces & Routing

3-layer routing: Root CLAUDE.md → Workspace CONTEXT.md → Skills/Tools

| Task | Go to | Read first | Skip |
|------|-------|------------|------|
| Spec a feature or plan a phase | /planning | CONTEXT.md | /ops |
| Write or fix code (backend) | /backend | CONTEXT.md | /ops |
| Write or fix code (frontend) | /frontend | CONTEXT.md | /ops |
| Widget config or knowledge base | /widget | CONTEXT.md | /backend, /frontend |
| Deploy, monitor, debug infra, write docs | /ops | CONTEXT.md | /planning |
| Fix a bug (unknown location) | — | All CONTEXT.md files | — |
| **"Council this"** or complex decision with stakes | /skills/llm-council | SKILL.md | — |

Each workspace has a `CONTEXT.md` with local rules, patterns, and known issues. Read it before working in that area.

## Workspace Index

- `/backend` — FastAPI service, routers, services, migrations. See `backend/CONTEXT.md`
- `/frontend` — React/Vite dashboard. See `frontend/CONTEXT.md`
- `/planning` — Specs, architecture decisions, phase tracking. See `planning/CONTEXT.md`
- `/ops` — Deploy, monitoring, scripts, documentation. See `ops/CONTEXT.md`
- `/widget` — Tenant knowledge bases, embed configs, smoke tests. See `widget/CONTEXT.md`
- `/skills/llm-council` — LLM Council for complex decisions. See `skills/llm-council/SKILL.md`

## Naming Conventions (Architecture Files)

- Specs: `feature-name_spec.md` (in `/planning/specs/`)
- Decisions: `YYYY-MM-DD-decision-title.md` (in `/planning/decisions/`)
- Knowledge bases: `tenant-name_kb.md` (in `/widget/knowledge-bases/`)
- Test prompts: `tenant-name_smoke-tests.md` (in `/widget/test-prompts/`)

## LLM Council (Complex Decisions)

**Triggers:** "council this", "pressure-test this", "war room this", "debate this", or any decision with real stakes and tradeoffs.

When triggered: read `/skills/llm-council/SKILL.md` and execute the full council protocol. Five independent AI advisors run in parallel, peer-review anonymously, chairman synthesizes. Output: HTML report + markdown transcript saved to `/skills/llm-council/reports/` and `/skills/llm-council/transcripts/`.

**Do NOT run the council on:** simple questions, factual lookups, or creation tasks. Only run when the user faces genuine uncertainty where multiple perspectives add value.
