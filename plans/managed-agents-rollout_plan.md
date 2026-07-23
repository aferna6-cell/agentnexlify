# Managed Agents — Production Rollout Plan

**Issue:** #33 (open since 2026-04-16)
**Status:** proposed
**Owner:** Aidan
**Created:** 2026-07-23
**Supersedes:** `plans/managed-agents-production-rollout_plan.md` (PR #522, 2026-07-21) — that draft predates the Agent OS plan gate (PR #561) and the owner MCP server launch (#564). This plan folds both in; keep the old file for its readiness-gate table until this one merges.

## Goal

Take the Managed Agents surface from "structured 503 stubs + planned health status" to revenue-producing runs for real tenants, per-agent, reversibly, without a big-bang launch.

## Current state (evidence)

**Live in prod today:**
- Run surface: `backend/routers/managed_agent_runs.py` — `POST /{tenant_id}/lead-qualify` (:235), `/draft-document` (:348), `/support-query` (:399), `/extract` (:432), document download (:561), authed health (:279), public health (:120). All registered in `backend/main.py:1018`.
- Stub behavior: unconfigured agents raise `ManagedAgentNotConfigured` → structured 503 `managed_agents_unavailable` with `planned_update: true` + `missing_config` env var (`managed_agent_runs.py:83-95`). Health reports `"planned"` when nothing is provisioned (`:98-117`). This is the backward-compat contract #33 requires us to keep.
- Registry: `backend/services/managed_agents_registry.py` — 9 env-gated handles (`lead_qualifier` :60 … `data_analyst` :92, `appointment_booker` :231), `is_any_configured()` :96, Opus-advised wrappers `advised_*()` :139-251.
- Runtime: `backend/services/advisor_executor.py` — `AdvisorExecutorRunner` (Opus advises, Managed Agent executes; advisor failure falls back to pure executor, never blocks the run). Shared call/logging path: `backend/services/llm_runtime.py` (usage logged per call).
- Plan gating: `backend/services/agent_os_gate.py:38-45` — `AGENT_OS_PLANS = {agent_os, growth, autopilot, professional, enterprise}`; 402 upsell payload; every authed `/api/v1/os/*` surface gated as of 2026-07-22 (stages 1-3 complete). Service-level gates already exist in `backend/services/document_drafting.py:342-355` (PREMIUM_PLANS) — `chatbot`/`free` blocked before the agent is invoked.
- MCP: owner MCP server mounted at `/mcp` (`backend/main.py:1097`, `backend/mcp_server.py`, doc: `docs/dev-knowledge/mcp-owner-server.md`); first tenant activated 2026-07-22 (#564). Tenant-configured outbound MCP servers: `backend/routers/os_mcp.py` (platform-flagged `os_mcp_enabled`, owner-in-loop tool calls).
- Tests: `backend/tests/test_managed_agent_runs.py`, `test_managed_agents.py`, `test_mcp_client.py`, `test_os_mcp_router.py`.
- Sales collateral: `planning/managed-agents/` — 6 agent packages (SPEC/AGENT/SOP), $1.5k-5k setup + $500/mo retainer.

**Not live:** `MANAGED_AGENTS_ENVIRONMENT_ID` and all `*_AGENT_ID` vars unset in Railway prod → every run endpoint 503s, health = `planned`. No provisioned Anthropic Managed Agents environment. No run-history table (runs return transcripts synchronously; nothing persisted except drafted documents).

**Business context:** 3 paid tenants (Keys Koffee, MTOptions, 914 Exterior). Plans: `chatbot` $19.99 / `agent_os` $99.99 (`backend/services/stripe_service.py:33-37`).

## Rollout principle

Each agent is independently gated by its `*_AGENT_ID` env var. Unset = handle raises = caller falls back / 503s (existing behavior). Rollout is per-agent, per-tenant-cohort, reversible by unsetting one variable. Kill switch for the whole line: unset `MANAGED_AGENTS_ENVIRONMENT_ID` (`registry.py:96-112`). No migration needed to disable.

## Phases

### Phase 0 — Provision + internal dogfood (1 week)

Smallest tracer bullet: one agent (`lead_qualifier` — most-exercised handle, eval harness exists per `.github/workflows/lead-qualifier-eval.yml`), one internal tenant (support@ / demo tenant), zero external exposure.

- [ ] **Owner:** create Anthropic Managed Agents environment; accept billing tier (Tier C decision — see §Owner decisions).
- [ ] Run `python -m scripts.managed_agents.provision`; set `MANAGED_AGENTS_ENVIRONMENT_ID` + `LEAD_QUALIFIER_AGENT_ID` in Railway prod.
- [ ] Smoke: public health flips `planned` → `configured`; `POST /lead-qualify` returns 200 transcript for internal tenant; unset-var path still 503s with same payload shape (contract check).
- [ ] Add run logging: persist tenant_id, agent, tokens, outcome per run (extend `llm_runtime.py` usage log or new `managed_agent_run_log` migration — next free number in `migrations/`).
- [ ] E2E tests from #33 scope: success, unavailable runtime, auth failure, tenant isolation (`_verify_tenant` :78-80), rate-limit hit.

**Entry:** environment provisioned; billing accepted. **Exit:** 1 week internal use, zero cross-tenant data access, golden eval ≥ threshold, cost/run measured and logged.

- **Packaging:** none — internal only.
- **Tenant surface:** none.
- **Ops:** watch Railway logs for `managed_agents:` lines; manual daily check.
- **Risks:** blocking httpx client stalls workers under load (`managed_agent_runs.py:6-10`) → cap at existing rate limits (10/min), defer async client; cost surprise → per-run token budget via `task-budgets.md` tiers.

### Phase 1 — First sellable slice: lead-qualify + doc drafting for one design partner (2-4 weeks)

- [ ] **Owner:** pick 1 design-partner tenant on `agent_os` plan (MTOptions or 914 Exterior — whichever has live lead volume).
- [ ] Set `DOCUMENT_DRAFTER_AGENT_ID`; doc-drafting plan gate already blocks non-premium (`document_drafting.py:342-355`).
- [ ] Dashboard surface: qualify-lead button on lead detail + drafted-doc download (endpoints exist; wire `frontend/src/pages/` lead view; 402/503 states render the existing upsell/planned cards).
- [ ] Propose-only enforcement: qualifier writes a suggestion, never mutates `leads` directly (`.claude/rules/propose-only-records.md`; suggestion flow in `backend/routers/leads.py`).
- [ ] Weekly review: task-success rate, cost/run, fallback rate (advisor + `ManagedAgentNotConfigured` fallbacks in `lead_qualification.py:382-385`).

**Entry:** Phase 0 exit met. **Exit:** 30 days, partner sign-off, success rate ≥ 80%, cost/run within margin at $99.99/mo, zero tenant-isolation incidents.

- **Packaging:** included in `agent_os` ($99.99/mo) — these two agents ARE the "full platform" promise; no new SKU. `chatbot` stays widget-only.
- **Ops:** alert on run error-rate spike + cost/run over budget; add agents to existing admin health view.
- **Risks:** partner churn from bad qualifications → propose-only means owner approves everything, worst case is ignored suggestions; runaway spend → per-run `max_tokens` + monthly baseline already tracked in `ai_usage_guard.PLAN_BASELINE_TOKENS` (`ai_usage_guard.py:27`).

### Phase 2 — Agent OS GA: all agent_os tenants (4-8 weeks)

- [ ] Enable `SUPPORT_AGENT_ID` + `STRUCTURED_EXTRACTOR_AGENT_ID` (endpoints live at `managed_agent_runs.py:399,:432`).
- [ ] Announce to all `agent_os` + grandfathered tenants; upsell card (402 payload) becomes the `chatbot`→`agent_os` upgrade funnel.
- [ ] Per-tenant monthly token guard extended to managed-agent runs (same `ai_usage_guard` path as widget chat).
- [ ] Runbook + smoke checks in `ops/` (#33 acceptance); update `planning/managed-agents/<agent>/SOP.md` per enabled agent.

**Entry:** Phase 1 exit; ≥2 agents stable. **Exit:** all agent_os tenants have access, support load < 2 hrs/wk/tenant, ≥1 `chatbot` tenant upgrades citing agents.

- **Packaging:** `agent_os` unchanged at $99.99. Usage guard is the margin protector, not a new meter.
- **Ops:** weekly eval trend + cost review; error-rate alerting mandatory before GA.
- **Risks:** Sonnet-5 tokenizer inflation (~1.0-1.35x) erodes margin → re-baseline against `tenant_ai_usage_monthly` (pattern: 2026-07-22 re-baseline in `.claude/rules/python-fastapi.md`).

### Phase 3 — Bespoke managed-agents service line (opens after Phase 2; sales-driven)

- [ ] Sell from `planning/managed-agents/README.md` catalog: $1.5k-5k setup + $500/mo retainer, on top of (not instead of) `agent_os` subscription.
- [ ] Enable long-tail handles per contract: `deep_researcher`, `field_monitor`, `data_analyst`, `appointment_booker`.
- [ ] Per-client integrations via tenant MCP servers (`os_mcp.py`) — flip `os_mcp_enabled` platform flag per tenant; every side-effecting call stays owner-in-loop.

**Entry:** first signed managed-agents contract. **Exit criteria per client:** 30-day post-launch iteration done, retainer active, SOP handed off.

- **Packaging:** separate invoice line (Stripe one-off + retainer); NOT a plan tier — do not add plan names (retired-names rule, CLAUDE.md).
- **Ops:** monthly retainer work per SOP; per-agent task budget ≥ 20k tokens (`.claude/rules/task-budgets.md`).
- **Risks:** solo-founder delivery capacity → cap at 2 concurrent setups; scope creep → 1-page contract per `planning/managed-agents/README.md` sales process.

## Owner decision points (Tier C — cannot proceed autonomously)

1. Anthropic Managed Agents billing/quota tier + account provisioning (Phase 0 blocker).
2. Which design-partner tenant for Phase 1 (and confirming their plan is `agent_os`).
3. Pricing confirmation: agents included in `agent_os` vs. metered add-on (this plan assumes included; usage guard protects margin).
4. SOC 2 / DPA paperwork before first external tenant (Phase 1 blocker if partner asks).
5. Go/no-go at each phase exit.

## Autonomous-executable (agent team, Tier A/B)

- Run-log persistence migration + logging wire-up (Phase 0).
- E2E test matrix for success/503/auth/tenant-isolation/rate-limit paths.
- Dashboard lead-detail + document UI states (403/402/503/success/empty).
- Runbook, smoke script, SOP updates, admin health view extension.
- Provision script dry-run hardening (`scripts/managed_agents/provision.py`).

## Success metrics (rollout-wide)

- Health endpoint `configured` in prod; 503 stub path still contract-identical for unconfigured agents.
- Per agent: task-success ≥ 80%, human-override rate trending down, cost/run < 5% of tenant MRR.
- Line: ≥1 plan upgrade attributed to agents (Phase 2); ≥1 bespoke contract (Phase 3); zero tenant-isolation incidents ever.

## Out of scope / non-goals

- Async Managed Agents client / streaming run status (revisit if concurrency > a handful of runs per worker).
- New plan tiers or price changes — `chatbot`/`agent_os` stand.
- `codebase_reviewer` for tenants (internal dev tool only).
- Replacing widget chat runtime with Managed Agents — widget stays on direct `claude-sonnet-5` path.
- Self-serve agent builder UI — bespoke agents are white-glove (Phase 3) by design.

## Cross-refs

- `backend/routers/managed_agent_runs.py` · `backend/services/managed_agents_registry.py` · `backend/services/advisor_executor.py` · `backend/services/agent_os_gate.py`
- `planning/managed-agents/README.md` (pricing + sales process) · `docs/dev-knowledge/mcp-owner-server.md`
- `plans/managed-agents-production-rollout_plan.md` (prior draft, PR #522 — readiness-gate table §2 still applies per agent)
- `.claude/rules/propose-only-records.md` · `.claude/rules/task-budgets.md`
