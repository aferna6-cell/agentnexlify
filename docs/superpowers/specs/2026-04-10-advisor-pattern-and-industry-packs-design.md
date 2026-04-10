# Advisor Pattern + Industry Packs — Design Spec

**Date:** 2026-04-10
**Author:** Claude (brainstorming skill) + Aidan
**Status:** Approved — ready for implementation

## Problem

1. **Opus cost ceiling.** Routing every task through Opus is 5x Sonnet cost. Routing everything through Sonnet alone misses architectural nuance on complex tasks.
2. **Vertical gap.** Product has 13 `business_profiles` (dental, hvac, salon, medical, legal, etc.) with widget-level personalization, but no per-vertical workflow packs (form presets, sequence templates, smart lists, automation rules). The "dentist use case" (book appts, 24/7 Q&A, dunning, review collection, intake, reactivation) is ~85% supported at the primitive level but 0% packaged as a turnkey industry template.

## Goal

1. **Advisor pattern (both dev-time and product runtime):** Opus advises, Sonnet/Haiku executes — near-Opus quality at ~1.3x Sonnet cost instead of 5x.
2. **Industry packs:** Turnkey workflow bundles seeded per tenant based on `business_type`, covering the 6 dentist-style problems (bookings, 24/7 Q&A, dunning, reviews, intake, reactivation) across all 13 supported verticals.

## Non-Goals

- No new database migration. Industry packs seed into existing `forms`, `sequences`, `smart_lists`, `automation_rules` tables with a `source='industry_pack:{key}'` tag for idempotency/upgrades.
- Not changing the existing `business_profiles.py` widget personalization. Packs are additive.
- Not touching the Claude Code hook system. Pattern is opt-in via subagent invocation.
- Not replacing the 3 existing managed agents (lead_qualifier, document_drafter, codebase_reviewer). Wrapping is opt-in per call site.

## Architecture

Three independent workstreams, built in order: A1 → A2 → B.

### Section A1 — Dev-time advisor pattern (`.claude/agents/`)

**Files:**
- `NEW .claude/agents/opus-advisor.md` — Opus, tools: `[Read, Grep, Glob]` only (read-only, no writes). Produces a written brief.
- `NEW .claude/agents/sonnet-executor.md` — Sonnet, full tool suite, consumes a brief from `opus-advisor`.
- `UPDATE .claude/rules/model-routing.md` — add "Advisor-Executor Pattern" section describing when/how to chain.

**Protocol:**
1. Main Claude receives complex task → invokes `opus-advisor` subagent with task description.
2. Advisor reads relevant files (read-only), produces brief: `{objective, files_to_touch, constraints, test_gates, known_gotchas, output_shape}`. Writes brief to `.claude/agent-comms/advisor-brief-{timestamp}.md`.
3. Main Claude invokes `sonnet-executor` with the brief path. Executor reads brief, executes, reports.

**Cost model:** Advisor ≈ 2-5k output tokens at Opus rate. Executor ≈ 20-50k at Sonnet rate. Net ≈ 1.3x pure-Sonnet cost. Quality approaches pure-Opus on planning-sensitive tasks.

**Trigger rules (in model-routing.md):**
- Auto-invoke advisor when task touches 3+ files, involves schema change, or involves security-critical code.
- Manual invoke via `advisor:` prefix in prompt.
- Skip advisor for mechanical work (renames, grammar, lookups).

### Section A2 — Product-runtime advisor pattern (`backend/services/`)

**Files:**
- `NEW backend/services/advisor_executor.py` — `AdvisorExecutorRunner` class.
- `UPDATE backend/services/managed_agents_registry.py` — add `advised_lead_qualifier()`, `advised_document_drafter()`, `advised_codebase_reviewer()` helpers that return an `AdvisorExecutorRunner` bound to the corresponding executor agent.
- `NEW tests/test_advisor_executor.py` — smoke test (mock HTTP, verify two-pass flow).

**Flow:**
```
runner = AdvisorExecutorRunner(
    executor_handle=lead_qualifier(),         # Sonnet-backed Managed Agent
    advisor_model="claude-opus-4-6",          # Direct Messages API, not Managed Agents
)
result = runner.run(task_prompt, resources=..., session_title=...)
```

