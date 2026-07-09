# Audit — Booking Funnel Root Cause (2026-07-09)

Follow-up to `audit-post-deploy-measurement-2026-07-09.md`, which found real booking
conversion is 0% (all 9 prod "appointments" are demo seeds) despite the June 23
booking-nudge prompt work.

## Root cause

`widget_configs.booking_enabled` has been `DEFAULT false` since migration 005, and
**no insert path ever set it**:

- `backend/routers/auth.py` register flow — widget_configs insert omitted the column
- `backend/routers/auth.py` dashboard auto-create fallback — same omission
- Onboarding/preset auto-apply — never touches booking_enabled

Verified live in prod 2026-07-09: `booking_enabled = false` for ALL THREE real paying
tenants (MTOptions, 914 Exterior LLC, Keys Koffee), 0 service_types rows for each.

The June 23 booking-nudge (widget_chat.py `if widget.get("booking_enabled")`) therefore
**never fired for a single real customer**. The product's headline feature — appointment
booking — has been silently disabled for every tenant since launch.

## Fix (shipped 2026-07-09)

1. **Prod data**: `booking_enabled = true` flipped for the 3 real tenants (verified via
   RETURNING). Widget config cache is 5-min TTL, so live within minutes.
2. **Migration 163** (`163_booking_enabled_default_true.sql`, applied to prod):
   column default flipped to `true` — any future insert path gets booking on.
3. **Code** (`backend/routers/auth.py`): both widget_configs inserts now set
   `booking_enabled: True` explicitly.

Tenants can still disable booking in dashboard settings; only the default changed.

## What to watch

- The booking nudge is prompt-level (offers the booking link) and does not require
  service_types or business hours, so enabling it is safe for all three tenants.
- Next measurement pass should check `appointments` for the real tenants (excluding
  demo/internal per the new `is_internal_tenant` demo exclusion) — with 7 real leads
  per 16 days and the nudge now actually firing, any booking >0 validates the funnel.
- If bookings stay at 0 with the nudge live, next suspects: the widget-side booking UI
  flow itself (does the link render/work cross-origin?) and per-tenant fit (MTOptions
  is trading alerts — "book a call" framing may need vertical copy).

## Verification

- Prod: `UPDATE ... RETURNING` showed booking_enabled=true for all 3 tenant_ids;
  migration 163 applied via `apply_migration` — success.
- Live probe of the booking flow with real traffic is pending real visitors; the config
  gate (the blocker) is confirmed removed.
