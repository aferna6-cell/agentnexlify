# AgentNexLiFy — CLAUDE.md

AI-powered business automation platform. Embeddable chat widget captures leads, books appointments, and automates follow-ups for small businesses. Multi-tenant SaaS from day one.

> This file is your onboarding doc, not a README. Keep it ≤500 lines. Reference rule files — never duplicate their contents.

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
- AI: Anthropic Claude (`claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5-20251001`)
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
- `_archive/`, `landing-page-v2/`, `public/` — **legacy, do not touch**

### Plan names + prices
- `free`, `growth` ($249/mo), `professional` ($499/mo), `autopilot` ($299/mo), `enterprise` ($899/mo)
- Legacy prices (billed on old contracts): growth $199, professional $399, enterprise $799
- Retired names, **never use**: `foundation`, `operations`

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
9. **Never use WebFetch / WebSearch tools** — use `agent-browser` via Bash. Blocked by `.claude/settings.json` hook.
10. **Never research code before reading it** — CLAUDE.md Rule 7 from user-rules.md. Read source before editing.

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
- **Behavioral** — caveman-mode, model-routing, no-assumptions, parallel-approaches, ultrathink, prompt-library, kb-first, claude-usage-patterns, personality, user-rules, one-task-one-chat, prompt-formula, claude-execution-layers
- **Security** — claude-code-security (permissions.deny + ask + sandbox, Trail of Bits pattern)
- **Tooling** — claude-version-pin (v2.1.98 workaround for 20k phantom tokens in v2.1.100+), claude-renderer (CLAUDE_CODE_NO_FLICKER=1 virtual terminal renderer)
- **Plugins** — `.claude/rules/plugins.md` (36 plugins as of 2026-04-12; project skills beat plugin skills on overlap)

### Automation
- **Pre-commit hook** — blocks secrets, `from __future__ import annotations`, bare-except blocks
- **Pre-push hook** — frontend build + schema consistency check
- **GitHub Actions** — daily health check, PR validation, auto bug logging, AI auto-improve
- **Agent system guardrail** - `scripts/check_agent_system.py` runs in PR validation and proves CLAUDE.md, Everything Claude Code agents, Claude Code 2.1.98 pin, and issue-to-PR workflows are intact.
- **Claude Code hooks** — pre-edit sensitive-file warn, post-edit pattern scan, anti-desperation, UltraPlan/UltraThink, 90% confidence gate, 15-msg handoff summary (`scripts/claude-hooks/message-counter.sh`)
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

### Naming conventions
- Specs: `/planning/specs/feature-name_spec.md`
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
