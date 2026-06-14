# Issues: onboarding-v2

Each issue is independently grabbable. Blocking relationships explicit.

---

## Issue 1: Add migrations 113-116 (widget_configs extras, vertical_presets, integrations encryption, welcome_email_attempts)

**Labels:** `migration`, `backend`, `priority:high`

**User story:**
As a developer, I need the schema landed before any v2 service can run so that all writes have valid storage.

**Acceptance criteria:**
- `migrations/113_widget_configs_v2_extras.sql` adds `vertical_preset`, `last_health_check_at`, `last_health_check_status` to `widget_configs`
- `migrations/114_vertical_presets.sql` creates table + RLS + 6-row seed from `config/vertical_defaults.yaml`
- `migrations/115_integrations_encrypt_access_token.sql` enables pgcrypto + adds `access_token_enc BYTEA`, `refresh_token_enc BYTEA`
- `migrations/116_welcome_email_attempts.sql` creates table + indexes + RLS
- All 4 apply via `mcp__supabase__apply_migration` against staging without error
- `docs/dev-knowledge/schema-log.md` updated with rationale + numbering reconciliation

**Files expected to change:**
- `migrations/113_widget_configs_v2_extras.sql` (new)
- `migrations/114_vertical_presets.sql` (new)
- `migrations/115_integrations_encrypt_access_token.sql` (new)
- `migrations/116_welcome_email_attempts.sql` (new)
- `config/vertical_defaults.yaml` (new)
- `docs/dev-knowledge/schema-log.md` (modify)

**Blocked by:** none.
**Blocks:** Issues 2, 3, 4, 5, 6, 7.

---

## Issue 2: Build integration_key_vault with 100% test coverage

**Labels:** `backend`, `security`, `priority:critical`

**User story:**
As a tenant, I need my Stripe/Twilio/Resend keys encrypted at rest so a DB leak doesn't expose them.

**Acceptance criteria:**
- `backend/services/integration_key_vault.py` exposes `encrypt(key) -> bytes`, `decrypt(ct) -> str`, `mask(key) -> str`
- Uses `INTEGRATIONS_ENC_KEY` env var (AES-256 via pgcrypto pgp_sym_encrypt or app-side cryptography.fernet — pick in PR description)
- Module raises at import time if `INTEGRATIONS_ENC_KEY` missing (fail-fast)
- `backend/tests/test_integration_key_vault.py` covers: round-trip, wrong-key fail, malformed ciphertext fail, NULL handling, mask helper, key version metadata
- `pytest --cov=backend.services.integration_key_vault --cov-fail-under=100` passes
- No `from __future__ import annotations`

**Files expected to change:**
- `backend/services/integration_key_vault.py` (new)
- `backend/tests/test_integration_key_vault.py` (new)

**Blocked by:** Issue 1.
**Blocks:** Issue 8.

---

## Issue 3: Build vertical_preset_loader (DB-first, YAML fallback)

**Labels:** `backend`, `priority:medium`

**User story:**
As a wizard service, I need to fetch per-vertical defaults so I can pre-seed the wizard 70% filled.

**Acceptance criteria:**
- `backend/services/vertical_preset_loader.py::load(vertical) -> dict` returns `{display_name, default_services, default_faqs, default_hours, avg_ticket_amount, avg_hours_saved_per_lead}`
- DB read from `vertical_presets` first, falls back to `config/vertical_defaults.yaml` if row missing
- 6 verticals: plumbing, hvac, cleaning, power_washing, landscaping, electrical
- Test: DB hit, YAML fallback, unknown vertical returns None
- Hook into `backend/services/industry_packs/__init__.py` so packs ALSO seed KB (not just automations)

**Files expected to change:**
- `backend/services/vertical_preset_loader.py` (new)
- `backend/services/industry_packs/__init__.py` (modify)
- `backend/tests/test_vertical_preset_loader.py` (new)
- `config/vertical_defaults.yaml` (new — same file as Issue 1, share author)

