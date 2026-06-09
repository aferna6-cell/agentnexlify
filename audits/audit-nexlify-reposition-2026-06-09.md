# Audit — Repositioning AgentNexLiFy as "Amazon Quick Suite for Non-Technical SMB Owners"

**Date:** 2026-06-09
**Scope:** `agentnexlify` (main repo) + `Agent-Nexlify-OS` (standalone demo repo)
**Question:** Where do we stand against the target positioning — a conversational agentic workspace ("talk to your business, it answers and acts") for non-technical small-business owners — and what gaps remain?

---

## 1. Verdict (TL;DR)

The repositioning is **already ~60% built, not a pivot**. The Agent OS v2 engine (orchestrator + 8 department-head agents + honest trace + draft/approval) is spec'd, QA'd 12/12, and vendored into `agent-service/src/agent-os/` (PRs #203–#208, migrations 123–132). What's missing is the back half of the merge plan and everything that turns drafts into outcomes:

1. **Phase 4 cutover not done** — two agent frameworks coexist (old Python `os_workers/` layer + new TS engine). Half-migration state, violates user rule 8 if left.
2. **Agents draft but do not act** — draft approval logs to console in the demo path; real send (SMS/email/calendar) exists as Python `os_actions/` handlers but is not wired through the new engine end-to-end.
3. **The dashboard is the opposite of the positioning** — 106 form/table SaaS pages vs. one conversational surface. Quick Suite's pitch is "one chat box, agents do the work"; ours still leads with the widget + dashboard.
4. **Launch readiness is NO-GO (59.9%, 2026-04-25)** — independent of positioning: GDPR deletion, cookie consent, uptime monitoring, plan gating, insurance quote.
5. **v2 consolidation refactor unfinished** — `departments.ts` defines 8 heads, but 24 individual agents still register separately; skill dispatch is heuristic; Generalist not eliminated.
6. **Dual-repo drift risk** — OS repo keeps evolving (RunStore extraction #5, hardening #4) while a vendored copy lives in `agent-service/`. The OS repo's own `PROD_MERGE_PLAN.md` still says "merge not started," which is stale.

Estimated distance to a demoable repositioned product: **~4–6 weeks of focused work** (cutover + real send + conversational dashboard surface). Distance to *sellable*: add the launch-rubric blockers on top.

---

## 2. The target model (what "Amazon Quick Suite" means here)

Amazon Quick Suite (AWS, GA 2025-10) is an agentic workspace: one conversational entry point backed by capability agents —
Quick Index (unified org data), Quick Research, Quick Sight (NL business intelligence), Quick Flows (NL-built simple automations), Quick Automate (multi-agent process automation) — with human approval gates and per-action auditability. Sold to enterprises (~$20/user/mo base).

Our translation for non-technical SMB owners:

| Quick Suite capability | SMB-owner equivalent | Nexlify asset today | Status |
|---|---|---|---|
| One chat entry point | "Ask Maya anything" orchestrator | `_orchestrator.ts` + `_classifier.ts` (Haiku routing, confidence rules, clarify/decline) | **Built, vendored** |
| Capability agents | 8 department heads (Sales, Marketing, CS, Ops, Invoicing, Accounting, Admin, People) | `departments.ts` + 24 agent impls, v2 spec | **Built; consolidation refactor pending** |
| Quick Index (unified data) | SharedContext: widget history, leads, appointments, invoices, KB | `SharedContextProvider` seam; `GET /api/v1/os/context` per merge plan; pgvector KB per tenant | **Seam built; KB feed stubbed** |
| Quick Sight (NL BI) | "How did this week go?" → weekly briefing, widget-activity direct answers | weekly_briefing agent + orchestrator direct answers; 8 analytics pages (form-based) | **Briefing built; NL-over-analytics absent** |
| Quick Flows / Automate | Approved drafts → real sends; automations in plain English | `os_actions/{sms,email,crm,calendar}.py`; automation_engine (advanced flows stubbed); drafts log to console in demo path | **Biggest gap** |
| Approval + audit | Draft → approve/reject; honest trace | `Draft.requiresApproval`, hardcoded `never_auto_send` (complaint/quote/payment), `TraceStep` honest-load trace, `os_engine_telemetry` (migration 131) | **Built — this is the moat-grade asset** |
| Workspace UI | Owner's daily surface IS the chat | Demo UX at agent-nexlify-os.vercel.app; main dashboard = 106 traditional pages | **Demo only; main product not converted** |

Differentiators we have that Quick Suite can't follow down-market: widget-as-data-source (the embedded widget feeds real customer conversations into agent context), vertical packs (contractors/salons/dental/health), per-tenant KB, and pricing an SMB can buy ($99–250/mo vs. enterprise seats).

---

## 3. Current state — evidence

### 3.1 Main repo (`agentnexlify`)
- **Scale:** 87 routers (~36.8k LOC), 86 services, 106 dashboard pages (~45.4k LOC), 135 migrations, v0.1.0, ~600+ commits. Production on Railway/Vercel/Supabase; 5 design-partner testers (MTOptions top).
- **Agent OS v2 landed:** PR #203 "Adopt demo agent framework as Agent OS orchestration core"; #204 widget un-hijacked (opt-in via migrations 130–132); #205 agent-service auth hardening; #207–208 v2 response shape + routing chip in dashboard. Nightly reviews clean 3 runs straight.
- **Vendored engine verified:** `agent-service/src/agent-os/agents/` contains `_orchestrator.ts`, `_classifier.ts`, `departments.ts`, `_run-store.ts`, and all agent dirs. RunStore seam present (`lib/providers/run-store.ts`).
- **Old layer still alive:** `backend/services/os_thread_runner.py`, `os_workers/` (8 files), `managed_agents_registry.py`, Python `orchestrator.py` — slated for retirement in merge-plan Phase 4 (`plans/agent-os-demo-merge_plan.md` §3).
- **Monetization:** Stripe end-to-end (checkout, portal, webhooks, dunning partial); plan-tier gating stubbed in `usage_meter.py`; cancel UX partial.
- **Launch rubric** (`planning/launch-readiness-rubric.md`, scored 2026-04-25): **157/262 = NO-GO**. Open HIGH item: insurance quote (partner). Zeros: GDPR deletion endpoint, cookie consent, DPA template, external uptime monitor, log retention, status page, public case study, outreach templates.
- **Managed-agents product line** (`planning/managed-agents/README.md`): 6 sellable agents at $1.5–5k setup + $500/mo — high-touch services motion, distinct from the self-serve OS positioning. Needs an explicit decision on how it folds in (likely: becomes the "done-for-you" tier of the same 8 departments).

### 3.2 Standalone repo (`Agent-Nexlify-OS`)
- **Phases 0–5 complete**; live demo (Vercel, demo bypass, seeded Sunset Auto Care); 12/12 QA scenarios pass with LLMs on; median cost $0.0049/run; 36 test files incl. seam-isolation and SQLite↔Postgres schema-parity tests; runs fully offline via deterministic local composer.
- **v2 spec done, code transitional:** 18 specialists → 8 departments designed; `defineDepartment()` + `resolveSkill()` exist, but agents are still individual registry entries and the Generalist survives in code.
- **Phase 6 (real actions, triggers, production data) deferred by design.** Draft approval = `console.log`. Lead Triage + Appointment Reminder fully implemented but triggers unwired.
- **Single-tenant** (`userId` scoping); multi-tenancy inherited at merge per `docs/INTEGRATION.md`.
- **Stale doc:** `docs/PROD_MERGE_PLAN.md` says merge not started — contradicted by main-repo PRs #203–#208. Per `fill-instructions-before-guessing.md`, fix at source when next touching that repo.

---

## 4. Gap list, ranked

### P0 — blocks the repositioned product from existing
| # | Gap | Evidence | Effort |
|---|---|---|---|
| G1 | **Phase 4 cutover**: route all OS traffic through the TS engine; retire `os_thread_runner`, `os_workers/`, Python orchestrator; demote `managed_agents_registry` to documented fallback | `plans/agent-os-demo-merge_plan.md` §3 Phase 4; files still present in `backend/services/` | ~1 wk + separate dead-code-sweep session |
| G2 | **Real send**: approved draft → actual SMS/email/calendar/payment-link via existing `os_actions/` handlers, behind `feature_agent_os_autosend`, honoring hardcoded `never_auto_send` | `os_actions/{sms,crm,calendar}.py` exist; demo path logs to console; merge plan Phase 2 channel mapping | ~1–1.5 wk |
| G3 | **2-tenant isolation test green** on the new engine (merge-plan blocking gate) — verify it exists and runs in CI, not just planned | merge plan Phase 1 "Multi-tenancy gate (blocking)" | days (verify) → 1 wk (if absent) |
| G4 | **Conversational dashboard surface**: `/agent-os` chat (OrchestratorChat + TraceView + DraftPanel) becomes the default landing surface of the dashboard, with the 106 pages demoted to drill-down views | merge plan Phase 3; #207/208 started this | ~1–2 wk |

### P1 — blocks selling it
| # | Gap | Evidence | Effort |
|---|---|---|---|
| G5 | v2 consolidation refactor: 8 department registry entries with internal skill dispatch; delete Generalist | OS repo `departments.ts` transitional; v2 spec §8.2 | ~1 wk |
| G6 | Plan-tier gating enforced (which departments/sends per plan) + cancel UX finished | `usage_meter.py` stub; rubric 3.4/7.4 | ~1 wk |
| G7 | Launch-rubric soft-launch path: GDPR deletion endpoint, cookie consent, external uptime monitor, insurance quote (partner) | rubric: 157/262, needs +3 weighted + HIGH zero closed | ~1 wk eng + partner actions |
| G8 | Dual-repo convergence: declare `agent-service/` canonical, freeze OS repo to spec/demo, or set up a sync check; fix stale `PROD_MERGE_PLAN.md` | RunStore #5 landed in OS repo post-vendoring; drift unverified | days |
| G9 | Positioning artifacts: README/CLAUDE.md/landing still say "chat widget captures leads"; competitive frame still GoHighLevel-only. Rewrite around "AI staff for your business — one conversation"; widget becomes a feature, the OS becomes the product | `CLAUDE.md` line 3; `Home.jsx` hero | days (copy) + pricing decision |

### P2 — strengthens the wedge
| # | Gap | Evidence | Effort |
|---|---|---|---|
| G10 | NL-over-analytics ("Quick Sight" move): orchestrator direct answers over the 6 analytics domains, not only widget activity | direct-answer pattern exists in `_orchestrator.ts` | ~1 wk |
| G11 | Vertical packs tuned per department (Automotive or Home & Trade first — demo data already Automotive) | v2 Decision 3; main repo has 4 vertical FAQ/automation packs to reuse | ~1–2 wk/pack |
| G12 | KB feed into SharedContext (`kb` field currently stubbed) — per-tenant pgvector KB is the stated moat; agents should cite it | OS repo `_shared-context.ts`; main repo `knowledge-base/` infra | ~1 wk |
| G13 | Managed-agents line repackaged as "done-for-you" tier of the same 8 departments (avoid two competing agent stories) | `planning/managed-agents/README.md` | decision + docs |
| G14 | Onboarding rewrite: 2-step industry cluster picker + "first conversation" replaces wizard-first onboarding | merge plan Phase 3; `onboarding-v2_spec.md` | ~1 wk |

---

## 5. Risks

1. **Half-migration freeze (G1).** Two engines serving overlapping concerns is the highest-entropy state in the codebase right now; every week it persists, new code couples to the wrong layer. The merge plan itself rates "two frameworks coexist" a Med risk *during* migration — it is now the steady state.
2. **Cross-tenant leak on the new path.** The TS engine pulls SharedContext over HTTP by accountId. The blocking isolation test from merge-plan Phase 1 must be verified as real and in CI before any beta tenant touches it.
3. **Demo-to-production credibility gap.** The demo's magic (instant, honest, cheap) is partly the deterministic composer and seeded data. Real tenants bring sparse data — the `skipped_no_data` / honest-trace pattern is the right defense, but cold-start UX for a tenant with 0 leads needs design.
4. **Positioning whiplash for the 5 design partners.** They bought a widget. The repositioning keeps the widget (as data source + channel), so message it as "your widget now has a staff behind it," not a product swap.
5. **Cost at scale.** $0.0049/run median is excellent; budget logic (`task-budgets.md` tiers) must be wired into agent-service before autonomous triggers (lead triage cron, appointment reminders) multiply run volume.

---

## 6. Recommended sequence (6 weeks to repositioned beta)

1. **Wk 1:** G3 (verify/build isolation test) → G1 cutover behind flag for one internal tenant; G8 declare canonical copy + fix stale OS-repo merge plan.
2. **Wk 2:** G1 complete + dead-code sweep (separate session per audit/fix rule); G5 v2 consolidation in the canonical copy.
3. **Wk 3–4:** G2 real send through `os_actions/` with approval gates + `never_auto_send`; wire Lead Triage + Appointment Reminder triggers.
4. **Wk 4–5:** G4 conversational dashboard default surface; G14 onboarding-as-first-conversation.
5. **Wk 5–6:** G6 plan gating, G9 positioning copy + pricing decision, G7 soft-launch rubric items; rescore rubric.
6. **Then:** G10–G12 (NL analytics, vertical pack #1, KB feed) as the differentiation sprint while beta tenants dogfood.

**Decision needed from Aidan (carried over from merge plan §6, still open):** agent-service SDK convergence; cluster-picker vs. flat business_type; cost/routing-log table choice; agent-service hosting split. Plus new: managed-agents tier framing (G13) and post-repositioning pricing.

---

*Grounded in: `plans/agent-os-demo-merge_plan.md`, `planning/launch-readiness-rubric.md`, `planning/managed-agents/README.md`, `planning/vertical-positioning-2026-04-18.md`, `agent-service/src/agent-os/*`, `backend/services/os_*`, `migrations/123–132`, main-repo PRs #203–#208; `Agent-Nexlify-OS`: `docs/AgentNexLiFy_Agent_Library_v2.md`, `docs/INTEGRATION.md`, `docs/PROD_MERGE_PLAN.md`, `AgentOS_PostQA_Round2_findings.md`, `src/agents/*`, commits through `7c27d55`. Amazon Quick Suite reference: aws.amazon.com/quicksuite (announcement + FAQs).*
