# AgentNexLiFy — CLAUDE.md

AI-powered business automation platform. Chat widget captures leads, books appointments, and automates follow-ups for small businesses.

## Critical Rules
- Research the codebase before editing. Never change code you haven't read.
- NEVER use `from __future__ import annotations` in any Python file — it breaks FastAPI
- NEVER use localStorage in React artifacts
- Always use `client_id` (not `tenant_id`) when querying the `leads` table
- Always use `status` (not `lead_stage`) for lead status in the `leads` table
- Widget JS must be identical in widget/ AND frontend/public/widget/
- NEVER commit .env files or log secret values
- Database schema changes ONLY via numbered migration files in migrations/
- NEVER use WebFetch or WebSearch — use `agent-browser` via Bash instead

## Operating Rules (behavioral)
- **Caveman mode** output by default — drop filler, fragments OK. See `.claude/rules/caveman-mode.md`
- **UltraPlan + UltraThink** always — extended thinking, plan mode for 2+ files. See `.claude/rules/ultrathink.md`
- **No assumptions** — confidence <80% → ask. See `.claude/rules/no-assumptions.md`
- **Model routing** — Haiku for mechanical, Sonnet for code, Opus for planning. See `.claude/rules/model-routing.md`
- **Parallel approaches** — 2 worktree agents when approach unclear. See `.claude/rules/parallel-approaches.md`
- **Prompt library first** — read `PROMPTLIBRARY.md` before tasks. See `.claude/rules/prompt-library.md`
- **KB first** — check `knowledge-base/wiki/` before researching. See `.claude/rules/kb-first.md`
- **12 usage patterns** — fight-me, interview-first, specific-reader, decision-framework, stress-test, living-doc, build-the-system, etc. See `.claude/rules/claude-usage-patterns.md`
- **Personality** — direct, evidence-first, no preamble/hedging. See `.claude/rules/personality.md`
- **Karpathy guidelines** — think before coding, simplicity first, surgical changes, goal-driven execution. See `.claude/skills/karpathy-guidelines/SKILL.md`

> Domain-specific rules in `.claude/rules/`: schema-discipline, python-fastapi, frontend-patterns, security-rules, widget-rules, api-conventions, testing-standards, gitnexus, workflow-orchestration, codex-subagents
>
> Behavioral rules in `.claude/rules/`: caveman-mode, model-routing, no-assumptions, parallel-approaches, ultrathink, prompt-library, kb-first, claude-usage-patterns, personality
>
> Security hardening in `.claude/rules/`: claude-code-security (permissions.deny + ask + sandbox config per Trail of Bits-style guide)

## Tech Stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React, Vite, Tailwind-style CSS, Recharts
- Database: Supabase (PostgreSQL with RLS)
- AI: Anthropic Claude API (claude-sonnet-4-6, claude-opus-4-6, claude-haiku-4-5-20251001)
- Email: Resend | SMS: Twilio | Payments: Stripe
- Hosting: Railway (backend), Vercel (frontend)

## Architecture

```
Browser → Chat Widget (embedded JS) → FastAPI /api/chat → Claude API
                                     → Supabase (messages, leads, appointments)
Dashboard (React/Vite) → FastAPI /api/* → Supabase
```

Widget is tenant-scoped. Every request carries a tenant/client ID. Multi-tenant from day one.

## Key Directories
- `backend/` — FastAPI service (`main.py`, `routers/`, `services/`)
- `frontend/` — React/Vite dashboard (`src/pages/`, `src/utils/api/`)
- `widget/` + `frontend/public/widget/` — Embeddable chat widget (must be identical)
- `migrations/` — SQL migration files (001–096+)
- `docs/dev-knowledge/` — Knowledge base (bug-patterns.md, schema-log.md, architecture-decisions.md)
- `knowledge-base/` — LLM-compiled KB (`raw/`, `wiki/`, pgvector embeddings)
- `_archive/`, `landing-page-v2/`, `public/` — Legacy (do not touch)

## Common Commands
- Frontend dev: `cd frontend && npm run dev`
- Frontend build: `cd frontend && npm run build`
- Backend dev: `uvicorn backend.main:app --reload --port 8000`
- Install git hooks: `bash scripts/install-hooks.sh`

## Plan Names
- free, growth ($249), professional ($499), autopilot ($299), enterprise ($899)
- Old prices (legacy): growth ($199), professional ($399), enterprise ($799)
- Old names (DO NOT USE): foundation, operations

## Automation
- **Pre-commit hook** — blocks secrets, dangerous imports, bare except blocks
- **Pre-push hook** — frontend build + schema consistency check
- **GitHub Actions** — daily health check, PR validation, auto bug logging, AI auto-improve
- **Claude Code hooks** — pre-edit sensitive file warning, post-edit pattern scan, anti-desperation, UltraPlan/UltraThink, 90% confidence gate

