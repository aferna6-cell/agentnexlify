# Blocked Items
_Things that need human intervention. Don't waste cycles retrying these._

## Active Blockers

### Migration 065 (client_accounts) not applied
- The `client_accounts` table for white-label client login exists as a migration file but is marked "Pending" in schema-log.md
- Client portal login endpoints will error until this is applied to live Supabase
- **Action needed:** Run migration 065 in Supabase SQL editor

### Migration 066 (waitlist_entries) not applied
- The `waitlist_entries` table for appointment waitlist exists as a migration file
- Waitlist endpoints will error until this is applied to live Supabase
- **Action needed:** Run migration 066 in Supabase SQL editor

### Migration 067 (scoring_configs) not applied
- The `scoring_configs` table for configurable lead scoring exists as a migration file
- Scoring config endpoints will error until this is applied to live Supabase
- **Action needed:** Run migration 067 in Supabase SQL editor

### Migration 068 (conversation_sentiment) not applied
- The `sentiment` column on conversations exists as a migration file
- Sentiment analysis background task + analytics endpoint will work but return empty data
- **Action needed:** Run migration 068 in Supabase SQL editor

### Migration 069 (widget_chat_hours) not applied
- The `chat_hours` and `chat_hours_enabled` columns on widget_configs exist as a migration file
- Chat hours feature will fail silently (falls back to manual toggle)
- **Action needed:** Run migration 069 in Supabase SQL editor

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

### Migration 070 (birthday_automation) not applied
- Adds `birthday_enabled` and `birthday_message` columns to tenants
- Birthday automation settings on SettingsPage will fail until applied
- **Action needed:** Run migration 070 in Supabase SQL editor

### Migration 071 (widget_proactive_greeting) not applied
- Adds `proactive_enabled`, `proactive_delay_seconds`, `proactive_message` to widget_configs
- Proactive greeting feature will fail silently (uses defaults)
- **Action needed:** Run migration 071 in Supabase SQL editor
