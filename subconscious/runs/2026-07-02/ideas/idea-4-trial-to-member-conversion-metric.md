# Idea 4: Trial-to-Member Conversion Tracking (Fitness Vertical)

**Category:** customer_value  
**Effort:** Low  
**AUTONOMOUS-EXECUTABLE:** NO

## Evidence

`docs/dev-knowledge/customer-gaps.md` (Fitness section): "Trial-to-member conversion tracking | Medium | Low" — calls it a Low-effort gap. Fitness simulation confirmed no visibility into how many trial clients convert to paying members.

## Action

1. Backend: `GET /api/v1/analytics/trial-conversion` — counts leads where `source ILIKE '%trial%'` + `status = 'converted'` vs total trial leads in rolling 30/60/90 day windows
2. Frontend: KPI card on AnalyticsPage.jsx (or fitness-specific dashboard view) showing trial→member conversion rate

## Expected Impact

- Closes a specific fitness vertical gap
- Low effort per customer-gaps.md estimate

## Why Not Winner

Single-vertical (fitness). Doesn't apply to the majority of tenants. Moratorium active — adds to queue. Parking lot until moratorium lifts AND fitness vertical has enough tenants to validate.
