# Feature: Onboarding v2 — Spec

**Status:** draft
**Owner:** Aidan
**Created:** 2026-04-21
**Tenant scope:** gated (feature flag `onboarding_v2`)
**Priority:** P0
**Phase:** 3b (parallel with ops-automation, marketing-automation, self-maintenance)
**Schema reference:** `audits/existing-infra-reference-2026-04-21.md` (CANONICAL — all schema decisions below cite this)
**Flow audit:** `audits/audit-onboarding-2026-04-21.md`
**Migration range:** 115-117 (111-113 reserved marketing; 114 reserved ops-auto)

---

## 1. Executive Summary

Today's onboarding works for a tenant who owns a developer. A plumber doesn't. Real activation — widget live on the tenant site + KB populated + Stripe/Twilio/Resend wired — takes 60-130 minutes today, most of it spent copy-pasting script tags into a footer the owner can't find, and pestering a developer for env var edits. Non-tech owners abandon at step 10 (HTML paste) or step "Integrations" (admin-only env vars).

Onboarding v2 collapses that to under 2 hours, with the script-paste step replaced by a WordPress plugin, API keys entered in a Settings UI instead of env vars, and the KB auto-compiled from the tenant's existing website URL. Six vertical presets (plumbing, HVAC, cleaning, power-washing, landscaping, electrical) seed services, FAQs, and hours so the wizard starts 70% filled instead of blank. A post-install health check tells the owner "widget is live on example.com" without opening devtools.

This PRD is the friction-cutting half of Phase 3. It is ship-behind a feature flag, additive to existing v1 signups, mobile-tested on iPhone and Android, and explicitly reuses pre-existing schema (see §15).

---

## 2. Goals

Primary metric: **time-to-first-lead drops from current 60-130 min median to under 2 hours for a non-tech SMB owner working alone on a phone.**

Secondary metrics:

- Signup form completion rate: current 42% (8 fields) → target 75% (4 fields + Google OAuth primary)
- Wizard completion rate: current 68% → target 90%
- Widget-live-on-site rate (health check green within 24h of signup): current ~40% → target 85%
- KB "Ready to launch" badge achieved within onboarding session: current ~15% → target 70%
- Integration health dashboard usage in first 7 days: target 60% of tenants view it at least once

Hours saved per tenant onboarding (anchor metric per `project_value_prop_framework.md`): current 0 (friction-heavy) → target 1-2 hours of owner time recovered per signup, amortized across first-month revenue.

Dollars preserved per converted tenant (post-conversion retention angle): every tenant who completes onboarding and has widget live is worth $99-899/mo. Cutting abandonment from 32% → 10% at $99/mo recovers ~$22/tenant/mo in expected LTV.

---

## 3. Non-Goals

Explicitly OUT of scope for v1:

- Shopify plugin install (V2 — architecturally similar to WordPress, deferred to avoid scope creep)
- Wix plugin install (V2)
- Squarespace plugin install (V2)
- Stripe Connect migration (tenants still bring their own Stripe keys in v1; platform-held billing is V2)
- Twilio number auto-provisioning (tenant brings own phone number + credentials in v1)
- Post-onboarding KB editor UI (wizard-step-only in v1; editor UI deferred to V2 per audit §M3)
- Markdown preview for KB editor (V2)
- Google Calendar token-refresh failure notifications (V2 — reuses existing `integrations` table, but UI copy deferred)
- Team management / multi-user invites during onboarding (unchanged from v1 spec)
- Custom domains / white-labeling (unchanged from v1)
- Re-onboarding existing v1 tenants (v2 flag applies to new signups only)

---

## 4. User Stories

Protagonist: non-technical SMB owner. Examples below use Maria (45, owns MN Plumbing, 3 techs, no developer, does admin from iPhone in her truck).

1. As Maria, I want to sign up with Google in one tap so I don't fill out 8 fields on a phone keyboard.
2. As Maria, I want the wizard to read my existing website and fill in my services, hours, and FAQs automatically so I'm not typing them from scratch on my phone.
3. As Maria, I want to pick "plumbing" and have the system pre-seed typical services (drain cleaning, water heater repair, sewer line) so I can tweak a 70%-filled form instead of starting from zero.
4. As Maria, I want a WordPress plugin that installs in one click via the WP admin, so I never touch HTML or a theme editor.
5. As Maria, I want a Settings page where I paste my own Stripe, Twilio, and Resend keys — without emailing a developer — and a green/yellow/red light for each.
6. As Maria, I want to see "Your widget is live on mnplumbing.com" confirmed by the system, not inferred from refreshing my site in a panic.
7. As Maria, I want to upload a CSV of my 20 FAQs from a Google Sheet export, not type each question into its own form field.
8. As Maria, I want to pick my hours with a visual weekly grid on my phone, not edit JSON.
9. As Maria, I want to restrict my widget to only load on mnplumbing.com so a competitor can't embed it somewhere else.
10. As Maria, I want a badge that says "Ready to launch" when my KB has enough content, so I know I've done enough to go live.
11. As Maria, if the welcome email doesn't land, I want the system to retry quietly without dropping it, and tell me if all three retries failed.
12. As a developer reading this codebase in 6 months, I want the wizard to reuse the existing `integrations` table (mig 007) and `widget_configs` table (mig 001) — not a parallel `tenant_secrets` or duplicate table that fragments tenant config.

---

## 5. Success Metrics

