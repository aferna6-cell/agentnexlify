# Plan: onboarding-v2

Spec: `/home/aidan/agentnexlify/specs/onboarding-v2_spec.md`
Audit: `/home/aidan/agentnexlify/audits/audit-onboarding-2026-04-21.md`
Migration started: `/home/aidan/agentnexlify/migrations/112_widget_configs_onboarding_v2.sql` (already applied scope of spec §6.1.1)

## Migration numbering reconciliation (BLOCKER FIX FIRST)

Spec §6.1.1/6.1.3/6.1.4 specifies 115/116/117. Repo committed `112_widget_configs_onboarding_v2.sql` which already contains the 6.1.1 ALTERs (`onboarding_version`, `ready_to_launch`, `readiness_criteria`). It does NOT contain `vertical_preset` or `last_health_check_at` columns from spec §6.1.1 — those still need to ship.

**Decision (per `fill-instructions-before-guessing.md`):** Spec is stale on numbers. Code wins. New migrations slot at next sequential number after 112.

Per `git status` / `migrations/` content baseline (sequential numbering rule in CLAUDE.md):
- `113_widget_configs_v2_extras.sql` — adds `vertical_preset`, `last_health_check_at`, `last_health_check_status` to widget_configs (deferred from 112)
- `114_vertical_presets.sql` — new `vertical_presets` table + RLS + seed
- `115_integrations_encrypt_access_token.sql` — pgcrypto + `access_token_enc BYTEA`, `refresh_token_enc BYTEA`
- `116_welcome_email_attempts.sql` — retry tracking table

**Action item phase 1 step 1**: confirm next-free number with `ls migrations/ | sort -V | tail`. If 113-116 collide, shift up. Document final numbers in `docs/dev-knowledge/schema-log.md`.

## Phasing

Each phase is independently mergeable. Phases 1-3 are backend; 4-5 frontend; 6 WordPress plugin; 7 rollout. Phases 1-3 unblock phases 4-5 once API contracts frozen end of phase 3.

---

### Phase 1 — Schema + encryption foundation

**Goal:** all DB structure landed, encryption vault working, 100% test coverage on key vault.

**Files:**
- `migrations/113_widget_configs_v2_extras.sql` (new)
- `migrations/114_vertical_presets.sql` (new)
- `migrations/115_integrations_encrypt_access_token.sql` (new)
- `migrations/116_welcome_email_attempts.sql` (new)
- `config/vertical_defaults.yaml` (new) — 6 verticals × {services, faqs, hours, avg_ticket, avg_hours_saved_per_lead}
- `backend/services/integration_key_vault.py` (new) — pgp_sym_encrypt/decrypt wrapper, mask helper
- `backend/services/vertical_preset_loader.py` (new) — DB-first, YAML fallback
- `backend/tests/test_integration_key_vault.py` (new) — 100% cov
- `backend/tests/test_vertical_preset_loader.py` (new)
- `docs/dev-knowledge/schema-log.md` (modify)

**Acceptance:**
- All 4 migrations apply cleanly via `mcp__supabase__apply_migration` against staging
- `vertical_presets` seeded with 6 rows from yaml on first apply
- `pytest --cov=backend.services.integration_key_vault --cov-fail-under=100` passes
- Round-trip encrypt→decrypt with `INTEGRATIONS_ENC_KEY` env returns input
- Wrong key → decrypt raises; malformed ciphertext → raises; NULL handling explicit

**Dependencies:** none (foundation phase).

**Edge cases:**
- `INTEGRATIONS_ENC_KEY` missing → vault import raises at module load (fail-fast, not silent)
- pgcrypto extension already enabled on prod (verify via `SELECT * FROM pg_extension WHERE extname='pgcrypto'`)
- Existing `integrations` rows have plaintext `access_token`; backfill is app-level (deferred to phase 3 to avoid half-migration — Rule 8)
- `vertical_presets` global RLS allow-all read intentional; verify no tenant column accidentally added

