# Onboarding Friction Audit — 2026-04-21

**Target user:** non-technical small biz owner (plumber, cleaner, landscaper). Mobile-likely. No code skills. No DNS access. No dev team.

**Method:** 4 parallel Explore agents, one per friction area (signup+embed, KB, managed agents, integrations). File:line citations + friction rubric 1-5.

---

## Exec summary

### 5 findings
1. **Realistic onboarding today: 60-130 min, not 5.** Wizard demo completes in 3-5 min (OAuth + defaults + skip). Real setup to "widget live + KB useful + integrations wired" = 1-2 hours assuming tenant has dev skills. Non-tech owner ≈ blocked at multiple steps.
2. **Backend capability > frontend exposure.** Major features exist server-side with zero UI: `widget_configs.allowed_domains` column (no UI), `/api/v1/onboarding/{tenant}/auto-kb` URL-scrape endpoint (no wizard step), appointment_booker agent (code + env var, never called).
3. **Silent failures dominate.** Wrong webhook URL, revoked Google token, failed welcome email, disabled Stripe webhook all fail without tenant notification. Tenant assumes feature is broken, can't self-diagnose.
4. **Agents run invisibly.** Lead qualifier fires on every lead on Growth+ with zero tenant UI, no logs, no toggle, no thresholds, no vertical tuning. Free tier skips silently with no upgrade prompt.
5. **Installation on tenant's site = hardest step.** Wizard step 6 hands owner a `<script>` tag and says "paste before `</body>`." Non-tech owner doesn't know where `</body>` lives in WordPress/Shopify/Wix.

### 3 cross-cutting patterns
| Pattern | Impact | Examples |
|---|---|---|
| **Backend-ready / frontend-missing** | Huge leverage — redesign wires existing infra | `allowed_domains` UI, `/auto-kb` wizard step, industry pack KB seeds, appointment_booker endpoint |
| **Admin-only config via env vars** | Non-tech tenant has zero agency | Stripe/Twilio/Resend all env-var-gated, no Settings UI for keys |
| **Silent defaults with no tenant visibility** | Tenant can't tell if features work | Agent run logs, webhook health, email delivery, Calendar token refresh |

### Top fix list (preview — ranked in §5)
1. **Auto-KB in wizard** — wire existing `/auto-kb` to a wizard step. ~1 day. HIGH leverage.
2. **No-script embed for WordPress/Shopify/Wix** — CMS-specific install paths. ~1 wk. CRITICAL leverage.
3. **Integration health dashboard** — surface Stripe/Twilio/Resend/Calendar status. ~2 days. HIGH.
4. **Vertical agent presets** — per-industry lead qualifier prompts. ~3 days. HIGH.
5. **Post-install "widget live" verification** — health-check endpoint + status pill. ~2 days. CRITICAL.

---

## 1. Signup + widget embed

### Flow (10 steps)
| # | Step | File:line | Friction |
|---|---|---|---|
| 1 | Landing CTAs | `frontend/src/pages/Home.jsx` | 1 |
| 2 | Signup form (8 fields) or Google OAuth | `frontend/src/pages/SignupPage.jsx:38-340` | 3 / 1 |
| 3 | `/auth/register` POST | `backend/routers/auth.py:341-349` | 2 |
| 4 | Tenant provisioning (API key, widget_config, FAQ seed, welcome email) | `backend/routers/auth.py:206-277` | 0 |
| 5 | Redirect to `/setup` wizard | `SignupPage.jsx:149` | 1 |
| 6 | Wizard step 1: Business (name+city required) | `wizard/WizardStepBusiness.jsx:42-73` | 2 |
| 7 | Wizard steps 2-5: services, KB, customize, plan | — | 2-3 |
| 8 | Wizard step 6: Embed (display script tag) | `wizard/WizardStepEmbed.jsx:1-100` | 2 |
| 9 | Dashboard with onboarding checklist | `Dashboard/OnboardingChecklist.jsx` | 1 |
| 10 | **Paste script tag on tenant's site** | (offsite) | **4-5** |

### Hotspots
- **Step 10 (HTML paste, friction 5 blocker)** — non-tech owner must locate footer, edit HTML, or navigate Shopify/WordPress theme editor. No CMS plugins, no one-click install.
- **Step 2 signup (friction 3)** — 8 fields including city (unclear why needed). Google OAuth path exists but not promoted as primary.
- **No `allowed_domains` UI (friction 4 gap)** — column exists in `widget_configs`, blocked by widget server-side (`widget_chat_helpers.py:_check_origin`), but zero UI to set it. Creates both security risk (any origin can embed) AND support risk (owner blocked from own domain silently).
- **No post-install verification (friction 3 gap)** — no endpoint/UI answers "is my widget live on example.com?" Owner pastes code, refreshes site, sees nothing, has no diagnostic path.