| Metric | Baseline | Target | Measurement |
|---|---|---|---|
| Time-to-first-lead (median) | 60-130 min | <120 min | timestamp delta between `auth/register` and first row in `leads` WHERE `client_id = tenant` |
| Signup form completion rate | 42% | 75% | `wizard_started` events / `signup_landing_view` events |
| Wizard completion rate | 68% | 90% | `wizard_completed` / `wizard_started` |
| Widget-live rate (health check green within 24h) | ~40% | 85% | `GET /api/v1/widget/health` returns `{loaded: true, reachable: true}` |
| KB "Ready to launch" badge in-session | ~15% | 70% | `kb_badge_ready` event before wizard exit |
| Welcome email delivery (inc. retries) | ~92% | 99% | `email_events.status = 'delivered'` within 12 min of signup |
| Stripe/Twilio/Resend keys configured in v2 | N/A | 50% of paid tenants | count of `integrations` rows where `provider IN ('stripe','twilio','resend')` per tenant |
| Mobile signup share | unknown | measured | User-Agent header on `/auth/register` POST |

Dashboards: `frontend/src/pages/Analytics/OnboardingFunnelPage.jsx` (new, ships with v1 of this PRD).

Event taxonomy additions: `onboarding_v2_started`, `onboarding_v2_step_completed` (step 1-5), `onboarding_v2_completed`, `auto_kb_invoked`, `auto_kb_succeeded`, `auto_kb_failed`, `vertical_preset_applied`, `widget_health_check`, `integration_key_saved`.

---

## 6. Design — Data Model, API, UI

### 6.1 Data Model

**Guiding rule (per `audits/existing-infra-reference-2026-04-21.md`):** EXTEND existing tables, do not CREATE parallel ones. Every schema change below either ALTERs an existing table or adds a genuinely novel table.

#### 6.1.1 Extend `widget_configs` (migration 001, ALTER only — no parallel config table)

Migration `115_widget_configs_onboarding_v2.sql`:

```sql
ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS onboarding_version TEXT
    DEFAULT 'v1'
    CHECK (onboarding_version IN ('v1', 'v2'));

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS ready_to_launch BOOLEAN DEFAULT false;

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS readiness_criteria JSONB
    DEFAULT '{"services_count": 0, "hours_filled": false, "faqs_count": 0, "logo_uploaded": false}'::jsonb;

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS vertical_preset TEXT
    CHECK (vertical_preset IS NULL OR vertical_preset IN (
      'plumbing','hvac','cleaning','power_washing','landscaping','electrical'
    ));

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS last_health_check_at TIMESTAMPTZ;

ALTER TABLE widget_configs
  ADD COLUMN IF NOT EXISTS last_health_check_status TEXT
    CHECK (last_health_check_status IS NULL OR last_health_check_status IN ('green','yellow','red'));
```

`allowed_domains TEXT[]` is **already present** on `widget_configs` (mig 001 line 44) — do NOT re-add; only expose a UI.

#### 6.1.2 Reuse `integrations` (migration 007) for Stripe/Twilio/Resend

No schema change. The table already supports any provider. Storage contract for onboarding v2:

| Field | Stripe | Twilio | Resend |
|---|---|---|---|
| `provider` | `'stripe'` | `'twilio'` | `'resend'` |
| `access_token` | Stripe secret key (sk_live_… or sk_test_…), encrypted at rest via pgcrypto | Twilio Auth Token, encrypted | Resend API key (re_…), encrypted |
| `refresh_token` | NULL | NULL | NULL |
| `token_expiry` | NULL | NULL | NULL |
| `metadata` | `{"publishable_key": "pk_…", "webhook_secret": "whsec_…", "account_id": "acct_…"}` | `{"account_sid": "AC…", "phone_number": "+1…", "voice_webhook_url": "…", "sms_webhook_url": "…"}` | `{"from_email": "noreply@tenant.com", "webhook_secret": "…"}` |

**Encryption delta:** migration 007 stored `access_token TEXT` in plaintext. V2 adds a pgcrypto wrapper + a migration to encrypt existing rows.

Migration `116_integrations_encrypt_access_token.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE integrations
  ADD COLUMN IF NOT EXISTS access_token_enc BYTEA;

ALTER TABLE integrations
  ADD COLUMN IF NOT EXISTS refresh_token_enc BYTEA;

-- One-time backfill (app-level, not migration — see §7)
-- After backfill, a follow-up migration drops access_token/refresh_token TEXT columns
-- (deferred to avoid a half-migration; see Rule 8 in user-rules.md)
```

Encryption key: stored in Railway env var `INTEGRATIONS_ENC_KEY` (AES-256). Column helpers wrap `pgp_sym_encrypt(value, current_setting('app.enc_key'))` and `pgp_sym_decrypt(…)` via a tiny PL/pgSQL function or app-side via `cryptography.fernet`. Decision below in §9.

**Do NOT** create a new `tenant_secrets` table. **Do NOT** extend `tenant_integrations` (mig 109) — that table is Drive-scoped (provider CHECK locked to `'drive','dropbox','onedrive','box'`) and must stay that way.

#### 6.1.3 New table `vertical_presets` (migration 115 — same file as 6.1.1)

Genuinely novel. Seeds per-vertical defaults. Loaded from `config/vertical_defaults.yaml` on first migration run (one-time seed in same migration).