## Daily Routine
Automated: 8 AM morning, 8 PM evening (scripts/daily/). Interactive: `/morning`, `/evening`.

## Workflows
- **New API endpoint:** Check routers → schema-guard → Pydantic model → route → register in main.py
- **New dashboard page:** `frontend/src/pages/` → dark theme → live API → helpful empty states → sidebar
- **Database migration:** Next numbered file in `migrations/` → apply via Supabase MCP → update schema-log.md

## Competitive Intel
- GoHighLevel: AI Employee, white-label SaaS, $97-497/mo — #1 competitor
- Drillbit (YC): AI receptionist + quoting + CRM for contractors
- Phonely/Toma (YC): AI receptionists
- Birdeye/Podium: $300-600/mo, AI review responses
- Oscar Chat: $40/mo budget competitor

## Knowledge Base
`docs/dev-knowledge/`: bug-patterns.md, schema-log.md, architecture-decisions.md. Always update after fixing bugs or changing schema.

## Workspaces & Routing

| Task | Go to | Read first |
|------|-------|------------|
| Spec a feature or plan | /planning | CONTEXT.md |
| Backend code | /backend | CONTEXT.md |
| Frontend code | /frontend | CONTEXT.md |
| Widget/knowledge base | /widget | CONTEXT.md |
| Deploy, monitor, docs | /ops | CONTEXT.md |
| Complex decision | /skills/llm-council | SKILL.md |

Workspaces: `/backend`, `/frontend`, `/planning`, `/ops`, `/widget` — each has `CONTEXT.md`.

## Naming Conventions
- Specs: `feature-name_spec.md` (in `/planning/specs/`)
- Decisions: `YYYY-MM-DD-decision-title.md` (in `/planning/decisions/`)
- Knowledge bases: `tenant-name_kb.md` (in `/widget/knowledge-bases/`)

## LLM Council
Triggers: "council this", "pressure-test this", "war room this". Five independent AI advisors in parallel, peer-review, chairman synthesizes. Only for genuine uncertainty with real stakes.

<!-- autoskills:start -->

Summary generated by `autoskills`. Check the full files inside `.claude/skills`.

## Accessibility (a11y)

Audit and improve web accessibility following WCAG 2.2 guidelines. Use when asked to "improve accessibility", "a11y audit", "WCAG compliance", "screen reader support", "keyboard navigation", or "make accessible".

- `.claude/skills/accessibility/SKILL.md`
- `.claude/skills/accessibility/references/A11Y-PATTERNS.md`: Practical, copy-paste-ready patterns for common accessibility requirements. Each pattern is self-contained and linked from the main [SKILL.md](../SKILL.md).
- `.claude/skills/accessibility/references/WCAG.md`

## AI Feature Pattern

Use this skill when building any feature that calls the Claude API for AI-powered functionality (text generation, categorization, extraction, analysis). Ensures consistent prompt engineering, JSON parsing, and error handling.

- `.claude/skills/ai-feature-pattern/SKILL.md`

## Autonomous Webapp Test

Use when user says 'test everything' or wants autonomous end-to-end testing of the web app. Claude drives the whole dashboard + widget via Playwright MCP — reads the accessibility tree, clicks every button, fills every form, checks console + network for errors. Returns structured bug report. Type...

- `.claude/skills/autonomous-webapp-test/SKILL.md`

## Buddy — Your Coding Companion

Tamagotchi-style coding companion. Deterministic creature generated from user ID. Has species, rarity, stats, and personality. Shows up in responses with mood based on session health.

- `.claude/skills/buddy/SKILL.md`

## Autonomous Build Loop

Autonomous infinite development loop. Constantly builds features, tests, debugs, refactors, and evolves the codebase. Reads backlog, picks highest-priority work, executes it, commits, and repeats.

- `.claude/skills/build-loop/SKILL.md`

## challenge-assumptions

Generate steelman counterarguments for recent wiki articles. Prevents echo-chamber thinking by challenging assumptions in the knowledge base.

- `.claude/skills/challenge-assumptions/SKILL.md`

## Coding Standards & Best Practices

Universal coding standards, best practices, and patterns for TypeScript, JavaScript, React, and Node.js development.

- `.claude/skills/coding-standards/SKILL.md`

## Compound Engineering Pipeline

5-agent compound pipeline for every task. Brainstorm → Plan → Execute → Review → Vertical Check. Each agent focused on one thing. Everything documented in markdown. Combined with worktree parallelism for 4-8x throughput.

- `.claude/skills/compound-engineering/SKILL.md`

