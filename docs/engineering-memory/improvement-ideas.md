# Improvement Ideas
_Ideas captured mid-build for later sessions._

## 2026-03-23 Session 2

### Scoring config integration with actual scorer
- The scoring_configs table stores weights but the lead_scoring.py service doesn't read them yet
- Need to update score_lead() to fetch tenant scoring config and apply custom weights
- Currently the config is UI-only; the actual scoring uses hardcoded weights
- Priority: HIGH (feature is incomplete without this integration)

### Waitlist: widget integration
- The waitlist join endpoint exists but the widget JS doesn't offer a "Join Waitlist" button yet
- When available slots are empty, the widget booking panel should show a waitlist option
- Need to update widget JS + booking flow backend to check slot availability and offer waitlist

### Timeline: pagination and filtering
- The timeline endpoint returns all events in a single request
- For leads with long histories (100+ events), should add cursor-based pagination
- Could add type filters (show only messages, only appointments, etc.)

### Daily digest: opt-out setting
- Currently all paid-plan owners get the daily digest
- Should add a `daily_digest_enabled` boolean to tenants table
- Toggle on Settings page

### Pre-commit hook for conversations.tenant_id
- This bug has been fixed 5+ times across different sessions
- A pre-commit hook that greps for `table("conversations").*eq("tenant_id"` would catch it early
- Would save 10+ minutes per occurrence
