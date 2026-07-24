# Improvement Backlog — Run 101 (2026-07-24)

## Active This Run: Step 9G
See `winning-concept.md`. Awaiting human approval before implementation.

---

## Parking Lot (future runs)

### Step 9H — Per-Tenant Zero-Conversation Heartbeat Alert
**Evidence:** Keys Koffee widget embed dropped ~2026-06-14, discovered 2026-07-23 — 39 days silent for a paying tenant. Bug pattern: "Silent-green automation: paying tenant's widget missing for 5+ weeks, nobody noticed" (`docs/dev-knowledge/bug-patterns.md` 2026-07-23).
**What's needed:** File GH issue: "Alert when paying tenant has zero widget conversations for >7 days." Implementation requires: (1) Supabase query for per-tenant conversation counts with 7d window, (2) baseline per tenant to distinguish new tenants from drop-offs, (3) Resend email alert on drop-off. Supabase MCP unavailable in headless nightly sessions — must be a separate scheduled job or GH Actions workflow, not a SKILL.md bash block.
**Priority:** HIGH — revenue-risk silent failure class. Keys Koffee is one confirmed case; other tenants may be affected.
**Blocked by:** Supabase MCP headless unavailability. Resolve by building a standalone `scripts/daily/per-tenant-health-check.sh` that uses the REST API (SUPABASE_URL + SUPABASE_SERVICE_KEY env vars) instead of MCP.

### First Booking Conversion Monitoring (Post AI-Panel Ship)
**Evidence:** e9b4972 shipped AI-triggered native booking panel (SHOW_BOOKING_PANEL → `show_booking=True`). No post-ship conversion data yet.
**What's needed:** Query `appointments` table for bookings where `source='widget'` in last 7 days. Alert if zero for >7 days post-ship (would indicate booking panel trigger not reaching production tenants).
**Priority:** MEDIUM — good to verify the feature is converting, but no evidence of failure yet.
**Blocked by:** Same Supabase MCP headless limitation as Step 9H.

### Step 9E Coverage: AUTOPILOT_GH_TOKEN
**Evidence:** GH #399 open — AUTOPILOT_GH_TOKEN expired, blocking automations. Unclear whether Step 9E's credential-rotation check includes this token name in its list.
**What's needed:** Verify the credential list in Step 9E SKILL.md includes `AUTOPILOT_GH_TOKEN`. If not, 1-line addition.
**Priority:** LOW — Step 9E already alerts on expiring credentials; #399 is a human-rotation task regardless.

---

## Closed / No Longer Active
- email_sequences.py god-class split → DONE (ab1a7c2, 2026-07-24)
- Booking CTA plain-text bug → FIXED (e9b4972, 2026-07-24)
- Migration 187 pending_automations policy → DONE (ab1a7c2, 2026-07-24)
- KB compile freshness → DONE (e9b4972 batch compile, 2026-07-24, 124 articles)
- Step 9F KB staleness alert → IMPLEMENTED (run 99)
