# Plan — Non-Technical Owner Readiness Roadmap

**Goal:** "Amazon Quick, but for small business." A non-technical owner (plumber, salon,
restaurant) signs up and goes live **self-serve in minutes**, no developer, no code,
no SSH. North-star activation metric stays: one automation fires in first 24h.

**Status:** roadmap created 2026-06-08. Sequences the 4 build targets the user locked
("all of these") + 2 unscheduled trust gaps. Source assessment: subagent eval
2026-06-08 (this branch session) + `audits/audit-onboarding-2026-04-21.md` +
`audits/audit-ops-automations-2026-05-01.md`.

**Rule:** one item = one session (`.claude/rules/one-task-one-chat.md`). Each item
below is independently grabbable. Run grill-me → tdd → build per `daily-skills.md`.

---

## Where we already are (do NOT rebuild)

Shipped since the April audit: 7-step signup wizard (`OnboardingWizardPage.jsx`),
auto-KB from website URL, OAuth integrations (Calendar/HubSpot/Facebook, no keys),
in-app Twilio phone provisioning (`settings/PhoneProvisioningCard.jsx`), missed-call
text-back end-to-end, appointment booking (`routers/appointments.py` + `widget_booking.py`),
pending-automation retry queue (`migrations/133`, Phase 4 — this branch).

The **automation engine is real and visible**. The gap is **self-onboarding** (site
install + payments) and **trust signals** (silent failures, generic agent).

---

## The blockers, sequenced (worst-leverage-first within dependency order)

### Item 1 — Activity-log parity  ⏱ S  ·  no dependencies  ·  QUICK WIN FIRST  ·  ✅ DONE 2026-06-08
**Problem (corrected 2026-06-08):** original claim ("3 of 4 automations silent") was
partly stale. Verified against code: email-sequences ALREADY logs `email_sequence_sent`
(`routers/email_sequences.py:1019,1188`); `widget_booking.py` handles `orders`, not
appointments. The two REAL gaps were appointment booking and document drafting.
**What shipped:** `appointment_booked` now emitted from `services/booking.py::create_appointment`
(single chokepoint — covers both widget + dashboard booking endpoints DRY); `document_drafted`
emitted from `services/document_drafting.py::draft_document` success path, plus a matching
`EVENT_LABELS` entry in `Dashboard/AutomationActivityCard.jsx` (`appointment_booked` label
already existed). Mirrors the row shape used by missed-call text-back. No schema change.
Phone numbers never written to activity metadata. Tests: `test_booking_overlap.py`,
`test_document_drafting.py`.
**Why first:** cheapest, makes the dashboard honest, zero dependencies, high trust.