```sql
CREATE TABLE vertical_presets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vertical TEXT NOT NULL UNIQUE
    CHECK (vertical IN ('plumbing','hvac','cleaning','power_washing','landscaping','electrical')),
  display_name TEXT NOT NULL,
  default_services JSONB NOT NULL DEFAULT '[]'::jsonb,
  default_faqs JSONB NOT NULL DEFAULT '[]'::jsonb,
  default_hours JSONB NOT NULL DEFAULT '{}'::jsonb,
  avg_ticket_amount NUMERIC(10,2),
  avg_hours_saved_per_lead NUMERIC(4,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE vertical_presets ENABLE ROW LEVEL SECURITY;

CREATE POLICY vertical_presets_read_all ON vertical_presets
  FOR SELECT USING (true);  -- reference data, readable by all authenticated tenants

CREATE POLICY vertical_presets_service_write ON vertical_presets
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

**Why new table, not YAML only:** tenants can override presets (future V2 feature), and the preset is the source of truth for `avg_ticket` defaults referenced by ops-automation's attribution service.

#### 6.1.4 New table `welcome_email_attempts` (migration 117)

For retry-with-exponential-backoff. One row per attempt.

```sql
CREATE TABLE welcome_email_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  attempt_number INT NOT NULL CHECK (attempt_number BETWEEN 1 AND 3),
  scheduled_for TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','sent','failed','skipped')),
  error_message TEXT,
  resend_message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_welcome_email_tenant_attempt ON welcome_email_attempts(tenant_id, attempt_number);
CREATE INDEX idx_welcome_email_pending ON welcome_email_attempts(status, scheduled_for)
  WHERE status = 'pending';

ALTER TABLE welcome_email_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY welcome_email_service ON welcome_email_attempts
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

Retry schedule: attempt 1 fires at `created_at + 0s` (immediate). On failure, attempt 2 at +30s, attempt 3 at +2min, attempt 4 at +10min. Cap at 3 retries (attempts 2-4 are retries).

#### 6.1.5 Tenant column conventions (per schema-discipline)

- `widget_configs.tenant_id` — already uses `tenant_id` (mig 001 line 33). Keep.
- `integrations.tenant_id` — already uses `tenant_id` (mig 007 line 5). Keep.
- `vertical_presets` — no tenant column (global reference data).
- `welcome_email_attempts.tenant_id` — follows `tenants(id)` FK pattern of appointments/chat_messages (exception list in schema-discipline).
- **Leads/conversations still use `client_id`** — no changes here in this PRD, but the wizard's "KB ingestion" step writes to `widget_configs.knowledge_base` (mig 077, `tenant_id`-scoped) and `faq_entries` (mig 001 line 84, `tenant_id`-scoped). Nothing in this PRD touches `leads`.

### 6.2 API Surface

All new endpoints auth-gated by JWT (existing pattern from `backend/dependencies.py::get_current_tenant`). Feature-flag-gated by `tenants.feature_flags->>'onboarding_v2' = 'true'` (flag column already present per existing plan).

| Method | Path | Purpose | Auth | Request/Response |
|---|---|---|---|---|
| POST | `/api/v1/onboarding/v2/start` | Initialize wizard session; apply vertical preset | JWT | `{vertical: "plumbing"}` → `{wizard_state: {...}, preset_applied: true}` |
| POST | `/api/v1/onboarding/v2/step/{n}` | Persist step n data (n in 1-5) | JWT | `{field_updates: {...}}` → `{saved: true, readiness_criteria: {...}}` |
| POST | `/api/v1/onboarding/v2/complete` | Mark wizard complete; fire welcome email + schedule retries | JWT | `{}` → `{ready_to_launch: true, widget_api_key: "..."}` |
| POST | `/api/v1/onboarding/v2/auto-kb` | Wizard step 3 — wraps existing `/auto-kb` endpoint, attributes result to v2 session | JWT | `{website_url: "…"}` → `{services: [...], faqs: [...], hours: {...}, source_url: "..."}` |
| POST | `/api/v1/onboarding/v2/preset/{vertical}` | Return preset payload (services, faqs, hours, avg_ticket) | JWT | none → `{default_services: [...], default_faqs: [...], ...}` |
| POST | `/api/v1/integrations/keys` | Save per-tenant API key (Stripe/Twilio/Resend) | JWT | `{provider: "stripe", api_key: "sk_...", metadata: {...}}` → `{saved: true, verified: true/false}` |
| GET | `/api/v1/integrations/keys` | List configured providers + mask keys | JWT | `{providers: [{provider, masked_key, health, last_verified_at}]}` |
| DELETE | `/api/v1/integrations/keys/{provider}` | Revoke/remove a key | JWT | `{deleted: true}` |
| POST | `/api/v1/integrations/keys/{provider}/verify` | Ping provider API to confirm key works | JWT | `{health: "green"/"yellow"/"red", detail: "..."}` |
| GET | `/api/v1/integrations/health` | Aggregate dashboard — all providers + Google Calendar (existing) | JWT | `{integrations: [...], overall: "green/yellow/red"}` |
| GET | `/api/v1/widget/health` | Post-install check — widget JS loaded + `/api/chat` reachable for tenant domain | widget API key | `?domain=example.com` → `{loaded: true, reachable: true, last_ping_at: "...", origin_allowed: true}` |
| POST | `/api/v1/widget/allowed-domains` | Set `widget_configs.allowed_domains` array | JWT | `{domains: ["example.com", "www.example.com"]}` → `{saved: true}` |
| POST | `/api/v1/onboarding/v2/faqs/bulk` | CSV upload OR newline-separated paste | JWT | CSV file or `{text: "Q1\nA1\nQ2\nA2..."}` → `{imported: N, skipped: M, errors: [...]}` |
| POST | `/api/v1/onboarding/v2/hours` | Save structured hours (visual picker writes here) | JWT | `{timezone: "America/Chicago", hours: {monday: {...}}}` → `{saved: true}` |
| GET | `/api/v1/onboarding/v2/readiness` | Recompute + return readiness_criteria | JWT | `{services_count: 4, hours_filled: true, faqs_count: 6, logo_uploaded: false, ready_to_launch: false}` |

