# Ideas — Run 101 (2026-07-21)

## Evidence Digest

45 commits in last 24h — fastest sprint to date (Agent OS PRs 539-544: os_projects, os_research, workforce_digest, customer_memory, batch_runtime, suite plan gate). Migration 176 committed but unapplied (INTEGRATIONS_ENC_KEY missing in Railway — irreversible drop of plaintext token columns). Migrations 180-182 draft/unapplied — 3 features silently no-op. Step 9F confirmed in nightly SKILL.md (grep: 6 matches) but NOT in today's nightly log (105 lines, no "Step 9F:" text) — monitoring gap despite 8-day KB staleness. GH #399 (autopilot-loop token expired) Day 17+, 30 ai-ready issues blocked. GH #413 CLOSED 2026-07-20 — referral program live, no analytics dashboard. god-class splits: widget_chat.py (976 tests) + invoices.py (1006 tests) shipped. loop_health_scan SUPABASE_SERVICE_KEY guard added (26f7829).

---

### Idea 1: Fix Step 9F execution gap — KB staleness check present in SKILL.md but silent in automated nightly

**Evidence:** knowledge-base/log.md last entry 2026-07-13 (8 days stale, >7-day threshold). SKILL.md grep returns 6 matches for "Step 9F" (confirmed present). Nightly log 2026-07-21 (105 lines) has zero "Step 9F:" text — the check did not fire despite threshold breach. Runs 97+98+99+100 carried this forward; Step 9F was directly implemented by run 99 into SKILL.md; yet automated nightly does not emit it. Gap: SKILL.md is a human/AI guide, but the automated nightly-commit-review.sh bash script may not execute the SKILL.md's bash block. The system believes KB monitoring is live; it is not.

**Action:** Read `scripts/daily/nightly-commit-review.sh` to confirm whether Step 9F bash block is included. If absent, add the KB staleness bash check (read knowledge-base/log.md last-date, compare to today, if >7 days log warning + comment on GH #403) directly into the automated shell script, not just SKILL.md.

**Impact:** KB staleness monitoring restored end-to-end. Prevents silent 30+ day KB gaps from compounding (KB last ran 2026-07-13 = 8 days ago and nobody noticed until this subconscious run).

**Category:** operational

---

### Idea 2: Add referral analytics to LeadAttributionPage now that referral program is live

**Evidence:** GH #413 CLOSED 2026-07-20 — human activated REFERRAL_REWARD_ENABLED=1. `customer-gaps.md` lists "Lead source analytics: source column exists, no dashboard visualization" as HIGH-priority open gap. `referral_code` captured on leads table at time of submission. No referral dashboard exists. The feature is live and generating data with zero visibility into performance.

**Action:** Add referral analytics section to `frontend/src/pages/LeadAttributionPage.jsx` (or create `ReferralPage.jsx`) — referral_code distribution, conversion rate by referral source, total rewards owed. Backend endpoint: `/api/referrals/summary` scoped by `client_id`.

**Impact:** Enables measurement of referral program ROI. Supports reward payout decisions. Closes the highest-priority item in customer-gaps.md (lead source analytics) as a side effect.

**Category:** customer_value

---

### Idea 3: Add `check_pending_migrations()` to loop_health_scan to surface silent feature no-ops

**Evidence:** nightly-2026-07-21 lists 3 unapplied migrations causing silent no-ops: migration 180 (pending_automations — missed-call text-back silently skipped), migration 181 (kb_article_provenance — KB article tracking absent), migration 182 (conversation_message_memory — widget conversation memory no-ops). loop_health_scan.py recently fixed (26f7829 SUPABASE_SERVICE_KEY guard). It already monitors the automation loop. Adding a table-presence check extends existing monitoring with zero new infrastructure.

**Action:** Add `check_pending_migrations()` to `backend/services/loop_health_scan.py` that queries Supabase for expected tables (pending_automations, kb_article_provenance, conversation_message_memory). Returns WARN entries in the health report when tables are absent. Hook into existing `/api/health/loop` endpoint.

**Impact:** Silent no-ops become visible failures in existing monitoring. Operations team sees missing migration before a customer complaint surfaces it.

**Category:** operational

---

### Idea 4: Post GH #399 resolution runbook as comment to reduce human friction to zero

**Evidence:** GH #399 opened 2026-07-04 (Day 17). AUTOPILOT_GH_TOKEN expired — autopilot-issue-loop dead, 30 ai-ready issues backlogged. Subconscious has flagged this 5+ consecutive runs with no fix. Root cause is simple (token rotation, ~5 min). Blocker is that the steps require looking up Railway Variables dashboard path + GitHub token settings. The fix IS the runbook — if it's posted as a comment with exact steps, human friction drops to near zero.

**Action:** Via mcp__github__add_issue_comment on GH #399: post a step-by-step comment: (1) GitHub Settings → Developer settings → Personal access tokens → generate token with `repo` + `issues` scope, (2) Railway project → AgentNexLiFy → Variables → set AUTOPILOT_GH_TOKEN, (3) redeploy. Estimate: 5 min total. Tag the comment with "self-written runbook by subconscious run 101".

**Impact:** Removes the last human-friction barrier to unblocking 30 ai-ready issues. Cost: 0 code changes, 1 MCP call.

**Category:** workflow

---

### Idea 5: Add `/api/integrations/vault-status` endpoint to gate migration 176 apply-readiness

**Evidence:** nightly-2026-07-21 Action Required: migration 176 committed (ec0de08), NOT applied, requires INTEGRATIONS_ENC_KEY in Railway prod before apply. Migration is irreversible (drops plaintext token columns). Current state: all readers route through `decrypt_integration_row`, prod integrations table has 0 rows. Zero programmatic check exists to verify INTEGRATIONS_ENC_KEY is set before a human applies the migration. Risk: human applies before key is set → new OAuth connects have nowhere to store tokens.

**Action:** Add `GET /api/admin/integrations/vault-status` that checks `os.environ.get("INTEGRATIONS_ENC_KEY")` and returns `{ready: bool, key_present: bool, migration_176_safe_to_apply: bool}`. Document in migration 176 file: "Run this endpoint first. Only apply when ready=true."

**Impact:** Eliminates the risk of irreversible data loss from premature migration apply. Single endpoint, zero schema changes.

**Category:** operational
