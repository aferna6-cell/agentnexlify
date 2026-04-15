# Spec — Replace regex lead parser with structured_extractor managed agent

**Status:** Draft · 2026-04-11
**Owner:** Aidan
**Related:** `backend/routers/widget_helpers.py::_extract_lead_info`, managed agent `structured_extractor`
**Priority:** P1 (accuracy > cost on 704 msgs/mo top-tenant signal)

## Problem

`backend/routers/widget_helpers.py::_extract_lead_info` is a regex parser (~25 lines) that extracts `{name, email, phone}` from a user chat message. It runs on every widget message.

**Known failure modes** (from `docs/dev-knowledge/bug-patterns.md`):

1. **Name false negatives** — "I'm John from XYZ" parses but "It's John Smith here" doesn't. `NAME_RE` is narrow.
2. **Name false positives** — "My car is a Honda Civic" matches the standalone-name regex → lead created with name="Honda Civic".
3. **Phone number fragments** — "call me at 555 or 6 PM" captures "555" as phone.
4. **Email with spaces** — `sara @ gmail.com` is handled but `sara @ gmail . com` is not.
5. **No interest / timeline / budget capture.** These fields exist on the `leads` table (`areas_of_interest`, `timeline`, `budget`) but the regex doesn't populate them — they come in via later AI-driven fields or stay null.

MTOptions accounts for 704/month of widget messages. ~8% of those created leads with missing or malformed data per the 2026-04-08 tenant-chatbot-audit.

We already have `backend/services/structured_extractor.py` — a managed agent built on Haiku with a fence-tolerant JSON parser. It supports schema `'lead'` out of the box and was live-smoked on 2026-04-10.

## Goal

Swap the regex-based `_extract_lead_info` for a call to `extract_structured(tenant_id, raw_text, target_schema="lead")`, behind a per-tenant feature flag, with cost/latency guardrails.

## Non-goals

