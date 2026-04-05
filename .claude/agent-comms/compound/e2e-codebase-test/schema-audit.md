# Schema Consistency Audit

**Agent:** schema-guardian
**Date:** 2026-04-05
**Status:** WARNING (4 issues found, 0 critical)

---

## Check 1: Migration Numbering

**Status:** WARNING

**Total migration files:** 88 files spanning 001 through 082.

**Duplicate numbers found:**

| Number | Files | Documented in schema-log? |
|--------|-------|---------------------------|
| 005 | `005_appointments.sql`, `005_automation_sequences.sql` | Yes (historical) |
| 007 | `007_google_calendar_integration.sql`, `007_team_members.sql`, `007_webhooks.sql` | Yes (historical) |
| 066 | `066_appointment_waitlist.sql`, `066_waitlist.sql` | Yes (flagged as duplicate, pending dedup) |
| 067 | `067_lead_scoring_config.sql`, `067_scoring_configs.sql` | Yes (flagged as duplicate, pending dedup) |
| 068 | `068_invoice_number_unique.sql`, `068_password_reset_tokens.sql` | Yes (flagged as must-renumber) |

**Gaps:** No numbering gaps detected in the 001-082 range.

**Findings:**
- 005 and 007 duplicates are historical and documented. No action needed.
- 066 and 067 each have two files that likely define the same table with different filenames. Schema-log flags these for dedup before applying. Still pending.
- 068 has two completely different migrations (invoice unique index vs. password reset tokens) sharing the same number. One must be renumbered before applying.

---

## Check 2: client_id vs tenant_id in leads table

**Status:** PASS

Scanned all `backend/` files for `.table("leads").*.eq("tenant_id"` -- **zero matches found**. All leads queries correctly use `client_id`.

**Verified correct usage in these files (sample):**

| File | Line | Pattern |
|------|------|---------|
| `backend/routers/leads.py` | 51 | `.eq("client_id", tenant_id)` |
| `backend/routers/leads.py` | 101 | `.eq("client_id", tenant_id)` |
| `backend/routers/leads.py` | 167 | `"client_id": tenant_id` (insert) |
| `backend/routers/leads.py` | 218 | `.eq("client_id", tenant_id)` |
| `backend/routers/leads.py` | 256 | `.eq("client_id", tenant_id)` |
| `backend/routers/leads.py` | 463-464 | `.eq("client_id", tenant_id)` (merge) |
| `backend/routers/analytics.py` | 266 | `.eq("client_id", tenant_id)` |
| `backend/routers/analytics.py` | 919, 931, 1058, 1121, 1916 | `.eq("client_id", tenant_id)` |
| `backend/routers/pipeline.py` | 294, 359 | `.eq("client_id", tenant_id)` |
| `backend/routers/marketing_campaigns.py` | 84 | `.eq("client_id", tenant_id)` |
| `backend/routers/smart_lists.py` | 139, 141 | `.eq("client_id", tenant_id)` |
| `backend/routers/forms.py` | 368 | `.eq("client_id", tenant_id)` |
| `backend/routers/documents.py` | 206 | `.eq("client_id", tenant_id)` |
| `backend/routers/reviews.py` | 399 | `.eq("client_id", tenant_id)` |
| `backend/routers/invoices.py` | 1146 | `.eq("client_id", tenant_id)` |
| `backend/services/lead_scoring.py` | 268 | `.eq("client_id", tenant_id)` |
| `backend/services/automation_engine.py` | 2313 | `.eq("client_id", tid)` |
| `backend/mcp_server.py` | 268 | `.eq("client_id", tenant["id"])` |

All 22+ unique query sites use `client_id` correctly.

---

## Check 3: conversations table (client_id vs tenant_id)

**Status:** WARNING (misleading comment, but no code bug)

Scanned all `backend/` files for `.table("conversations").*.eq("tenant_id"` -- **zero matches found**. All conversations queries correctly use `client_id`.

**Verified correct usage:**

| File | Line | Pattern |
|------|------|---------|
| `backend/routers/widget_helpers.py` | 282-284 | `.eq("client_id", tenant_id)` (lookup) |
| `backend/routers/widget_helpers.py` | 298 | `{"client_id": tenant_id, ...}` (upsert) |
| `backend/routers/widget_helpers.py` | 982-984 | `.eq("client_id", tenant_id)` (tag update) |
| `backend/routers/widget_chat.py` | 649 | `.eq("client_id", tenant["id"])` |
| `backend/routers/auth.py` | 1248 | `.eq("client_id", tenant_id)` |
| `backend/routers/auth.py` | 1339 | `.eq("client_id", tenant_id)` |
| `backend/routers/auth.py` | 1348 | `{"client_id": tenant_id, ...}` (insert) |
| `backend/routers/conversation_inbox.py` | 42, 53 | `.eq("client_id", tenant_id)` |
| `backend/routers/conversation_inbox.py` | 406 | `.eq("client_id", tenant_id)` |
| `backend/routers/sms.py` | 102 | `.eq("client_id", tenant_id)` (lookup) |
| `backend/routers/sms.py` | 120 | `{"client_id": tenant_id, ...}` (insert) |
| `backend/services/channel_manager.py` | 120 | `.eq("client_id", tenant_id)` |
| `backend/services/channel_manager.py` | 129 | `{"client_id": tenant_id, ...}` (insert) |
| `backend/routers/analytics.py` | 748 | `.eq("client_id", tenant_id)` |
| `backend/routers/analytics.py` | 1301 | `.eq("client_id", tenant_id)` |
| `backend/mcp_server.py` | 272 | `.eq("client_id", tenant["id"])` |
| `backend/services/automation_engine.py` | 2324 | `.eq("client_id", tid)` |