## Coordinator Mode

Multi-agent orchestrator. Auto-decomposes complex tasks into parallel workstreams with dependency resolution.

- `.claude/skills/coordinator/SKILL.md`

## Dead Code Sweep

Scan the codebase for dead code — unused files, unreachable functions, orphan imports, dead config. Verify each item is truly dead, then remove.

- `.claude/skills/dead-code-sweep/SKILL.md`

## Debug API

Use this skill when diagnosing any API error — 422s, 500s, CORS failures, silent data loss, or webhook issues.

- `.claude/skills/debug-api/SKILL.md`

## Deep Research

Multi-source deep research using firecrawl and exa MCPs. Searches the web, synthesizes findings, and delivers cited reports with source attribution.

- `.claude/skills/deep-research/SKILL.md`

## Deploy to Vercel

Deploy applications and websites to Vercel. Use when the user requests deployment actions like "deploy my app", "deploy and give me the link", "push this live", or "create a preview deployment".

- `.claude/skills/deploy-to-vercel/SKILL.md`

## Deploy Workflow

Use BEFORE pushing to main or triggering a Railway/Vercel deploy. Runs pre-deploy gates (build, tests, migration status, widget-file sync) and flags any blocker before remote deploy starts. This is the Type 7 (CI/CD & Deployment) skill per the 9-type taxonomy.

- `.claude/skills/deploy-workflow/SKILL.md`
- `.claude/skills/deploy-workflow/references/railway-cli.md`: Quick cheat sheet for Railway operations agentnexlify uses in production.
- `.claude/skills/deploy-workflow/references/vercel-cli.md`: Quick cheat sheet for Vercel operations agentnexlify uses for the frontend.

## E2E Testing Patterns

Playwright E2E testing patterns, Page Object Model, configuration, CI/CD integration, artifact management, and flaky test strategies.

- `.claude/skills/e2e-testing/SKILL.md`

## Eval Harness Skill

Formal evaluation framework for Claude Code sessions implementing eval-driven development (EDD) principles.

- `.claude/skills/eval-harness/SKILL.md`

## Feature Build

Use this skill when building any new feature. Ensures schema safety, consistent patterns, and proper documentation.

- `.claude/skills/feature-build/SKILL.md`

## Design Thinking

Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beaut...

- `.claude/skills/frontend-design/SKILL.md`

## GitNexus CLI Commands

- `.claude/skills/gitnexus/gitnexus-cli/SKILL.md`: Run GitNexus CLI commands for analyzing, indexing, checking status, cleaning the index, generating a wiki, or listing indexed repos.
- `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md`: Debug bugs, trace errors, and investigate unexpected behavior using GitNexus query, context, and process tools.
- `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md`: Explore unfamiliar codebases, understand architecture, trace execution flows, and answer how code works using GitNexus.
- `.claude/skills/gitnexus/gitnexus-guide/SKILL.md`: Reference guide for all GitNexus MCP tools, resources, graph schema, and the skill routing table for different code tasks.
- `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md`: Analyze the blast radius of code changes to understand what will break if you modify a function, class, or file.
- `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md`: Safely rename, extract, split, move, or restructure code using GitNexus impact mapping and automated rename tools.

## Industry Content — Adding a New Business Type

Use when adding support for a new business type or industry to ensure all industry-specific content is created consistently.

- `.claude/skills/industry-content/SKILL.md`

## KAIROS -- Persistent Background Agent

Persistent background agent for memory consolidation, project monitoring, and dream reports.

- `.claude/skills/kairos/SKILL.md`

## Karpathy Guidelines

Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria. Derived from Andrej Karpathy's observations on LLM coding pitfalls.

- `.claude/skills/karpathy-guidelines/SKILL.md`

## KB Compile — Wiki Compilation

Compile raw sources into the wiki by reading pending sources, creating or updating wiki articles, generating embeddings, storing in Supabase pgvector, and rebuilding INDEX.md.

- `.claude/skills/kb-compile/SKILL.md`

## KB Discover — Automated Article Discovery

Automated article discovery for the knowledge base that searches the web, scores relevance, and ingests high-quality results.

- `.claude/skills/kb-discover/SKILL.md`

## KB Health — Wiki Audit

Audit the knowledge base for staleness, gaps, contradictions, and missing cross-links, reporting a health score and suggesting improvements.

- `.claude/skills/kb-health/SKILL.md`

## KB Ingest — Manual Source Addition

Manually add a source to the knowledge base by fetching a URL or reading a local file, converting to markdown, categorizing, and registering in kb_sources.

- `.claude/skills/kb-ingest/SKILL.md`

## KB Query — Semantic Q&A

Ask natural language questions against the knowledge base using semantic search with pgvector cosine similarity.

