# Nightly Commit Review — 2026-06-13

**Run time:** 2026-06-13 UTC  
**Commits reviewed:** 27 (last 24h)  
**Status: NO ISSUES REQUIRING IMMEDIATE ACTION**

---

## Triage Summary

| Risk | Count | Action |
|------|-------|--------|
| LOW (docs/ops/CI) | 18 | No action |
| MEDIUM (new features/endpoints) | 6 | Reviewed, no bugs found |
| HIGH (auth/security/tenant isolation) | 3 | Reviewed, all invariants pass |

---

## HIGH-Risk Commits — Reviewed

### `3f79d7f` — PR #254: approve-by-text, activation nudges, tenant health, Spanish widget, web push, e2e journeys

**Files:** 31 changed (+3,500 / -43)  
**Review:** PASS

- `backend/routers/push_subscriptions.py` — SSRF guard present (`endpoint_host_allowed` validates against 5 known browser push service domains). Auth uses `verify_tenant`. No `__future__` import. Uses `tenant_id` on `push_subscriptions` table (new OS-adjacent table, explicitly documented — NOT the `leads`/`conversations` tables).
- `backend/services/activation_nudges.py` — Queries `leads` table using `client_id` (line 253: `.eq("client_id", tenant_id)`). HTML injection protection via `html.escape()` on all tenant-supplied values in email bodies.
- `backend/routers/admin_health.py` — Admin-only (API secret, `hmac.compare_digest`). Rate-limited (10/minute). Correctly aggregates by `client_id` for `leads` and `os_agent_runs`.
- `backend/services/os_push_notify.py` — SSRF guard re-checked at send time (not just subscribe time). Degrades gracefully when VAPID keys not configured.
- `widget/agentnexlify-widget.js` + `frontend/public/widget/agentnexlify-widget.js` — **BYTE-IDENTICAL** (diff confirmed). Spanish i18n added cleanly.
- `frontend/public/sw.js` — Service worker for web push. Minimal scope, no PII.
- `e2e/journeys/` — 3 new journey specs (approval-inbox, demo-funnel, demo-vertical). Read-only demo sessions, soft assertions on timing-sensitive steps.

### `a5e008c` — PR #246: SMS guard (CRITICAL), conversion tracking, audit fixes

**Files:** 21 changed  
**Review:** PASS

- `backend/services/twilio_service.py` — SMS guard added. Demo tenants blocked from sending real SMS via `is_demo_tenant()` check. Guard uses strict identity check (`is True`) to prevent MockMock truthy from silencing real sends.
- `backend/routers/auth_demo.py` — Rate limited, demo token scoped to 2-hour TTL, `block_demo_role` guards billing/phone/deletion routers.
- `backend/services/voice_twiml.py` — demo guard wired.
- All `leads`/`conversations` queries in touched routers use `client_id`. No invariant violations.

### `fe92d28` — PR #245: Public live-demo sandbox

**Files:** 27 changed  
**Review:** PASS

- `backend/routers/auth_demo.py` — Validates vertical slug against allowlist regex before any DB lookup. Falls back gracefully when vertical not seeded. Rate limited (10/minute).
- `backend/services/demo_guard.py` — Cache fails OPEN ("not demo") on DB errors to protect real tenants. Strict `is True` identity check. 5-minute TTL.
- `backend/dependencies.py` — `block_demo_role` dependency added for billing/phone/account-deletion routes.
- Tenant isolation: demo token carries `role="demo"`, guarded by `block_demo_role` on destructive endpoints.

---

## MEDIUM-Risk Commits — Reviewed

| SHA | Description | Verdict |
|-----|-------------|---------|
| `3be44b0` | Demo token budget + delete dead scheduled_jobs tree | PASS — deletion was clean (tree unused since Phase 4 cutover) |
| `aedd701` | Demo chokepoint: webhook + email-reply guards | PASS — guards in email_sender + webhook_dispatcher properly scoped |
| `abc15c4` | SMS approval alerts, review agent, ROI calculator | PASS — `review_requester.py` uses `tenant_table()` for correct `client_id` routing |
| `03cad05` | Wave 2: multi-vertical demo tenants + guided demo tour | PASS — auth_demo expanded cleanly, DemoTour is display-only |
| `5dd16bb` | Wave 1: welcome thread at signup, phone-first PWA | PASS — welcome_thread.py explicitly documents `os_threads`/`os_messages` use `client_id` |
| `066a151` | calls.py split, plumbing demo seeder, funnel readout | PASS — calls.py correctly refactored, voice_call_summary.py isolated |

---

## LOW-Risk Commits

18 commits: 12 auto-log doc commits, CLAUDE.md docs update, ops morning digest, subconscious run, previous nightly review, e2e smoke CI fix, home-services FAQ depth. No action needed.

---

## Invariant Checklist

| Invariant | Status |
|-----------|--------|
| `client_id` (not `tenant_id`) on `leads` + `conversations` | ✅ PASS |
| `status` (not `lead_stage`) for lead status | ✅ PASS — no `lead_stage` column usage found |
| `areas_of_interest` (not `service_interest`) | ✅ PASS — only as compat mapping alias |
| Widget byte-identical (`widget/` == `frontend/public/widget/`) | ✅ PASS |
| No `from __future__ import annotations` in FastAPI files | ✅ PASS |
| Secrets not committed | ✅ PASS |

---

## Design Concerns (Not Bugs)

**MEDIUM — `admin_health.py:103` unbounded leads query**

```python
leads_result = db.table("leads").select("client_id, created_at").execute()
```

Fetches ALL leads rows with no pagination. Code comment says "Zero per-tenant queries; fine at current scale." This will degrade as tenant count grows into tens of thousands. The endpoint is admin-only, rate-limited, and only selects 2 light columns, so not urgent. Recommend adding a `created_at` cutoff (e.g., last 90 days) when leads table exceeds ~500k rows.

**Tracking:** No GitHub issue created — acknowledged design decision per code comment. Flag for architecture review when leads count > 100k.

---

## Auto-Fixes Applied

None — no LOW-risk bugs found in new code.

---

## Next Steps for Human Review

None required. All HIGH-risk commits passed invariant checks. The demo sandbox is live and well-guarded.