### Item 2 — WordPress plugin (one-click widget install)  ⏱ L  ·  #1 BLOCKER
**Problem:** owner is handed a `<script>` tag + "paste before `</body>`." Non-tech owners
on WordPress/Wix can't do this. Single biggest blocker. WordPress ≈ 40% of SMB sites.
**Scope:** a WP plugin that takes the tenant's widget key and injects the existing
snippet (the byte-identical `frontend/public/widget/agentnexlify-widget.js` loader) — no
theme editing. Plus a "send install link to my web person" email fallback in
`WizardStepEmbed.jsx`.
**Plan coverage:** `plans/onboarding-v2_plan.md` Phase 6 (specced, `wordpress-plugin/` dir
absent on disk).
**Dependency:** none hard. Can start anytime. Keep widget JS byte-identical (CLAUDE.md inv #4).

### Item 3 — Integration health dashboard + "is my widget live?" probe  ⏱ M
**Problem:** revoked Calendar token, wrong webhook, failed welcome email, widget 403'd off
owner's own domain (`allowed_domains`) — all fail silently. Owner assumes AI is broken,
churns. Biggest churn-prevention lever.
**Scope:** `backend/services/widget_health.py` probe endpoint (is the loader present on
owner's URL?) + `IntegrationHealthDashboard.jsx` with status pills per integration +
`allowed_domains` editor UI (currently no UI → owner can self-403).
**Plan coverage:** `plans/onboarding-v2_plan.md` Phase 3 + 5 (specced, unbuilt).
**Dependency:** none hard; pairs naturally after Item 1 (both are "make state visible").

### Item 4 — Vertical agent presets + lead-qualifier control UI  ⏱ M  ·  DIFFERENTIATOR
**Problem:** one industry-agnostic prompt (`config/managed_agents.yaml`). Restaurant
scores delivery drivers as hot leads. Lead qualifier runs invisibly — no toggle, no
threshold, no "why was this lead hot" trail. This is the moat vs GoHighLevel ("vertical
KB per tenant," CLAUDE.md competitive positioning).
**Scope:** per-vertical preset prompts (plumber/salon/dental/restaurant/...) selectable in
onboarding; qualifier enable/disable + threshold + reasoning trail in
`AgentControlCenterPage.jsx`.
**Plan coverage:** NONE — only April audit H1/H2 rows. Write a spec first (write-prd).
**Dependency:** none hard.

### Item 5 — Stripe Connect (self-serve own payments)  ⏱ M-L  ·  SCAFFOLD SHIPPED (flag OFF), build-out gated
**Decision RESOLVED (2026-06-09):** Stripe Connect **Standard** (OAuth), store account-id
only (no secret key → no key-vault liability), zero application fee (pass-through, not a
marketplace cut). Rejected per-tenant key vault. Shipped inert behind
`tenant_payments_byok_enabled` (default OFF): migration 135 (additive `tenants` columns),
`backend/services/tenant_payments.py` resolver, seam in `invoices.py`, 8 tests. Prod behavior
unchanged (platform account) until the flag flips. **Remaining (gated, next session):** Connect
OAuth onboarding router, Settings "Connect Stripe" UI, `account.updated` webhook, connected-
account payment webhook routing. See `docs/dev-knowledge/schema-log.md` §135.

**Problem:** Stripe keys are env-vars set at deploy (`config.py:34-49`). Owner can't connect
their own payment processing without a developer in Railway.
**Scope:** Stripe Connect OAuth (platform-as-marketplace) OR per-tenant key vault + Settings
UI. **Architecture decision required first** — these are different products.
**Plan coverage:** `plans/onboarding-v2_spec.md` §6 / open question #2 (decision unresolved).
**Dependency:** BLOCKED on a billing-architecture decision. Resolve that (Fight-Me /
LLM-council on Connect-vs-key-vault) before building. Do last.

---

## Recommended execution order
1. **Item 1** (activity-log parity) — quick win, makes dashboard honest. 1 session.
2. **Item 2** (WordPress plugin) — biggest blocker. 1-2 sessions.
3. **Item 3** (health dashboard) — churn prevention. 1-2 sessions.
4. **Item 4** (vertical presets) — differentiator. 1 session spec + 1-2 build.
5. **Item 5** (Stripe Connect) — after billing decision. Decision session + build.

## Next concrete action (fresh session)
Start a clean session. First message: "Build Item 1 (activity-log parity) from
`plans/non-technical-readiness-roadmap_plan.md`." Run grill-me, then tdd-workflow.

## Open decisions for the user
- **Item 5:** Stripe Connect (marketplace model, platform takes a cut) vs per-tenant key
  vault (owner brings own Stripe). Pick before building Item 5.
- **Issues vs roadmap:** want me to run `prd-to-issues` to turn Items 1–5 into GitHub
  issues so they're parallel-grabbable? (Recommended if you'll hand any to the
  issue-to-pr-loop.)

## Cross-refs
- `plans/onboarding-v2_plan.md` — Phases 3/5/6 cover Items 2 & 3 (specced, unbuilt)
- `audits/audit-onboarding-2026-04-21.md` — original gap source (partly stale; 3 CRITICALs shipped)
- `audits/audit-ops-automations-2026-05-01.md` — Item 1 source
- `specs/ops-automation-surfacing_spec.md` — Phase 3a, COMPLETE (Phase 4 retry_worker shipped this branch)
