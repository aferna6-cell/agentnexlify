# Ideas — Subconscious Run 2026-05-05-pm (Run 14)

## Context
First free-choice run since moratorium was triggered (run 8). Run 13 winner (JS Silent Catch Guard + AdminAnalyticsPage fix) was IMPLEMENTED by nightly review on 2026-05-05 (commit 72f8204). Moratorium lifted: pending_approvals 4→3 (runs 4, 7, 8 remain).

**Critical governance update this run:**
- Em-dash check_project_invariants.py blocker CLEARED — commit 8f680e8 fixed WizardStepAutoKB.jsx + AutomationActivityCard.jsx, all 6 invariant checks now PASS
- SettingsPage.jsx split done (27e06f0) — parking lot ROI 1.9 complete
- Pre-commit now has 9 checks (Check 9 = JS silent catch, added 72f8204)

---

### Idea 1: Wire Golden Eval Harness to CI
**Evidence:** `backend/tests/evals/test_lead_qualifier_golden.py` + `lead_qualifier_golden.json` added 7854ede. No corresponding `.github/workflows/lead-qualifier-eval.yml` exists. parking_lot ROI 2.5. Issue #110 open. Governance explicitly flags as "first post-moratorium winner." Lead qualifier is the core AI feature all tenants use. Current: zero regression guard on it.
**Action:** Create `.github/workflows/lead-qualifier-eval.yml` with Monday 9 AM cron + PR trigger. Env-var gated (`LEAD_QUALIFIER_AGENT_ID`). Passes when ≥80% golden set matches expected classifications.
**Impact:** Prevents silent quality regression on highest-impact tenant-facing feature. One broken model prompt → catch in CI, not in production tenant chat.
**Category:** operational

---

### Idea 2: Fix email_sequences N+1 Queries
**Evidence:** GH #112 opened 2026-05-02. `list_enrollments` at line 728 issues 1 DB call per enrollment row (1001 queries per 1000 enrollments). `list_sequences` issues 2 DB calls per sequence. Both confirmed in email_sequences.py (1255 lines). M-effort bulk `.in_()` fix documented in issue.
**Action:** Refactor `list_enrollments` to use bulk Supabase `.in_()` filter fetching all related data in 2 queries total. Same for `list_sequences`. Add index if needed.
**Impact:** Eliminates N+1 before email automation adoption scales. At 10 tenants × 1000 enrollments = 10,000 → 20 queries. No user-visible today but operational timebomb.
**Category:** code_health

---

### Idea 3: AI-to-Human Handoff v1 (Explicit Trigger)
**Evidence:** customer-gaps.md: Critical rating, all 7 industries affected. Run 4 winner (2026-04-16), pending_approval 19+ days. Infrastructure exists: conversations table, Twilio, Resend, webhooks. Explicit-trigger-only (button/keyword) scoped to 1.5-2 days.
**Action:** Add `trigger_human_handoff()` function in widget_chat.py. Widget sends `handoff_requested` event. Backend records in conversations table, sends Resend email to tenant. No AI loop replacement — just escalation signal.
**Impact:** Covers the most-cited gap across all customer types. Enables first revenue from tenants who need human oversight for complex queries.
**Category:** customer_value

---

### Idea 4: Fix KB Broken Wikilinks / Orphan Articles
**Evidence:** `scripts/kb/kb-health.py` added 64e9058 (285 lines). First run today shows: 11 orphaned wiki articles (no inbound wikilinks), 13 broken wikilinks (targets don't exist — e.g. `[[model-routing]]`, `[[claude-code-security]]`, `[[seo-audit-marketing]]`). Broken wikilinks mean KB context7 lookups fail to traverse the graph.
**Action:** Fix 13 broken wikilinks in wiki/ articles by updating slug references to match actual filenames. Remove or consolidate 11 orphaned articles.
**Impact:** Knowledge graph integrity. Every broken link = one missed context hop when KB is queried. S-effort (sed replacements + 2-3 file merges).
**Category:** operational

---

### Idea 5: Extract _process_pending_sends() from email_sequences.py
**Evidence:** GH #113 opened 2026-05-02. `process_sequences` (lines 875-1087) and `run_sequence_processor` (lines 1088-1255) share ~120 lines of near-identical per-send loop logic. Any bug fix in send logic must be applied twice. email_sequences.py already at 1255 lines.
**Action:** Extract shared send loop into private `_process_pending_sends(pending_sends, client_id)` helper. Both calling functions delegate to it.
**Impact:** Next bug fix touches 1 function instead of 2. Prevents divergent bug fixes (one copy patched, other missed). M-effort refactor.
**Category:** code_health