- Replacing the AI-driven lead categorizer (that's a separate background task).
- Removing `_extract_lead_info` entirely — keep it as a fast-path fallback for tenants without the flag.
- Adding new fields to the `leads` table (migration out of scope).

## Architecture

### Option A — Every message (rejected)

Call `extract_structured` on every user message. **Rejected**: 704 msgs × $0.002/call = $1.40/tenant/month — acceptable cost, but ~400ms added latency per message is not. User-visible regression for 90% of messages that don't contain contact info.

### Option B — Triggered on regex miss (REJECTED — ordering problem)

Run regex first. If regex returns empty dict AND the message looks like it might contain contact info (length > 20, has digits or `@` or matches `my (name|number)`), call managed agent. **Rejected**: the "looks like contact info" heuristic is the exact class of bug we're trying to replace.

### Option C — Structured as background enrichment (RECOMMENDED)

1. Keep `_extract_lead_info` regex as-is for the fast-path on every message (shows instant "captured" state in UI).
2. After the response is sent, fire a background task that calls `extract_structured` for the same message.
3. If the managed agent returns MORE or CONFLICTING data than the regex, merge/update the `leads` row.
4. Gate on a new `widget_configs.enable_structured_lead_parser` boolean (default false).
5. Respect existing widget chat rate limits (60/min).

This keeps happy-path latency unchanged (regex is synchronous, managed agent is async), gets the accuracy benefit over time, and bounds cost to opt-in tenants.

## Schema

### New flag: `widget_configs.enable_structured_lead_parser` ✅ SHIPPED migration 103

```sql
-- Migration 103 — applied 2026-04-15 (102 was taken by marketing_addon)
ALTER TABLE widget_configs
    ADD COLUMN IF NOT EXISTS enable_structured_lead_parser boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN widget_configs.enable_structured_lead_parser IS
'When true, widget chat runs the structured_extractor managed agent as a background enrichment pass on each user message to fill in name/email/phone/interest/timeline/budget fields the regex parser missed. Added 2026-04-15 (migration 103).';
```

### Optional new column: `leads.enrichment_source`

```sql
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS enrichment_source text;
-- Values: 'regex', 'managed_agent', 'merged'
```

Optional — useful for analytics but not strictly required. Can be added later.

## Implementation

### File 1: `backend/routers/widget_helpers.py`

Add a new helper alongside `_extract_lead_info`:

```python
async def _enrich_lead_from_message(
    tenant_id: str,
    session_id: str,
    raw_text: str,
    regex_extracted: dict[str, str],
) -> None:
    """Background task: run structured_extractor on the message and merge
    any new fields into the existing lead row.

    Non-blocking: errors are logged but never raised. Must not crash the
    widget pipeline.
    """
    # NOTE 2026-04-15: spec originally referenced ExtractorError but
    # backend/services/structured_extractor.py raises ValueError directly.
    # Helper catches ValueError (parse failure) + Exception (anthropic
    # outage, ManagedAgentNotConfigured, etc.). See actual implementation
    # in backend/routers/widget_helpers.py::_enrich_lead_from_message.
    from backend.services.structured_extractor import extract_structured
    try:
        result = extract_structured(
            tenant_id=tenant_id,
            raw_text=raw_text,
            target_schema="lead",
        )
    except ValueError as exc:
        logger.warning(
            "lead_enrichment: structured_extractor parse failed for session=%s: %s",
            session_id, exc,
        )
        return
    except Exception:
        logger.exception(
            "lead_enrichment: unexpected extractor error for session=%s",
            session_id,
        )
        return

    # Merge: managed agent wins on fields regex missed; regex wins on
    # fields both populated (regex is cheap and tends to be more literal).
    merged = dict(regex_extracted)
    for key in ("name", "email", "phone", "interest", "timeline", "budget"):
        val = result.get(key)
        if val and not merged.get(key):
            merged[key] = val

    if merged == regex_extracted:
        return  # No new info, nothing to do

    # Update the lead row via tenant_scope helper.
    # NOTE 2026-04-15: spec originally said dedup by session_id but the
    # leads table has no such column. Real implementation dedups by
    # email + client_id (matching _capture_leads_from_session at line
    # 1102 of widget_helpers.py). If neither regex nor extractor produced
    # an email or phone, the helper skips because there's no safe key.
    db = get_service_supabase()
    db.table("leads").update(
        _lead_fields_for_update(merged),
    ).eq("client_id", tenant_id).eq("email", merged["email"]).execute()

    log_activity(
        tenant_id=tenant_id,
        activity_type="lead_enriched",
        description="Lead fields enriched by structured_extractor managed agent",
        metadata={"session_id": session_id, "fields_added": [k for k in merged if k not in regex_extracted]},
    )
```

### File 2: `backend/routers/widget_chat.py`

In the main handler, after `_extract_lead_info` runs, queue the background task only when the flag is on:

```python
if widget.get("enable_structured_lead_parser"):
    background_tasks.add_task(
        _enrich_lead_from_message,
        tenant["id"],
        req.session_id,
        req.message,
        _extract_lead_info(req.message),
    )
```

### File 3: `frontend/src/pages/WidgetPage.jsx`

Add a toggle field mirroring the `enable_ai_fallback` pattern shipped 2026-04-11:

```jsx
<ToggleField
  label="Smart lead enrichment"
  description="Uses a managed AI agent to fill in name/email/phone/interest fields the basic parser missed. Runs in the background — zero latency impact. Adds ~$0.002 per chat message."
  checked={form.enable_structured_lead_parser}
  onChange={(v) => setForm({...form, enable_structured_lead_parser: v})}
/>
```

## Tests

`backend/tests/test_lead_enrichment.py` (new file, ~8 tests):

1. `test_enrichment_skipped_when_flag_off`
2. `test_enrichment_fills_missing_fields`
3. `test_enrichment_respects_regex_wins_policy`
4. `test_enrichment_extractor_error_does_not_crash`
5. `test_enrichment_extractor_timeout_does_not_crash`
6. `test_enrichment_activity_log_written`
7. `test_enrichment_no_update_when_nothing_new`
8. `test_enrichment_handles_fenced_json_reply` (Haiku fence regression)

Mock `structured_extractor.extract_structured` — no live API calls.

## Rollout

1. Ship migration 103 + code behind flag, default off. Zero impact on existing tenants.
2. Enable for MTOptions (top driver). Monitor `activity_log WHERE activity_type = 'lead_enriched'` for 24 hours.
3. Compare before/after lead-field completion rate. Target: ≥95% of leads have all of name/email/phone within first 3 messages.
4. Roll to the other 4 testers if MTOptions shows improvement.
5. Default new widget configs to `true` after 1 week of clean data.

## Cost + latency budget

- Cost per enrichment call: ~$0.002 (Haiku, <500 input tokens, <200 output tokens)
- MTOptions volume: 704 msgs/mo × $0.002 = **$1.41/mo per top tenant**
- Latency impact on chat happy path: **0ms** (runs in background task after response)
- Latency impact on lead row update: ~1-2s background, user-invisible
- Anthropic rate limit risk: Haiku has very high throughput, not a concern

## Risks + mitigations

1. **Managed agent hallucinating field values** — only merge fields that pass strict type validation (email must match `EMAIL_RE`, phone must be 7-15 digits). Reject obviously wrong values.
2. **Duplicate leads** — background task may race with the sync `_capture_leads_from_session` path. Use `session_id` as the dedup key and `INSERT ... ON CONFLICT UPDATE` semantics.
3. **Anthropic outage** — graceful degrade. Regex still runs synchronously, lead is still created. Enrichment is pure upside.
4. **Flag on but extractor not provisioned** — `extract_structured` raises `ManagedAgentNotConfigured`. Catch and log. Flag can stay on, no crash.
5. **Cost blowout on a spam tenant** — rate limit is already 60/min at the widget chat level. If a tenant gets abused, the upstream limit kicks in before costs run up.

## Out of scope

- Deleting `_extract_lead_info` — keep for fallback.
- Changing the `leads` table column set (add `enrichment_source` is optional, defer).
- A/B framework — just use the flag.
- Dashboard UI showing enrichment history (query `activity_log` directly for now).
- Migrating historical leads (N = ~50, not worth batch reprocessing).

## Verification

```bash
# 1. Unit tests
python3 -m pytest backend/tests/test_lead_enrichment.py -v

# 2. Apply migration 103
# via Supabase MCP or Management API

# 3. Enable flag for test tenant
UPDATE widget_configs SET enable_structured_lead_parser = true WHERE tenant_id = '<test>';

# 4. Send a test widget message that the regex would miss
curl -X POST https://agentnexlify-production.up.railway.app/api/v1/widget/chat \
    -H "Content-Type: application/json" \
    -d '{"api_key":"<test>","session_id":"spec-test","message":"Hi — its Sarah Kim, reach me at sarah.kim @ example . com or (555) 867-5309 — looking for a quote on your autopilot plan by June"}'

# 5. Verify enrichment
SELECT * FROM activity_log WHERE activity_type = 'lead_enriched' ORDER BY created_at DESC LIMIT 5;
SELECT name, email, phone, areas_of_interest, timeline FROM leads WHERE session_id = 'spec-test';
```

## Delegation model

Opus planned this (file you're reading). **Sonnet executes** after approval.
- Phase 1: migration + helper + tests (~1hr)
- Phase 2: widget_chat.py wiring + frontend toggle (~30min)
- Phase 3: live smoke on test tenant → monitor → roll out (~1 day elapsed)
