# Managed Agents — Production Rollout Plan

Issue: #33. Author: fable5 (product/architecture steward). Status: proposed.

Rollout plan for the sellable **Managed Agents** product line onto Anthropic
Claude Managed Agents infrastructure. Grounds on what already exists in-repo:
- `backend/services/managed_agents_registry.py` — 8 env-var-gated agent handles
  (`lead_qualifier`, `document_drafter`, `codebase_reviewer`, `support_agent`,
  `structured_extractor`, `deep_researcher`, `field_monitor`, `data_analyst`) +
  `is_any_configured()` health gate + advisor-executor wrappers.
- `backend/routers/managed_agent_runs.py` — run invocation surface.
- Per-agent callers: `lead_qualification.py`, `document_drafting.py`,
  `support_agent.py`, `structured_extractor.py`, `appointment_booker.py`.
- `planning/managed-agents/` — 6 client-facing agent SPEC/AGENT/SOP packages +
  pricing ($1.5k–5k setup, $500/mo).

## 1. Rollout principle

Each agent is **independently gated by its `*_AGENT_ID` env var** — an unset ID
means the handle raises and the caller falls back (existing behavior). So rollout
is per-agent and reversible by unsetting one variable. No big-bang launch.

## 2. Readiness gates (all must be green before an agent leaves internal)

| Gate | Check |
|------|-------|
| Provisioned | `MANAGED_AGENTS_ENVIRONMENT_ID` + the agent's `*_AGENT_ID` set in Railway prod |
| Approval gates | Every destructive tool (send email, charge card, delete/overwrite a record) sits behind an Events approval gate — see `propose-only-records.md` |
| Tenant isolation | Agent session credentials are per-tenant; no cross-tenant tool/data access |
| Cost ceiling | Per-run token budget set (`task-budgets.md`); advisor-executor keeps spend near Sonnet |
| Observability | Runs logged with tenant + agent + tokens + outcome; failures alert |
| Eval | A golden-dataset structural eval exists and is CI-gated (pattern: `lead-qualifier-eval.yml`) |
| SOP | The `planning/managed-agents/<agent>/SOP.md` monitoring runbook is written |

## 3. Phases

### Phase 0 — internal dogfood (no external tenants)
- Provision `MANAGED_AGENTS_ENVIRONMENT_ID` + `LEAD_QUALIFIER_AGENT_ID` first
  (lead_qualifier is the most-exercised handle + already has an eval harness).
- Run against internal/synthetic tenants only. Confirm approval gates fire,
  logging is complete, and the golden eval passes.
- Exit criterion: 1 week, zero tenant-data leaks, eval ≥ threshold.

### Phase 1 — design-partner pilot (2–3 friendly tenants per agent)
- Enable one agent for a named pilot tenant via its `*_AGENT_ID`.
- Wire only the integrations that agent needs (Gmail/Slack/Stripe/Supabase via
  MCP), each behind an approval gate.
- 30-day iteration window (matches the sold package). Track: task success rate,
  approval-gate overrides, cost/run, escalations.
- Exit criterion: pilot tenant signs off + metrics within target.

### Phase 2 — general availability (per agent)
- Flip the agent from pilot to sellable. Publish its `planning/managed-agents/<agent>`
  package as the onboarding artifact.
- Onboarding = provision the tenant's `*_AGENT_ID`, run the SOP kickoff, wire
  integrations, hand over the approval-gate config.
- Order agents by readiness, not all at once: recommended sequence —
  lead_qualifier → document_drafter/document-processor → support_agent →
  structured_extractor → data_analyst → deep_researcher/field_monitor.

## 4. Safety + trust (non-negotiable)

- **Propose-only on customer/financial records** — agents draft, a human approves
  (`.claude/rules/propose-only-records.md`). No AI write path edits invoices or
  overwrites owner-entered fields.
- **Approval gates** on every outbound/destructive action, surfaced to the tenant.
- **Secrets** — integration tokens vault-encrypted at rest (`integration_key_vault`,
  GH #266); dedicated MCP keys, never widget keys.
- **Kill switch** — unset the agent's `*_AGENT_ID` to disable instantly; callers
  fall back to the existing non-agent path.

## 5. Observability + ops

- Every run emits: tenant_id, agent, tokens in/out, tool calls, approval outcomes,
  final status. Surface in an admin view (extend `admin_loop_health` /
  `managed_agent_runs`).
- Alert on: run error-rate spike, cost/run over budget, approval-gate override
  rate, escalation rate.
- Weekly: review per-agent eval trend + cost; monthly retainer work (prompt tune,
  integration adds) per the sold package.

## 6. Rollback

- Per-agent: unset `*_AGENT_ID` → instant disable, callers fall back.
- Whole line: unset `MANAGED_AGENTS_ENVIRONMENT_ID` → `is_any_configured()` false,
  all handles disabled.
- No schema migration is required to disable — the gate is env-var only.

## 7. Success metrics

- Per agent: task-success rate, human-override rate (lower = more trusted),
  cost/run, tenant retention at 60/90 days.
- Line: number of live agent-tenants, MRR from the $500/mo retainers, setup-fee
  revenue, gross margin after Anthropic infra cost.

## 8. Open owner decisions (Tier C — need the owner)

- Which design-partner tenants for Phase 1 (per agent).
- Anthropic Managed Agents billing/quota tier for prod scale.
- Whether any agent needs SOC 2 / DPA paperwork before its first external tenant.

## Cross-refs
- `planning/managed-agents/README.md` — product line + pricing
- `backend/services/managed_agents_registry.py` — handles + gates
- `.claude/rules/task-budgets.md`, `.claude/rules/propose-only-records.md`
- `.github/workflows/lead-qualifier-eval.yml` — the eval-gating pattern to mirror
