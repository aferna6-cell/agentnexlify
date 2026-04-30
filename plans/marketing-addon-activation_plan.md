# Marketing Add-on Activation + Adjacent Wins — Plan

**Created:** 2026-04-29
**Owner:** AI agent (Sonnet executor recommended)
**Source:** Tenant signal (Kevin, paying customer) + partner alignment thread (Dad + Niko)

---

## Context (read this first — no prior chat needed)

### Customer signal
Kevin is a paying tenant. His website has low traffic, so the chat widget is underused. He explicitly asked for the marketing tool: "We gotta get you the marketing tool" → "the marketing tool would probably be more helpful if it alleviates all the social media shit I have to do."

### Internal alignment thread (Dad + Niko, business partners)
- **Dad's position:** ICP = $250-500k revenue businesses, no CRM, mundane-task burdened. Bot ≠ marketing piece. Marketing helps anyone regardless of traffic.
- **Niko's position:** Bot value gated by traffic. Bigger biz already have CRMs. Worried bot route requires heavy outreach. Suggested CSV import of existing customer history → bot learns + helps net-new on top.
- **Synthesis (validated):** Both right. Marketing add-on = universal value (Dad). Bot value unlocked by historical data import (Niko's idea kills traffic-gating).

### Codebase state — VERIFIED via grep 2026-04-29
Marketing add-on is **already built and shipped**:
- `backend/routers/social_media.py` — social posting API
- `backend/routers/content.py` + `content_repurpose.py` — content engine
- `backend/services/local_seo_ai.py` — SEO automation
- `backend/services/addon_gate.py` — gates 7 features behind `tenants.marketing_addon_active` column at $49.99/mo, upgrade path `/billing/marketing-addon`
- `frontend/src/pages/SocialMediaPage.jsx` — UI
- `frontend/src/components/MarketingAddonUpsell.jsx` — upsell component

**Implication:** This is NOT a build-from-scratch task. It's activation + UX audit + one targeted feature gap (CSV import).

---

## Goals

1. Activate Kevin on marketing add-on this week (revenue + customer save)
2. Audit upsell UX so other tenants can self-serve activate
3. Ship CSV import to decouple bot value from traffic (resolves Niko's concern, opens broader ICP)
4. Document tier/positioning shift (marketing-first acquisition, bot upsell at autopilot+)

---

## Non-goals (do NOT do these)

- Don't build a new social media tool — exists already
- Don't redesign billing — add-on already wired through Stripe
- Don't change widget behavior
- Don't refactor `addon_gate.py` — works fine
- Don't touch `tenants.marketing_addon_active` schema — column exists and used

---

## Workstream 1 — Kevin Activation (P0, this week)

**Owner:** Human (Aidan)
**Effort:** 30 min sales + 1 hr onboarding session
**AI agent role:** None for the sales motion itself, but agent should prep onboarding artifacts.

### AI agent tasks
1. Read `backend/routers/social_media.py` and produce a 1-page tenant-facing capability sheet:
   - Which platforms are supported (verify in code, do not assume)
   - Posting cadence options
   - Approval workflow (autopilot vs draft-review)
   - Content types supported
   - Voice/brand training flow
   - Output: `docs/tenant-onboarding/marketing-addon-capabilities.md`
2. Read `frontend/src/pages/SocialMediaPage.jsx` and produce a 5-step onboarding checklist (file paths and screenshots not required, just the click sequence).
   - Output: `docs/tenant-onboarding/marketing-addon-first-session.md`
3. Verify the activation path works end-to-end:
   - Read `backend/routers/billing.py` for the marketing-addon Stripe flow
   - Confirm `tenants.marketing_addon_active` flips to `true` after webhook
   - Confirm gated routes return 200 (not 402) for activated tenant
   - Output: `docs/tenant-onboarding/marketing-addon-activation-checklist.md` (manual QA script)

### Acceptance criteria
- Capability sheet matches code (no aspirational features listed)
- Onboarding checklist is 5 steps or fewer
- Activation checklist runs against staging and passes

---

## Workstream 2 — Upsell UX Audit (P1, next week)

**Owner:** AI agent (Sonnet executor) + frontend-dev subagent
**Effort:** 4-6 hours

### Hypothesis
`MarketingAddonUpsell.jsx` exists but conversion is unknown. If Kevin had to be told via text rather than seeing the upsell in-app, the upsell is buried or unclear.

### AI agent tasks
1. Audit `MarketingAddonUpsell.jsx` placement:
   - Where is it rendered? (grep `<MarketingAddonUpsell` across `frontend/src/`)
   - Is it shown to all tenants without `marketing_addon_active=true`?
   - Is it conditionally shown based on activity signal (e.g., low widget conversation count → surface marketing as alternative)?
2. Read tracking events for the upsell component:
   - Are impressions logged?
   - Are clicks → `/billing/marketing-addon` logged?
   - If neither, propose minimal analytics instrumentation (PostHog or whatever exists in the repo)
3. Compare against Stripe data:
   - How many tenants without `marketing_addon_active=true` exist?
   - Of those, how many have <N widget conversations in last 30 days (low-traffic, Kevin-like)?
   - Output: a count, not a query plan
4. Produce a report: `audits/audit-upsell-conversion-2026-05-XX.md`
   - Findings (5 bullets max)
   - 3 concrete UX changes ranked by expected lift / effort
   - Decision request to human owner

### Acceptance criteria
- Report is ≤500 words
- 3 changes proposed, each with clear effort estimate (XS/S/M)
- No code changes shipped from this workstream — audit only

---

## Workstream 3 — CSV Import → Tenant KB (P1, in parallel with W2)

**Owner:** AI agent (Sonnet executor) + backend-dev + schema-guardian subagents
**Effort:** ~1 sprint (5-7 working days)

### Why
Niko's concern: bot value depends on traffic. Solution: import existing customer data so bot has context day-one regardless of traffic. Decouples bot value from incoming traffic. Also feeds the social/marketing engine with real customer language.

### Pre-build gate (mandatory)
Run `.claude/skills/grill-me/SKILL.md` first. Minimum 40 questions across these branches:
- Goal — what specific use case does CSV-imported data unlock?
- Scope — which tenant tables receive imports? (`leads`? `customers`? new table?)
- Data model — schema for imported rows. Column mapping UI? Required fields?
- API contract — endpoint shape, file size limits, auth, rate limits
- UI/UX — upload page placement, mapping UI, preview-before-commit, error reporting
- Edge cases — duplicates, malformed rows, partial success, encoding issues, PII
- Failure modes — half-imported state, transaction boundary, rollback
- Dependencies — does it touch widget chat KB? Marketing engine? Lead scoring?
- Performance — N rows × M tenants without N+1, async ingestion?
- Security — PII handling, tenant isolation (`client_id` not `tenant_id`!), RLS policies
- Tests — unit + integration + edge case coverage
- Rollout — feature flag? Tier-gated to autopilot+? All tenants?

### Then run `.claude/skills/write-prd/SKILL.md` → `specs/csv-import_spec.md`
### Then run `.claude/skills/prd-to-issues/SKILL.md` → GH issues
### Then build via `.claude/skills/feature-build/SKILL.md` (TDD)

### Hard requirements (non-negotiable per CLAUDE.md)
- `client_id` NOT `tenant_id` on any new column referencing tenant
- New migration file `migrations/NNN_csv_import_XXX.sql` (next sequential number)
- Pydantic models without `from __future__ import annotations`
- pgvector embeddings for imported customer notes if they feed widget KB
- Apply migration via `mcp__supabase__apply_migration`
- Update `docs/dev-knowledge/schema-log.md`

### Acceptance criteria
- Tenant can upload CSV up to N rows (TBD in grill-me)
- Mapping UI lets them align CSV columns to canonical fields
- Preview shows first 10 rows before commit
- Errors reported per row, not whole-file failure
- Imported data feeds at least ONE downstream system (widget KB, lead scoring, OR marketing content) — pick one in grill-me, not all three day one
- Tests: 80%+ coverage on new modules, 100% on tenant isolation paths
- Documented in `docs/tenant-onboarding/csv-import.md`

---

## Workstream 4 — Pricing & Positioning Memo (P2, no code)

**Owner:** Human (Aidan) with AI agent draft assist
**Effort:** 2 hours

### AI agent task
Draft `planning/decisions/2026-04-29-marketing-first-positioning.md`:
- Current state: 5 plan tiers (free, growth $99, autopilot $150, professional $250, enterprise $899) + marketing add-on $49.99/mo
- Problem: bot-led acquisition is traffic-gated (Niko correct)
- Proposal: marketing-first messaging on landing page; bot upsell at autopilot tier+
- Decision matrix (criteria + weights + tradeoffs per `.claude/rules/claude-usage-patterns.md` #5):
  - Customer save risk (Kevin churn likelihood)
  - Expansion revenue potential
  - CAC implications
  - ICP fit (Dad's $250-500k businesses)
  - Build cost (W2 + W3 only — no new tier creation)
- Open questions for human decision

### Acceptance criteria
- Memo is ≤2 pages
- Decision matrix has 4-6 weighted criteria
- 3 options compared (status quo, marketing-first lead, hybrid)
- No tier prices changed without human sign-off

---

## Sequencing

```
Week 1 (this week):
  W1 — Kevin activation (Aidan + AI agent prep artifacts)
  W4 — Pricing memo draft (AI agent)

Week 2:
  W2 — Upsell audit (AI agent)
  W3 — CSV import grill-me + write-prd (AI agent)

Week 3:
  W3 — CSV import build (AI agent + subagents, TDD)

Week 4:
  W3 — CSV import ship + Kevin gets it as a follow-on
  W2 — Upsell UX changes ship if approved
```

---

## Risks

1. **Kevin churns before activation** — mitigate by reaching out within 48 hours
2. **Marketing add-on doesn't actually do what Kevin needs** — W1 capability sheet exposes this early; if gap found, scope a focused fix BEFORE selling him
3. **CSV import scope creep** — grill-me gate + single-downstream-system rule prevents this
4. **Upsell audit reveals analytics gap** — instrument first, redesign second; don't fly blind
5. **Tier repositioning confuses existing tenants** — W4 is a memo, not a launch; human sign-off required

---

## Definition of Done

- Kevin: marketing add-on active, completed first onboarding session, sent feedback
- Upsell: audit shipped, 1 high-leverage UX change live in production
- CSV import: shipped behind feature flag, tested with at least 2 pilot tenants
- Pricing: decision memo signed by Aidan + filed in `planning/decisions/`

---

## AI agent execution rules

When running this plan:
- Honor `CLAUDE.md` and all rules in `.claude/rules/` (especially `user-rules.md` 1-12)
- Plan-first for any 2+ file change (Rule 1)
- Ask when confidence <80% (Rule 2)
- 15-message handoff summary (Rule 3, hook-enforced)
- Model routing: Opus plans, Sonnet executes, Haiku cleans (Rule 4)
- Self-verification line on every task completion (`rules/self-verification.md`)
- `/ultrareview` before merging any PR >20 lines (`rules/ultrareview.md`)
- No `tenant_id` on `leads`/`conversations` — use `client_id` (CLAUDE.md critical invariant)
- No `from __future__ import annotations` in FastAPI files
- Widget JS stays byte-identical between `widget/` and `frontend/public/widget/` (not relevant here, but rule applies)
- Schema changes only via numbered migrations in `migrations/`

## Cross-refs

- `CLAUDE.md` — project rules
- `.claude/rules/daily-skills.md` — grill-me + write-prd + prd-to-issues + tdd-workflow gates
- `.claude/rules/user-rules.md` — 12 engineering discipline rules
- `backend/services/addon_gate.py` — existing gating
- `frontend/src/components/MarketingAddonUpsell.jsx` — existing upsell UI
- `backend/routers/social_media.py` — existing social tool