### Dead ends
- API key generation failure rolls back widget_config insert → wizard step 6 shows "Loading…" forever.
- Welcome email delivery failure is side-effect (non-blocking), no retry, no tenant notification.
- Widget CDN (`app.agentnexlify.com/widget/agentnexlify-widget.js`) hardcoded in `WidgetPage.jsx:175` + `WizardStepEmbed.jsx:4`. CDN down = all tenant widgets dead silently.
- Origin 403 (wrong domain) surfaces in browser dev tools only — never reaches tenant UI.

### Time
- Fastest: 3 min (Google OAuth + skip wizard + copy embed).
- Realistic non-tech SMB: **25-40 min** (most of it on step 10).

---

## 2. Knowledge base setup

### Flow (7 steps)
| # | Step | File:line | Friction |
|---|---|---|---|
| 1 | Wizard steps 1-4 collect business info | `OnboardingWizardPage.jsx:67-121` | 3 |
| 2 | Wizard step 5: auto-generate KB via Claude Sonnet | `wizard/WizardStepKnowledgeBase.jsx:18-46` + `onboarding.py:588-670` | 1 |
| 3 | Optional edit in markdown textarea | `WizardStepKnowledgeBase.jsx:75-90` | 2-4 (markdown syntax) |
| 4 | Persist to `widget_configs.knowledge_base` TEXT | `onboarding.py:665` | 0 |
| 5 | Widget chat uses KB with null-state guard | `widget_chat.py:564-607` | 0 |
| 6 | Post-onboarding FAQ editor | `FaqManagerPage.jsx:1-50` | 4 |
| 7 | **Alt path: `/auto-kb` website crawl + Claude extract** | `onboarding.py:673-825` | **2 — but NO UI** |

### Hotspots
- **Markdown textarea editing (friction 4)** — raw markdown, no preview. Non-tech owner won't debug `##` vs `**`.
- **FAQ manager form-per-field (friction 4)** — 20 FAQs = 40 text inputs. No bulk CSV, no Google Docs paste.
- **`/auto-kb` endpoint unwired (friction 2 blocked by missing UI)** — backend crawls homepage + 4 linked pages, Claude extracts services + hours + 8-10 FAQs, persists to widget_configs + faq_entries. SSRF-validated. Zero frontend button or wizard step.
- **Industry packs seed automations, NOT KB** — `backend/services/industry_packs/` loads email sequences + forms, leaves KB blank. Plumber tenant gets generic output.
- **Hours as JSON (friction 3)** — wizard shows raw JSON textarea, not day-of-week picker.

### Dead ends
- Empty KB + no FAQs + business_type="other" → widget falls through to "setup incomplete" (`widget_chat.py:592`). Customer hangs.
- Owner skips KB, never returns → no email nag, no dashboard warning, widget remains generic.
- Markdown syntax errors not validated → saved KB renders poorly in prompt.
- Post-onboarding KB editor doesn't exist; owner must re-run wizard or hit API.

### Time
- Fastest: 2 min (accept autogen, skip edits).
- Realistic: **15-20 min** minimal, **30-50 min** proper.

---

## 3. Managed agent config

### Agents present
| Agent | File | Tenant config surface |
|---|---|---|
| lead_qualifier | `config/managed_agents.yaml:35` | **None** — plan gate only |
| appointment_booker | `backend/services/appointment_booker.py` | **Ghost — never called** |
| document_drafter | `config/managed_agents.yaml:86` | None |
| support_agent | `config/managed_agents.yaml:211` | None |
| structured_extractor, deep_researcher, field_monitor, data_analyst | yaml | Internal only |

### Flow
1. Tenant navigates to `frontend/src/pages/Automations/index.jsx` or `AgentControlCenterPage.jsx` — friction 1 — but **zero toggles exist**.
2. Plan gate auto-checks (`lead_qualification.py:290`) — silent skip on free tier.
3. Lead arrives, `widget_lead.py:82` fires `qualify_lead_background()` — friction 1 fully auto.
4. Result writes to `qualification_json/recommendation/qualified_at` — friction 1.
5. Result renders read-only in `Dashboard/LeadDetailDrawer.jsx:166-200` — friction 1.

### Hotspots
- **Zero tenant config UI (friction 5)** — no enable/disable, no prompt tuning, no threshold knobs, no tool permissions.
- **Static industry-agnostic prompt** — plumbing + salon + restaurant all scored with same rules. Restaurant qualifies delivery drivers as "hot" because "delivery" keyword.
- **No audit trail UI** — tenant can't see why lead was marked hot. Session ID in backend logs only.
- **Plan gate opaque** — Free tier leads skip qualification with no upgrade prompt.
- **No usage meter** — unbounded API cost, no tenant dashboard.

