# Improvement Backlog — 2026-07-25-pm (Run 102)

## Active — Implemented This Run

### Step 9G: KB autopopulate self-healing trigger (IMPLEMENTED DIRECTLY — 3rd carry-forward)
**Status:** IMPLEMENTED — direct SKILL.md edit, 3rd carry-forward escalation rule fired
**Category:** operational
**Effort:** XS (~35 bash lines in SKILL.md)
**Evidence:** KB 10 days stale when selected (run 100). Step 9F fires alert but no repair. Step 9G absent for 3+ consecutive cycles.
**Action taken:** Step 9G bash block inserted after Step 9F in nightly-commit-review SKILL.md. GH #500-aware: trigger failure branches to GH #403 diagnostic comment with spending-limit as candidate cause.
**Next run mandate:** Verify Step 9G present in SKILL.md (≥1 occurrence). Verify nightly fired it. Verify GH #403 or GH #500 received a diagnostic comment if KB stale.

---

## Parking Lot

### GH Actions spending limit monitor (Step 9H candidate)
**Status:** Deferred — merge into Step 9G failure branch (already done)
**Category:** operational
**Effort:** XS
**Evidence:** GH #500 blocking all CI and workflow automation. Step 9G failure branch now mentions GH #500 explicitly.
**Promote when:** GH #500 recurs a second time OR Step 9G consistently fails with spending-limit as cause.

### Tenant-silence alert nightly step
**Status:** Deferred — waiting for PR #575 merge
**Category:** operational / customer_value
**Effort:** S (nightly step)
**Evidence:** Bug-patterns.md 2026-07-23: Keys Koffee widget missing 5+ weeks undetected. PR #575 (draft, 38 tests) is the canonical fix.
**Blocked by:** Supabase MCP unavailable in headless sessions (confirmed run 88 + run 102). PR #575 is the correct implementation path.
**Promote when:** PR #575 merged AND a second silent-tenant incident occurs.

### VOYAGE_API_KEY credential rotation schedule entry
**Status:** Deferred
**Category:** operational
**Effort:** XS (2-line addition to ops/credential-rotation-schedule.md)
**Evidence:** ops/credential-rotation-schedule.md missing VOYAGE_API_KEY. Step 9G diagnostic comment mentions VOYAGE_API_KEY; rotation schedule should match.
**Promote when:** VOYAGE_API_KEY expires OR Step 9G diagnoses it as a failure cause.

### Booking panel first-week conversion audit
**Status:** Deferred
**Category:** customer_value / code_health
**Effort:** S (query + GH issue)
**Evidence:** Bug-patterns.md 2026-07-23: Booking CTA rendered as unclickable plain text for unknown duration. Revenue impact unquantified.
**Promote when:** Bookings data is queryable in Supabase (requires GH #403 resolved or manual query).

---

## Rejected This Run

*(none new — all top-3 ideas either won, were parked, or had their substance merged into Step 9G)*

---

## Previously Active (carried forward)

### Step 9F: KB staleness alert → GH #403
**Status:** IMPLEMENTED (run 99 winner, nightly-2026-07-22 confirmed firing)

### BotHealthPage.jsx, appointment_completion.py, AttributionPage.jsx
**Status:** IMPLEMENTED (PR #475, run 99 findings)

### LoopHealthPage.jsx — admin frontend for Agent OS loop health
**Status:** Deferred — promote when Agent OS >5 active tenants (currently 3)

### Voice test regression audit
**Status:** Deferred — nightly reports "250 voice tests pass"; re-promote if regression detected

### Owner MCP "Getting Started" quickstart
**Status:** Deferred — human-authored content, not autonomous
