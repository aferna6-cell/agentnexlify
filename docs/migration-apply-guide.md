# Migration Application Guide — 025 through 032

**Status:** These migrations exist as SQL files but need to be manually applied in the Supabase SQL editor.

**All migrations use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`, so they are safe to re-run.**

## Application Order

Run these in order in the Supabase SQL editor. Copy the full contents of each file.

| # | File | What It Does | Dependencies |
|---|------|-------------|--------------|
| 025 | `migrations/025_content_scheduled_for.sql` | Adds `scheduled_for` DATE to `content_items` | content_items table (migration 023) |
| 026 | `migrations/026_lead_assignment.sql` | Adds `assigned_to` UUID FK to `leads` | leads + team_members tables |
| 027 | `migrations/027_ai_feedback.sql` | Creates `ai_feedback` table | tenants table |
| 028 | `migrations/028_website_content.sql` | Adds `tenants.website_url`, creates `website_content` table | tenants table |
| 029 | `migrations/029_menu_items.sql` | Creates `menu_items` table | tenants table |
| 030 | `migrations/030_orders.sql` | Creates `orders` table | tenants + leads tables |
| 031 | `migrations/031_jobs.sql` | Creates `jobs` + `job_applications` tables | tenants table |
| 032 | `migrations/032_tenant_tag_definitions.sql` | Creates `tenant_tag_definitions` table + seeds system tags | tenants table |

## Verification Queries

After applying, run these to confirm:

```sql
-- 025: content scheduling
SELECT column_name FROM information_schema.columns WHERE table_name = 'content_items' AND column_name = 'scheduled_for';

-- 026: lead assignment
SELECT column_name FROM information_schema.columns WHERE table_name = 'leads' AND column_name = 'assigned_to';

-- 027: ai_feedback table
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ai_feedback');

-- 028: website_content table + tenants.website_url
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'website_content');
SELECT column_name FROM information_schema.columns WHERE table_name = 'tenants' AND column_name = 'website_url';

-- 029: menu_items table
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'menu_items');

-- 030: orders table
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'orders');

-- 031: jobs + job_applications tables
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'jobs');
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'job_applications');

-- 032: tenant_tag_definitions table
SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tenant_tag_definitions');
```

## Features Blocked Without These Migrations

| Migration | Feature | Impact if Missing |
|-----------|---------|-------------------|
| 025 | Content Studio calendar | Scheduled posts won't save dates |
| 026 | Lead assignment | Can't assign leads to team members |
| 027 | AI tuning | Thumbs up/down ratings won't save |
| 028 | Website scanner | Crawl results won't persist |
| 029 | Menu management | Restaurant menu won't save |
| 030 | Order management | Orders won't be created |
| 031 | Job board | Job postings + applications won't work |
| 032 | Conversation tags | AI auto-categorization tags won't persist |