### Dead ends
- Agent ID env var not loaded → swallowed error (`lead_qualification.py:301`), tenant never knows feature is dead.
- Plan downgrade mid-month → new leads silently stop qualifying.
- Threshold miscalibration → wrong hot/cold calls, no feedback loop to correct.
- Appointment booker = ghost feature. Code + env var exist, no router endpoint, no UI, no DB writes.

### Time
- Fastest: 0 min (auto on Growth+).
- Realistic confident config: **30+ min** hunting for UI that doesn't exist.

---

## 4. Third-party integrations

### Matrix
| Provider | Required | Method | File | Friction |
|---|---|---|---|---|
| Google Calendar | Opt | OAuth redirect | `integrations.py:66-130` | **1** |
| Stripe | **Req** | Env var (admin only) + manual webhook | `config.py:38`, `stripe_webhooks.py:33` | **5** |
| Twilio | Opt | Env var + TWO manual webhooks | `config.py:34-36`, `twilio_webhooks.py:78` | **5** |
| Resend | Opt | Env var + manual webhook | `config.py:49`, `resend_webhooks.py:68` | **5** |

### Hotspots
- **Google Calendar is the only self-service integration.** OAuth redirect, token refresh, status visible in `IntegrationsPage.jsx:246`. Gold standard.
- **Stripe/Twilio/Resend are admin-only.** Env vars set at deploy time. No Settings page lets tenant paste their own keys. No per-tenant onboarding step. Non-tech owner can't wire their own Stripe.
- **Webhook copy-paste is silent-failure central.** Wrong URL → tenant pays, Stripe records subscription, AgentNexLiFy DB never activates, widget locked forever.
- **Twilio requires TWO separate webhook URLs** (voice missed-call + SMS reply). Either wrong → feature dark.
- **Zero tenant health UI** for Stripe/Twilio/Resend. IntegrationsPage shows Google only.
- **No "skip for now"** in wizard — assumes all env vars pre-configured.

### Dead ends
- Stripe webhook misconfigured → paid tenant, locked widget, no error.
- Twilio webhook wrong → missed call, no auto-SMS, no log to tenant.
- Google token revoked → `google_calendar.py:236` returns None, appointment syncs locally not to calendar, tenant unaware.
- Resend webhook missing → bounce events lost, tenant re-mails same broken addresses → reputation damage.

### Time per provider (non-tech SMB)
- Google Calendar: 3-5 min (fine).
- Stripe: 20-30 min (needs dev access to deploy env vars).
- Twilio: **30-45 min** (dual webhook pain).
- Resend: 15-20 min.

**Total integration time for non-tech SMB wanting SMS + email + payments: ~2 hours, assumes they can ssh into Railway or have a dev do it.**

---

## 5. Ranked fix list

Severity × effort matrix. Severity = impact on non-tech SMB activation. Effort = engineering days.

### CRITICAL (blocks activation for target user)

| # | Fix | Area | Severity | Effort | Leverage |
|---|---|---|---|---|---|
| C1 | No-script embed for WordPress, Shopify, Wix, Squarespace | Signup+Embed | CRIT | 5-8 d | 10x |
| C2 | Per-tenant Settings page for Stripe/Twilio/Resend keys (replace env vars) | Integrations | CRIT | 3-5 d | 8x |
| C3 | Auto-KB wizard step wiring `/auto-kb` endpoint | KB | CRIT | 1-2 d | 10x |
| C4 | Post-install "widget live on example.com" health check | Signup+Embed | CRIT | 1-2 d | 6x |
| C5 | Integration health dashboard (Stripe, Twilio, Resend, Calendar) | Integrations | CRIT | 2-3 d | 8x |

### HIGH (major friction reduction)

| # | Fix | Area | Severity | Effort | Leverage |
|---|---|---|---|---|---|
| H1 | Vertical agent presets (plumber/cleaner/salon/restaurant lead qualifier prompts) | Agents | HIGH | 3-5 d | 6x |
| H2 | Lead qualifier tenant UI (toggle, threshold, audit log, usage meter) | Agents | HIGH | 3-5 d | 5x |
| H3 | Visual hours picker (replace JSON textarea) | KB | HIGH | 1 d | 4x |
| H4 | Allowed_domains UI in WidgetPage + wizard | Signup+Embed | HIGH | 1 d | 4x |
| H5 | Industry KB seed content (plumbing/cleaning/salon/HVAC FAQs) | KB | HIGH | 2-3 d | 6x |
| H6 | FAQ bulk import (CSV, Google Sheets, or markdown paste) | KB | HIGH | 2 d | 4x |
| H7 | "Skip for now" + gentle nag for optional integrations | Integrations | HIGH | 1-2 d | 3x |
| H8 | Appointment booker MVP — wire existing code to router+UI | Agents | HIGH | 3-5 d | 6x |