**Blocked by:** Issue 1.
**Blocks:** Issue 5.

---

## Issue 4: Build welcome_email_retrier with exponential backoff

**Labels:** `backend`, `priority:high`

**User story:**
As Maria, if my welcome email fails once, the system should retry quietly and tell me only if all retries failed.

**Acceptance criteria:**
- `backend/services/welcome_email_retrier.py` schedules 3 retries: +30s, +2min, +10min after initial send fails
- Writes one row per attempt to `welcome_email_attempts` (status pending/sent/failed/skipped)
- 4th-attempt failure flips a banner-trigger flag readable by frontend
- Hook into `backend/services/automation/scheduled_jobs.py` for execution
- Hook into `backend/services/email_sender.py` to record initial attempt
- Test simulates time-travel; covers cap-3, idempotency, 429-retry-later
- No `from __future__ import annotations`

**Files expected to change:**
- `backend/services/welcome_email_retrier.py` (new)
- `backend/services/automation/scheduled_jobs.py` (modify)
- `backend/services/email_sender.py` (modify)
- `backend/tests/test_welcome_email_retrier.py` (new)

**Blocked by:** Issue 1.
**Blocks:** Issue 13 (banner UI).

---

## Issue 5: Build onboarding_v2_service + Pydantic models + router

**Labels:** `backend`, `priority:critical`

**User story:**
As Maria, I need a 5-step wizard that persists my answers, applies a vertical preset, and computes readiness so I know when I'm ready to launch.

**Acceptance criteria:**
- `backend/models/onboarding_v2.py` defines all request/response Pydantic models for 13 endpoints (per spec §6.2)
- `backend/services/onboarding_v2_service.py` implements: state machine (5 steps), readiness calculator, preset applier, hours saver, FAQ bulk import (CSV + paste-lines, 200-row cap)
- `backend/routers/onboarding_v2.py` mounts all `/api/v1/onboarding/v2/*` paths with JWT auth + feature-flag gate
- CSRF token issued on `/start`, rotated per step
- httpx integration test: full happy-path wizard
- Backend unit ≥80% on service
- No `from __future__ import annotations`
- `tenant_id` from JWT only — never from body
- Register router in `backend/main.py:746-813`
- `backend/routers/auth.py:206-349` sets `widget_configs.onboarding_version='v2'` when feature flag on

**Files expected to change:**
- `backend/models/onboarding_v2.py` (new)
- `backend/services/onboarding_v2_service.py` (new)
- `backend/routers/onboarding_v2.py` (new)
- `backend/main.py` (modify)
- `backend/routers/auth.py` (modify)
- `backend/routers/onboarding.py` (modify, 673-825 — v2 wrapper for `/auto-kb`)
- `backend/tests/test_onboarding_v2.py` (new)

**Blocked by:** Issues 1, 3, 4.
**Blocks:** Issues 9, 10, 11, 12.

---

## Issue 6: Expose widget_configs.allowed_domains in widget_config router

**Labels:** `backend`, `priority:medium`

**User story:**
As Maria, I want to restrict my widget to mnplumbing.com so a competitor can't embed it.

**Acceptance criteria:**
- `backend/routers/widget_config.py:132-150` returns `allowed_domains` field in GET response
- POST `/api/v1/widget/allowed-domains` accepts `{domains: ["example.com", "www.example.com"]}` and writes to `widget_configs.allowed_domains`
- Validation: lowercase, no protocol prefix, no trailing slash
- httpx test for save + retrieve

**Files expected to change:**
- `backend/routers/widget_config.py` (modify)
- `backend/tests/test_widget_config.py` (modify)

**Blocked by:** none.
**Blocks:** Issue 14 (frontend allowed_domains UI).

---

## Issue 7: Build widget_health_probe + endpoint

**Labels:** `backend`, `priority:high`

**User story:**
As Maria, I want to confirm "widget is live on mnplumbing.com" without opening devtools.

