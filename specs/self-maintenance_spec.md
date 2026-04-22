# Feature: Self-Maintenance — Phase 3c

**Status:** Draft (schema-verified against `audits/existing-infra-reference-2026-04-21.md`)
**Author:** Aidan
**Date:** 2026-04-21
**Phase:** 3c (parallel with ops-automation-surfacing + marketing-automation + onboarding-v2)
**Positioning:** "Install once — it keeps itself current."
**Target tier:** Full Office **only** (V1). AI Receptionist + Marketing tier in V2. AI Receptionist tier never (LLM cost model incompatible).
**Ship bar:** ≥80% of Full Office tenants have a KB ≤30 days fresh (verified via `website_crawl_history.crawled_at`).

---

## 1. Executive Summary

SMBs don't keep their chatbot KB current. Prices change, hours shift seasonally, a crew member quits, a service line is added or dropped. The tenant never logs in to fix the KB, so the widget starts answering stale. Three months in, trust erodes: the widget quotes last season's pricing and books appointments during the hours the tenant no longer works.

Self-maintenance makes the KB self-healing. Every Sunday 7 AM tenant-local time, the system re-crawls the tenant's website, detects diffs in four categories (services, hours, prices, contact info), runs Claude Haiku across the before/after snippets, and produces suggestion cards on the dashboard. Each card is a one-tap approve/reject/edit decision. A Sunday digest email summarizes the pending work. The whole experience takes the tenant under 60 seconds per week and keeps the KB within 30 days of reality.

This is the one feature that positions AgentNexLiFy as "install once" — every competitor (GoHighLevel, Birdeye, Podium) is another dashboard the owner has to maintain. We invert that.

All scheduling rides the existing `automation_rules` event-driven framework (migration 087) via a new `website_resync` rule_type. All diff detection rides the existing `kb_section_hashes` table (migration 109). No parallel cron, no parallel hashing. Two new tables, one ALTER on `widget_configs`.

---

## 2. Goals (measurable)

