# Audit — Ops Automations Wiring Depth (2026-05-01)

**Scope:** 4 ops automations advertised in the platform. Compare wiring depth, prod usage, and dashboard surfacing.

**Sources:**
- `backend/routers/twilio_webhooks.py` (529 LOC)
- `backend/services/appointment_booker.py` (304 LOC)
- `backend/services/document_drafting.py` (510 LOC)
- `backend/routers/email_sequences.py` (1065 LOC)
- Supabase prod, queried via `backend.models.database` 2026-05-01

## Summary

| Automation | Status | Activity-log integration | Automations-table integration | Dashboard surface | Prod usage |
|------------|--------|---------------------------|--------------------------------|-------------------|------------|
| missed-call-textback | code shipped, 0 activated | YES (`activity_type='missed_call_textback'`) | YES (`automations.runs_total++`) | AutomationActivityCard | 0 textbacks sent; 6 tenants have automation row enabled but `tenants.textback_enabled=false` |
| auto-follow-up (email seq) | wired, in use | NO | NO | none (dedicated email seq pages only) | 20 `email_sequence_sends` rows |
| appointment-booker | service exists, managed-agent path only | NO | NO | none (managed_agent_runs only) | 0 `appointments` rows |
| document-drafter | service exists, managed-agent path only | NO | NO | none (managed_agent_runs only) | 0 `documents` rows |

## Gap analysis

### 1. Dashboard surface inconsistency
Only missed-call-textback emits `activity_log` rows. The `AutomationActivityCard` (frontend/src/pages/Dashboard/index.jsx:414) feeds off that table. The other 3 automations are invisible to the user from the dashboard.

**Impact:** owner pitch is "see what your automations did today" but only 1 of 4 contributes events. When the other 3 fire, the activity card stays empty.

**Fix shape (per automation):**
- Add `log_activity(...)` call at success path
- Add `db.table("automations").update({"runs_total": ...})` increment
- Use consistent `activity_type` taxonomy: `appointment_booked`, `document_drafted`, `email_sequence_sent`

### 2. Two-source-of-truth for textback enable flag
- `automations.type='missed_call_textback' AND is_enabled=true` → 6 rows
- `tenants.textback_enabled=true` → 0 rows
- Webhook handler (twilio_webhooks.py:274) reads `tenants.textback_enabled`. The `automations` row is currently decorative.

**Impact:** future PR could either (a) consolidate to single source, (b) auto-sync when settings save, or (c) add admin tool that surfaces the divergence.

### 3. Appointment + document drafter are managed-agent-only
Both services are wired exclusively through `backend/services/managed_agents_registry.py` → `managed_agent_runs.py`. There is no platform-side "automation" the way missed-call has. They are agent-as-a-service surfaces, not background automations.

**Decision needed:** are appointment_booker and document_drafting meant to be listed as "ops automations" alongside missed-call and auto-follow-up, or are they a separate "managed agents" product surface? Current marketing does not distinguish.

If they are automations:
- Add cron / event trigger (currently fired by API call only)
- Wire activity_log + automations.runs_total
- Add to AutomationActivityCard taxonomy

If they are managed agents:
- Move out of "ops automations" in marketing copy
- Surface in a separate Managed Agents page

### 4. Auto-follow-up has prod usage but no dashboard
20 `email_sequence_sends` rows exist. Email seq has its own dedicated UI (`email_sequences.py` is 1065 LOC) but does NOT feed AutomationActivityCard. Owner has to leave the dashboard to see follow-up activity.

**Fix shape:** add activity_log emission at `/internal/process-sequences` send-success path (line ~774).

## Ranked fix list

| Priority | Item | Effort |
|----------|------|--------|
| HIGH | Wire auto-follow-up to activity_log + AutomationActivityCard | S (1 file edit) |
| HIGH | Resolve textback two-source-of-truth (consolidate or auto-sync) | M (2 files + migration) |
| MEDIUM | Decide managed-agents vs automations product framing for appointment + document | XS (decision doc) |
| MEDIUM | If "automations": wire appointment + document to activity_log + automations table | M (4 files) |
| LOW | Add admin view that surfaces tenant config divergence (automations row vs tenant flag) | S (1 page) |

## Verification

- `Verified: queried prod tenants + automations + activity_log + email_sequence_sends + appointments + documents tables — PASS`
- `Verified: read all 4 service files for activity_log and automations.update calls — PASS`
- `Verified: confirmed AutomationActivityCard mount at frontend/src/pages/Dashboard/index.jsx:414-418 — PASS`

## Cross-refs

- `docs/ops/runbook-mtoptions-textback-activation.md` — fix #2 (two-source-of-truth) noted at bottom
- `frontend/src/pages/Dashboard/AutomationActivityCard.jsx` — taxonomy consumer
- `backend/routers/twilio_webhooks.py:179` — only place that increments `automations.runs_total`