Under the hood:
1. **advise()** — single `anthropic.messages.create()` call to Opus with a strict system prompt: "Output JSON with `{plan, constraints, risks, success_criteria}`. Do not execute." Returns ~300-500 output tokens.
2. **execute()** — creates a new Managed Agent session on the executor handle, injects the advice brief into the kickoff user message, streams to terminal state via existing `ManagedAgentsClient.run_until_idle()`.

**Why not use Managed Agents for the advisor pass?** Three reasons:
1. We don't need tools/MCP/skills during advice — it's a pure reasoning call.
2. Avoids double environment overhead.
3. Lets us swap the advisor model independently (Opus → cheaper reasoning model later) without touching the executor agent.

**Why keep Managed Agents for the executor pass?** Sessions, events, resources, files, and vault_ids are all already wired. Re-using that surface avoids duplicating session management.

**Opt-in per call site.** Existing direct `lead_qualifier()` calls keep working unchanged. New code that wants the advisor boost uses `advised_lead_qualifier()`. No behavior change for existing callers.

**Cost delta per run:** +~$0.015 for Opus advice. Saves estimated 30-50% on executor retry loops for complex tasks (internal measurement pending).

**Error handling:**
- If advisor call fails → fall back to pure executor (log warning, continue).
- If executor call fails → bubble `ManagedAgentsError` as today.
- Never let advisor failures block user-facing runs.

### Section B — Industry packs (`backend/services/industry_packs/`)

**Package layout:**
```
backend/services/industry_packs/
├── __init__.py               # Registry: load_pack(business_type) -> IndustryPack
├── base.py                   # @dataclass IndustryPack + seeding helpers
├── _shared/
│   ├── __init__.py
│   ├── form_presets.py       # Reusable form field sets
│   ├── sequence_templates.py # Appt reminder, dunning ladder, reactivation
│   ├── smart_list_templates.py
│   └── automation_rules.py   # Post-appt review, CSAT gate, overdue trigger
├── dental.py                 # Full dentist-6 pack
├── hvac.py
├── home_services.py
├── medical.py
├── salon.py
├── restaurant.py
├── legal.py
├── auto_shop.py
├── fitness.py
├── professional_services.py
├── retail.py
├── real_estate.py
└── default.py                # Fallback for unknown business_type
```

**`IndustryPack` dataclass:**
```python
@dataclass(frozen=True)
class IndustryPack:
    key: str                                      # "dental", "hvac", ...
    label: str                                    # "Dental Office"
    form_presets: list[FormPreset]
    sequence_templates: list[SequenceTemplate]
    smart_list_templates: list[SmartListTemplate]
    automation_rules: list[AutomationRuleTemplate]
    kb_seed_articles: list[KBSeedArticle]         # FAQs to seed tenant KB
```

**Seeding flow (`apply_pack_to_tenant()`):**
1. Resolve tenant → read `business_type` → pick pack via `load_pack(business_type)`.
2. For each pack item, insert with `source='industry_pack:{pack.key}'` tag.
3. Idempotent: check `source` + `name` before insert. Upgrading a pack (new version) updates rows matching `source='industry_pack:{key}'` and lets tenant customizations (identified by absence of that tag) survive untouched.
4. Returns a `SeedResult(forms: int, sequences: int, smart_lists: int, automation_rules: int, kb_articles: int)` for the response payload.

**Dentist pack content (the 6 problems):**