Pydantic models all in `backend/models/onboarding_v2.py` (new file). No `from __future__ import annotations` (critical — see CLAUDE.md rule 5).

### 6.3 UI Layout

All new pages in `frontend/src/pages/onboarding-v2/`. Mobile-first — iPhone 13 and Pixel 6 are the default viewports during development. Tailwind breakpoints target 375px first.

**Signup (modified existing `SignupPage.jsx`):**
- 4 fields: name, email, password, business_type (dropdown — includes 6 presets + "other")
- Primary CTA: "Continue with Google" (OAuth button on top)
- Secondary: "Sign up with email" (expands to 4-field form)
- Removes: city, phone, website_url, owner_name, business_size fields (moved to wizard step 1 OR inferred)

**Wizard — 5 steps (mobile-first, single-column, progress bar top):**

| Step | Title | Fields / Actions | New Component |
|---|---|---|---|
| 1 | "Tell us about your business" | Business name (pre-filled from signup), website URL (NEW — required, drives auto-KB), service area (single text field, no dropdown), time zone (auto-detected from browser, override dropdown) | `WizardStepBusinessV2.jsx` |
| 2 | "Pick your services" | Vertical preset applied from signup's business_type → pre-seeded services list (3-8 chips, tenant can add/remove); "avg ticket" auto-fills from preset | `WizardStepServicesV2.jsx` |
| 3 | "Auto-fill from your website" | Button: "Scan mnplumbing.com" → calls `/auto-kb` → shows services/FAQs/hours pulled; tenant reviews, clicks accept-all or edit-each | `WizardStepAutoKbV2.jsx` |
| 4 | "Confirm your hours + FAQs" | Visual weekly grid for hours (day toggle + 2 time pickers per day); FAQs list with bulk-import CTA (CSV upload OR paste lines); logo upload | `WizardStepHoursFaqV2.jsx`, `VisualHoursPicker.jsx`, `FaqBulkImport.jsx` |
| 5 | "Install your widget" | WordPress plugin CTA (primary): "Download plugin (zip)" + "How to install" video; script tag (secondary, collapsed by default); allowed_domains input; post-install health check button | `WizardStepInstallV2.jsx`, `WordpressPluginDownload.jsx`, `AllowedDomainsInput.jsx`, `WidgetHealthCheck.jsx` |

**New Settings pages:**

- `frontend/src/pages/Settings/IntegrationsKeysPage.jsx` — Stripe/Twilio/Resend key entry + green/yellow/red health pills
- `frontend/src/pages/Settings/IntegrationHealthDashboard.jsx` — aggregate view with Google Calendar + the three new providers
- `frontend/src/pages/Settings/AllowedDomainsPage.jsx` — standalone editor (also accessible from wizard step 5)

Sidebar additions in `Sidebar.jsx`: "Integrations" becomes a sub-menu: "Google Calendar", "Stripe", "Twilio", "Resend", "Health Dashboard".

Readiness badge component: `frontend/src/components/widget/ReadyToLaunchBadge.jsx`. Four checkmarks: services ≥3, hours filled, FAQs ≥5, logo uploaded. All four checked → pill flips green, badge says "Ready to launch."

---

## 7. Technical Implementation

### 7.1 New files

**Backend:**
- `backend/routers/onboarding_v2.py` — all `/api/v1/onboarding/v2/*` routes
- `backend/routers/integration_keys.py` — `/api/v1/integrations/keys*` routes
- `backend/routers/widget_health.py` — `/api/v1/widget/health` route (split from `widget_config.py` to respect Rule 9 god-class threshold)
- `backend/services/onboarding_v2_service.py` — wizard state machine, readiness calculator, preset applier
- `backend/services/integration_key_vault.py` — pgcrypto encrypt/decrypt wrapper for `integrations.access_token`; bcrypt-style masking helper
- `backend/services/integration_health_checker.py` — per-provider ping logic (Stripe: `stripe.Account.retrieve()`, Twilio: `Account.fetch()`, Resend: `GET /domains`)
- `backend/services/vertical_preset_loader.py` — load from `vertical_presets` table + fallback to `config/vertical_defaults.yaml`
- `backend/services/welcome_email_retrier.py` — retry scheduler (consumed by existing `backend/services/automation/scheduled_jobs.py` or new cron)
- `backend/services/widget_health_probe.py` — simulates a `/api/chat` ping for a given domain; verifies `api_key` resolves; checks `allowed_domains`
- `backend/models/onboarding_v2.py` — Pydantic request/response models
- `backend/models/integration_key.py` — Pydantic for key entry + masked listing

**Config:**
- `config/vertical_defaults.yaml` — 6 verticals × {services, faqs, hours, avg_ticket, avg_hours_saved_per_lead}
- `config/hours_saved_formula.yaml` — reused from ops-automation PRD; referenced here for `avg_hours_saved_per_lead`

**WordPress plugin (new directory at repo root):**
- `wordpress-plugin/agentnexlify-widget/agentnexlify-widget.php` — plugin entry + hook
- `wordpress-plugin/agentnexlify-widget/admin.php` — admin page UI (API key input)
- `wordpress-plugin/agentnexlify-widget/widget-injector.php` — adds the script tag to `wp_footer`
- `wordpress-plugin/agentnexlify-widget/readme.txt` — WP directory compliance
- `wordpress-plugin/agentnexlify-widget/assets/icon.png`
- `scripts/build-wp-plugin.sh` — zips the plugin for download