**Acceptance criteria:**
- `backend/services/widget_health_probe.py::probe(api_key, domain) -> {loaded, reachable, last_ping_at, origin_allowed}`
- `backend/routers/widget_health.py` mounts GET `/api/v1/widget/health?domain=...` (auth: widget API key)
- Rate limit 60/min/api_key
- Probe verifies `api_key` resolves to a tenant + `domain` in `allowed_domains`
- Updates `widget_configs.last_health_check_at` + `last_health_check_status`
- Unit + integration tests; mocked tenant site
- New router file (Rule 9 god-class threshold; do not extend `widget_config.py`)

**Files expected to change:**
- `backend/services/widget_health_probe.py` (new)
- `backend/routers/widget_health.py` (new)
- `backend/main.py` (modify — register)
- `backend/tests/test_widget_health_probe.py` (new)

**Blocked by:** Issue 1.
**Blocks:** Issue 15 (frontend health check component).

---

## Issue 8: Build integration_health_checker + integration_keys router

**Labels:** `backend`, `security`, `priority:critical`

**User story:**
As Maria, I want to paste my Stripe/Twilio/Resend keys in a Settings UI without emailing a developer, with green/yellow/red verification.

**Acceptance criteria:**
- `backend/services/integration_health_checker.py` implements ping per provider:
  - Stripe: `stripe.Account.retrieve()`
  - Twilio: `Account.fetch()`
  - Resend: `GET /domains`
- Returns `{health: green|yellow|red, detail: str}`; sk_test in prod env → yellow
- `backend/routers/integration_keys.py` mounts: POST/GET/DELETE `/integrations/keys`, POST `/{provider}/verify`, GET `/integrations/health`
- Saved keys encrypted via `integration_key_vault`; GET returns masked (`sk_live_••••1234`)
- DELETE blocked with 409 if active Stripe subscription
- Rate limit 10/min/tenant on verify
- Audit log on every write (action, provider, never key value)
- `backend/config.py:34-49` fallback chain: per-tenant key → env var → error
- Backfill script `scripts/backfill_integration_keys_encrypt.py` for existing plaintext rows
- Unit tests with mocked SDKs; integration test happy + sad path per provider

**Files expected to change:**
- `backend/services/integration_health_checker.py` (new)
- `backend/routers/integration_keys.py` (new)
- `backend/models/integration_key.py` (new)
- `backend/config.py` (modify)
- `backend/main.py` (modify — register)
- `scripts/backfill_integration_keys_encrypt.py` (new)
- `backend/tests/test_integration_health_checker.py` (new)
- `backend/tests/test_integration_keys_router.py` (new)

**Blocked by:** Issues 1, 2.
**Blocks:** Issues 16, 17.

---

## Issue 9: Reduce SignupPage to 4 fields, promote Google OAuth

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria on my iPhone, I want one-tap Google signup, not 8 fields.

**Acceptance criteria:**
- `frontend/src/pages/SignupPage.jsx:38-340` reduces to 4 fields: name, email, password, business_type (6 verticals + "other")
- Google OAuth button rendered above email form
- Removed: city, phone, website_url, owner_name, business_size (moved to wizard step 1)
- Mobile-first: 375px viewport, no horizontal scroll
- No localStorage usage
- Vitest unit + Playwright mobile E2E

**Files expected to change:**
- `frontend/src/pages/SignupPage.jsx` (modify)
- `frontend/tests/SignupPage.test.jsx` (new or modify)

**Blocked by:** none (frontend can start parallel; flag-gates v2 path).
**Blocks:** Issue 10.

---

## Issue 10: Build OnboardingWizardV2Page + 5 step components

**Labels:** `frontend`, `priority:critical`

**User story:**
As Maria, I want a 5-step mobile wizard that walks me through business → services → auto-KB → hours/FAQs → install.