| # | Problem | Pack Item |
|---|---|---|
| 1 | Books appts + confirms + reminds | **Form preset:** "New Patient Appointment" (name, phone, email, preferred_date, insurance). **Sequence:** "Appointment Reminder" (-2d email, -2d SMS, morning-of SMS). **Automation rule:** `on appointment.created → schedule 'Appointment Reminder'` |
| 2 | 24/7 Q&A | **KB seed:** 20 dental FAQs (Delta Dental, crown cost, payment plans, hours, new patient process, emergency, cleaning cost, whitening, braces, insurance list). Widget chat already consumes tenant KB — no code change needed. |
| 3 | Dunning | **Sequence:** "Overdue Invoice Ladder" (d3 polite, d7 firmer, d14 final + escalate). **Automation rule:** `on invoice.due_date + 3d, status='overdue' → start 'Overdue Invoice Ladder'` |
| 4 | Reviews + unhappy interception | **Automation rule:** `on appointment.status='completed' → wait 2h → send CSAT`. **Automation rule:** `on csat_response.rating >= 4 → send GBP review link`. **Automation rule:** `on csat_response.rating <= 3 → create action_item 'Follow up with unhappy patient {name}' + suppress review link` |
| 5 | Intake | **Form preset:** "Dental New Patient Intake" (contact, emergency contact, insurance carrier+ID, medical history yes/no, medications, allergies, consent signature). **Automation rule:** `on appointment.created + lead.is_new=true → send intake form link via email + SMS` |
| 6 | Reactivation | **Smart list:** "Lapsed Patients (6mo+)" — `last_appointment_date < now - 180d AND status='active'`. **Sequence:** "Patient Reactivation" (email day 0, SMS day 3, email day 10 w/ discount). **Automation rule:** `weekly cron → for each lead in 'Lapsed Patients' without active 'Patient Reactivation' sequence → enroll` |

**Other 12 verticals:** Reuse the same `_shared` templates, swap content.
- **HVAC/home_services:** Appt → maintenance reminder (6mo). Dunning same. Review same. Reactivation → "seasonal tune-up due".
- **Salon:** Rebook at 4wk. Birthday promo. Referral request post-visit.
- **Legal:** Consultation follow-up. Retainer dunning. Matter status updates.
- **Restaurant:** Reservation confirm/remind. Special occasion follow-up. Loyalty push.
- **Medical:** Same as dental minus dental-specific FAQs.
- **Auto shop:** Service reminder (oil change 3mo). Estimate follow-up. Dunning.
- **Fitness:** Trial follow-up. Membership renewal. No-show reactivation.
- **Real estate:** Nurture sequences for buyers/sellers. Showing follow-up.
- **Retail:** Abandoned cart. Birthday. Win-back.
- **Professional services:** Consultation follow-up. Scope change alerts. Retainer renewal.

**Onboarding wire-up:**
- New endpoint: `POST /onboarding/apply_industry_pack` in `backend/routers/onboarding.py`.
- Body: `{business_type: str, dry_run: bool = false}` (if `business_type` omitted, reads from tenant record).
- Returns `SeedResult` + list of seeded item names.
- Called automatically by existing wizard at the "Industry Template" step (or opt-in from Settings).

## Testing Strategy

**A1:** Manual verification — invoke `opus-advisor` on a 3-file task, verify brief output shape. Invoke `sonnet-executor` with brief, verify execution matches brief constraints. No automated test (Claude Code agent tests are manual).

**A2:**
- Unit test with mocked `httpx` — verify `AdvisorExecutorRunner.run()` makes Opus call first, then session creation with brief injected.
- Smoke test with real API (gated on `ANTHROPIC_API_KEY` env + `MANAGED_AGENTS_ENVIRONMENT_ID` + `LEAD_QUALIFIER_AGENT_ID`) — runs a tiny task through the full pipe.
- Error path test: Opus call raises → runner falls back to pure executor.

**B:**
- Unit test for each pack — load, verify required sections present.
- Integration test for dental pack — seed into a test tenant, verify rows inserted with correct `source` tag, verify idempotency (second seed is no-op).
- E2E test: create test tenant with `business_type='dental'`, call `apply_industry_pack`, verify all 6 workflows show up in tenant's dashboard.

## Rollout

**A1:** Ship immediately — no user-facing surface. Subagent files + rule update.

**A2:** Ship behind feature flag `advisor_pattern_enabled` in `settings`. Default off. Enable after smoke-testing on dev tenant.

**B:**
- Ship dental pack first (most validated use case).
- Run `apply_industry_pack` on a test tenant, verify workflows fire correctly on simulated events.
- Ship remaining 12 packs in one batch once dental pattern is proven.
- Wire onboarding auto-apply after all packs are in.