**Frontend:**
- `frontend/src/pages/onboarding-v2/OnboardingWizardV2Page.jsx`
- `frontend/src/pages/onboarding-v2/WizardStepBusinessV2.jsx`
- `frontend/src/pages/onboarding-v2/WizardStepServicesV2.jsx`
- `frontend/src/pages/onboarding-v2/WizardStepAutoKbV2.jsx`
- `frontend/src/pages/onboarding-v2/WizardStepHoursFaqV2.jsx`
- `frontend/src/pages/onboarding-v2/WizardStepInstallV2.jsx`
- `frontend/src/components/onboarding-v2/VisualHoursPicker.jsx`
- `frontend/src/components/onboarding-v2/FaqBulkImport.jsx`
- `frontend/src/components/onboarding-v2/WordpressPluginDownload.jsx`
- `frontend/src/components/onboarding-v2/AllowedDomainsInput.jsx`
- `frontend/src/components/onboarding-v2/WidgetHealthCheck.jsx`
- `frontend/src/components/onboarding-v2/VerticalPresetPicker.jsx`
- `frontend/src/components/widget/ReadyToLaunchBadge.jsx`
- `frontend/src/pages/Settings/IntegrationsKeysPage.jsx`
- `frontend/src/pages/Settings/IntegrationHealthDashboard.jsx`
- `frontend/src/pages/Settings/AllowedDomainsPage.jsx`
- `frontend/src/utils/api/onboardingV2.js`
- `frontend/src/utils/api/integrationKeys.js`

**Tests:**
- `backend/tests/test_onboarding_v2.py`
- `backend/tests/test_integration_key_vault.py` — 100% coverage required (security-critical)
- `backend/tests/test_widget_health_probe.py`
- `backend/tests/test_welcome_email_retrier.py`
- `backend/tests/test_vertical_preset_loader.py`
- `frontend/tests/onboarding-v2/wizard-flow.spec.js` — Playwright mobile viewport E2E

### 7.2 Files to modify

**Backend:**
- `backend/main.py:746-813` — register new routers
- `backend/routers/auth.py:206-349` — set `widget_configs.onboarding_version = 'v2'` on signup when feature flag on
- `backend/routers/onboarding.py:673-825` — existing `/auto-kb` gets a v2 wrapper; no breaking changes
- `backend/routers/widget_config.py:132-150` — expose `allowed_domains` field in config response (UI was missing — per audit §4 hotspot)
- `backend/services/industry_packs/__init__.py` — hook into `vertical_preset_loader` so packs seed KB (addresses audit finding: packs only seeded automations, not KB)
- `backend/config.py:34-49` — no longer hard-fail on missing Stripe/Twilio/Resend env vars when v2 keys exist per tenant; fallback chain: per-tenant key → env var → error
- `backend/services/email_sender.py` — wire into `welcome_email_retrier`

**Frontend:**
- `frontend/src/pages/SignupPage.jsx:38-340` — reduce to 4 fields; promote Google OAuth
- `frontend/src/App.jsx` — route `/onboarding` to v2 component when `onboarding_v2` flag true, else v1
- `frontend/src/components/Sidebar.jsx` — sub-menu for Integrations
- `frontend/src/pages/IntegrationsPage.jsx:246` — add Stripe/Twilio/Resend pills alongside Google Calendar

**Widget (byte-identical rule — CLAUDE.md rule 4):**
- `widget/agentnexlify-widget.js` — no change in v1 of this PRD; WordPress plugin injects the same script tag
- If any widget change occurs: copy byte-identical to `frontend/public/widget/agentnexlify-widget.js`

### 7.3 Feature flag mechanics

Column already exists: `tenants.feature_flags JSONB` (existing infra, used for other flags). Flag key: `onboarding_v2`. Default: `false` for existing tenants, `true` for new signups after flag flip.

Global kill-switch: env var `ONBOARDING_V2_GLOBAL_ENABLED=true`. Off → all tenants revert to v1 regardless of per-tenant flag. Non-negotiable per PRD scope.

Percentage rollout: Railway env var `ONBOARDING_V2_ROLLOUT_PERCENT=0..100`. On signup, hash `email` to `[0..99]`; if hash < percent, flip per-tenant flag on.

---

## 8. Edge Cases + Failure Modes