**Acceptance criteria:**
- 6 new files under `frontend/src/pages/onboarding-v2/`
- Single-column layout, progress bar top, fits 375px viewport
- Step 1: business name/website/service-area/timezone (auto-detect)
- Step 2: vertical preset auto-applied from signup business_type, services as chips, avg-ticket auto-fill
- Step 3: auto-KB scan button → calls `/onboarding/v2/auto-kb` → review services/FAQs/hours, accept-all or edit
- Step 4: visual hours grid + FAQ bulk import + logo upload
- Step 5: WordPress plugin download (primary) + script tag (collapsed) + allowed_domains + health check
- API client `frontend/src/utils/api/onboardingV2.js` wraps 13 endpoints
- `frontend/src/App.jsx` routes `/onboarding` to v2 when flag on
- Playwright mobile E2E (iPhone 13 + Pixel 6) covers full flow

**Files expected to change:**
- `frontend/src/pages/onboarding-v2/OnboardingWizardV2Page.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepBusinessV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepServicesV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepAutoKbV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepHoursFaqV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepInstallV2.jsx` (new)
- `frontend/src/utils/api/onboardingV2.js` (new)
- `frontend/src/App.jsx` (modify)
- `frontend/tests/onboarding-v2/wizard-flow.spec.js` (new)

**Blocked by:** Issues 5, 9.
**Blocks:** Issues 11, 12, 13.

---

## Issue 11: Build VisualHoursPicker component

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria on my phone, I want to tap days and times, not edit JSON.

**Acceptance criteria:**
- `frontend/src/components/onboarding-v2/VisualHoursPicker.jsx` — 7-day grid, day toggle, 2 native time pickers per day
- Timezone auto-detected from browser, override dropdown
- Saves via POST `/onboarding/v2/hours`
- Vitest unit + Playwright touch interaction test on iPhone 13

**Files expected to change:**
- `frontend/src/components/onboarding-v2/VisualHoursPicker.jsx` (new)
- `frontend/tests/components/VisualHoursPicker.test.jsx` (new)

**Blocked by:** Issue 5.
**Blocks:** Issue 10 (consumed by step 4).

---

## Issue 12: Build FaqBulkImport component (CSV + paste-lines)

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria, I want to upload my FAQ CSV from a Google Sheet export, not type 20 questions.

**Acceptance criteria:**
- `frontend/src/components/onboarding-v2/FaqBulkImport.jsx` — CSV file upload + paste-lines textarea
- Cap 200 rows; reject larger with 413 message
- Reject odd-line paste with 422 "Q/A pairs expected"
- Calls POST `/onboarding/v2/faqs/bulk`
- Vitest covers parsers + error cases

**Files expected to change:**
- `frontend/src/components/onboarding-v2/FaqBulkImport.jsx` (new)
- `frontend/tests/components/FaqBulkImport.test.jsx` (new)

**Blocked by:** Issue 5.
**Blocks:** Issue 10.

---

## Issue 13: Build ReadyToLaunchBadge + welcome-email failure banner

**Labels:** `frontend`, `priority:medium`

**User story:**
As Maria, I want a green "Ready to launch" badge so I know I've done enough.

**Acceptance criteria:**
- `frontend/src/components/widget/ReadyToLaunchBadge.jsx` — 4 checkmarks (services ≥3, hours filled, FAQs ≥5, logo), pill flips green when all met
- Reads `readiness_criteria` from GET `/onboarding/v2/readiness`
- Welcome-email failure banner on dashboard when 4th-attempt failed; click to resend
- Vitest state matrix test

**Files expected to change:**
- `frontend/src/components/widget/ReadyToLaunchBadge.jsx` (new)
- `frontend/src/pages/Dashboard/WelcomeEmailFailedBanner.jsx` (new — or inline)
- `frontend/tests/components/ReadyToLaunchBadge.test.jsx` (new)

**Blocked by:** Issues 4, 5.
**Blocks:** none.

---

## Issue 14: Build AllowedDomainsInput + standalone Settings page

**Labels:** `frontend`, `priority:medium`

**User story:**
As Maria, I want to set/edit my allowed domains both in the wizard and in Settings.