## Open Questions (resolved pre-spec)

- **Migration?** No — use `source` tag on existing tables. (Approved)
- **Number of packs in scope?** Full 13. (Approved)
- **Build order?** A1 → A2 → B. (Approved)
- **Advisor pass via Managed Agents or direct Messages API?** Direct Messages — cheaper, simpler, independent model swap. (Designer call)

## Implementation Notes (2026-04-10 end-of-build)

- **Zero-migration tag storage**: Inspection of the actual schema (forms, smart_lists, automation_sequences, automation_rules, widget_configs) revealed that none of them have a dedicated `source` column. Rather than add a migration, the source tag is embedded inside the existing JSONB columns on each table:
  - `forms.settings_json.industry_pack_source`
  - `automation_sequences.trigger_config.industry_pack_source`
  - `smart_lists.filter_json._industry_pack_source`
  - `automation_rules.trigger_config.industry_pack_source`
  - `widget_configs.knowledge_base` (text) — wrapped in `<!-- industry_pack:{key} BEGIN vN -->` / `END` marker fences for idempotent upgrades

- **Idempotency** via Supabase `.contains()` JSONB containment queries before every insert. Re-running `apply_pack_to_tenant` on a seeded tenant is a no-op.

- **automation_rules trigger_type CHECK enum**: some pack-level trigger events (`weekly_cron`, `csat_response`, `invoice_overdue`) aren't in migration 087's enum. Rather than extend the enum (would require migration 101), the seeder maps them to the closest allowed value and stores the original in `trigger_config.original_trigger_event` for the automation engine to dispatch on. Mapping table in `backend/services/industry_packs/seed.py:_TRIGGER_EVENT_MAP`.

- **Advisor-Executor runtime wrapper**: shipped as `backend/services/advisor_executor.py`. Uses existing `call_claude_messages_sync` from `llm_runtime.py` for the Opus advisor pass, reuses `ManagedAgentsClient` for the executor pass. Opt-in per call site via `advised_lead_qualifier()` / `advised_document_drafter()` / `advised_codebase_reviewer()` in `managed_agents_registry.py`.

- **Dev-time advisor pattern**: shipped as `.claude/agents/opus-advisor.md` + `.claude/agents/sonnet-executor.md`. Model routing doc at `.claude/rules/model-routing.md` has a new "Advisor-Executor Pattern" section with trigger rules and cost model.

- **Tests shipped**:
  - `backend/tests/test_advisor_executor.py` — 11 tests, all passing
  - `backend/tests/test_industry_packs.py` — 11 tests (registry, alias resolution, trigger mapping, seed dry-run, seed fresh insert, seed idempotent skip, KB marker fencing), all passing
  - Full regression sweep: 70/70 across advisor + industry packs + managed_agents + llm_runtime + industry_presets

- **Shipped verticals** (13): dental (reference, 15 FAQs), medical, hvac, home_services, salon, restaurant, legal, auto_shop, fitness, professional_services, retail, real_estate, default.

## API Surface (shipped 2026-04-10)

- `GET  /api/v1/onboarding/industry-packs` — list all 13 packs with counts (role: any)
- `POST /api/v1/onboarding/{tenant_id}/apply-industry-pack` — seed a pack (role: owner/admin)
  - Body: `{business_type?: str, dry_run: bool = false}`
  - If `business_type` omitted, reads from tenant record
  - Returns `SeedResult`: per-component insert/skip counts + any errors

## References

- `backend/services/managed_agents.py` — existing Managed Agents HTTP client
- `backend/services/managed_agents_registry.py` — agent handle registry
- `backend/services/business_profiles.py` — existing 13-vertical widget personalization
- `backend/routers/onboarding.py` — onboarding flow
- `.claude/rules/model-routing.md` — current model routing rules
- `.claude/agents/architect.md` — existing subagent file format example
- Anthropic docs on advisor/executor: https://platform.claude.com/docs (Opus planning + Sonnet execution pattern)
