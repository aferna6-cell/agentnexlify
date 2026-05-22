# God-Class Refactor Plan

Staged plan to bring oversized files under the 600-line threshold
(`.claude/rules/user-rules.md` Rule 9). One file = one self-contained PR.
Never split a file across PRs (Rule 8 — no half-migrations).

## Status

- **Done (template):** `backend/services/local_seo_handlers.py` (886 lines)
  split by concern into `local_seo_execute.py` + `local_seo_fetch.py`
  (+ `local_seo_shared.py` if shared helpers exist). Single importer
  (`routers/local_seo.py`) and its test file fully migrated, old file
  deleted. This split is the reference pattern for service modules.

## Why staged, not one PR

54 files exceed 600 lines (29 backend, 25 frontend). A single mega-PR
touching all of them would be unreviewable and would violate Rule 8:
any file left with some call sites on the old module and some on the
new is a half-migration. Each file is refactored in its own PR, with
its test suite green before and after, then merged before the next.

## Refactor pattern

Per file: (1) read fully, (2) identify 2-3 concerns, (3) extract each
concern to a new module (Rule 12 — new files over bloat), (4) update
ALL importers in the same PR, (5) delete or thin the original — no
re-export shim, (6) run the file's test suite, confirm pass count
unchanged, (7) `grep` the old symbol path returns nothing.

## Backend targets — ranked by size

| File | Lines | Suggested split axis |
|------|-------|----------------------|
| `routers/auth.py` | 1506 | login/signup · token refresh · password reset · OAuth — HARD-STOP grill-me area, plan separately |
| `routers/widget_chat.py` | 1271 | chat loop · streaming · context assembly — widget byte-identical rule does NOT apply (backend) but high blast radius |
| `routers/email_sequences.py` | 1255 | CRUD · enrollment · send/schedule |
| `routers/invoices.py` | 1211 | CRUD · PDF render · payment status |
| `routers/onboarding.py` | 1199 | wizard steps · provisioning · KB seed |
| `routers/calls.py` | 1175 | inbound webhooks · outbound · recording/transcript |
| `routers/leads.py` | 1158 | CRUD · enrichment · pipeline transitions |
| `routers/booking_page.py` | 1065 | page config · slot logic · booking submit |
| `models/schemas.py` | 999 | split per domain → `schemas/leads.py`, `schemas/billing.py`, etc. |
| `main.py` | 909 | extract router registration + middleware setup into modules |
| `routers/billing.py` | 907 | HARD-STOP grill-me area (Stripe) — plan separately |
| `services/automation/rule_engine.py` | 875 | condition eval · action dispatch · scheduling |
| `routers/forms.py` | 860 | builder CRUD · submission handling |
| `routers/bids.py` | 858 | CRUD · quote calc · status flow |
| `routers/widget_lead_helpers.py` | 833 | lead extraction · enrichment · tagging |
| `routers/client_portal.py` | 830 | auth · document access · activity feed |
| `services/automation/scheduled_jobs_ext.py` | 792 | group by job family |
| `routers/widget_chat_helpers.py` | 776 | response formatting · order extraction |
| `routers/marketing_campaigns.py` | 721 | CRUD · send · metrics |
| `routers/admin_analytics.py` | 690 | per report family |
| `routers/sequences.py` | 679 | CRUD · enrollment |
| `routers/appointments.py` | 648 | CRUD · availability · reminders |
| `routers/analytics/dashboard.py` | 628 | per widget group |
| `services/booking.py` | 622 | slot search · conflict check · confirm |
| `routers/pipeline.py` | 619 | stage CRUD · transitions |
| `routers/social_media.py` | 618 | per platform |
| `routers/channels_facebook.py` | 607 | webhook · publish |
| `services/branding_service.py` | 606 | theme · assets |
| `routers/analytics/control_center.py` | 606 | per panel |

## Frontend targets — ranked by size

`LocalSEOPage.jsx` (2253), `ConversationsPage.jsx` (2039),
`LeadDetailDrawer.jsx` (1688), `EmailSequencesPage.jsx` (1554),
`WidgetPage.jsx` (1398), `DocumentsPage.jsx` (1311),
`FormBuilderPage.jsx` (1306), `Home.jsx` (1231), `LeadsPage.jsx` (1206),
`BidsPage.jsx` (1132), `ABTestsPage.jsx` (1119),
`SmartListsPage.jsx` (1114), `SequenceBuilder.jsx` (1044),
`ContentRepurposePage.jsx` (1027), `SocialMediaPage.jsx` (1019),
`OnboardingChecklist.jsx` (1003), `AutomationRulesPage.jsx` (972),
`AnalyticsPage.jsx` (941), `ContentStudioPage.jsx` (938),
`JobsPage.jsx` (896), `MarketingCampaignsPage.jsx` (880),
`IntegrationsPage.jsx` (864), `AdminAnalyticsPage.jsx` (824),
`AgentControlCenterPage.jsx` (756), `MCPSetupPage.jsx` (739).

Frontend split axis: extract presentational sub-components into a
sibling folder (`pages/<Page>/` with `index.jsx` + child components),
extract data-fetching hooks into `hooks/`, keep the page file as
composition only. `npm run build` must pass per PR.

## PR batching

Group ~3-5 independent files per PR-set (no shared importer edits),
ordered low-risk first. Defer `auth.py` and `billing.py` to dedicated
PRs with full grill-me. Run `improve-architecture` skill weekly to
re-rank as files shrink.