**Acceptance criteria:**
- `frontend/src/components/onboarding-v2/AllowedDomainsInput.jsx` — add/remove tags, lowercase, no protocol
- `frontend/src/pages/Settings/AllowedDomainsPage.jsx` — standalone editor route
- Both call POST `/api/v1/widget/allowed-domains`
- Mobile-first

**Files expected to change:**
- `frontend/src/components/onboarding-v2/AllowedDomainsInput.jsx` (new)
- `frontend/src/pages/Settings/AllowedDomainsPage.jsx` (new)
- `frontend/src/App.jsx` (modify — route)

**Blocked by:** Issue 6.
**Blocks:** none.

---

## Issue 15: Build WidgetHealthCheck component

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria, after I install the widget I want to click "Check it's live" and see green.

**Acceptance criteria:**
- `frontend/src/components/onboarding-v2/WidgetHealthCheck.jsx` — button calls GET `/api/v1/widget/health?domain=...`
- Renders `loaded`, `reachable`, `origin_allowed` as 3 traffic-light pills
- Origin mismatch surfaces "add www.example.com" hint
- Vitest unit

**Files expected to change:**
- `frontend/src/components/onboarding-v2/WidgetHealthCheck.jsx` (new)
- `frontend/tests/components/WidgetHealthCheck.test.jsx` (new)

**Blocked by:** Issue 7.
**Blocks:** Issue 10 (consumed by step 5).

---

## Issue 16: Build IntegrationsKeysPage (Stripe/Twilio/Resend)

**Labels:** `frontend`, `security`, `priority:critical`

**User story:**
As Maria, I want a Settings page where I paste my own Stripe/Twilio/Resend keys with green/yellow/red status.

**Acceptance criteria:**
- `frontend/src/pages/Settings/IntegrationsKeysPage.jsx` — paste field per provider, save → verify → pill
- `frontend/src/utils/api/integrationKeys.js` API client
- Mask keys client-side after save (never show plaintext post-save)
- Cooldown timer when verify rate-limited
- Mobile-first
- Vitest + Playwright

**Files expected to change:**
- `frontend/src/pages/Settings/IntegrationsKeysPage.jsx` (new)
- `frontend/src/utils/api/integrationKeys.js` (new)
- `frontend/tests/IntegrationsKeysPage.test.jsx` (new)

**Blocked by:** Issue 8.
**Blocks:** Issue 17.

---

## Issue 17: Build IntegrationHealthDashboard + Sidebar sub-menu

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria, I want one dashboard showing all 4 integrations (Google + Stripe + Twilio + Resend) at a glance.

**Acceptance criteria:**
- `frontend/src/pages/Settings/IntegrationHealthDashboard.jsx` — aggregate view
- `frontend/src/components/Sidebar.jsx` — Integrations sub-menu (Google, Stripe, Twilio, Resend, Health)
- `frontend/src/pages/IntegrationsPage.jsx:246` — extend with Stripe/Twilio/Resend pills
- Mobile-first
- Vitest

**Files expected to change:**
- `frontend/src/pages/Settings/IntegrationHealthDashboard.jsx` (new)
- `frontend/src/components/Sidebar.jsx` (modify)
- `frontend/src/pages/IntegrationsPage.jsx` (modify)

**Blocked by:** Issue 16.
**Blocks:** none.

---

## Issue 18: Build WordPress plugin (zip + admin + injector)

**Labels:** `wordpress`, `priority:critical`

**User story:**
As Maria, I want to install the widget via WordPress admin upload, never touching HTML.

**Acceptance criteria:**
- `wordpress-plugin/agentnexlify-widget/` directory with PHP files per spec §7.1
- `scripts/build-wp-plugin.sh` produces installable zip
- Admin page accepts API key, stores in `wp_options`
- `wp_footer` hook injects `<script src=".../agentnexlify-widget.js" data-api-key="...">`
- `readme.txt` declares WP 5.5+ requirement
- Manual install verified on local WP 6.4 docker
- Widget JS bytes unchanged (`widget/agentnexlify-widget.js` = `frontend/public/widget/agentnexlify-widget.js`)

