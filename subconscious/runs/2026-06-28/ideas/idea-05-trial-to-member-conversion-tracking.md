# Idea 05: Trial-to-Member Conversion Tracking (Fitness Vertical)

**Category:** Customer Value (Vertical-Specific)  
**Effort:** ~2 days  
**Priority:** LOW

---

## The Opportunity

Fitness vertical gap (`docs/dev-knowledge/customer-gaps.md`): gym/studio tenants need to track when widget-captured leads convert to paying members. Currently, lead status goes from `new` → `qualified` → `converted` with no membership-specific metadata.

Fitness tenants want:
- Trial-to-member conversion rate
- Time from lead capture to first payment
- Which widget campaigns drive best conversion

---

## Evidence

- `customer-gaps.md` — fitness vertical section: "trial-to-member tracking"
- `leads` table has `status` column — no membership lifecycle columns
- Would require migration for `membership_start_date`, `trial_start_date`

---

## Why Not Winner

Fitness-vertical only. Migration required (adds risk, complexity). Impact contained to <20% of tenant base. SMS Dashboard serves all agent_os tenants immediately with no migration.

Defer to vertical-specific sprint.