- `.claude/skills/kb-query/SKILL.md`

## Kevin Mode

Ultra-compressed caveman-style responses named after Kevin Malone, toggled on with 'kevin mode' and off with 'normal mode'.

- `.claude/skills/kevin-mode/SKILL.md`

## `/last30days` Skill — Claudeopedia Knowledge Synthesis

Synthesize recent knowledge accumulation into a 'State of Your Mind' report by grouping by theme, identifying patterns, and surfacing blind spots.

- `.claude/skills/last30days/SKILL.md`

## Migration Workflow

Use this skill when creating, applying, or verifying database migrations to prevent migrations that exist as files but are never applied to live Supabase.

- `.claude/skills/migration-workflow/SKILL.md`

## Node.js Backend Patterns

Build production-ready Node.js backend services with Express/Fastify, implementing middleware patterns, error handling, authentication, database integration, and API design best practices. Use when creating Node.js servers, REST APIs, GraphQL backends, or microservices architectures.

- `.claude/skills/nodejs-backend-patterns/SKILL.md`
- `.claude/skills/nodejs-backend-patterns/references/advanced-patterns.md`: Advanced patterns for dependency injection, database integration, authentication, caching, and API response formatting.

## Node.js Best Practices

Node.js development principles and decision-making. Framework selection, async patterns, security, and architecture. Teaches thinking, not copying.

- `.claude/skills/nodejs-best-practices/SKILL.md`

## obsidian-sync

Sync wiki articles to an Obsidian vault with wikilinks and frontmatter in a one-way sync that never modifies source wiki files.

- `.claude/skills/obsidian-sync/SKILL.md`

## Prompt Library Workflow

Reusable prompt library for consistent AI agent workflows. Always consult PROMPTLIBRARY.md before starting tasks to pick the right prompt, gather context, and execute with proven patterns.

- `.claude/skills/prompt-library/SKILL.md`

## Schema Guard

Use this skill BEFORE writing any database query, migration, or Pydantic model that touches the database to prevent schema mismatch bugs.

- `.claude/skills/schema-guard/SKILL.md`

## Security Audit

Scan the codebase for security vulnerabilities including missing tenant verification, unverified webhooks, unsigned OAuth state, XSS, and dangerous imports.

- `.claude/skills/security-audit/SKILL.md`

## Security Patch from Review

Systematically close every finding from a code review or audit report by parsing findings, fixing in severity order, tracking status, and committing with matching classification codes.

- `.claude/skills/security-patch-from-review/SKILL.md`

## SEO optimization

Optimize for search engine visibility and ranking. Use when asked to "improve SEO", "optimize for search", "fix meta tags", "add structured data", "sitemap optimization", or "search engine optimization".

- `.claude/skills/seo/SKILL.md`

## Strategic Compact Skill

Suggest manual context compaction at logical task boundaries to preserve context through task phases rather than arbitrary auto-compaction.

- `.claude/skills/strategic-compact/SKILL.md`

## Subconscious Agent — Self-Improvement Loop

Self-improvement loop that gathers evidence, generates improvement ideas, debates them, synthesizes one recommendation, and writes artifacts.

- `.claude/skills/subconscious/SKILL.md`

## Test-Driven Development Workflow

Enforce test-driven development with 80 percent plus coverage including unit, integration, and E2E tests for new features, bug fixes, and refactoring.

- `.claude/skills/tdd-workflow/SKILL.md`

## Team Orchestration

Use this skill when a task is complex enough to benefit from delegating to multiple agents with specific roles and coordination patterns.

- `.claude/skills/team-orchestration/SKILL.md`

## Tenant Chatbot Audit

Audit a specific tenant chatbot for data gaps, RLS failures, FAQ quality, orphaned sessions, and knowledge base issues.

- `.claude/skills/tenant-chatbot-audit/SKILL.md`

## Verification Loop Skill

Run a comprehensive verification system for Claude Code sessions covering build, types, lint, tests, security, and diff review.

- `.claude/skills/verification-loop/SKILL.md`

## Widget Test

Test, debug, or verify the chat widget covering load, conversation, data capture, cross-origin behavior, and file sync.

- `.claude/skills/widget-test/SKILL.md`

## `/wiki` Skill — Claudeopedia Fast Ingest

Capture any input (screenshot, URL, text, file, YouTube) into a Karpathy-style wiki article in one step from raw to wiki.

- `.claude/skills/wiki/SKILL.md`

## Worktree Orchestrator

Manage 4-8 parallel git worktrees, each running its own compound engineering pipeline for high quality at high throughput.

- `.claude/skills/worktree-orchestrator/SKILL.md`

<!-- autoskills:end -->
