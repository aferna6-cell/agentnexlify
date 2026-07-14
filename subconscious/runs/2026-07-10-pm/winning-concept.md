# Winning Concept — Run 87 (2026-07-10-pm)

**Date:** 2026-07-10-pm
**Run:** 87
**Category:** customer_value
**Effort:** XS
**Confidence:** HIGH
**Status:** AUTONOMOUS-EXECUTABLE

---

## Mandate Fulfillment Note

Run_87_mandate conditions were met ahead of schedule by morning-digest-2026-07-10:
- ✅ `ops/credential-rotation-schedule.md` created
- ✅ Step 9E added to `.claude/skills/nightly-commit-review/SKILL.md`
- ✅ Lead Source Analytics GH issue created with `ai-ready` label (run 85 promotion)

All three mandate items confirmed. This run proceeds with free-choice winner.

---

## Recommendation

Query `widget_configs` for real tenant `booking_enabled` status and file a GH issue with exact UPDATE statements if any paying tenant has `booking_enabled=false`.

---

## Why This, Why Now

AgentNexLiFy has 7 real leads and 0 real bookings. The booking feature shipped 2026-06-23 (17 days ago). The `0e0ee00` commit (2026-07-09) set `booking_enabled=True` as the default for new onboarding — but it writes this flag during the onboarding flow, not retroactively. MTOptions, 914 Exterior, and Keys Koffee all onboarded before `0e0ee00`. If any of them have `booking_enabled=false`, they have been silently unable to receive bookings for the full 17 days since the booking feature launched.

This is testable in one Supabase query. If booking is already on, the diagnostic closes the question and we can focus elsewhere. If booking is off, fixing it takes one Supabase UPDATE per tenant — the first real booking could happen the same day.

The Supabase MCP runs independently of the broken GitHub Actions workflows (GH #399/#403). Nightly commit review uses MCP tools directly, not GitHub Actions secrets. This idea is unblocked by the credential crisis.

---

## Implementation Sketch

**AUTONOMOUS-EXECUTABLE — nightly commit review executes this during Step 9 or Step 10:**

1. **Query real tenant booking_enabled status:**
   Use `mcp__supabase__execute_sql` (or equivalent) to run:
   ```sql
   SELECT slug, name, booking_enabled, created_at
   FROM widget_configs
   WHERE slug NOT IN ('demo', 'test', 'sandbox', 'preview')
   ORDER BY created_at ASC;
   ```
   Note: exclude demo tenants by checking against known demo slugs from `brain/Maps/` or by looking for `is_demo=true` flag if present.

2. **Identify real paying tenants:**
   Cross-reference results against known real tenants:
   - MTOptions (mtoptions)
   - 914 Exterior (914-exterior or similar)
   - Keys Koffee (keys-koffee or similar)
   
   Look for `booking_enabled=false` on any of these.

3. **If any real tenant has `booking_enabled=false`:**
   File GH issue via `mcp__github__issue_write`:
   - **Title:** `fix(tenants): booking_enabled=false on real paying tenants — revenue blocked`
   - **Labels:** `bug`, `revenue`, `human-action-required`
   - **Body:**
     ```
     ## Problem
     {N} real paying tenant(s) have booking_enabled=false as of {date}.
     The booking feature launched 2026-06-23. These tenants cannot receive bookings.
     
     ## Tenants affected
     {list each: slug, name, booking_enabled value}
     
     ## Fix
     Run in Supabase SQL editor or via MCP:
     ```sql
     UPDATE widget_configs
     SET booking_enabled = true
     WHERE slug IN ({list slugs})
     AND booking_enabled = false;
     ```
     
     ## Verification
     After update: re-run SELECT above to confirm booking_enabled=true for all real tenants.
     Check booking endpoint returns availability for affected tenant.
     
     ## Context
     0e0ee00 (2026-07-09) set booking_enabled=true as onboarding default — but this
     only applies to new tenants. Existing tenants retain their original value.
     ```

4. **If all real tenants have `booking_enabled=true`:**
   Log "Booking Enabled Audit: all {N} real tenants have booking_enabled=true — no action needed"
   in nightly commit log. The 0-booking problem is elsewhere (widget UI, availability setup, etc.).

5. **Add to nightly log:**
   "Booking Enabled Audit: {N} tenants checked, {M} have booking_enabled=false"

---

## What This Replaces

Previous active direction was Lead Source Analytics (run 85) — GH issue now created by morning digest. That feature will be implemented by issue-to-pr-loop once GH #399 (AUTOPILOT_GH_TOKEN) is fixed by human.

This run pivots to the revenue question that doesn't require any new features to answer: are existing tenants even able to book?

---

## Confidence

**HIGH** — Evidence is specific (0 bookings × 17 days × known tenant list × known boolean flag). Implementation uses Supabase MCP which is unblocked by the GitHub Actions credential crisis. If booking is already on, the diagnostic still provides value by ruling out this hypothesis. No schema change, no code change, no production risk.

---

## Run 88 Mandate

1. Verify nightly ran the Booking Enabled Audit (check nightly log for "Booking Enabled Audit:")
2. Report result: how many real tenants have `booking_enabled=false`?
3. If `booking_enabled=false` found: verify GH issue was filed with `revenue` + `human-action-required` labels.
4. If all tenants have `booking_enabled=true`: next question is booking availability setup. Do real tenants have business hours configured? (Check `tenant_availability` or equivalent table.) If hours missing = no available slots = bookings silently rejected.
5. Secondary: verify Lead Source Analytics GH issue has a draft PR (once GH #399 is fixed by human). If still no PR: diagnose loop via Step 9D nightly report.
6. Parking lot from this run: Referral Reward Pre-Gate Diagnostic (run 88 candidate once automation pipeline restored).
