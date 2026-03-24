# Blocked Items
_Things that need human intervention. Don't waste cycles retrying these._

## 2026-03-24
- **Migrations 064-067 need manual Supabase application**: lead_date_of_birth (064), client_accounts (065), waitlist (066), scoring_configs (067) SQL files exist but must be applied to the live database.
- **Social media platform OAuth** — Requires Facebook/Twitter/LinkedIn developer app approval. Cannot be automated.
- **Real SERP data integration** — Requires paid SEMrush/Ahrefs API key.
- **Google Business Profile OAuth** — Code is scaffolded but awaiting Google API credentials/app verification.
- **Python dependencies not in a requirements.txt** — Should create one from the installed packages for deployment reproducibility.
