# Marketing Suite Add-on — $49.99/mo

Separate Stripe subscription gating 7 features:
SEO Audit Hub, Social Media, Marketing Campaigns, Marketing Dashboard,
A/B Tests, Automation Rules, Trigger Logs.

## Rollout Steps

### 1. Create Stripe product + price (one-time)
```bash
curl https://api.stripe.com/v1/products \
  -u "$STRIPE_SECRET_KEY:" \
  -d name="Marketing Suite Add-on" \
  -d description="SEO Audit Hub, Social Media, Campaigns, Dashboard, A/B Testing, Automation Rules, Trigger Logs" \
  -d metadata[addon]=marketing
# → copy prod_XXX

curl https://api.stripe.com/v1/prices \
  -u "$STRIPE_SECRET_KEY:" \
  -d product=prod_XXX \
  -d unit_amount=4999 \
  -d currency=usd \
  -d recurring[interval]=month \
  -d nickname="Marketing Addon Monthly" \
  -d metadata[addon]=marketing \
  -d metadata[interval]=monthly
# → copy price_XXX
```

### 2. Set env var (Railway + local .env)
```
STRIPE_PRICE_MARKETING_ADDON_MONTHLY=price_XXX
```

### 3. Apply migration 102
```bash
# Via Supabase MCP or SQL editor
psql "$DATABASE_URL" -f migrations/102_marketing_addon.sql
```
Migration adds 4 columns to `tenants` and grandfathers existing paid customers.

### 4. Deploy backend + frontend
Backend gates 6 routers via `backend/services/addon_gate.py`:
- `/api/v1/seo` (local_seo)
- `/api/v1/social`
- `/api/v1/campaigns`
- `/api/v1/marketing` (analytics)
- `/api/v1/ab-tests`
- `/api/v1/automation-rules`

Frontend hides sidebar links + shows upsell modal for gated pages in `App.jsx`.

### 5. Verify Stripe webhook
Ensure webhook endpoint `POST /api/v1/billing/webhook` subscribes to:
- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

The dedicated `POST /api/v1/webhooks/stripe` endpoint uses the same add-on
routing, so either configured Stripe webhook URL keeps add-on state in sync.
Webhook handlers distinguish add-on events via `metadata[addon]=marketing`.

### 6. Announce carve-out to grandfathered customers
Existing paid customers (growth/professional/autopilot/enterprise) were auto-grandfathered. Send notice (30-day window recommended) before running deactivation script.

### 7. (Later) Deactivate grandfathered access
```bash
# TODO: script to set marketing_addon_active=false where marketing_addon_grandfathered=true
# Do NOT run until notice window elapses.
```

## Schema reference
`tenants` columns added by migration 102:
| Column | Type | Purpose |
|--------|------|---------|
| `marketing_addon_active` | bool | Gate check. FALSE default. |
| `marketing_addon_stripe_sub_id` | text | Stripe sub id (null for grandfathered). |
| `marketing_addon_started_at` | timestamptz | When access began. |
| `marketing_addon_grandfathered` | bool | TRUE for auto-grandfathered, FALSE for paid sub. |

## API reference
- `POST /api/v1/billing/marketing-addon/checkout` → returns `{checkout_url}`
- `POST /api/v1/billing/marketing-addon/cancel` → schedules cancel at period end
- `/me` response includes `marketing_addon_active` + `marketing_addon_grandfathered`

## Gate behavior
Backend: 402 Payment Required with JSON payload including `upgrade_path`.
Frontend: the dashboard keeps the suite visible in the sidebar, and `App.jsx`
renders `MarketingAddonUpsell` when a tenant without add-on access opens a
gated page.
