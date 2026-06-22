# AgentNexLiFy — CLAUDE.md

AI-powered business automation platform. Embeddable chat widget captures leads, books appointments, and automates follow-ups for small businesses. Multi-tenant SaaS from day one.

> This file is your onboarding doc, not a README. Keep it ≤200 lines per [Anthropic guidance](https://docs.claude.com/en/docs/claude-code/memory#write-effective-instructions) — files >200 lines reduce adherence. Reference rule files — never duplicate their contents.

## SECOND BRAIN — READ FIRST
Before any task, read `brain/Maps/Home.md` — the source-backed operating memory for AgentNexLiFy (people, products, decisions, open loops, procedures, DB schema, competitors). Start there, follow wikilinks for depth. Re-sync with `brain/_tools/refresh_connectors.py`; ask it questions via `brain/_tools/ask.py`. Full guide: `brain/README.md`.

## Scope Ladder
Claude merges CLAUDE.md files in this order (last wins on conflict):
1. **Global** — `~/.claude/CLAUDE.md` — personal defaults across all projects
2. **Project** — `./CLAUDE.md` — this file, project-specific rules
3. **Folder** — workspace `CONTEXT.md` at `backend/CONTEXT.md`, `frontend/CONTEXT.md`, `widget/CONTEXT.md`, `planning/CONTEXT.md`, `ops/CONTEXT.md`. Scoped context for that subtree.

---

## WHAT — facts

### Tech stack
- Backend: FastAPI, Python 3.11, Pydantic, Supabase Python client
- Frontend: React 18, Vite 6, Tailwind-style CSS, Recharts
- Database: Supabase Postgres with RLS
- AI: Anthropic Claude (`claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5-20251001`)
- Email: Resend · SMS/voice: Twilio · Payments: Stripe
- Hosting: Railway (backend) · Vercel (frontend)

### Architecture
```
Browser → Chat Widget (embedded JS) → FastAPI /api/chat → Claude API
                                    ↓
                        Supabase (messages, leads, appointments)
Dashboard (React/Vite) ─────────→ FastAPI /api/* ─────→ Supabase
```

### Key directories
- `backend/` — FastAPI service (`main.py`, `routers/`, `services/`)
- `frontend/` — React/Vite dashboard (`src/pages/`, `src/utils/api/`)
- `widget/` + `frontend/public/widget/` — embeddable chat widget (**must stay byte-identical**)
- `migrations/` — SQL migration files, numbered 001–102+
- `docs/dev-knowledge/` — bug-patterns.md, schema-log.md, architecture-decisions.md
- `knowledge-base/` — LLM-compiled wiki (`raw/`, `wiki/`, pgvector embeddings)
- `.claude/` — config, rules, skills, agents, commands, hooks
- `_archive/`, `public/` — **legacy, do not touch**. `landing-page-v2/` deploys via Vercel project `agentnexlify` — edit deliberately, content-only changes preferred. **WARNING (found 2026-06-12): agentnexlify.com + www are attached to the separate, stale `agentnexlify-site` Vercel project — landing-page-v2 edits do NOT reach the public domain until the domains are moved to the `agentnexlify` project in the Vercel dashboard (its prod URLs are also auth-protected + latest deploy BLOCKED — check spend limits/protection).**

### Plan names + prices (repriced 2026-06-15)
- **Current paid plans**: `chatbot` ($19.99/mo — widget/chat only) · `agent_os` ($99.99/mo — full platform). `free` = internal lapsed/no-subscription state, never sold. Canonical: `backend/services/stripe_service.py` + `ai_usage_guard.PLAN_BASELINE_TOKENS`.
- **Feature gating**: `agent_os` unlocks all premium gates (Zapier, unlimited SMS, doc drafting, lead qualification, branded automation, white-label). `chatbot` is widget/chat only. New gates → add to `backend/tests/test_plan_gating_new_plans.py`.
- **Legacy/grandfathered** (still honored on old contracts; gates include them): `growth`, `autopilot`, `professional`, `enterprise`.
- **Retired names, never use**: `foundation`, `operations`.

### Agents + skills
- 57 agents in `.claude/agents/` — backend-dev, frontend-dev, schema-guardian, widget-specialist, devops, opus-advisor, sonnet-executor, vertical-checker, qa-tester, gan-*, + 39 from `everything-claude-code` (per-language reviewers, build resolvers, loop-operator, etc.). Load lazily; don't burn context unless invoked.
- Everything Claude Code source is pinned in `.claude/everything-claude-code.lock.json`; do not load the full plugin surface by default.
- Skills in `.claude/skills/` — caveman-mode, schema-guard, widget-test, karpathy-guidelines, compound-engineering, tdd-workflow, issue-to-pr-loop, feature-build, + research-backed additions (supabase-postgres-best-practices, vercel-react-best-practices, skill-creator, mcp-builder, churn-prevention, email-sequence, seo-audit-marketing) + **planning/quality additions (2026-04-15)**: grill-me, write-prd, prd-to-plan, prd-to-issues, triage-issue, ubiquitous-language, dependency-auditor, edit-article, api-docs-generator, systematic-debugging.
- Rules in `.claude/rules/` — domain + behavioral + security hardening. Index below.

---

## WHY — non-negotiable rules (past bugs = future prevention)

### Critical invariants
1. **`client_id` not `tenant_id`** on `leads` + `conversations` tables — we've shipped production bugs from this 3+ times. See `.claude/rules/schema-discipline.md`.
2. **`status` not `lead_stage`** for lead status — column never existed as `lead_stage`.
3. **`areas_of_interest` not `service_interest`** on leads — column never existed as `service_interest`.
4. **Widget JS byte-identical** in `widget/` AND `frontend/public/widget/` — mismatched copies break embeds on tenant sites.
5. **No `from __future__ import annotations`** in FastAPI files — PEP 563 deferred annotations make Pydantic resolve bodies as strings → every request 422s.
6. **No `localStorage` in React artifacts** — storage isn't available in claude.ai artifact sandbox.
7. **Secrets never in commits or logs** — `.env*` gitignored; pre-commit hook scans; CI audits.
8. **Schema changes only via numbered migration files** in `migrations/` — no ad-hoc SQL. Apply via Supabase MCP or UI.
9. **Never research code before reading it** — CLAUDE.md Rule 7 from user-rules.md. Read source before editing.

### Design principles
- **Multi-tenant from day one** — every request carries a tenant/client ID. Never write un-scoped queries.
- **Karpathy** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution. See `.claude/skills/karpathy-guidelines/SKILL.md`.
- **Deterministic-first** — don't use an LLM for something a script can do.

### Competitive positioning (why we're building this)
- **#1 competitor**: GoHighLevel ($97–497/mo, AI Employee, white-label SaaS) — our diff is widget-first + lower friction.
- Others: Drillbit (YC — AI receptionist + quoting for contractors), Phonely/Toma (AI receptionists), Birdeye/Podium ($300–600/mo, AI review responses), Oscar Chat ($40/mo budget).
- Our moat: vertical knowledge-base pattern per tenant, not generic LLM replies.

---

## HOW — commands, workflows, rules

### Commands
```bash
cd frontend && npm run dev              # frontend dev (Vite :3001)
cd frontend && npm run build            # prod build
python -m uvicorn backend.main:app --reload --port 8000   # backend dev (requires .venv)
npm run agent-system:check              # verify Claude/Codex agent control plane
npm run check:instruction-budget        # keep always-on instruction surface small
npm run agent-config:scan               # baseline-gated AgentShield scan for agent/MCP/hook config
npm run kb:health                       # deterministic knowledge-base health report
npm run kb:lint                         # validate wiki article template + index coverage
npm run claude:2.1.98 -- --version      # pinned Claude Code runner
npm run claude:noflicker                # pinned + experimental no-flicker renderer
bash scripts/install-hooks.sh           # install git hooks
bash scripts/claude-hooks/auto-commit.sh  # manual auto-commit
```

### Workflows
- **New API endpoint** — check existing routers → schema-guard skill → write Pydantic model → route → register in `main.py` (lines 746–813) → test.
- **New dashboard page** — `frontend/src/pages/<Name>.jsx` → dark theme, live API, helpful empty state, sidebar entry in `Sidebar.jsx` → route in `App.jsx`.
- **Database migration** — next number in `migrations/NNN_name.sql` → apply via `mcp__supabase__apply_migration` → update `docs/dev-knowledge/schema-log.md` → flag in commit msg.
- **New widget feature** — edit `widget/agentnexlify-widget.js` → copy byte-identical to `frontend/public/widget/agentnexlify-widget.js` → test cross-origin embed per `.claude/skills/widget-test/SKILL.md`.
- **New skill** — use `.claude/skills/skill-creator/SKILL.md` for eval-driven authoring → frontmatter description ≤200 chars, ruthlessly specific triggers → body ≤150 lines, move long refs to `resources/`.

### Operating rules (behavioral)
- **Caveman mode** output default — `.claude/rules/caveman-mode.md`
- **UltraPlan + UltraThink** always — plan mode for 2+ files. `.claude/rules/ultrathink.md`
- **No assumptions** — confidence <80% → ask. `.claude/rules/no-assumptions.md`
- **Model routing** — Haiku mechanical / Sonnet code / Opus plan. `.claude/rules/model-routing.md`
- **Parallel approaches** — 2 worktree agents when approach unclear. `.claude/rules/parallel-approaches.md`
- **Prompt library first** — `PROMPTLIBRARY.md` before tasks. `.claude/rules/prompt-library.md`
- **KB first** — `knowledge-base/wiki/` before researching. `.claude/rules/kb-first.md`
- **12 usage patterns** — fight-me, interview-first, stress-test, build-the-system. `.claude/rules/claude-usage-patterns.md`
- **Personality** — direct, evidence-first, no preamble/hedging. `.claude/rules/personality.md`
- **Karpathy** — `.claude/skills/karpathy-guidelines/SKILL.md`
- **User rules (12)** — plan first / ask when unsure / 15-msg handoff (hook-enforced) / Opus only for deep work / don't speed / stop to rethink / never ignore CLAUDE.md or AGENTS.md / no half migrations / factor god classes / never change tests to fit intent / additive wins / new files over bloat. `.claude/rules/user-rules.md`

### Rule files index (referenced, not duplicated)
- **Domain** — schema-discipline, python-fastapi, frontend-patterns, security-rules, widget-rules, api-conventions, testing-standards, gitnexus, workflow-orchestration, codex-subagents
- **Behavioral** — caveman-mode, model-routing, no-assumptions, parallel-approaches, ultrathink, prompt-library, kb-first, claude-usage-patterns, personality, user-rules, one-task-one-chat, prompt-formula, claude-execution-layers, **daily-skills** (grill-me gate, write-prd, prd-to-issues, tdd-workflow, improve-architecture), **fill-instructions-before-guessing** (stop when instructions are missing/ambiguous/wrong — real incidents: twilio 10.x ghost, pyiceberg blame)
- **Model (Opus 4.7)** — **opus-4-7** (canonical reference — `claude-opus-4-7` ID, xhigh effort default, same $5/$25 pricing as 4.6), **self-verification** ("Verified: … — PASS/FAIL" on every task completion), **ultrareview** (invoke /ultrareview for PRs >20 LOC, auth/payments/tenant code, pre-deploy), **task-budgets** (call-site budget tiers: widget none / advisor 5k / executor 50k), **vision-3x** (high-res input for screenshots, diagrams, design comps), **opus-4-7-prompting** (batch clarifications, positive examples > negative rules, delete progress scaffolding, explicit fan-out, /ultraplan vs plan mode)
- **Security** — claude-code-security (permissions.deny + ask + sandbox, Trail of Bits pattern)
- **Tooling** — claude-version-pin (v2.1.98 workaround for 20k phantom tokens in v2.1.100+), claude-renderer (CLAUDE_CODE_NO_FLICKER=1 virtual terminal renderer), **effort-per-prompt** (set `/effort` on the prompt that needs depth, not the session — xhigh default burns ~2x medium), **usage-observability** (claude-usage historical + claude-usage-monitor real-time + platform cache dashboard for API)
- **Plugins** — `.claude/rules/plugins.md` (36 plugins as of 2026-04-12; project skills beat plugin skills on overlap)

### Automation
- **Pre-commit hook** — blocks secrets, `from __future__ import annotations`, bare-except blocks
- **Pre-push hook** — frontend build + schema consistency check
- **GitHub Actions** — daily health check, PR validation, auto bug logging, AI auto-improve
- **Agent system guardrail** - `scripts/check_agent_system.py` runs in PR validation and proves CLAUDE.md, Everything Claude Code agents, Claude Code 2.1.98 pin, and issue-to-PR workflows are intact.
- **Instruction budget** - `scripts/check_instruction_budget.py` keeps `CLAUDE.md` under 200 lines and blocks unconditional UserPromptSubmit prompt-injection sprawl.
- **Agent config security** - `npm run agent-config:scan` runs pinned baseline-gated AgentShield on Claude/Codex agents, hooks, MCP config, and project instruction files; CI triggers on those paths.
- **Claude Code hooks** — pre-edit sensitive-file warn, post-edit pattern scan, anti-desperation, UltraPlan/UltraThink, 90% confidence gate, 15-msg handoff summary (`scripts/claude-hooks/message-counter.sh`), Opus 4.7 feature reminder (`scripts/claude-hooks/invoke-opus-47-features.sh` — nudges self-verification / /ultrareview / task-budgets / 3x-vision based on prompt keywords), agent-browser router (`scripts/claude-hooks/route-to-agent-browser.sh` — routes WebFetch/WebSearch to agent-browser CLI when installed; falls back to native tools otherwise)
- **Issue → PR loop** — `.claude/skills/issue-to-pr-loop/SKILL.md`. Polls assigned GH issues every 15 min, Haiku classifies, Sonnet worktree implements, PR opens + feedback loop patches reviews. Replaces `autopilot-loop` (kept for reference).
- **Nightly commit review** — `.claude/skills/nightly-commit-review/SKILL.md`. Fires daily 2:37 AM local via scheduled-tasks MCP. Haiku triages last 24h commits, Sonnet fixes LOW-risk bugs (commits + pushes), MEDIUM/HIGH → GH issue feeding issue-to-pr-loop. Manual trigger: `bash scripts/daily/nightly-commit-review.sh`. Disable: `CLAUDE_NIGHTLY_REVIEW=0`.
- **KB auto-populate** — twice daily 6 AM + 6 PM via `scripts/daily/kb-autopopulate.sh`. Log at `knowledge-base/log.md`.

### Daily routine
- Automated 8 AM / 8 PM via `scripts/daily/*`. Interactive via `/morning`, `/evening` slash commands.

### Workspaces + routing
| Task | Workspace | Read first |
|------|-----------|------------|
| Spec or plan a feature | `/planning` | `CONTEXT.md` |
| Backend code | `/backend` | `CONTEXT.md` |
| Frontend code | `/frontend` | `CONTEXT.md` |
| Widget or knowledge base | `/widget` | `CONTEXT.md` |
| Deploy, monitor, docs | `/ops` | `CONTEXT.md` |
| Complex decision | `/skills/llm-council` | `SKILL.md` |
| Sell managed agents to clients | `/planning/managed-agents` | `README.md` |

### Dedicated Tools
Prefer these over general Bash/Read when applicable:

| Tool | Use for | Over |
|------|---------|------|
| `agent-browser` CLI | Web fetch with a11y snapshots | WebFetch raw HTML |
| `pdftotext <file> -` | PDF text extraction (80-95% token reduction) | Read on PDFs (`.claude/rules/pdf-handling.md`) |
| `scripts/claude_rules_doctor.py` | Validate `paths:` globs in rule frontmatter | Manual grep |
| `scripts/lint_claude_agents.py` | Lint agent frontmatter (name/desc/model/tools) | Manual review |
| `scripts/reindex_contextual.py` | Contextual retrieval reindex (--dry-run, --target) | Ad-hoc DB queries |
| `scripts/check_plan_drift.py` | Detect ghost refs in `plans/` (default; pass `--dirs plans audits` to widen). Mark aspirational paths with `<!-- drift-skip -->` on the line. Wired into pre-push as warning-only CHECK 9. | Manually re-checking plans before starting work |

### Naming conventions
- Specs: `/specs/feature-name_spec.md` (root, see `STRUCTURE.md`)
- Plans: `/plans/feature-name_plan.md` (root, see `STRUCTURE.md`)
- Audits: `/audits/audit-<topic>-YYYY-MM-DD.md` (root, see `STRUCTURE.md`)
- Decisions: `/planning/decisions/YYYY-MM-DD-title.md`
- Tenant KBs: `/widget/knowledge-bases/tenant-name_kb.md`
- Migrations: `migrations/NNN_name.sql` (zero-padded, sequential)
- Skills: `.claude/skills/kebab-name/SKILL.md`

### LLM Council
Triggers: "council this", "pressure-test this", "war room this". Five independent AI advisors in parallel, peer-review, chairman synthesizes. Only use for genuine uncertainty with real stakes.

---

## Maintenance
- **Expect ~70% compliance** — CLAUDE.md is read once per session; hooks enforce the hard rules.
- **Update monthly** — stale facts cause wrong-direction work. Last audit: 2026-04-15.
- **/init was run once** — this file is the curated version.
- **Reference, never duplicate** — point to rule files and configs; don't copy contents.