- **G1 — Freshness:** ≥80% of Full Office tenants have `last_crawl_at ≤ 30 days ago` at any point after 60 days on the feature.
- **G2 — Engagement:** ≥1 suggestion approved per tenant per month (validates the cards are readable and the LLM's flags are meaningful).
- **G3 — Crawl reliability:** 95%+ of scheduled crawls succeed on first attempt. 99%+ succeed within 3 retries.
- **G4 — Digest read-through:** ≥60% open rate on Sunday digest email; ≥30% click-through to dashboard.
- **G5 — Zero dashboard drift:** No tenant has `next_crawl_at IS NULL` for > 24 hours after `self_maintenance_enabled = true`.

---

## 3. Non-Goals (V1)

- GCal sync of business hours → KB (V2)
- Stripe new-product webhook → KB suggestion (V2)
- Lead qualifier "uncertain" feedback loop → KB low-confidence flag (V2)
- FAQ staleness detector (FAQ unused in chat for 60 days) (V2)
- Auto-generate FAQ from repeated chat patterns (3+ similar asks/month) (V2)
- Auto-apply approved changes without tenant review (never — trust breaks)
- Multi-site crawling (tenant.com + tenant.shop) — V1 single domain only
- Non-HTML sources (PDF menus, Google Sheets, Drive docs) — V1 web only
- AI Receptionist tier gating (permanent exclusion — LLM cost per tenant exceeds tier ARPU)
- Marketing + AI Receptionist tier (V2 — pending cost model validation)
- Weekly crawl cadence configurable per-tenant (V1 fixed Sunday 7 AM local; plan-based cadence in V2)
- Sub-page change attribution beyond category tagging (V2 adds "what page this came from" click-through)

---

## 4. User Stories

### Tenant — "doesn't have time"

1. As a plumbing owner who hasn't logged into the dashboard since month 2, I want my Sunday digest email to tell me "3 things changed on your site this week — 2 approve, 1 needs your eye" so I can review in under 60 seconds while drinking coffee.
2. As an HVAC owner who raised my emergency-call-out fee from $149 to $189 on my website, I want the system to detect the price change, show me a card that says "Your emergency fee page changed $149 → $189. Update chatbot?", and let me tap Approve.
3. As a cleaning company owner who added Saturday hours, I want the chatbot to stop telling customers "we're closed weekends" within 7 days of my website reflecting the new hours — without me touching the KB editor.
4. As a power-washing owner who dropped a service line (gutter cleaning), I want the suggestion card "Service removed from website: gutter cleaning. Stop chatbot from offering it?" so I can one-tap Reject if it was temporary or Approve if permanent.
5. As a tenant on my dashboard, I want a status card that says "X suggestions pending, last crawl 2 days ago" so I know the system is actively working.
6. As a tenant who rejected a suggestion last week (false positive), I want the system to NOT resurface the same diff next week unless the website changed again — reject is sticky until the underlying content changes.

### Customer (end user of the widget)

7. As a homeowner asking "what's your after-hours rate" via the widget, I want an answer that reflects this month's pricing, not last season's — my trust in the business depends on the chatbot being right.

### Developer / Operator

8. As a backend dev, I want self-maintenance scheduling to ride `automation_rules` (migration 087) via a new `website_resync` rule_type, not a parallel cron table, because we already have execution logging + RLS + tenant scoping solved.
9. As a backend dev, I want diff detection to use `kb_section_hashes` (migration 109) — one row per section, `content_sha256` tells me if anything changed — not a parallel hash table.
10. As a backend dev, I want PII scrubbing in a single chokepoint before any crawled content reaches the LLM so compliance audit is a single-file review.

### Compliance

11. As a compliance officer, I want a recorded opt-in event for every tenant before first crawl fires, with timestamp + IP + user-agent + ToS version.
12. As a compliance officer, I want the crawler to respect `robots.txt` and back off on 429s — we don't crawl sites that don't want to be crawled.
13. As a compliance officer, I want PII (phone numbers, emails, full names) stripped from crawled HTML before it reaches Claude so we never send third-party PII to an LLM without a processor agreement.

---

## 5. Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Tenant KB age (days since last_crawl_at) | ∞ (no crawl infra) | ≤30 days for 80%+ of Full Office tenants after 60 days | `SELECT AVG(NOW() - last_crawl_at) FROM widget_configs WHERE self_maintenance_enabled = true` |
| Suggestions approved per tenant per month | 0 | ≥1 | `SELECT client_id, COUNT(*) FROM maintenance_suggestions WHERE status='approved' AND approved_at > NOW() - interval '30 days' GROUP BY client_id` |
| Crawl first-attempt success rate | n/a | ≥95% | `website_crawl_history.status='success' AND attempt=1 / total crawls` |
| Crawl 3-retry success rate | n/a | ≥99% | `website_crawl_history.status='success' AND attempt<=3 / total crawls` |
| Sunday digest open rate | n/a | ≥60% | `email_events.event_type='open' AND campaign_tag='self_maint_digest'` |
| Sunday digest click-to-dashboard | n/a | ≥30% | `email_events.event_type='click' AND campaign_tag='self_maint_digest'` |

**Ship → V2 criteria (any 2 of 3):**
- ≥5 Full Office tenants approved ≥1 suggestion in first 30 days
- Crawl reliability ≥95% first-attempt over 4 weeks
- Zero P1 Sentry errors in `self_maintenance_service` over 2 weeks

---

## 6. Design

### 6.1 Data Model

#### Reuse (DO NOT RECREATE)

**Scheduling: `automation_rules` (migration 087).**
One row per tenant with:
- `trigger_type = 'scheduled_weekly'` (existing enum value)
- `trigger_config = {"day_of_week": 0, "hour": 7, "timezone": "<tenant tz>"}` (0 = Sunday)
- `actions = [{"type": "website_resync"}]` (new action type handled by `automation_engine`)
- `is_active = true` (drives disable via `self_maintenance_enabled=false`)
- Executions log to `automation_rule_executions` (existing) — gives us free retry tracking, `execution_time_ms`, `error_message`, `actions_run` JSONB.

**NO new cron table. NO parallel scheduler.** `automation_engine.py` already wakes on schedule and dispatches actions; we add `website_resync` to its action switch.

**Diff hashing: `kb_section_hashes` (migration 109).**
Existing columns — `client_id uuid`, `section_id text`, `content_sha256 text`, `embedded_at timestamptz`. We reuse by:
- Treating each crawled page's 4 category sections as a `section_id` (e.g., `website:services:homepage`, `website:hours:contact-page`, `website:prices:services-page`, `website:contact:footer`).
- On crawl, compute SHA256 of each scrubbed section → compare with existing `content_sha256` for that `(client_id, section_id)` → if different, it's a diff, route to LLM flagging.
- `embedded_at` doubles as "last seen at this hash" — update whenever we confirm the content is re-processed.

**NO new hash table.** `kb_section_hashes` is already the canonical content-diff primitive.

**Tenant column:** `kb_section_hashes` uses `client_id` (confirmed migration 109 line 75). `widget_configs` uses `tenant_id` (confirmed migration 001 line 33). We follow each table's existing convention — do not rename.

**Email events: `email_events` (migration 022)** with `campaign_tag='self_maint_digest'` for digest tracking.

#### New tables (migration 118)

**`maintenance_suggestions`** — one row per LLM-flagged diff awaiting tenant decision.

```sql
CREATE TABLE maintenance_suggestions (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id          uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    crawl_id           uuid NOT NULL REFERENCES website_crawl_history(id) ON DELETE CASCADE,
    category           text NOT NULL CHECK (category IN ('services','hours','prices','contact')),
    section_id         text NOT NULL,                              -- matches kb_section_hashes.section_id
    source_url         text NOT NULL,                              -- page the diff came from
    before_snippet     text NOT NULL,                              -- scrubbed pre-change excerpt
    after_snippet      text NOT NULL,                              -- scrubbed post-change excerpt
    llm_explanation    text NOT NULL,                              -- Haiku one-liner
    llm_confidence     numeric(3,2) NOT NULL CHECK (llm_confidence BETWEEN 0 AND 1),
    proposed_kb_patch  jsonb NOT NULL DEFAULT '{}'::jsonb,         -- what to apply on approve
    status             text NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending','approved','rejected','edited','expired','superseded')),
    rejected_hash      text,                                       -- locks-out same diff until underlying hash changes
    approved_at        timestamptz,
    approved_by        uuid REFERENCES tenants(id),                -- tenant user UUID
    rejected_at        timestamptz,
    edited_at          timestamptz,
    edited_content     jsonb,                                       -- tenant modifications before approve
    applied_to_kb_at   timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_maint_sugg_client_status
    ON maintenance_suggestions(client_id, status, created_at DESC);

CREATE INDEX idx_maint_sugg_crawl
    ON maintenance_suggestions(crawl_id);

ALTER TABLE maintenance_suggestions ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_full_access ON maintenance_suggestions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
```

**`website_crawl_history`** — one row per crawl attempt (success or failure).

```sql
CREATE TABLE website_crawl_history (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id           uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    automation_rule_id  uuid REFERENCES automation_rules(id) ON DELETE SET NULL,
    automation_execution_id uuid REFERENCES automation_rule_executions(id) ON DELETE SET NULL,
    crawled_at          timestamptz NOT NULL DEFAULT now(),
    started_at          timestamptz NOT NULL,
    completed_at        timestamptz,
    duration_ms         int,
    status              text NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running','success','partial','failed','rate_limited','robots_blocked')),
    attempt             int NOT NULL DEFAULT 1,
    max_attempts        int NOT NULL DEFAULT 3,
    pages_crawled       int NOT NULL DEFAULT 0,
    pages_failed        int NOT NULL DEFAULT 0,
    sections_hashed     int NOT NULL DEFAULT 0,
    sections_diffed     int NOT NULL DEFAULT 0,
    suggestions_created int NOT NULL DEFAULT 0,
    error_message       text,
    robots_txt_snapshot text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_crawl_hist_client_crawled
    ON website_crawl_history(client_id, crawled_at DESC);

CREATE INDEX idx_crawl_hist_status
    ON website_crawl_history(status) WHERE status IN ('failed','rate_limited');

ALTER TABLE website_crawl_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_full_access ON website_crawl_history
    FOR ALL TO service_role USING (true) WITH CHECK (true);
```

#### ALTER existing (migration 118)

**`widget_configs`** — `tenant_id` convention per migration 001.

```sql
ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS self_maintenance_enabled boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS last_crawl_at            timestamptz,
    ADD COLUMN IF NOT EXISTS next_crawl_at            timestamptz,
    ADD COLUMN IF NOT EXISTS self_maintenance_consent_at timestamptz,
    ADD COLUMN IF NOT EXISTS self_maintenance_consent_ip text,
    ADD COLUMN IF NOT EXISTS self_maintenance_consent_tos_version text;

CREATE INDEX IF NOT EXISTS idx_widget_configs_next_crawl
    ON widget_configs(next_crawl_at)
    WHERE self_maintenance_enabled = true;
```

The `next_crawl_at` index is the hot path for `scripts/daily/self_maintenance_crawl.sh` — pulls tenants due for a crawl in < 5 ms.

### 6.2 API Surface

**Dashboard — Suggestions inbox**

```
GET /api/v1/maintenance/suggestions
    ?status=pending|approved|rejected|all
    &category=services|hours|prices|contact|all
    &limit=20 (max 100)

Auth: Bearer JWT (tenant scoped)
Response: { "suggestions": [...], "pending_count": int, "last_crawl_at": ts, "next_crawl_at": ts }
```

```
POST /api/v1/maintenance/suggestions/{id}/approve
Body: { "patch_override"?: {...} }   // optional tenant edits
Auth: Bearer JWT

Effects:
  - suggestions.status = 'approved'
  - Applies proposed_kb_patch (or patch_override) to KB
  - Marks kb_section_hashes row as re-embedded
  - activity_feed.record_event(client_id, 'kb_maintenance_approved', {...})
Response: 200 { "applied": true }
```

```
POST /api/v1/maintenance/suggestions/{id}/reject
Body: { "reason"?: string }
Auth: Bearer JWT

Effects:
  - suggestions.status = 'rejected'
  - suggestions.rejected_hash = kb_section_hashes.content_sha256 (locks out same diff)
Response: 200 { "rejected": true }
```

```
POST /api/v1/maintenance/suggestions/{id}/edit
Body: { "edited_content": {...} }   // tenant-modified patch
Auth: Bearer JWT

Effects:
  - suggestions.status = 'edited'
  - suggestions.edited_content = provided JSON
  - Then auto-approves with edited_content as patch
Response: 200 { "applied": true }
```

**Dashboard — Status card**

```
GET /api/v1/maintenance/status
Auth: Bearer JWT
Response: {
    "enabled": true,
    "last_crawl_at": "2026-04-19T12:02:31Z",
    "next_crawl_at": "2026-04-26T11:00:00Z",
    "pending_count": 3,
    "last_crawl_status": "success"
}
```

**Opt-in (onboarding)**

```
POST /api/v1/maintenance/consent
Body: { "tos_version": "2026-04" }
Auth: Bearer JWT
Effects:
  - widget_configs.self_maintenance_enabled = true
  - widget_configs.self_maintenance_consent_at = now()
  - widget_configs.self_maintenance_consent_ip = request IP
  - widget_configs.self_maintenance_consent_tos_version = tos_version
  - Inserts automation_rules row (trigger_type='scheduled_weekly', action='website_resync')
  - widget_configs.next_crawl_at = next Sunday 7 AM tenant tz
Response: 200 { "enabled": true, "next_crawl_at": ts }
```

### 6.3 UI Layout

**Dashboard status card** (top of dashboard, below ops-automation card):

```
┌───────────────────────────────────────────────────────┐
│  KB Self-Maintenance                                  │
│                                                       │
│  3 suggestions pending  ·  last crawl 2 days ago     │
│  Next crawl: Sun Apr 26, 7:00 AM                      │
│                                                       │
│  [Review suggestions →]                               │
└───────────────────────────────────────────────────────┘
```

**Suggestions page** (`/maintenance` route): Card list, one per pending suggestion.

```
┌──────────────────────────────────────────────────────────┐
│  Hours changed — Saturday                                 │
│  From: "Closed Saturdays"                                 │
│  To:   "Open 9 AM – 5 PM Saturdays"                       │
│  Source: yourdomain.com/contact                           │
│  LLM: "Looks like you added weekend hours."              │
│                                                          │
│  [ Approve ] [ Edit ] [ Reject ]                          │
└──────────────────────────────────────────────────────────┘
```

- **Approve**: applies `proposed_kb_patch`, shows success toast, card disappears.
- **Edit**: opens inline form with before/after side-by-side, tenant modifies after text, save → approves with edits.
- **Reject**: opens single-line reason prompt (optional), records `rejected_hash`, card disappears + won't return until website changes that section again.

**Sunday digest email** (sent 7:30 AM tenant local via existing `email_sender.py` + `email_events` tracking):

```
Subject: 3 things changed on your site this week

Hi {tenant_name},

Your website self-check ran this morning. Here's what I found:

1. [HOURS] Saturday hours added — looks safe to approve.
2. [PRICES] Emergency service fee changed $149 → $189 — please review.
3. [SERVICES] "Gutter cleaning" page removed — want me to stop offering it?

[Review all 3 suggestions →]

Your next scan is Sunday, May 3 at 7 AM.
```

### 6.4 Crawler architecture

- Respects `robots.txt`. Fetches it first, parses `Disallow` rules, honors `Crawl-delay`. Stored in `website_crawl_history.robots_txt_snapshot` for audit.
- User-agent: `AgentNexLiFy-SelfMaintenance/1.0 (+https://agentnexlify.com/bot)`
- Rate limit: 1 request per 2 seconds within a crawl; max 50 pages per crawl.
- Timeout: 30 s per page, 10 min total crawl.
- HTTP 429 → back off, mark `status='rate_limited'`, retry next cron cycle.
- Same-origin only (no following off-site links).
- HTML-only (V1). PDFs + Drive docs → V2.

### 6.5 Category extraction

Crawler tags each page region with one of the 4 categories using heuristics + structured data:
- **Hours** — regex for `Mon|Tue|...|Sun` near time patterns, or JSON-LD `openingHours`.
- **Prices** — currency symbols (`$`, `USD`), or JSON-LD `offers/price`.
- **Services** — headings matching tenant's vertical service list, or JSON-LD `Service`.
- **Contact** — phone/email/address regex in `<footer>`, `<address>`, or JSON-LD `ContactPoint`.

Each category → distinct `section_id` → distinct `kb_section_hashes` row.

---

## 7. Technical Implementation — File by File

### New files

**`backend/services/self_maintenance_service.py`** (new — primary service)
```python
async def run_crawl(client_id: str, automation_execution_id: str | None) -> dict
async def detect_category_diffs(client_id: str, crawl_id: str) -> list[dict]
async def generate_suggestions(client_id: str, crawl_id: str, diffs: list[dict]) -> list[str]
async def approve_suggestion(suggestion_id: str, patch_override: dict | None) -> None
async def reject_suggestion(suggestion_id: str, reason: str | None) -> None
async def edit_suggestion(suggestion_id: str, edited_content: dict) -> None
async def schedule_next_crawl(client_id: str, tz: str) -> datetime
```
- `run_crawl`: HTTP fetch pages, scrub PII, extract 4 category sections, hash each, compare to `kb_section_hashes`, write `website_crawl_history` row, return diff summary.
- `detect_category_diffs`: joins crawl output with `kb_section_hashes` by `(client_id, section_id)` where `content_sha256` differs, excludes sections where existing `maintenance_suggestions.rejected_hash` matches the new hash (sticky-reject).
- `generate_suggestions`: Haiku call per diff (batched up to 10 per request) with before/after snippets → explanation + proposed_kb_patch JSON, writes `maintenance_suggestions` rows, increments `website_crawl_history.suggestions_created`.
- `approve_suggestion`: applies `proposed_kb_patch` via existing KB patch utility (`backend/services/kb_patcher.py` — to be created as small helper; search first for existing KB editor logic before adding), updates `kb_section_hashes.content_sha256` + `embedded_at`, marks suggestion `approved`, logs to `activity_feed_service.record_event` (from ops-automation PRD).
- `schedule_next_crawl`: computes next Sunday 7 AM in tenant's tz, writes `widget_configs.next_crawl_at`.

**`backend/services/pii_scrubber.py`** (new — chokepoint)
```python
def scrub_html(raw_html: str) -> str
def scrub_text(text: str) -> str
```
- Regex-based masking: phone `(\+?1?[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}` → `[PHONE]`
- Emails: RFC-lite pattern → `[EMAIL]`
- Full names: NER only if spaCy available; else fall back to regex of `\b[A-Z][a-z]+ [A-Z][a-z]+\b` → `[NAME]` (aggressive; tolerable because context is tenant website, not PII-sensitive — we're stripping OTHER people's PII that may have made it onto the tenant's site like testimonial names).
- Addresses: street + city + state regex → `[ADDRESS]`.
- Tenant's own business phone/email/address/name are allow-listed via `widget_configs` and `tenants` rows before scrubbing — we want to *see* those to compare across crawls, just not third-party PII.

Single-file chokepoint so compliance can audit PII handling by reading one file.

**`backend/routers/maintenance_suggestions.py`** (new)
```python
@router.get("/suggestions") -> list[SuggestionResponse]
@router.post("/suggestions/{id}/approve")
@router.post("/suggestions/{id}/reject")
@router.post("/suggestions/{id}/edit")
@router.get("/status") -> MaintenanceStatusResponse
@router.post("/consent")
```
All routes `verify_tenant(claims, client_id)`. Register in `backend/main.py` (lines 746–813 per CLAUDE.md).

**`backend/services/website_crawler.py`** (new)
```python
async def fetch_robots_txt(domain: str) -> str
async def parse_robots_rules(robots_txt: str, user_agent: str) -> RobotsRules
async def crawl_page(url: str, rules: RobotsRules) -> CrawlResult
async def crawl_site(root_url: str, max_pages: int = 50) -> list[CrawlResult]
async def extract_categories(page: CrawlResult) -> dict[str, str]   # 4 categories
```
Uses `httpx.AsyncClient`. Timeout 30s/page, 10 min/crawl. Respects `robots.txt`. 2s delay between requests.

**`backend/services/automation_engine.py`** (MODIFY — add `website_resync` action handler)
Current engine handles `scheduled_daily` + `scheduled_weekly` with configured actions. Add switch case for `action.type == 'website_resync'`:
```python
elif action_type == 'website_resync':
    await self_maintenance_service.run_crawl(
        client_id=rule.tenant_id,
        automation_execution_id=execution.id
    )
```
Execution logs already land in `automation_rule_executions` — free retry telemetry, error_message, execution_time_ms. If run_crawl raises, engine's existing retry logic (attempt count in execution row) drives re-attempts up to `max_attempts=3`.

**`backend/services/digest_emailer.py`** (new — or add method to existing `email_sender.py`)
```python
async def send_self_maintenance_digest(client_id: str) -> None
```
Runs Sunday 7:30 AM tenant tz (30 min after crawl). Queries `maintenance_suggestions WHERE client_id=$1 AND status='pending' AND created_at > NOW() - interval '7 days'`. Renders email via existing template system (`email_templates` table, migration 014). Sends via Resend with `campaign_tag='self_maint_digest'` for `email_events` tracking.

**`frontend/src/pages/SuggestionsPage.jsx`** (new)
Full-page list of suggestion cards. Filter chips (All / Hours / Services / Prices / Contact). Card component reused from dashboard. Empty state: "All caught up — next crawl Sunday 7 AM."

**`frontend/src/components/MaintenanceStatusCard.jsx`** (new — dashboard widget)
Pending count, last_crawl_at (relative), next_crawl_at (absolute), "Review suggestions" CTA. Rendered only if `self_maintenance_enabled`.

**`frontend/src/utils/api/maintenance.js`** (new API client)
```js
export const getSuggestions = (params) => ...
export const approveSuggestion = (id, patch) => ...
export const rejectSuggestion = (id, reason) => ...
export const editSuggestion = (id, edited) => ...
export const getStatus = () => ...
export const optIn = (tosVersion) => ...
```

**`scripts/daily/self_maintenance_crawl.sh`** (new cron script)
```bash
#!/usr/bin/env bash
# Runs nightly 2 AM UTC. Finds tenants with next_crawl_at <= now()
# AND self_maintenance_enabled=true, enqueues via automation_engine.
# Idempotent — automation_engine dedupes by (rule_id, execution_window).
python -m backend.scripts.enqueue_due_self_maintenance_crawls
```
Hooked into existing cron harness (see `scripts/daily/kb-autopopulate.sh` pattern). Logs to `scripts/logs/self_maintenance.log`.

Note: The primary scheduler is `automation_engine` via `automation_rules` rows. This cron script is a **safety net** that wakes tenants whose `next_crawl_at` drifted (e.g., engine down during their window). It checks `widget_configs.next_crawl_at <= NOW()` and manually enqueues an `automation_rule_executions` row for the website_resync rule. 99% of the time it finds nothing to do.

**`migrations/118_self_maintenance.sql`** (new)
- CREATE `maintenance_suggestions` + indexes + RLS
- CREATE `website_crawl_history` + indexes + RLS
- ALTER `widget_configs` ADD the 6 columns above

**`config/self_maintenance.yaml`** (new — shared constants)
```yaml
crawl:
  max_pages: 50
  request_delay_seconds: 2
  page_timeout_seconds: 30
  total_timeout_seconds: 600
  user_agent: "AgentNexLiFy-SelfMaintenance/1.0 (+https://agentnexlify.com/bot)"
llm:
  model: claude-haiku-4-5-20251001
  max_diffs_per_batch: 10
  max_output_tokens_per_diff: 200
digest:
  send_delay_minutes_after_crawl: 30
  campaign_tag: self_maint_digest
```

### Tests

**`backend/tests/test_self_maintenance_service.py`** — 80%+ coverage
- `test_run_crawl_writes_history_row`
- `test_run_crawl_respects_robots_txt_disallow`
- `test_run_crawl_retries_on_429`
- `test_detect_diffs_skips_sticky_rejected_hash`
- `test_generate_suggestions_batches_haiku_calls`
- `test_approve_suggestion_updates_kb_and_hash`
- `test_reject_suggestion_sets_rejected_hash`
- `test_edit_suggestion_applies_tenant_override`
- `test_schedule_next_crawl_sunday_7am_tenant_tz`

**`backend/tests/test_pii_scrubber.py`** — 100% coverage (compliance)
- Phone, email, name, address mask cases
- Tenant-own-PII allow-list preservation

**`backend/tests/test_maintenance_suggestions_router.py`** — 100% on auth
- Unauthorized returns 401
- Tenant A cannot approve Tenant B's suggestion
- Approve happy path
- Reject → rejected_hash set

**`backend/tests/test_website_crawler.py`**
- Robots.txt parse
- Per-page timeout
- Same-origin enforcement
- Rate-limit honored

**E2E (Playwright)**
- Seed tenant with fake website page → run crawl → seed new content → run crawl → assert suggestion card appears → click Approve → assert KB updated.

---

## 8. Edge Cases + Failure Modes

| Scenario | Behavior |
|----------|----------|
| Website fully offline during crawl | `status='failed'`, error stored, `automation_rule_executions.status='failed'`, retry next cron cycle (up to `max_attempts=3`). No suggestion created. |
| Website changed drastically (rewrite) | Likely floods 20+ diffs. Cap at 10 suggestions per crawl; store overflow with status='expired' immediately + dashboard banner "Major website change detected — review manually." |
| `robots.txt` disallows everything | `status='robots_blocked'`, no crawl, one-time email to tenant: "We can't crawl your site because robots.txt blocks our bot. Add this line: `User-agent: AgentNexLiFy-SelfMaintenance Allow: /`". `widget_configs.self_maintenance_enabled` stays true (don't silently disable). |
| LLM hallucinates change | `llm_confidence < 0.5` → suggestion auto-marked `status='expired'`, never shown to tenant. Confidence threshold tunable in `config/self_maintenance.yaml`. |
| Tenant didn't opt in | `widget_configs.self_maintenance_enabled=false` → crawl never scheduled. Onboarding flow must hit `POST /api/v1/maintenance/consent` before first crawl. |
| Tenant rate-limit hit (website 429) | `status='rate_limited'`, increment attempt, retry with exponential backoff (5m, 30m, 2h). After 3 failures, email tenant: "We're hitting rate limits. Reach out to your webmaster." |
| Multiple diffs in same section (price changed twice) | Latest wins. `detect_category_diffs` always compares new hash vs. current DB hash — intermediate states not tracked V1. |
| Tenant approves suggestion then website reverts | Next crawl detects new diff, new suggestion fires normally. Approve history preserved in `maintenance_suggestions` (approved rows kept for audit). |
| Tenant rejects, same diff remains on next crawl | `rejected_hash` match → skip suggestion creation. When website content hashes DIFFERENTLY (even if meaning is same to a human), rejected_hash mismatches → new suggestion. Acceptable noise level for V1. |
| Diff is PII-related (phone changed) | PII scrubber masks third-party PII but preserves tenant-own phone. Phone change in tenant's footer → legitimate diff → normal suggestion. |
| LLM API timeout | Per-diff request retries once, then skip with `status='expired'`. Crawl result `status='partial'`. |
| Tenant on AI Receptionist tier | Plan gate at `POST /api/v1/maintenance/consent` and at crawl enqueue time. Returns 403 "Self-maintenance requires Full Office tier." |
| Tenant downgrades Full Office → AI Receptionist mid-cycle | Pending crawls stop (plan gate in engine). `self_maintenance_enabled` stays true (preserves opt-in record). Dashboard banner: "Self-maintenance paused — requires Full Office tier." On upgrade, resumes next Sunday. |
| Crawl window drifts (engine was down Sunday 7 AM) | Safety-net cron `scripts/daily/self_maintenance_crawl.sh` picks up stale `next_crawl_at` ≤ NOW() and enqueues within 24 h. |
| Suggestion older than 14 days, still pending | Cron marks `status='expired'` (stale UI cards rot trust). Surfaced on digest email as "1 suggestion expired — website may have changed again." |
| Tenant approves an edit where `edited_content` is malformed | Validation at `POST /edit`: JSON schema check, 400 on fail. No partial apply. |

---

## 9. Security + Compliance

**Opt-in (hard gate):**
- No crawl fires without `widget_configs.self_maintenance_consent_at IS NOT NULL`.
- Consent captured during onboarding V2 (see `specs/onboarding-v2_spec.md`) — checkbox: "Allow AgentNexLiFy to re-crawl my website weekly to keep my chatbot current."
- Stored with IP, ToS version, timestamp.

**ToS + robots.txt:**
- Tenant's own site being crawled by OUR service on THEIR behalf — ToS update required ("You authorize us to crawl your public website on a weekly schedule to keep your AI assistant current. You may revoke at any time by disabling self-maintenance.").
- Crawler respects `robots.txt`. Fetched + stored every crawl.
- `User-agent` identifies our bot + links to our bot info page.

**PII scrubbing (hard gate):**
- `pii_scrubber.scrub_html(raw_html)` called BEFORE any crawled content reaches the LLM. No bypass. Chokepoint verified by unit tests.
- Tenant-own PII preserved (we need to compare tenant's own phone/address across crawls).
- Third-party PII (testimonial names, customer phones in "Thanks Jane Smith 555-1234" quotes) stripped.

**Tenant isolation:**
- Every query scoped by `client_id` (or `tenant_id` for `widget_configs`).
- RLS on both new tables (service_role bypass only).
- Cross-tenant test in `test_maintenance_suggestions_router.py`.

**Plan gate:**
- `tenant.plan = 'full_office'` (or equivalent Full Office identifier — verify against `tenants` schema before implementation) required at consent-time AND at crawl enqueue time.
- AI Receptionist tier: 403 at consent endpoint. Never enqueued.
- Marketing + AI Receptionist tier (V2): feature-flagged, default off.

**Rate limits:**
- 1 crawl per tenant per week max (enforced by `automation_rules.last_triggered_at` + 6.5-day guard).
- Per-crawl: max 50 pages, 2s inter-request delay, 30s/page timeout, 10min total.

**Claude cost cap:**
- Haiku only (cheap). Max 10 diffs per crawl × 200 output tokens × $1/MTok = ~$0.002 per crawl. At 500 tenants × weekly = $4/mo LLM spend. Full Office tier ARPU covers this with 4+ orders of magnitude margin.
- Soft alert at $50/mo total LLM spend on self-maintenance.

**Audit log:**
- `automation_rule_executions` logs every crawl execution.
- `website_crawl_history` logs every attempt.
- `maintenance_suggestions` preserves approve/reject/edit history (never hard-deleted).

**Secrets:** No OAuth tokens stored for V1 (HTTP-only crawl of public site). V2 GCal sync will use existing `integrations` table (migration 007).

---

## 10. Testing Strategy

### Backend unit (80%+ new services; 100% PII scrubber + auth routes)
- `test_self_maintenance_service.py` — 9 cases listed §7
- `test_pii_scrubber.py` — full cartesian of mask cases + allow-list
- `test_maintenance_suggestions_router.py` — auth matrix, happy paths, edit validation
- `test_website_crawler.py` — robots, timeouts, rate-limit, same-origin
- `test_automation_engine_website_resync.py` — engine dispatches `website_resync` action, retries on failure, logs to `automation_rule_executions`

### Integration
- `test_self_maintenance_e2e_flow.py` (pytest + seeded local server): tenant opts in → crawl runs → diff detected → suggestion created → approve → KB + hash updated.

### E2E (Playwright)
- `self_maintenance.spec.ts`: Login, navigate to /maintenance, see card, click Approve, verify card disappears + success toast.

### Load
- 500 concurrent tenant crawls Sunday 7 AM (worst case) → engine backpressure tested in staging before Full Office rollout.

### Chaos
- Kill crawler mid-page → `status='running'` stale row reaped by janitor (`UPDATE WHERE status='running' AND started_at < NOW() - interval '1 hour' SET status='failed'`).
- LLM 500 → per-diff retry once → skip.
- Website returns different HTML each request (non-deterministic SSR) → hash-noise test: assert diff count below threshold by computing hashes of stable zones only. V1 acceptable noise tolerance: ≤3 false diffs per crawl.

---

## 11. Rollout Plan

**Feature flag:** `SELF_MAINTENANCE_V1_ENABLED` (env var global killswitch). Per-tenant via `widget_configs.self_maintenance_enabled`.

**Sequence:**
1. **Week 1** — Internal tenant (Aidan's own test tenant). Verify opt-in → crawl → suggestions → approve end-to-end. Fix anything.
2. **Week 2** — 3 Full Office paid testers. Monitor `website_crawl_history` + Sentry daily. Target: ≥1 approved suggestion per tester in week 1.
3. **Week 3** — All Full Office tenants. Watch freshness metric + digest open rate.
4. **AI Receptionist tier** — blocked permanently at plan gate. Dashboard banner explains upgrade path.
5. **Marketing + AI Receptionist tier** — V2, pending cost validation.

**Comms:** Sunday digest email is the primary comm. No marketing email blast V1. Dashboard banner on first opt-in: "Self-maintenance active — your first crawl runs this Sunday 7 AM."

**Revert plan:** `SELF_MAINTENANCE_V1_ENABLED=false` disables engine action. `automation_rules` rows stay in place; engine skips `website_resync` action until re-enabled. No data migration needed on revert.

---

## 12. Timeline Estimate

| Week | Work | Owner |
|------|------|-------|
| 1 | Migration 118, `pii_scrubber`, `website_crawler` (stub), `self_maintenance_service` (crawl+diff), tests. | Backend-dev |
| 1-2 | Extend `automation_engine` to dispatch `website_resync`. `schedule_next_crawl` logic. Tests. | Backend-dev |
| 2 | Haiku-backed `generate_suggestions`. `maintenance_suggestions` router (all 6 endpoints). Register in `main.py`. 100%-coverage auth tests. | Backend-dev |
| 2-3 | Digest emailer (reuse `email_sender` + `email_templates`). `scripts/daily/self_maintenance_crawl.sh` safety-net cron. | Backend-dev |
| 3 | `SuggestionsPage.jsx`, `MaintenanceStatusCard.jsx`, `maintenance.js` API client, consent flow in onboarding. | Frontend-dev |
| 3-4 | E2E Playwright, internal tenant dogfood, Sentry alerts configured, staging load test (500 concurrent). | QA |
| 4 | Roll to 3 paid Full Office testers. | — |
| 5 | Roll to all Full Office. | — |

**Total V1: 4-5 weeks.** Backend-heavy weeks 1-3. Frontend in parallel from week 3. No blocking external dependencies — all infra (Haiku, Resend, Supabase) is already wired.

---

## 13. V2 Scope (deferred — document only, do not detail)

- **GCal sync**: Tenant changes business hours in Google Calendar → KB auto-updates (via existing `integrations` table migration 007).
- **Stripe new-product event**: New SKU in Stripe → KB pricing page auto-gets suggestion (via Stripe webhook + `tenant_integrations` or `integrations`).
- **Lead-qualifier feedback loop**: If qualifier keeps saying "uncertain" on a vertical → flag KB section as low-confidence → crawl-time prioritization for that section.
- **FAQ staleness detector**: FAQs not referenced in chat in 60 days → flag as possibly stale → suggestion "Archive unused FAQ?".
- **Auto-FAQ generation**: 3+ similar questions asked in a month without a matching FAQ → suggestion "Create new FAQ?".
- **PDF + Drive doc crawling** (via `tenant_integrations` migration 109 — Drive already wired).
- **Multi-site per tenant** (tenant.com + tenant.shop).
- **Per-plan cadence** (daily for Marketing + AI Receptionist; weekly for Full Office).
- **Sub-page attribution** (click-through from suggestion card to exact page region).

---

## 14. Open Questions

None blocking implementation. Decisions locked above.

Post-rollout monitoring questions (not V1 blockers):
1. Does the Haiku "one-line explanation" land well? Measure: approve rate stratified by LLM confidence bucket. If low-confidence approves are common, raise threshold.
2. Is 50 pages / 10 min / 2s-delay the right crawl-shape for a typical SMB site? Measure: `website_crawl_history.pages_crawled` distribution. Tune in month 2.
3. Should the rejected_hash match be exact or fuzzy? V1 exact. If tenants complain about near-duplicate re-suggestions, add fuzzy match (embedding cosine > 0.95) in V2.
4. Is Sunday 7 AM the right window? A/B Saturday vs Sunday in month 3 if digest open rate < 60%.

---

## 15. Constraints Summary

- **Scheduling**: `automation_rules` (migration 087) with `trigger_type='scheduled_weekly'` + new action `website_resync`. NO parallel cron table.
- **Diff hashing**: `kb_section_hashes` (migration 109). NO parallel hash table.
- **Tenant column**: `widget_configs.tenant_id` (migration 001 line 33). `kb_section_hashes.client_id` (migration 109). `automation_rules.tenant_id` (migration 087). Follow each table's existing column name — do NOT rename.
- **New tables use `client_id`** (both `maintenance_suggestions` and `website_crawl_history`) — matches recent migration pattern (108, 109, 110).
- **Migration number**: **118**. (111-113 marketing per `audits/existing-infra-reference-2026-04-21.md` line 328; 114 ops-auto; 115-117 onboarding; 118 self-maintenance.)
- **No `from __future__ import annotations`** in any FastAPI file (Pydantic break).
- **Plan gate**: Full Office tier ONLY in V1. AI Receptionist tier permanently excluded (LLM cost model). Marketing + AI Receptionist tier V2.
- **PII scrubber chokepoint**: `pii_scrubber.scrub_html` called before every LLM send. No bypass.
- **Model routing**: Haiku only for diff explanation. No Opus, no Sonnet. Per-crawl cost ≤ $0.002.
- **Crawl rate limit**: 1/tenant/week hard cap V1.
- **Robots.txt**: honored. Snapshot stored in `website_crawl_history.robots_txt_snapshot`.
- **Test bar**: 80% new services; 100% `pii_scrubber` + auth routes. E2E Playwright happy path.
- **Widget JS byte-identical** rule N/A (no widget changes in V1).

---

## Schema Verification

- [x] Scheduling uses existing `automation_rules` table (migration 087) with `trigger_type='scheduled_weekly'` + new action `website_resync`. NOT a new cron table.
- [x] Scheduling execution logging rides existing `automation_rule_executions` (migration 087). NOT a new execution log.
- [x] Diff hashing uses existing `kb_section_hashes` table (migration 109). NOT a new hash table.
- [x] Email digest rides existing `email_events` (migration 022) via `campaign_tag='self_maint_digest'`. NOT a new email tracking table.
- [x] Email digest templates reuse existing `email_templates` (migration 014). NOT new template storage.
- [x] Migration number is **118** — next available after 110 + ops-auto 114 + onboarding 115-117 (per `audits/existing-infra-reference-2026-04-21.md` line 328).
- [x] `widget_configs` ALTER uses `tenant_id` convention (migration 001 line 33 confirmed).
- [x] New tables (`maintenance_suggestions`, `website_crawl_history`) use `client_id` — matches recent migration pattern (108, 109, 110).
- [x] V2 GCal sync will reuse existing `integrations` table (migration 007), NOT a new OAuth table.
- [x] Activity logging reuses `activity_feed_service.record_event` from `specs/ops-automation-surfacing_spec.md`. NOT a new event log.
- [x] PII scrubber is a new single-file chokepoint (genuinely novel — no existing PII infra) — justified creation.
- [x] Claude model selection: Haiku (`claude-haiku-4-5-20251001`) — mechanical classification, matches `rules/model-routing.md`. Opus/Sonnet not invoked.