**Files expected to change:**
- `wordpress-plugin/agentnexlify-widget/agentnexlify-widget.php` (new)
- `wordpress-plugin/agentnexlify-widget/admin.php` (new)
- `wordpress-plugin/agentnexlify-widget/widget-injector.php` (new)
- `wordpress-plugin/agentnexlify-widget/readme.txt` (new)
- `wordpress-plugin/agentnexlify-widget/assets/icon.png` (new)
- `scripts/build-wp-plugin.sh` (new)

**Blocked by:** none.
**Blocks:** Issue 19.

---

## Issue 19: Build WordpressPluginDownload component (wizard step 5)

**Labels:** `frontend`, `priority:high`

**User story:**
As Maria, I want a "Download plugin" button + walkthrough video in the wizard.

**Acceptance criteria:**
- `frontend/src/components/onboarding-v2/WordpressPluginDownload.jsx`
- Triggers download of `agentnexlify-widget.zip` from CDN/build artifact
- Shows install walkthrough (link/video)
- Falls back to script tag visibility if download blocked
- Tracks `wp_plugin_downloaded` event

**Files expected to change:**
- `frontend/src/components/onboarding-v2/WordpressPluginDownload.jsx` (new)
- `frontend/tests/components/WordpressPluginDownload.test.jsx` (new)

**Blocked by:** Issue 18.
**Blocks:** Issue 10 (consumed by step 5).

---

## Issue 20: Build OnboardingFunnelPage analytics + event taxonomy

**Labels:** `frontend`, `backend`, `priority:medium`

**User story:**
As Aidan, I want a funnel showing signup → step1 → … → completed with drop rates.

**Acceptance criteria:**
- Backend emits 9 events: `onboarding_v2_started`, `_step_completed` (1-5), `_completed`, `auto_kb_invoked/succeeded/failed`, `vertical_preset_applied`, `widget_health_check`, `integration_key_saved`, `kb_badge_ready`
- `frontend/src/pages/Analytics/OnboardingFunnelPage.jsx` renders funnel with drop rates per step
- Mobile-first

**Files expected to change:**
- `backend/services/analytics_events.py` (modify or new)
- `frontend/src/pages/Analytics/OnboardingFunnelPage.jsx` (new)

**Blocked by:** Issues 5, 10.
**Blocks:** Issue 21.

---

## Issue 21: Phased rollout (5% → 25% → 50% → 100%)

**Labels:** `devops`, `priority:critical`

**User story:**
As Aidan, I want to canary v2 to 5% of new signups and ramp based on metrics.

**Acceptance criteria:**
- Railway env vars set: `ONBOARDING_V2_GLOBAL_ENABLED=true`, `ONBOARDING_V2_ROLLOUT_PERCENT=5`, `INTEGRATIONS_ENC_KEY` (32-byte secret)
- Hash-based rollout: hash tenant email → `[0..99]`; flip per-tenant flag if hash < percent
- Global kill-switch verified: setting `ONBOARDING_V2_GLOBAL_ENABLED=false` reverts all in-flight sessions to v1
- Sentry monitoring: 7-day window without P0/P1 before each ramp
- Welcome email retry success ≥95% gate before 25%
- Mobile E2E green gate before 50%
- v1 sunset PR opened week 12 (separate ticket)

**Files expected to change:**
- Railway env config (ops, no code change)
- Possibly `backend/services/feature_flags.py` if hash-rollout helper not present

**Blocked by:** Issues 1-20.
**Blocks:** none.

---

Verified: plan covers 19/19 spec acceptance-criteria buckets across §2 (8 metrics), §6.1 (schema reuse), §6.2 (API contract), §6.3 (UI), §7.1 (new files), §7.2 (modify files), §7.3 (feature flag), §8 (14 edge cases), §9 (security: encryption + CSRF + RLS + audit), §10 (testing strategy), §11 (rollout) — PASS.

---