### MEDIUM

| # | Fix | Area | Severity | Effort |
|---|---|---|---|---|
| M1 | Welcome email retry + failure notification | Signup | MED | 1 d |
| M2 | Widget CDN fallback | Signup+Embed | MED | 1 d |
| M3 | Post-onboarding KB editor UI (replace wizard-only) | KB | MED | 2 d |
| M4 | Plan-gate upgrade prompt on free-tier leads | Agents | MED | 1 d |
| M5 | Markdown preview for KB editor | KB | MED | 1 d |
| M6 | Google token refresh failure notification in UI | Integrations | MED | 1 d |

### LOW

| # | Fix | Area | Severity | Effort |
|---|---|---|---|---|
| L1 | Reduce signup form from 8 to 4 fields (name/email/biz_type/password) | Signup | LOW | 1 d |
| L2 | Promote Google OAuth as primary signup path | Signup | LOW | 0.5 d |
| L3 | Copy-edit wizard step labels for non-tech clarity | Wizard | LOW | 0.5 d |

---

## 6. Open questions (for Phase 2 grill-me)

1. **No-script embed scope** — which CMS platforms first? WordPress alone unlocks 40%+ of SMB sites. Shopify next. Wix + Squarespace lower priority. Full matrix vs MVP one-platform?
2. **Self-service Stripe Connect** — do we migrate from platform-owned Stripe keys to Stripe Connect (each tenant connects their own Stripe account)? Changes billing architecture.
3. **Twilio per-tenant numbers** — do we provision numbers programmatically via Twilio API, or require tenant to bring their own?
4. **Vertical coverage** — 4 verticals to start (plumbing, cleaning, salon, restaurant) vs 10? Where's the ROI line?
5. **KB quality signal** — what tells tenant "KB is good enough"? Word count? Coverage checklist? Preview chat?
6. **Feature flag rollout** — new onboarding for new signups only, or migrate existing tenants? If migrating, what triggers re-onboarding?
7. **Mobile vs desktop-first** — non-tech owners likely on phone. Does wizard work on mobile today? (Unchecked in audit.)
8. **Support escalation path** — when automation fails, what replaces "call support"? Chat widget with human fallback? Video walk-through?

---

## 7. Files referenced (consolidated for PRD cross-ref)

**Frontend:**
- `frontend/src/pages/SignupPage.jsx:38-340`
- `frontend/src/pages/OnboardingWizardPage.jsx:36-208`
- `frontend/src/pages/wizard/WizardStepBusiness.jsx:42-73`
- `frontend/src/pages/wizard/WizardStepKnowledgeBase.jsx:5-90`
- `frontend/src/pages/wizard/WizardStepEmbed.jsx:1-100`
- `frontend/src/pages/Dashboard/OnboardingChecklist.jsx`
- `frontend/src/pages/WidgetPage.jsx:40-182`
- `frontend/src/pages/FaqManagerPage.jsx:1-50`
- `frontend/src/pages/IntegrationsPage.jsx:246`
- `frontend/src/pages/Automations/index.jsx`
- `frontend/src/pages/AgentControlCenterPage.jsx`
- `frontend/src/pages/Dashboard/LeadDetailDrawer.jsx:166-200`

**Backend:**
- `backend/routers/auth.py:206-349`
- `backend/routers/onboarding.py:255-825`
- `backend/routers/widget_config.py:132-150`
- `backend/routers/widget_chat.py:564-607`
- `backend/routers/widget_chat_helpers.py:212-227`
- `backend/routers/widget_lead.py:82-150`
- `backend/routers/integrations.py:66-130`
- `backend/routers/stripe_webhooks.py:33-48`
- `backend/routers/twilio_webhooks.py:78-186`
- `backend/routers/resend_webhooks.py:68`
- `backend/routers/managed_agent_runs.py:13-26`
- `backend/services/lead_qualification.py:49-356`
- `backend/services/appointment_booker.py`
- `backend/services/google_calendar.py:119-236`
- `backend/services/industry_packs/`
- `backend/config.py:34-49`

**Config:**
- `config/managed_agents.yaml:35-276`
- `.env.managed_agents`

**Migrations:**
- `migrations/077_widget_knowledge_base.sql`
- `migrations/081-kb-articles-and-sources.sql`

---

## Next phase

Phase 2: **grill-me gate** — batch 40+ questions across 12 branches before writing PRD. Covers §6 open questions + goal/scope/data/rollout/security/tests not yet framed.
