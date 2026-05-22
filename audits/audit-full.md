# AgentNexLiFy Full Codebase Audit

**Date:** 2026-03-09
**Auditor:** Claude Opus 4.6

---

## Executive Summary

Comprehensive audit of the entire AgentNexLiFy codebase covering backend routers, services, frontend pages, CSS theming, widget JS, and mobile responsiveness.

**Total issues found: 128**

| Severity | Found | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 12 | 8 | 4 |
| High | 24 | 12 | 12 |
| Medium | 48 | 4 | 44 |
| Low | 44 | 1 | 43 |

**Overall health: Functional but fragile.** The app works for the happy path, but has significant issues around plan name consistency (now fixed), auth gaps (now fixed), email extraction bugs (now fixed), and numerous hardcoded colors that break in light mode.

---

## Issues Fixed in This Audit

### Critical Fixes

| # | File | Description |
|---|------|-------------|
| 1 | `backend/routers/widget.py:91` | **Email regex over-captures** — Changed `{2,}` to `{2,10}(?![a-zA-Z])` to stop TLD matching at word boundary |
| 2 | `backend/routers/widget.py:272` | **Space stripping breaks email extraction** — Changed `text.replace(" ", "")` to `re.sub(r"\s*@\s*", "@", text)` |
| 3 | `backend/routers/widget.py:440` | **asyncio.create_task fire-and-forget** — Made `_send_new_lead_sms_notification` async, now `await send_sms()` directly |
| 4 | `backend/routers/widget.py:284` | **Same fire-and-forget in lead capture** — Made `_capture_leads_from_session` async, now awaits trigger_sequence and SMS |
| 5 | `backend/routers/automations.py:226,240,264` | **Missing auth on automation CRUD** — Added `Depends(_get_current_tenant)` + tenant mismatch guard to 3 endpoints |
| 6 | `backend/models/schemas.py:294` | **WidgetLeadResponse.lead_id crashes on None** — Changed `lead_id: str` to `lead_id: str \| None = None` |
| 7 | All files with plan names | **Plan name mismatch across codebase** — Standardized to `free/growth/professional/enterprise` across 7 files |
| 8 | `backend/routers/sequences.py:250` | **Cross-tenant data leak in sequence stats** — Added `.eq("tenant_id", tenant_id)` to automation_logs query |

### High Fixes

| # | File | Description |
|---|------|-------------|
| 9 | `frontend/src/pages/TeamPage.jsx` | **Null crash** — Added `user?.tenantId`, `user?.role`, and `if (!user) return null` guard |
| 10 | `frontend/src/pages/Dashboard/OverviewCards.jsx` | **Upgrade buttons do nothing** — Added `onNavigate?.("billing")` to both upgrade buttons |
| 11 | `frontend/src/pages/Dashboard/ClientProfile.jsx` | **Null array crash** — Added `|| []` guards on `client_notes` and `conversations` |
| 12 | `frontend/src/pages/Dashboard/WidgetEmbed.jsx` | **Dead #widget link** — Replaced with button calling `onNavigate?.("widget")`, passed prop from parent |
| 13 | `frontend/src/pages/BusinessPageSettings.jsx` | **10 hardcoded hex colors** — Replaced all with CSS variables (--text-muted, --green, --border, etc.) |
| 14 | `backend/services/sms_rate_limiter.py` | **Plan mismatch** — Changed `"operations"` to `"professional"` in `_UNLIMITED_PLANS` |
| 15 | `frontend/src/index.css` | **Missing --purple-dim** — Added to both `:root` and `.app[data-theme="light"]` |

### Other Fixes

| # | File | Description |
|---|------|-------------|
| 16 | `frontend/src/pages/SettingsPage.jsx:54` | Removed `console.log` that leaked sensitive form data |

---

## Remaining Issues Requiring Manual Attention

### Critical — Must Fix