**Rules applied:**
- `.claude/rules/schema-discipline.md` (migration numbering, RLS)
- `.claude/rules/security-rules.md` (env-var-only key)
- `.claude/rules/user-rules.md` Rule 8 (no half-migrations — plaintext column retained)
- `.claude/rules/python-fastapi.md` (no `from __future__ import annotations`)
- `.claude/rules/self-verification.md` (verify migrations applied + tests green)

**Tests:**
- Backend unit: round-trip, wrong-key fail, malformed fail, NULL handling, key version metadata
- Migration smoke: `mcp__supabase__list_tables` confirms columns exist post-apply

**Failure modes:**
- pgcrypto encrypt with NULL key → app should never reach this (config-checked); test asserts raise
- yaml seed file malformed → migration fails on first apply (acceptable; fix yaml)

---

### Phase 2 — Wizard state machine + readiness + welcome email retry

**Goal:** all `/api/v1/onboarding/v2/*` routes live, wizard state persists, welcome email retries with exponential backoff.

**Files:**
- `backend/models/onboarding_v2.py` (new) — Pydantic for start/step/complete/auto-kb/preset/faqs/hours/readiness
- `backend/routers/onboarding_v2.py` (new) — all `/api/v1/onboarding/v2/*` endpoints
- `backend/services/onboarding_v2_service.py` (new) — state machine, readiness calculator, preset applier
- `backend/services/welcome_email_retrier.py` (new)
- `backend/services/automation/scheduled_jobs.py` (modify) — wire retrier
- `backend/services/email_sender.py` (modify) — record attempt rows
- `backend/main.py` (modify, lines 746-813) — register router
- `backend/routers/auth.py` (modify, 206-349) — set `widget_configs.onboarding_version='v2'` on flagged signup
- `backend/routers/onboarding.py` (modify, 673-825) — v2 wrapper around existing `/auto-kb`
- `backend/services/industry_packs/__init__.py` (modify) — hook into `vertical_preset_loader` for KB seeding
- `backend/tests/test_onboarding_v2.py` (new)
- `backend/tests/test_welcome_email_retrier.py` (new)

**Acceptance:**
- Full wizard flow via httpx test client: start → 5 steps → complete returns `ready_to_launch=true` when criteria met, `widget_api_key`
- `readiness_criteria` JSONB recomputed on every GET — services_count, hours_filled, faqs_count, logo_uploaded
- Welcome email schedule writes 3 attempt rows with backoff (immediate, +30s, +2min, +10min — cap 3 retries)
- 4th-attempt failure flips banner-trigger flag (consumed by frontend phase 5)
- Backend unit ≥80% on new modules
- CSRF token issued on `/start`, rotated per step

**Dependencies:** Phase 1 (vertical_preset_loader, welcome_email_attempts table).

**Edge cases:**
- `business_type='other'` → `vertical_preset` stays NULL, manual entry path
- `/auto-kb` 30s timeout → partial-result return, tenant retry/skip
- Wizard mid-session, flag flipped off → state preserved; resume works regardless of flag
- Readiness criteria future-additive — recompute always; old rows benign
- Step n submitted out of order → 422 with current expected step
- Idempotency: same step submitted twice → second is no-op (return saved state)

