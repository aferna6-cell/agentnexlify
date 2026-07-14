# Winning Concept — Run 88 (2026-07-11)

**Date:** 2026-07-11
**Run:** 88
**Category:** customer_value
**Effort:** XS
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE (via GitHub MCP — mcp__github__issue_write)

---

## Recommendation

File a GH issue packaging both booking-funnel diagnostic SQL queries so the human can answer the 0-real-bookings mystery in <5 minutes from the Supabase dashboard.

---

## Why This, Why Now

The Booking Enabled Audit (run 87 winner) has been blocked for 2 consecutive runs by a Supabase MCP availability gap in headless sessions. The nightly-2026-07-11 log explicitly states: "Supabase MCP connector is installed (org level) but not enabled in this chat session." The same gap blocks this subconscious session. Autonomous SQL execution is not currently possible.

However, GitHub MCP IS available. The fastest path from 0-booking-mystery to first-real-booking is a GH issue that packages both diagnostic hypotheses with copy-paste SQL, visible in the human's GitHub dashboard, executable in the Supabase SQL editor in <5 minutes.

Two hypotheses need testing:
1. **booking_enabled=false** — 3 real tenants (MTOptions, 914 Exterior, Keys Koffee) onboarded before `0e0ee00` (2026-07-09). `0e0ee00` set `booking_enabled=True` as onboarding default for NEW tenants only. Pre-existing tenants retain their original value.
2. **No business hours in tenant_availability** — Even if booking_enabled=true, if no time slots exist in the availability table, the booking calendar has nothing to show and silently returns empty.

The asymmetric upside: if booking_enabled=false on any real tenant, the first real booking can happen the same day the human runs the UPDATE.

---

## Implementation Sketch

**AUTONOMOUS-EXECUTABLE — execute during next nightly run via mcp__github__issue_write OR execute this subconscious run if GitHub MCP is available:**

File a GH issue with the following content:

**Title:** `ACTION REQUIRED: Booking funnel diagnostic — 0 real bookings 18 days after launch`

**Labels:** `revenue`, `human-action-required`, `diagnostic`

**Body:**
```markdown
## Problem
0 real bookings since booking feature launched 2026-06-23 (18 days).

7 real leads exist (MTOptions, 914 Exterior, Keys Koffee). No bookings.

Two root-cause hypotheses to test:

---

## Hypothesis A — booking_enabled=false for pre-existing tenants

`0e0ee00` (2026-07-09) set `booking_enabled=True` as the default for new onboarding.
**This was NOT retroactive.** Tenants onboarded before 2026-07-09 retain their original `booking_enabled` value.

### SQL — Hypothesis A check
```sql
SELECT slug, name, booking_enabled, created_at
FROM widget_configs
WHERE slug NOT IN ('demo', 'test', 'sandbox', 'preview')
ORDER BY created_at ASC;
```

**If any real tenant has `booking_enabled=false`:**
```sql
UPDATE widget_configs
SET booking_enabled = true
WHERE slug IN ('mtoptions', '914-exterior', 'keys-koffee')
  AND booking_enabled = false;
```
Then verify: re-run SELECT above and confirm all show `booking_enabled=true`.

---

## Hypothesis B — No business hours configured in availability table

Even if booking_enabled=true, if no time slots exist in the availability table, the booking calendar returns empty — bookings silently fail before the customer ever sees a slot.

### SQL — Hypothesis B check
```sql
-- Check which real tenants have availability hours configured
-- (adjust table name if different from tenant_availability)
SELECT wc.slug, wc.name, wc.booking_enabled,
       COUNT(ta.id) AS availability_rows
FROM widget_configs wc
LEFT JOIN tenant_availability ta ON ta.client_id = wc.id
WHERE wc.slug NOT IN ('demo', 'test', 'sandbox', 'preview')
GROUP BY wc.slug, wc.name, wc.booking_enabled
ORDER BY wc.created_at ASC;
```
Note: if `tenant_availability` doesn't exist, check `widget_configs` for a `booking_hours` JSON column instead:
```sql
SELECT slug, name, booking_enabled, booking_hours
FROM widget_configs
WHERE slug NOT IN ('demo', 'test', 'sandbox', 'preview');
```

**If availability_rows = 0 for real tenants:** the booking calendar has no slots to show. Fix: add business hours via the dashboard Settings → Booking Hours page, or seed directly.

---

## Expected outcome

- Both queries run in the Supabase SQL editor in ~2 minutes.
- If Hypothesis A is true: 1 UPDATE fixes it immediately. 
- If Hypothesis B is true: configure business hours for affected tenants.
- If both are true: fix both.
- If neither: investigate the widget booking UI flow end-to-end (next diagnostic step).

## Context

- Booking feature launched: 2026-06-23
- `0e0ee00` merged: 2026-07-09 (sets booking_enabled=true for new tenants only)
- Real tenants: MTOptions, 914 Exterior, Keys Koffee (all pre-0e0ee00)
- Real leads: 7 (all captured, 0 converted to bookings)
- Supabase MCP unavailable in autonomous sessions — human execution required
```

---

## What This Replaces

Previous active direction: Booking Enabled Audit (run 87, AUTONOMOUS-EXECUTABLE via Supabase MCP). Blocked twice. This replaces the autonomous mechanism with a human-action GH issue — same goal, different execution path.

---

## Confidence

**HIGH** — Evidence is specific (0 bookings × 18 days × known real tenants × known boolean flag × known table). GitHub MCP is available to file the issue. Execution requires human but is fast (<5 minutes). If booking is already enabled for all tenants, the diagnostic still narrows the hypothesis space and guides the next investigation step.

---

## Run 89 Mandate

1. Verify GH issue was filed (check for open issue with `revenue + human-action-required + diagnostic` labels on the booking funnel).
2. Report whether the human ran the diagnostic — check GH issue for a comment with results.
3. If human ran it and found booking_enabled=false: verify UPDATE was applied. Check if first real booking happened.
4. If human ran it and found booking_enabled=true + availability_rows=0: recommend configuring business hours for real tenants. Candidate: add Step 9F to nightly SKILL.md (tenant availability check) — this is now unblocked by the human having confirmed the schema.
5. If GH issue was NOT filed by nightly (AUTONOMOUS-EXECUTABLE path failed): escalate as P0 human-action item with direct revenue label.
6. Secondary: check if GH #399 (AUTOPILOT_GH_TOKEN) + GH #403 (ANTHROPIC_API_KEY) are resolved — if yes, issue-to-pr-loop resumes and Lead Source Analytics (GH #409) gets a draft PR.