| Scenario | v1 behavior | v2 handling |
|---|---|---|
| Website URL in step 1 is malformed or 404 | crash | `/auto-kb` returns `{status: "skipped", reason: "unreachable"}`; step 3 falls back to manual entry |
| `/auto-kb` takes >30s | spinner forever | 30s timeout → partial-result return; tenant can retry or skip |
| Vertical preset not picked (legacy `business_type = 'other'`) | KB empty | wizard shows manual entry; `vertical_preset` column stays NULL; readiness criteria still apply |
| Tenant pastes invalid Stripe key | no-op | `/integrations/keys/verify` returns `red` with error detail; UI shows red pill + error text |
| Tenant pastes Stripe TEST key in prod | accepted silently | health check detects `sk_test_` prefix in prod env; yellow pill with warning |
| Tenant configures `allowed_domains = ["example.com"]` then installs widget on `www.example.com` | 403 no UI feedback | `GET /widget/health` returns `origin_allowed: false`; wizard step 5 shows "Domain mismatch — add www.example.com" |
| WordPress plugin download fails mid-signup | user stuck | fallback: show script tag as secondary option (existing v1 behavior preserved) |
| Welcome email fails all 3 retries | silently dropped | 4th attempt write to `welcome_email_attempts` with `status='failed'`; banner on dashboard "We couldn't deliver your welcome email — click to resend" |
| Tenant deletes Stripe key while subscription active | billing breaks | DELETE endpoint checks `tenants.stripe_subscription_id` — if active, 409 "Cannot remove — active subscription"; offer admin path |
| FAQ CSV has 500 rows | OOM risk | cap import at 200 rows; reject larger with 413 + "Split into smaller files" |
| FAQ paste-lines has odd-number lines | last Q orphaned | reject with 422 + "Expect Q/A pairs — got N lines" |
| Hours JSON from preset + tenant override = conflict | unclear | tenant override always wins; preset is seed-only, never over-writes post-save |
| Tenant on v2 wizard, flag flipped off mid-session | state lost | keep in-progress `widget_configs.onboarding_version` row; resume works; API respects saved state regardless of flag |
| Readiness criteria change (future: add "integrations count ≥1") | stale badges | criteria stored in `readiness_criteria JSONB` — recomputed on every GET; badge flips green/yellow on next check |
| Encryption key rotation | decryption breaks | versioned key header in `metadata.enc_key_version`; rotate by decrypt-with-old, encrypt-with-new job |
| Google OAuth signup returns no email scope | blocked | fall back to email-password form with google_id pre-linked |

---

## 9. Security + Compliance

**API key encryption at rest:**
- `integrations.access_token_enc BYTEA` via pgcrypto `pgp_sym_encrypt`
- Key: AES-256, stored in `INTEGRATIONS_ENC_KEY` env var (Railway). Never committed. Never logged.
- Decryption only via `backend/services/integration_key_vault.py::decrypt_key()` — logged at INFO level with tenant_id + provider (NOT the key itself)
- Masked display in API responses: `sk_live_••••1234` (first 8 + last 4 chars)
- Test coverage: 100% on `integration_key_vault.py` (non-negotiable; paths include round-trip, wrong-key failure, malformed ciphertext, NULL handling)

**CSRF protection on wizard steps:**
- All POST `/api/v1/onboarding/v2/*` require `X-CSRF-Token` header matched against session cookie
- Token issued by `/api/v1/onboarding/v2/start` response body
- Token rotated on every step submission (single-use)

**Tenant isolation:**
- Every new endpoint takes `tenant_id` from JWT via `get_current_tenant` dependency — never from request body
- `integrations` RLS already service-role-only (mig 007); widget-facing never touches the table
- `widget_configs` scoped by `tenant_id` (existing pattern)
- `welcome_email_attempts` scoped by `tenant_id`
- `vertical_presets` — global reference data; read-all-allow policy intentional; no tenant leakage

**WordPress plugin security:**
- Plugin embeds a single script tag with the tenant's widget API key
- API key scoped per-tenant; revokable via `/api/v1/widget/api-key/rotate` (future endpoint)
- Plugin signs outbound `/api/chat` requests with the API key in the `X-Widget-Api-Key` header; existing origin check (`widget_chat_helpers.py:_check_origin`) enforces `allowed_domains`
- No tenant credentials in the plugin itself beyond the public API key

**PII handling:**
- Welcome email stores tenant email (already in `tenants.email`)
- Scraped website content from `/auto-kb` stored in `widget_configs.knowledge_base` — never indexed externally
- FAQ imports stay in `faq_entries` (RLS-scoped per mig 001)

**Rate limits:**
- `/auto-kb` — 3/min per tenant (existing); unchanged
- `/integrations/keys/{provider}/verify` — 10/min per tenant (new — prevents credential stuffing of Stripe keys)
- `/widget/health` — 60/min per API key (widget clients may legitimately ping)

**Audit logging:**
- Every `integrations` write → row in `audit_log` table (existing) with `action: 'integration_key_saved'`, `provider`, NOT the key
- Every wizard step completion → event in analytics
- Every readiness-badge flip to green → event

---

## 10. Testing Strategy

**Backend unit tests (80% coverage on new services minimum):**
- `test_onboarding_v2.py` — wizard state machine, readiness calculator, preset applier
- `test_integration_key_vault.py` — **100% coverage required** (security-critical). Cases: encrypt round-trip, decrypt wrong-key fails, decrypt malformed fails, NULL handling, key rotation, masked display
- `test_widget_health_probe.py` — green/yellow/red decision tree, origin check, timeout handling
- `test_welcome_email_retrier.py` — exponential backoff timing, 3-attempt cap, failure banner trigger
- `test_vertical_preset_loader.py` — YAML parse, DB fallback, override wins
- `test_integration_health_checker.py` — mock Stripe/Twilio/Resend SDK responses

**Backend integration tests:**
- Full wizard flow via HTTPX client: start → step 1 → 2 → 3 → 4 → 5 → complete
- Key verification happy path + sad path per provider
- Widget health check against a mock tenant site

**Frontend unit tests (Vitest):**
- `VisualHoursPicker` — 7-day grid, time picker interactions, timezone change
- `FaqBulkImport` — CSV parse, paste-lines parse, error cases
- `ReadyToLaunchBadge` — 4-criteria state matrix
- `WordpressPluginDownload` — download trigger + tracking event