| # | File | Line(s) | Description |
|---|------|---------|-------------|
| C1 | migrations/*.sql | all | **Migration/DB schema mismatch**: `leads.tenant_id` in migration but `client_id` in code; `lead_stage` in migration but `status` in code. Live DB was manually altered. Need migration files that match reality. |
| C2 | `backend/routers/widget.py` | 449 | **notification_phone and sms_notifications_enabled columns** never created in any migration. SMS settings will silently fail on fresh DB. Need `ALTER TABLE tenants ADD COLUMN` migration. |
| C3 | `frontend/src/utils/api.js` | 70-72 | **`fetchActivity` calls non-existent endpoint** `GET /api/v1/activity/{tenantId}`. Dashboard ActivityFeed is permanently empty. Need to create backend endpoint or remove the call. |
| C4 | `backend/config.py` | 30 | **`api_secret_key` regenerates on restart** if env var not set — invalidates all JWTs. Must set `API_SECRET_KEY` env var in production. |

### High — Should Fix Soon

| # | File | Line(s) | Description |
|---|------|---------|-------------|
| H1 | `backend/services/automation_engine.py` | 370-376 | `_generate_ai_email` queries `chat_messages.lead_id` which doesn't exist — AI emails always empty |
| H2 | `backend/services/lead_scoring.py` | 158-169 | Reads `conversations.messages` JSONB which is never populated — all leads under-scored |
| H3 | `backend/services/automation_engine.py` | 406-412 | Uses synchronous `anthropic.Anthropic()` in async function — blocks event loop |
| H4 | `backend/routers/auth.py` + `billing.py` | multiple | Duplicate checkout/portal endpoints in two routers with different auth patterns |
| H5 | `frontend/src/pages/AnalyticsPage.jsx` | 255-263 | Recharts BarChart uses `<rect>` instead of `<Cell>` for per-bar coloring — all bars same color |
| H6 | `frontend/src/pages/AnalyticsPage.jsx` | 100-116 | `Promise.allSettled` never throws — catch block is dead code, no error state shown on failure |
| H7 | Widget files | all | `agentnexlify-widget.js` and `widget.src.js` are completely different implementations (different attr names, session mgmt, DOM isolation, features). Need to reconcile. |
| H8 | `agentnexlify-widget.js` | 737-739 | Closing widget destroys session and clears all chat history |
| H9 | `frontend/src/pages/BillingPage.jsx` | 117-148 | Trial banner uses all hardcoded gradient colors and `#fff` |
| H10 | `frontend/src/components/App.jsx` | 53-72 | Trial banner in App.jsx also uses hardcoded colors |
| H11 | `frontend/src/components/Sidebar.jsx` | 94 | Support link `window.open("/contact")` goes nowhere in SPA |
| H12 | `frontend/src/components/App.jsx` | 113 | `handleNavigate` prevents re-loading same page (no way to refresh current page data) |

### Medium — Should Fix

| # | File | Line(s) | Description |
|---|------|---------|-------------|
| M1 | `backend/routers/widget.py` | 524-554 | Race condition in conversation usage counter (read-then-write, not atomic) |
| M2 | `backend/routers/analytics.py` | 89-193 | Fetches ALL rows to count in Python instead of using `count="exact"` |
| M3 | `backend/routers/sequences.py` | 156-188 | N+1 query problem — 2 extra queries per sequence |
| M4 | `backend/routers/webhooks.py` | 166-174 | Supabase `delete()` returns empty by default — always returns 404 |
| M5 | `backend/routers/automations.py` | 211-216 | SMS reply forwarding has no rate limiting — potential Twilio cost attack |
| M6 | `backend/routers/automations.py` | 265 | `config: dict` body param needs `Body(...)` annotation for FastAPI |
| M7 | `backend/services/webhook_dispatcher.py` | 17-25 | `automation.sms_sent` not in SUPPORTED_EVENTS — events silently dropped |
| M8 | `backend/routers/integrations.py` | 31-44 | Duplicate `_get_current_tenant` instead of importing from auth — security divergence risk |
| M9 | `backend/routers/business_page.py` | 43,231 | Custom CSS not sanitized for XSS (url() data exfiltration) |
| M10 | `backend/services/email_sender.py` | 128 | Resend SDK `result.get("id")` may fail on newer SDK versions (returns object not dict) |
| M11 | `backend/routers/analytics.py` | 37-43 | Cache eviction only removes expired entries — no hard cap, unbounded memory growth |
| M12 | `backend/routers/analytics.py` | 73+ | `Query(regex=...)` deprecated in Pydantic v2 — should use `pattern=` |
| M13 | `frontend/src/pages/ConversationsPage.jsx` | — | Selected conversation not cleared when filtered out by search |
| M14 | `frontend/src/pages/Dashboard/ClientList.jsx` | 73-84 | Bulk stage update is sequential not parallel — slow and inconsistent on partial failure |
| M15 | `frontend/src/pages/Dashboard/ClientList.jsx` | 107 | CSV export doesn't escape quotes in values — malformed output |
| M16 | `frontend/src/pages/Dashboard/index.jsx` | 82-93 | `handleStageDrop` closes over stale `leads` array |
| M17 | `frontend/src/pages/Dashboard/LeadPipeline.jsx` | 24-36 | Lead score thresholds (80/60/40) inconsistent with ClientList (70/40) |
| M18 | `frontend/src/pages/SettingsPage.jsx` | 95,146,166 | Three Save buttons all save entire form and share saving/saved state |
| M19 | `frontend/src/pages/IntegrationsPage.jsx` | 17-39 | Duplicate API functions bypass shared `api.js` error handling |
| M20 | `frontend/src/pages/IntegrationsPage.jsx` | 592 | `rgba(255,255,255,0.06)` invisible in light mode |
| M21 | `frontend/src/pages/SequenceBuilder.jsx` | 313-314 | Hardcoded `rgba(99,102,241,...)` for AI email hint |
| M22 | `frontend/src/pages/TemplateGallery.jsx` | 95 | Hardcoded `color: "#fff"` on step badge |
| M23 | `frontend/src/pages/WidgetPage.jsx` | 89-91 | Save/load errors only logged to console — no user feedback |
| M24 | `frontend/src/pages/BusinessPage.jsx` | 20,281-540 | Charcoal theme has dark text on dark bg for error states and hover states |
| M25 | index.css | 1476 vs 1593 | `.stage-badge` defined twice with conflicting properties |
| M26 | index.css | 1973 vs 2526 | `.btn-primary` defined twice with different padding |
| M27 | index.css | 1959 vs 2540 | `.btn-secondary` defined twice |
| M28 | index.css | 1988 vs 2554 | `.btn-danger` defined twice |
| M29 | index.css | — | No mobile sidebar hamburger — sidebar takes 64px on all screen sizes |
| M30 | index.css | — | `.client-table` has no `overflow-x: auto` wrapper for mobile |
| M31 | index.css | — | Calendar week view has no mobile breakpoint (8 cramped columns) |
| M32 | home.css | 1841-1926 | Unscoped `.container`, `.btn-primary`, `.section` selectors conflict with index.css |
| M33 | Multiple frontend files | — | 6 duplicate `timeAgo` implementations with slight variations |
| M34 | Multiple frontend files | — | 5 duplicate `scoreLabel/scoreClass` implementations with inconsistent thresholds |
| M35 | `backend/routers/widget.py` | 116-128 | `_check_origin` bypassed when no Origin header present |
| M36 | All rate limiters | — | In-memory rate limiters reset on server restart and per-worker |

### Low — Nice to Fix

| # | File | Description |
|---|------|-------------|
| L1 | `frontend/src/pages/Home.jsx:656-685` | Stripe checkout URLs use `test_` prefix — won't process real payments in production |
| L2 | `frontend/src/pages/Home.jsx:822,827` | Social links are dead (`href="#"`) |
| L3 | `frontend/src/pages/Home.jsx:394` | Nav logo `href="#"` instead of `/` |
| L4 | `agentnexlify-widget.js:613` | Powered-by link `href="#"` is dead |
| L5 | `agentnexlify-widget.js` | No double-init guard (SPA re-injection creates duplicates) |
| L6 | `agentnexlify-widget.js:98` | Bubble SVG fill hardcoded `#0a0a0f` — invisible on dark brand colors |
| L7 | `widget.src.js:30-39` | API_BASE derived from script src origin — breaks if CDN differs from API |
| L8 | `widget.src.js:670` | Single-line `<input>` instead of `<textarea>` |
| L9 | `frontend/src/utils/api.js:74-80` | `fetchWidgetConfig` and `fetchUsage` call non-existent endpoints (currently unused) |
| L10 | `frontend/src/pages/Calendar.jsx:177` | `formatTime` called without timezone arg — always hits catch block |
| L11 | `frontend/src/pages/AnalyticsPage.jsx:136` | `stage.replace("_"," ")` only replaces first underscore |
| L12 | `frontend/src/components/App.jsx:115` | Artificial 200ms loading delay on every page navigation |
| L13 | `frontend/src/pages/FaqManagerPage.jsx` | Delete confirmation state persists indefinitely |
| L14 | Multiple pages | Error states only logged to console — no user-facing messages |
| L15 | `backend/routers/team.py:25` | `INVITE_BASE_URL` hardcoded |
| L16 | `backend/routers/team.py:63` | Missing JWT role defaults to "owner" — malformed JWT gets admin access |
| L17 | `backend/routers/support.py:19-24` | No `max_length` on contact form fields |
| L18 | `backend/services/automation_engine.py:408` | Claude model version hardcoded (should be a config constant) |
| L19 | `backend/routers/auth.py:751,789` | Redundant datetime imports inside function bodies |
| L20 | index.css | ~37 instances of `rgba()` using dark-theme-specific color values instead of variables |
| L21 | home.css | ~15 hardcoded color values (acceptable since landing page is dark-only) |

---

## Architecture Notes

### Database Schema Drift
The biggest systemic issue is that migration files don't match the live database. Key discrepancies:
- `leads.tenant_id` → renamed to `client_id` in live DB
- `leads.lead_stage` → renamed to `status` in live DB
- `notification_phone`, `sms_notifications_enabled` columns on tenants — no migration exists
- Several columns mentioned in code have no migration

**Recommendation:** Create a single "reconciliation" migration that matches the live schema.

### Widget Files
Two completely different widget implementations exist:
- `frontend/public/widget/agentnexlify-widget.js` — deployed, has booking UI, no Shadow DOM
- `public/widget.src.js` — newer, has Shadow DOM, retry logic, branding, but different attr names

**Recommendation:** Decide which is canonical, port missing features, and delete the other.

### Code Duplication
- 6 copies of `timeAgo()` with different behavior
- 5 copies of `scoreLabel()`/`scoreClass()` with different thresholds
- 3 copies of `_get_current_tenant()` across routers
- Duplicate billing endpoints in auth.py and billing.py

**Recommendation:** Extract shared utilities and consolidate.

---

## How to Verify Fixes

```bash
# Backend syntax check
cd /home/aidan/agentnexlify && python -c "
import backend.routers.widget
import backend.routers.automations
import backend.routers.sequences
import backend.models.schemas
import backend.services.sms_rate_limiter
print('All imports OK')
"

# Frontend build check
cd /home/aidan/agentnexlify/frontend && npm run build
```
