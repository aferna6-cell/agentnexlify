-- 163_booking_enabled_default_true.sql
--
-- Booking is the product's headline feature, but migration 005 created
-- widget_configs.booking_enabled with DEFAULT false and no insert path ever
-- set it — so every tenant since launch has had online booking silently
-- disabled. The 2026-07-09 post-deploy audit found ZERO real appointments
-- ever booked (the "9" in prod are demo seeds); the June booking-nudge prompt
-- work is gated on booking_enabled and therefore never fired for a real
-- customer.
--
-- Flip the column default to true so every future widget_config gets booking
-- on. Existing rows are updated separately (real tenants flipped 2026-07-09;
-- see audits/audit-booking-funnel-2026-07-09.md). Tenants can still disable
-- booking in dashboard settings — this only changes the default.

ALTER TABLE widget_configs ALTER COLUMN booking_enabled SET DEFAULT true;
