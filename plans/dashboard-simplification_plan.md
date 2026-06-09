# Dashboard Simplification ("Drill Down Unnecessary Pages")

Status: ready to execute (blocked only on the in-flight Item 3 Sidebar edit landing).
Goal: cut nav overwhelm for non-technical owners ("Amazon Quick for small business")
without deleting features. Everything here is reversible (nav visibility only).

## What already exists (do NOT rebuild)
`frontend/src/components/Sidebar.jsx`:
- `NAV_GROUPS` — collapsible sections (OVERVIEW, CRM, COMMUNICATIONS, MARKETING, …).
- Per-item `roles` gating (owner/admin/member/viewer).
- Per-item `businessTypes` gating — applied today only to `menu` + `orders` (restaurant).
- Render filter (Sidebar.jsx ~604-609): `!item.roles || roles.includes(userRole)` AND
  `!item.businessTypes || businessTypes.includes(businessType)`.

So the lever is already built. The bloat is ~50 flat-visible items because most
vertical-exclusive pages carry no `businessTypes` tag → they show for every tenant.

## The change: tag vertical-exclusive pages by `businessTypes`

Only tag pages that are clearly exclusive to a vertical. Broadly-useful pages
(reviews, local_seo, csat, campaigns, social_media, content_studio) stay visible
to all — hiding those is a taste call we are NOT making unilaterally.

| Page key | Add `businessTypes` | Rationale |
|----------|---------------------|-----------|
| `menu`   | `["restaurant"]` (already) | restaurant-only |
| `orders` | `["restaurant"]` (already) | restaurant-only |
| `jobs` (Job Board) | `["home_services","contractor","plumber","hvac","electrician","roofing","landscaping"]` | field-service job dispatch; meaningless to salon/dental/restaurant |
| `bids`   | same contractor set as `jobs` | quoting/estimates are a contractor workflow |
| `waitlist` | `["restaurant","salon","dental","medical"]` | seating/appointment waitlist verticals |

Business-type slugs must match what onboarding writes to `tenants.business_type`.
**Verify the slug set first** (do not guess): read `config/managed_agents.yaml` +
the onboarding write path, and the value `user.businessType` resolves to in
`AuthContext`. If slugs differ (e.g. `home-services` vs `home_services`), use the
real slugs. A wrong slug silently hides a page from everyone in that vertical →
worse than the bloat. This is the one hard gate on this change.

## Default-collapse advanced groups
In Sidebar.jsx group state init, default the advanced groups to collapsed so a new
owner sees Core expanded and Advanced tucked away:
- Expanded by default: OVERVIEW, CRM, COMMUNICATIONS.
- Collapsed by default: MARKETING, and any AUTOMATION/ADMIN/SETTINGS groups.
Keep last-state behavior if the component already persists group open/closed in
component state (it does NOT use localStorage — keep it that way).

## Explicitly NOT doing
- No page deletion. No route removal. No backend changes.
- Not hiding broadly-useful pages per vertical (reviews/local_seo/csat/etc.).
- Not touching the 5 ROUTED_NO_NAV deep-link pages (LeadsPage, ClientProfile,
  Availability, ContentRepurposePage, CallsPage) — those are intentional.

## Execution order (after Item 3 frontend agent lands)
1. Re-read Sidebar.jsx (agent will have added `integration_health`).
2. Confirm real `business_type` slugs (hard gate above).
3. Add `businessTypes` tags per the table.
4. Set default-collapsed advanced groups.
5. `cd frontend && npm run build` — must be clean.
6. Commit on `claude/gap-3-research-worker-87IXF`.

## Verification
- Build clean.
- Manually confirm filter logic: a `business_type="salon"` tenant no longer sees
  jobs/bids/menu/orders; a `restaurant` tenant still sees menu/orders; an untyped
  tenant (`business_type` null/empty) sees the untagged pages (no regression for
  existing tenants who never set a type — empty string fails `.includes`, so
  tagged pages hide; acceptable since untyped tenants are pre-onboarding).
  NOTE: if many live tenants have null business_type, gating would hide pages from
  them. Check that distribution before shipping; if risky, gate only `jobs`/`bids`
  (clearest non-overlap) and defer the rest.
