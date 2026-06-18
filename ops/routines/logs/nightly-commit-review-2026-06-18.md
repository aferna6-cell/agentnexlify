# Nightly Commit Review — 2026-06-18

**Run time:** 2026-06-18 UTC  
**Commits reviewed:** 29 commits from last 24h  
**Issues opened:** 2 (MEDIUM)  
**Fixes applied:** 1 (LOW — CLAUDE.md plan names)

---

## Triage Summary

### LOW risk (no action required)

| SHA | Description | Files |
|-----|-------------|-------|
| `af9a90b` | docs: auto-log bug fix | docs/dev-knowledge/bug-patterns.md |
| `8af5e94` | Fix em-dash in Tidio FAQ copy | frontend/src/pages/TidioAlternative.jsx |
| `0f0b12a` | Marketing pages: correct stale pricing/trial copy | 6 frontend files |
| `ecb5c34` | Support email: unify to support@agentnexlify.com | 22 files |
| `6bb8f10` | Welcome email: remove em dashes | backend/routers/auth.py |
| `727bf2e` | Pricing: AI Front Desk CTA reads 'Get Started' | frontend/src/pages/Home.jsx |
| `f6416a9` | subconscious: run 2026-06-17-pm | subconscious/ |
| `8de99ec` | Make /demo interactive product sample | frontend only |
| `ec22250` | Rename demo CTAs | frontend/src/pages/Home.jsx |
| `b2afaf2` | docs: auto-log bug fix | docs/dev-knowledge/bug-patterns.md |
| `9f76829` | Fix AgentShield CI (Linux runner) + brand-tagline | CI + frontend copy |
| `0104c14` | ops: morning-digest | ops log |
| `bc91e97` | ops: nightly-commit-review | ops log |

### MEDIUM risk (issues opened)

| SHA | Description | Risk | Issue |
|-----|-------------|------|-------|
| `93d9b85` | Stored conversation sentiment + intent (migration 154) | Migration not yet applied to production. Code degrades gracefully (nulls) but sentiment features are dark until applied. | [#329](https://github.com/aferna6-cell/agentnexlify/issues/329) |
| `20108e7` | TermsOfService + welcome email — commit self-flagged "flag for your review" | Legal copy changed. ToS section 4 rewritten. Needs human legal review. | [#330](https://github.com/aferna6-cell/agentnexlify/issues/330) |

### MEDIUM risk (reviewed, no issue needed)

| SHA | Description | Finding |
|-----|-------------|---------|
| `273c49b` + `13917a8` | Remove 7-day trial; charge immediately at signup | Intentional product decision. Test updated with explicit justification — Rule 10 compliant (commit doc explains why old contract was wrong). |
| `45a228a` | Checkout: disable Stripe Link | Good UX fix (stops unwanted wallet emails). Card-only is aligned with current payment collection. |
| `9e139a5` | Checkout: land non-wizard customers on /dashboard | Simple routing fix. Low blast radius. |
| `61947b9` | Gate AI Workforce to agent_os plan | Security hardening — closes access control gap. Tests included. Demo bypass correct. |
| `d7c574b` | Billing save-offer before cancel | Correct retention pattern. FTC/chargeback compliant. Uses existing change-plan path. |
| `8e523f1` | AI Workforce: 402 → upgrade prompt | Good UX: raw error → actionable upgrade CTA. |

### HIGH risk (reviewed, no issue needed)

| SHA | Description | Finding |
|-----|-------------|---------|
| `a7ece95` | Harden lead alerts (email+SMS, idempotent, demo-safe) | Good refactor. Fixes 3 real bugs: double-alert, missing tenant_id in SMS no-op, god-class bloat. Tests 100%. |
| `1f642f7` | Free-to-paid usage upgrade nudge | New feature — usage metering + frontend component + tests. No schema changes. Tenant-scoped correctly. |
| `e9474cb` | Front Desk Health overview card | New backend router + frontend card. Tests pass. client_id-scoped correctly. |
| `6894d53` | Outbound Outreach agent (TypeScript) | New agent in agent-service. No backend schema impact. |
| `2e00b5f` | Conversation Insights monthly auto-run | New scheduler job + tests. Main.py wiring clean. |
| `79ff623` | Instant KB from website URL in onboarding | New feature (router + service + tests). Not schema-touching on leads/conversations. |
| `cf297b2` | Add Conversation Insights agent (TypeScript) | TypeScript agent service only. |

---

## Fixes Applied

### LOW: CLAUDE.md plan names updated

**File:** `CLAUDE.md` — `### Plan names + prices`

CLAUDE.md listed `growth`, `autopilot`, `professional`, `enterprise` as current plan names. The actual codebase uses `chatbot` ($19.99/mo) and `agent_os` ($99.99/mo) since the 2026-06-15 repricing. Stale names in CLAUDE.md would cause future sessions to write wrong plan names in code. Updated to reflect `stripe_service.py` PLAN_PRICES as source of truth.

---

## CLAUDE.md Invariant Check

All commits checked against CLAUDE.md critical rules:

- **`client_id` not `tenant_id`** — `93d9b85` migration comment explicitly says "client_id-scoped conversations table". `conversation_enrichment.py` reads `chat_messages` (tenant_id scope) and writes `conversations` (client_id scope). PASS.
- **`status` not `lead_stage`** — no lead status columns touched. PASS.
- **No `from __future__ import annotations`** — no new FastAPI Python files with this import. PASS.
- **Widget byte-identical** — no widget JS changes in this batch. PASS.
- **Schema changes via numbered migrations** — `93d9b85` uses `migrations/154_conversation_sentiment_intent.sql`. PASS (but migration needs applying — see issue).

---

## No issues found in

- Auth/password/JWT changes
- Secrets or credential exposure  
- Tenant isolation violations  
- Double-writes or data corruption risks
