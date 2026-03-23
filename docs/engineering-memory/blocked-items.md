# Blocked Items
_Things that need human intervention. Don't waste cycles retrying these._

## Active Blockers

### Migration 065 (client_accounts) not applied
- The `client_accounts` table for white-label client login exists as a migration file but is marked "Pending" in schema-log.md
- Client portal login endpoints will error until this is applied to live Supabase
- **Action needed:** Run migration 065 in Supabase SQL editor

### Migration 064 (lead date_of_birth) application status unknown
- No "Applied" note in schema-log.md for migration 064
- Birthday greetings automation depends on this column existing
- **Action needed:** Verify in live Supabase, apply if missing

### Social media platform OAuth
- Requires Facebook/Twitter/LinkedIn API credentials and app approval
- Currently social posts are create-and-copy only
- **Action needed:** Register developer apps on each platform

### Real SERP data integration
- Requires SEMrush or Ahrefs API subscription ($100+/mo)
- Currently using AI-estimated scores which are directional but not precise
- **Action needed:** Business decision on whether to invest in API access