**E2E Playwright (MOBILE VIEWPORT — iPhone 13 + Pixel 6):**
- Full signup → wizard 1-5 → widget install verification
- Test script: `frontend/tests/onboarding-v2/wizard-flow.spec.js`
- Devices: iPhone 13 (390×844), Pixel 6 (412×915)
- Assertions:
  - Signup completes with 4 fields
  - Google OAuth button visible first
  - Wizard fits viewport without horizontal scroll
  - Auto-KB returns within 30s (mocked)
  - Visual hours picker usable with touch
  - FAQ CSV upload completes
  - WordPress plugin download triggers
  - Widget health check returns green after simulated install

**Security-path coverage:**
- Run `pytest --cov=backend.services.integration_key_vault --cov-fail-under=100`
- CI gate: fail PR if encryption paths drop below 100%

**Mobile verification:**
- Manual iPhone (Safari) + Android (Chrome) smoke test before merge
- Chrome DevTools mobile emulation in PR review pass

---

## 11. Rollout Plan

**Feature flag name:** `onboarding_v2` (per-tenant in `tenants.feature_flags` JSONB).
**Global kill-switch:** env var `ONBOARDING_V2_GLOBAL_ENABLED` (Railway).
**Percentage rollout:** env var `ONBOARDING_V2_ROLLOUT_PERCENT` (0-100).

**Phases:**

| Phase | Duration | Rollout % | Cohort | Gate to next phase |
|---|---|---|---|---|
| Dev + internal | Week 1-4 | 0% (manually flagged) | Aidan + 1 dogfood tenant | All 5 wizard steps pass E2E on mobile |
| Canary | Week 5 | 5% | Random 5% of new signups | Completion rate ≥60%, no crashes in Sentry |
| Ramp-1 | Week 6 | 25% | New signups | Completion rate ≥80%, welcome email retry success ≥95% |
| Ramp-2 | Week 7 | 50% | New signups | Mobile E2E still passing; no P0/P1 bugs 7 days |
| GA | Week 8 | 100% | All new signups | v1 signup page kept alive 30 days, then sunset |
| Sunset v1 | Week 12 | — | Remove v1 wizard components | All new tenants on v2; existing v1 tenants stay on v1 (no forced migration — see §3 non-goals) |

**Backward compatibility:**
- Existing v1 signups: `widget_configs.onboarding_version = 'v1'` (default). No schema break.
- Existing `SignupPage.jsx` stays functional until week 12.
- Existing `/api/v1/onboarding/*` endpoints remain — v2 adds `/api/v1/onboarding/v2/*` alongside.
- No destructive migrations until v1 sunset (week 12+ separate PR).

**Revert plan:**
- Flip `ONBOARDING_V2_GLOBAL_ENABLED=false` in Railway — instant revert for all in-flight sessions
- No schema rollback needed (all ALTERs are additive; new tables are empty until v2 tenants exist)

---

## 12. Timeline Estimate

| Week | Owner | Deliverables |
|---|---|---|
| 1 | backend-dev | Migrations 115, 116, 117; `vertical_preset_loader`; `config/vertical_defaults.yaml`; `integration_key_vault` + 100% test coverage |
| 2 | backend-dev | `onboarding_v2_service`; `/api/v1/onboarding/v2/*` routes; welcome email retrier; unit tests 80%+ |
| 3 | backend-dev + devops | `integration_health_checker`; `widget_health_probe`; `/integrations/keys/*`; `/widget/health`; integration tests |
| 4 | frontend-dev | SignupPage v2 (4 fields + Google primary); WizardStepBusinessV2-InstallV2; `VisualHoursPicker`; `FaqBulkImport`; `ReadyToLaunchBadge` |
| 5 | frontend-dev | Settings pages (IntegrationsKeys, IntegrationHealth, AllowedDomains); API clients; dark-theme polish; **mobile Playwright E2E** |
| 6 | devops + backend-dev | WordPress plugin scaffold + zip build; plugin install walkthrough video; canary deploy (5%) |
| 7 | full stack | Ramp-1 (25%); bug-bash; iteration on wizard copy; Android smoke |
| 8 | full stack | Ramp-2 (50%) → GA (100%); event dashboard at `OnboardingFunnelPage.jsx` |
| 9-11 | — | Monitor; iterate on abandonment data |
| 12 | backend-dev | Sunset v1 signup page; archive v1 wizard components |

**Critical path:** `integration_key_vault` encryption (week 1) blocks `/integrations/keys` routes (week 3). WordPress plugin (week 6) blocks canary.

**Parallelizable:** backend weeks 1-3 run parallel to frontend weeks 4-5 after API contracts frozen end of week 2.

---

## 13. V2 Scope (Deferred)

Documented only; not detailed here. Covered in future PRDs.

- **Shopify plugin** — architectural twin of WordPress plugin; different install flow (Shopify App Store).
- **Wix plugin** — Velo-based; lower priority (smaller SMB share).
- **Squarespace plugin** — code-injection-based; easiest to add after WP.
- **Stripe Connect migration** — platform holds, tenants don't need own Stripe account. Major billing architecture shift. See `planning/decisions/` for a future ADR.
- **Twilio API auto-provisioning** — platform provisions numbers on behalf of tenant; eliminates per-tenant Twilio signup.
- **Post-onboarding KB editor UI** — replace wizard-step-only editing with a standalone `/kb/editor` page.
- **Markdown preview in KB editor** — pairs with above.
- **Google token refresh expiry notifications** — reuses `integrations.token_expiry` (already present); adds UI banner on expiry < 7d.
- **Onboarding tenant migration from v1 to v2** — opt-in "redo your setup" flow.
- **Additional verticals** — auto repair, pest control, roofing, pool service.

---

## 14. Open Questions (Blockers Only)