**Misleading comment (non-critical):**
- `backend/routers/sms.py:184` — Comment says `"conversations table uses tenant_id"` but the function it calls (`_get_or_create_sms_conversation`) correctly uses `client_id` at line 102 and 120. The comment is wrong; the code is correct.

---

## Check 4: Pydantic Model Alignment (leads)

**Status:** PASS

**LeadCreateRequest** (`backend/routers/leads.py:141-149`):
- Fields: `name`, `email`, `phone`, `status`, `lead_temperature`, `areas_of_interest`, `deal_value`, `expected_close_date`
- Insert at line 166-175 maps to: `client_id`, `name`, `email`, `phone`, `status`, `lead_temperature`, `areas_of_interest`, `source`
- All fields exist in live schema per migration history. PASS.

**LeadUpdateRequest** (`backend/models/schemas.py:429-451`):
- Fields: `name`, `email`, `phone`, `status`, `conversation_summary`, `lead_type`, `areas_of_interest`, `timeline`, `budget`, `next_steps`, `tags`, `insurance_carrier`, `insurance_member_id`, `insurance_group`, `date_of_birth`
- `status` validated against `VALID_LEAD_STAGES = {"new", "contacted", "appointment_booked", "closed", "lost"}` at line 446-451. PASS.
- `insurance_carrier`, `insurance_member_id`, `insurance_group` added in migration 062. PASS.
- `date_of_birth` added in migration 064. PASS.
- `timeline` and `budget` are NOT columns in the leads table per any migration file. These would cause silent failures if passed (Supabase ignores unknown columns in updates). **Minor concern** but functionally low risk since update strips `None` values and these are optional fields.

**Query column alignment** (`backend/routers/leads.py:47-49`):
- Selected columns: `id, client_id, name, email, phone, status, lead_score, lead_temperature, areas_of_interest, tags, assigned_to, deal_value, created_at, updated_at`
- All match known schema columns from migrations. PASS.

**lead_stage references:**
- `backend/routers/sequences.py:84` — `"trigger_event": "lead_stage_change"` — This is an automation trigger event name (stored in `automation_sequences.trigger_event`), NOT a column name. PASS.
- `backend/routers/sequences.py:548-571` — Function named `update_lead_stage` but correctly queries `status` column and uses `client_id`. PASS.
- `backend/services/automation_engine.py:21,51` — `VALID_TRIGGER_EVENTS` includes `"lead_stage_change"` — trigger event name, not a column. PASS.

---

## Check 5: Schema-Log Freshness

**Status:** WARNING

**Migration files on disk:** 88 files (001 through 082, with duplicates at 005, 007, 066, 067, 068)

**Migrations documented in schema-log:** 001 through 082 (all documented, including duplicates and their notes)

**Schema-log is up to date** with respect to migration file coverage. All 88 files are documented.

**However, the schema-log still shows several migrations as "Pending":**
- 065 (client_accounts) — "Pending — must be run on live Supabase manually"
- 066 (waitlist entries) — "Pending — created 2026-03-23"
- 067 (scoring configs) — "Pending — created 2026-03-23"
- 068 (both) — "Pending — created 2026-03-25"
- 069 (lead email bounced) — "Pending — created 2026-03-25"
- 070 (pipeline automations) — "Pending — created 2026-03-25"
- 077 (widget knowledge base) — "Pending — created 2026-04-01"
- 078 (expand business_type) — "Pending — created 2026-04-01, CRITICAL"
- 079 (wizard events) — "Pending — created 2026-04-01"

These pending migrations may or may not have been applied since the log was written. The schema-log needs verification against live Supabase for accurate status.

**Plan name discrepancy:**
CLAUDE.md lists `autopilot` ($299) as a valid plan name, but no migration ever adds `autopilot` to the `tenants_plan_check` constraint. Migration 013 restricts plans to `free, growth, professional, enterprise` only. If `autopilot` is a real plan, a migration is needed to update the CHECK constraint. More likely, CLAUDE.md is inaccurate and `autopilot` refers to the feature flag (`autopilot_enabled` added in migration 046), not a plan tier.

---

## Summary

| Check | Status | Issues |
|-------|--------|--------|
| 1. Migration numbering | WARNING | 5 duplicate number pairs (005, 007 historical; 066, 067, 068 need resolution) |
| 2. client_id in leads | PASS | 0 misuses found across 22+ query sites |
| 3. client_id in conversations | WARNING | 0 code bugs; 1 misleading comment in sms.py:184 |
| 4. Pydantic model alignment | PASS | Models match schema; 2 minor ghost fields (timeline, budget) in LeadUpdateRequest |
| 5. Schema-log freshness | WARNING | Log is complete but 9 migrations still marked "Pending" with no verified apply status |

**Total issues:** 4 (0 critical, 0 code bugs, 3 warnings, 1 documentation issue)

**Critical finding: NONE.** The two historically most dangerous mismatch patterns (leads.tenant_id and leads.lead_stage) are fully remediated across the entire codebase.

### Recommendations

1. **Resolve migration 066/067/068 duplicates** before next apply batch. Renumber the second file in each pair (e.g., 068_password_reset_tokens.sql -> 083_password_reset_tokens.sql).
2. **Fix misleading comment** at `backend/routers/sms.py:184` — change "conversations table uses tenant_id" to "conversations table uses client_id".
3. **Verify pending migrations** (065-070, 077-079) against live Supabase and update schema-log apply status.
4. **Clarify CLAUDE.md plan names** — remove `autopilot` from the plan list or add a migration to update the CHECK constraint. The `autopilot_enabled` feature flag is separate from plan tiers.
5. **Consider removing ghost fields** `timeline` and `budget` from `LeadUpdateRequest` (schemas.py:437-438) since no corresponding DB columns exist, or create a migration to add them.