**Rules applied:**
- `.claude/rules/python-fastapi.md` (no `__future__`)
- `.claude/rules/api-conventions.md` (path shape, JWT dep)
- `.claude/rules/schema-discipline.md` (`tenant_id` on widget_configs/welcome_email_attempts)
- `.claude/rules/user-rules.md` Rule 9 (don't bloat existing routers; new file `onboarding_v2.py`)
- `.claude/rules/testing-standards.md` (80% on new services)
- `.claude/rules/self-verification.md` (run pytest, report PASS line)

**Tests:**
- Unit: state machine transitions, readiness calc, preset apply, CSRF rotation
- Integration: end-to-end wizard flow with httpx
- Email retrier: simulated time-travel for backoff; cap-3 enforced; 4th-attempt failure path

**Failure modes:**
- DB write fails mid-step → wizard returns 5xx; tenant retries; idempotent step write
- Welcome email Resend 429 → status='failed', schedule next attempt
- Industry pack KB seed conflict with auto-KB → tenant write wins (preset is seed-only post-save)

---

### Phase 3 — Integration keys, health probes, widget health

**Goal:** Stripe/Twilio/Resend keys storable per-tenant, verifiable, masked-readable; widget health endpoint live; allowed_domains exposed.

**Files:**
- `backend/models/integration_key.py` (new)
- `backend/routers/integration_keys.py` (new) — `/api/v1/integrations/keys*`
- `backend/routers/widget_health.py` (new) — `/api/v1/widget/health`
- `backend/services/integration_health_checker.py` (new) — Stripe/Twilio/Resend ping
- `backend/services/widget_health_probe.py` (new)
- `backend/routers/widget_config.py` (modify, 132-150) — expose `allowed_domains` field
- `backend/config.py` (modify, 34-49) — fallback chain: per-tenant key → env var → error
- `backend/main.py` (modify) — register routers
- `backend/tests/test_widget_health_probe.py` (new)
- `backend/tests/test_integration_health_checker.py` (new)
- `scripts/backfill_integration_keys_encrypt.py` (new) — one-shot app-level backfill of plaintext access_token → access_token_enc

**Acceptance:**
- POST `/integrations/keys` saves Stripe/Twilio/Resend, encrypts access_token, returns `verified` boolean
- GET returns masked keys (`sk_live_••••1234`)
- POST `/{provider}/verify` pings provider SDK, returns green/yellow/red with detail
- Stripe `sk_test_` in prod env → yellow with warning
- DELETE blocked if active subscription (Stripe) — 409 with admin path
- GET `/widget/health?domain=...` returns `{loaded, reachable, last_ping_at, origin_allowed}`
- Backfill script encrypts existing plaintext, leaves plaintext column for follow-up sunset migration
- Rate limits: `/keys/{provider}/verify` 10/min/tenant; `/widget/health` 60/min/api_key
- All `integrations` writes log to `audit_log` with tenant_id + provider, never key value

**Dependencies:** Phase 1 (vault, encrypted columns).

**Edge cases:**
- Tenant pastes Stripe key with leading/trailing whitespace → strip before save
- Tenant deletes key while subscription active → 409, surfaces admin path
- Twilio account_sid mismatch with key → verify returns red with parsed error
- Widget health: tenant domain not in `allowed_domains` → `origin_allowed: false` with hint
- Encryption key rotation → versioned `metadata.enc_key_version`; rotation job decrypts old, encrypts new

**Rules applied:**
- `.claude/rules/security-rules.md` (key never logged, masked display, env-only enc key)
- `.claude/rules/api-conventions.md` (auth dep, rate limits)
- `.claude/rules/schema-discipline.md` (RLS service-role on integrations preserved)
- `.claude/rules/widget-rules.md` (no widget JS change in this phase)
- `.claude/rules/user-rules.md` Rule 9 (split widget_health from widget_config router — Rule 9 god-class threshold)

**Tests:**
- Unit: health checker decision tree (mock Stripe/Twilio/Resend SDK), probe origin check, timeout
- Integration: save → verify → mask → delete happy path per provider; sad paths
- Backfill script: plaintext + missing-encrypted → encrypts; idempotent on re-run

**Failure modes:**
- Stripe SDK timeout → red with "timeout"; cached for 60s to prevent thrash
- Twilio account_sid drift → yellow "credentials match different account"
- Resend domain not verified yet → yellow "domain pending"

---

### Phase 4 — Wizard frontend (mobile-first)

**Goal:** Signup v2, 5 wizard steps, ReadyToLaunch badge, all under 375px viewport.

**Files:**
- `frontend/src/pages/SignupPage.jsx` (modify, 38-340) — reduce to 4 fields, Google primary
- `frontend/src/pages/onboarding-v2/OnboardingWizardV2Page.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepBusinessV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepServicesV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepAutoKbV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepHoursFaqV2.jsx` (new)
- `frontend/src/pages/onboarding-v2/WizardStepInstallV2.jsx` (new)
- `frontend/src/components/onboarding-v2/VisualHoursPicker.jsx` (new)
- `frontend/src/components/onboarding-v2/FaqBulkImport.jsx` (new)
- `frontend/src/components/onboarding-v2/AllowedDomainsInput.jsx` (new)
- `frontend/src/components/onboarding-v2/WidgetHealthCheck.jsx` (new)
- `frontend/src/components/onboarding-v2/VerticalPresetPicker.jsx` (new)
- `frontend/src/components/widget/ReadyToLaunchBadge.jsx` (new)
- `frontend/src/utils/api/onboardingV2.js` (new)
- `frontend/src/App.jsx` (modify) — route `/onboarding` to v2 when flag on

**Acceptance:**
- Signup completes with 4 fields on iPhone 13 / Pixel 6 viewports without horizontal scroll
- Google OAuth button visible above email form
- All 5 wizard steps fit 375px viewport, single-column, progress bar top
- Visual hours picker: tap day, tap from/to time, save → backend hours endpoint
- FAQ bulk import: CSV upload + paste-lines, 200-row cap with 413 surfaced
- ReadyToLaunchBadge: 4 checkmarks → pill flips green
- Auto-KB step: 30s spinner, partial-result fallback, manual entry escape
- Welcome email failure banner appears when 4th attempt fails

**Dependencies:** Phases 2-3 (API contracts frozen).

**Edge cases:**
- localStorage NOT used (CLAUDE.md rule 6) — wizard state via API, not browser
- Browser timezone detection fails → fall back to America/Chicago default + dropdown
- CSV with non-UTF8 encoding → reject 422 client-side
- Google OAuth no email scope → email-password fallback with google_id pre-link
- Touch hours picker on small viewport → time picker uses native iOS/Android picker

**Rules applied:**
- `.claude/rules/frontend-patterns.md` (dark theme, live API, helpful empty state)
- `.claude/rules/widget-rules.md` (no widget JS change)
- `.claude/rules/user-rules.md` Rule 12 (new files per concern)

**Tests:**
- Vitest unit: VisualHoursPicker grid + timezone, FaqBulkImport parsers, ReadyToLaunchBadge state matrix
- Playwright E2E mobile (`frontend/tests/onboarding-v2/wizard-flow.spec.js`): iPhone 13 + Pixel 6 devices, full signup → wizard 1-5 → install
- Manual mobile smoke (Safari iOS, Chrome Android) before merge

**Failure modes:**
- Step 3 auto-KB exceeds 30s → UI shows "Skip and enter manually"
- Step 5 plugin download blocked by browser → fallback to script tag visible
- WidgetHealthCheck 403 (origin mismatch) → hint with `www.` suggestion

---

### Phase 5 — Settings pages + sidebar

**Goal:** integration keys UI, health dashboard, allowed_domains standalone editor.

**Files:**
- `frontend/src/pages/Settings/IntegrationsKeysPage.jsx` (new)
- `frontend/src/pages/Settings/IntegrationHealthDashboard.jsx` (new)
- `frontend/src/pages/Settings/AllowedDomainsPage.jsx` (new)
- `frontend/src/utils/api/integrationKeys.js` (new)
- `frontend/src/components/Sidebar.jsx` (modify) — Integrations sub-menu
- `frontend/src/pages/IntegrationsPage.jsx` (modify, 246) — Stripe/Twilio/Resend pills
- `frontend/src/App.jsx` (modify) — route new Settings pages

**Acceptance:**
- IntegrationsKeysPage: paste key → save → green/yellow/red pill with verification status
- IntegrationHealthDashboard: aggregate view of Google Calendar + Stripe/Twilio/Resend
- AllowedDomainsPage: add/remove domains, save to backend, save reflected in widget config
- Sidebar sub-menu: Google Calendar, Stripe, Twilio, Resend, Health Dashboard
- Mobile-first under 375px

**Dependencies:** Phase 3 backend.

**Edge cases:**
- DELETE key with active sub → show 409 message inline, link to billing
- Stripe test key in prod → yellow pill with explicit copy "this is a test key"
- Verify rate-limited (10/min) → cooldown timer surface

**Rules applied:**
- `.claude/rules/frontend-patterns.md`
- `.claude/rules/security-rules.md` (never display unmasked key after save; mask client-side)

**Tests:**
- Vitest: pill component state matrix, mask helper
- Playwright: save → verify → delete loop per provider

**Failure modes:**
- Verify endpoint 5xx → pill red "verification unavailable", retry button

---

### Phase 6 — WordPress plugin

**Goal:** zip-downloadable plugin, embeds widget script, admin API key entry.

**Files (new directory):**
- `wordpress-plugin/agentnexlify-widget/agentnexlify-widget.php`
- `wordpress-plugin/agentnexlify-widget/admin.php`
- `wordpress-plugin/agentnexlify-widget/widget-injector.php`
- `wordpress-plugin/agentnexlify-widget/readme.txt`
- `wordpress-plugin/agentnexlify-widget/assets/icon.png`
- `scripts/build-wp-plugin.sh` (new) — zip
- `frontend/src/components/onboarding-v2/WordpressPluginDownload.jsx` (new) — download CTA + walkthrough

**Acceptance:**
- `bash scripts/build-wp-plugin.sh` produces `agentnexlify-widget.zip`
- Plugin installs via WP admin upload, shows admin page for API key
- Plugin injects script tag via `wp_footer` hook
- API key sent in `X-Widget-Api-Key`, origin enforced by existing `widget_chat_helpers.py:_check_origin`
- Plugin no PHP errors on WP 6.4+ (verify in local WP install)

**Dependencies:** Phase 4 (download component lives in WizardStepInstallV2).

**Edge cases:**
- Tenant pastes wrong API key → widget loads but `/api/chat` returns 401 → tenant sees error in admin page health panel (future scope; v1 just shows in widget devtools)
- Multiple WP sites with same key → both work as long as both domains in `allowed_domains`
- WP version <5.5 → plugin requires 5.5+; readme.txt declares

**Rules applied:**
- `.claude/rules/widget-rules.md` (script tag content unchanged from `widget/agentnexlify-widget.js` and `frontend/public/widget/agentnexlify-widget.js`)
- `.claude/rules/security-rules.md` (no tenant credentials in plugin beyond public API key)

**Tests:**
- Manual install in local WordPress 6.4 docker
- Plugin lint via `phpcs` if available
- Widget renders on WP page; chat reaches backend

**Failure modes:**
- Theme blocks `wp_footer` hook → plugin doc lists incompatible themes
- Plugin zip > WP upload limit → unlikely (assets small); chunk if needed

---

### Phase 7 — Funnel analytics + rollout

**Goal:** event taxonomy live, dashboard visible, 5%→25%→50%→100% rollout.

**Files:**
- `frontend/src/pages/Analytics/OnboardingFunnelPage.jsx` (new)
- `backend/services/analytics_events.py` (modify or new) — emit `onboarding_v2_started`, `_step_completed`, `_completed`, `auto_kb_invoked/succeeded/failed`, `vertical_preset_applied`, `widget_health_check`, `integration_key_saved`, `kb_badge_ready`
- Railway env vars (ops): `ONBOARDING_V2_GLOBAL_ENABLED`, `ONBOARDING_V2_ROLLOUT_PERCENT`, `INTEGRATIONS_ENC_KEY`

**Acceptance:**
- Each wizard step emits its event with tenant_id + step_n
- OnboardingFunnelPage shows: signup→step1→…→completed funnel with drop rates
- `ONBOARDING_V2_ROLLOUT_PERCENT=5` flips ~5% of new signups
- `ONBOARDING_V2_GLOBAL_ENABLED=false` reverts all in-flight sessions
- Welcome email retry success ≥95% in first canary week
- Mobile signup share metric exposed (User-Agent on register)

**Dependencies:** Phases 1-6 merged.

**Rollout phases (per spec §11):** dev/internal → 5% canary → 25% → 50% → 100% → v1 sunset week 12.

**Rules applied:**
- `.claude/rules/security-rules.md` (env vars never committed)
- `.claude/rules/self-verification.md` (post-deploy verify each rollout %)

**Tests:**
- Manual: flip flag for one tenant, verify v2 path; flip global off, verify revert
- Sentry watch: zero P0/P1 in canary week before ramp

**Failure modes:**
- Welcome email retrier dies under load → fall back to single-shot send (existing behavior)
- Funnel events drop → analytics gap, not user-facing break

---

## Cross-cutting risks

| Risk | Mitigation |
|---|---|
| Encryption key loss | Document key in 1Password + Railway; rotation procedure in `docs/dev-knowledge/architecture-decisions.md`; versioned key header |
| Plaintext `access_token` retained → exfil risk if DB leaks before sunset | Sunset migration scheduled as separate fully-planned PR after backfill verified (Rule 8) |
| Widget byte-identical drift between `widget/` and `frontend/public/widget/` | Pre-commit hook `diff -q`; v1 of this PRD makes zero widget JS changes |
| Mobile regressions on existing v1 wizard | v2 routes new — v1 untouched until week 12 sunset |
| `tenant_id` vs `client_id` confusion on new tables | All new tables use `tenant_id` (widget_configs, integrations, welcome_email_attempts pattern); leads/conversations untouched |
| Migration number collision with marketing/ops parallel work | Coordinate at branch open; use 113-116 if free, shift if not |
| Opus 4.7 literal-following on prompts to executor | Plan deliberate; phase boundaries explicit; acceptance criteria binary |

## Test strategy summary

- **Backend unit:** ≥80% on new services; **100% required** on `integration_key_vault.py` (CI gate)
- **Backend integration:** httpx-driven full wizard flow; key verification per provider (mocked SDKs)
- **Frontend unit:** Vitest on hours picker, FAQ import, readiness badge
- **E2E:** Playwright mobile-only on iPhone 13 + Pixel 6
- **Manual:** Safari iOS + Chrome Android smoke before each merge in phase 4-5
- **Security:** `pytest --cov=backend.services.integration_key_vault --cov-fail-under=100` CI gate
- **Migration smoke:** `mcp__supabase__list_tables` post-apply

## Self-verification checklist

Mapped to spec acceptance criteria:

| Spec § | Criterion | Phase covered |
|---|---|---|
| §2 metric 1 | Time-to-first-lead <120 min | 4, 5, 6, 7 (full path) |
| §2 metric 2 | Signup completion 75% | 4 (4-field signup) |
| §2 metric 3 | Wizard completion 90% | 2, 4 (state machine + UI) |
| §2 metric 4 | Widget-live rate 85% | 3, 4, 6 (probe + UI + WP plugin) |
| §2 metric 5 | KB badge 70% | 2, 4 (criteria + badge) |
| §2 metric 6 | Welcome email 99% | 2 (retrier) |
| §2 metric 7 | Integration keys 50% | 3, 5 (vault + UI) |
| §2 metric 8 | Mobile signup share | 7 (analytics) |
| §6.1 schema reuse | Extend not parallel | 1 (migrations 113-116) |
| §6.2 API contract | All 13 endpoints live | 2, 3 |
| §6.3 UI | 5 wizard steps + 3 settings pages | 4, 5 |
| §7.1 new files | All listed files | 1-6 |
| §7.2 modify files | All listed modifications | 1-7 |
| §7.3 feature flag | onboarding_v2 + global + percent | 7 |
| §8 edge cases | All 14 scenarios handled | 2, 3, 4, 5 |
| §9 security | Encryption + CSRF + RLS + audit | 1, 2, 3 |
| §10 testing | Unit + integration + E2E + 100% vault cov | 1-6 |
| §11 rollout | Phased % rollout + revert | 7 |

---