None. All prior open questions from `audits/audit-onboarding-2026-04-21.md` §6 either resolved in PRD scope or explicitly deferred to V2.

---

## 15. Constraints Summary

**Schema (per `audits/existing-infra-reference-2026-04-21.md`):**
- Tenant keys: REUSE `integrations` table (mig 007). Store API key in `access_token` (encrypted via new `access_token_enc BYTEA`). `refresh_token` NULL for API-key providers. `metadata JSONB` for auxiliary fields (webhook secrets, phone numbers, publishable keys).
- Widget config: EXTEND `widget_configs` via ALTER (mig 115). No parallel config table.
- Allowed domains: `widget_configs.allowed_domains TEXT[]` ALREADY EXISTS (mig 001 line 44). UI-only work; no schema change.
- Vertical presets: NEW table `vertical_presets` (mig 115) — global reference, not per-tenant.
- Welcome email retries: NEW table `welcome_email_attempts` (mig 117) — per-tenant, 3-retry cap.
- `tenant_integrations` (mig 109) stays Drive-scoped. DO NOT extend its CHECK constraint.
- `tenant_secrets` — DO NOT create. The ask was satisfied by `integrations`.

**Tenant column conventions (per `schema-discipline.md`):**
- `widget_configs.tenant_id` — uses `tenant_id` (existing; keep)
- `integrations.tenant_id` — uses `tenant_id` (existing; keep)
- `welcome_email_attempts.tenant_id` — uses `tenant_id` (follows appointments/chat_messages pattern)
- `vertical_presets` — no tenant column (global reference data)
- Leads/conversations — NOT touched in this PRD; would use `client_id` if they were

**Widget byte-identical (CLAUDE.md rule 4):**
- `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js` must match byte-for-byte
- v1 of this PRD makes zero widget JS changes; WordPress plugin embeds unchanged script tag
- Future changes: copy to both paths in same commit; run `diff -q` in pre-commit

**Plan names (CLAUDE.md):**
- Valid: `free`, `growth` ($99/mo Starter), `autopilot` ($150/mo Growth), `professional` ($250/mo Pro), `enterprise` ($899/mo)
- Legacy (billing-only): `growth $199`, `professional $399`, `enterprise $799`
- Retired (never use): `foundation`, `operations`
- This PRD's flag `onboarding_v2` applies regardless of plan

**Migration numbering:**
- 110 taken (zapier `tenant_api_keys`)
- 111-113 reserved (marketing-automation)
- 114 reserved (ops-automation)
- **115, 116, 117 — this PRD**
- 118-119 reserved (self-maintenance PRD)
- Next free after this set: 120

**FastAPI constraints (CLAUDE.md rule 5):**
- No `from __future__ import annotations` in any new backend file
- Pre-commit hook enforces; verified on PR

**Security (CLAUDE.md rule 7):**
- Secrets never in commits or logs
- `INTEGRATIONS_ENC_KEY` Railway env var only
- Logged events reference tenant_id + provider; never the key value

**Mobile-first (non-negotiable per this PRD scope):**
- All 5 wizard steps + Settings pages tested on iPhone + Android viewports before merge
- Tailwind breakpoints start at 375px
- No desktop-only components

---

## Schema Verification

Self-verification checklist — each bullet confirms reuse of existing infra vs reinvention:

- [x] API keys stored in existing `integrations` table (migration 007) — `access_token` column, NOT a new `tenant_secrets` table
- [x] `integrations.tenant_id` used (not `client_id`) — matches existing mig 007 schema
- [x] `refresh_token` NULL for API-key providers — documented convention, no new column
- [x] `metadata JSONB` on `integrations` used for webhook secrets + phone numbers + publishable keys — existing column, no ALTER
- [x] Widget config extended via ALTER on `widget_configs` (mig 115), not a parallel table
- [x] `widget_configs.allowed_domains TEXT[]` — CONFIRMED already exists (mig 001 line 44); UI-only work, no schema change
- [x] `widget_configs.tenant_id` used (not `client_id`) — matches existing mig 001 schema
- [x] `widget_configs.api_key UUID` — CONFIRMED already exists (mig 001); reused for widget health check
- [x] `widget_configs.branding JSONB` — CONFIRMED already exists (mig 008); reused for logo upload
- [x] `faq_entries` table reused for bulk FAQ import (mig 001 line 84); uses `tenant_id`
- [x] `business_hours` table reused for visual hours picker (mig 005); uses `tenant_id`, already has JSONB `hours` column
- [x] `tenant_integrations` (mig 109) NOT extended — kept Drive-only per reference doc
- [x] `tenant_api_keys` (mig 110) NOT overloaded — that is for Zapier CRM export, different scope
- [x] `tenants.feature_flags JSONB` reused for `onboarding_v2` per-tenant flag; no new flag table
- [x] `tenants.business_type` reused for vertical preset selection (mig 001 line 10 + mig 078 expansion)
- [x] New tables limited to: `vertical_presets` (global ref data) + `welcome_email_attempts` (novel retry tracking) — both genuinely novel, no existing equivalent
- [x] Migration numbers 115-117 chosen — confirmed 110 taken, 111-113 marketing reserved, 114 ops-auto reserved, 115+ free
- [x] Encryption added additively via `access_token_enc BYTEA` — plaintext column retained until follow-up migration sunsets it (Rule 8: no half-migrations — sunset is a separate fully-planned PR)
- [x] Leads/conversations untouched — this PRD does not reach `client_id` tables; no `client_id` vs `tenant_id` confusion risk
- [x] No `lead_stage` usage — leads status column is `status` per schema-discipline
