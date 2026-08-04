# Ideas — Run 101 (2026-08-04)

## Evidence Digest

Since run 100 (2026-07-23): 50 commits in 12 days — highest sustained velocity in months. Capabilities phases 1-5 (b67710c, 62 files, 13,916 insertions) shipped: inbox monitoring, SMS agent, social publish+images, prospecting, in-chat connectors. PWA (c5a5a62), autonomy sweeper (8e78f5b), typed KB notes (4853c31), plan-gate bug fix (2869124). Three pre-existing human blockers remain: GH #399 (AUTOPILOT_GH_TOKEN Day 26+), GH #394 (brain credentials Day 26+), GH #536 (INTEGRATIONS_ENC_KEY Day 14+ — HIGH, blocks Gmail/social OAuth token encryption). KB stale 12 days (last: 2026-07-23). Step 9G absent from SKILL.md — carry-forward fires (run 100 winner). MCP: 1 live tenant (enterprise, 2026-07-22). Agent OS LoopHealthPage promote condition still not met (<5 tenants).

---

### Idea 1: Step 9G — KB Autopopulate Self-Healing Trigger (carry-forward from run 100)
**Evidence:** grep returns 0 occurrences of "Step 9G" in .claude/skills/nightly-commit-review/SKILL.md (confirmed). KB last run 2026-07-23 — now 12 days stale as of 2026-08-04, exceeding the 7-day threshold. Step 9F alerting correctly (nightly-2026-07-22 confirmed "Step 9F: KB STALE (9 days) — comment added to GH #403") but alert-only posture cannot repair; staleness persists 12+ days. Steps 9B-9F all implemented in 1 nightly cycle each via same SKILL.md-edit channel. Run 100 winning-concept.md contains exact bash block ready to copy.
**Action:** Add Step 9G bash block to .claude/skills/nightly-commit-review/SKILL.md immediately after Step 9F block. When KB >7 days stale: `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify` → `sleep 30` → parse `gh run list` conclusion → if SUCCESS: log + exit; if FAILURE: comment on GH #403 with "Step 9G: kb-autopopulate.yml triggered but FAILED. Check ANTHROPIC_API_KEY + VOYAGE_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions Secrets."
**Impact:** KB self-heals on each nightly when stale, reducing human intervention to only genuine secret rotation failures. 3 live tenants' AI chat quality depends on freshness — salon FAQ, vertical answers, competitive intelligence.
**Category:** operational

---

### Idea 2: INTEGRATIONS_ENC_KEY — Targeted Security Escalation on GH #536
**Evidence:** nightly-2026-07-31 lists GH #536 as HIGH: "provision INTEGRATIONS_ENC_KEY in Railway before applying migration 176" — open 14+ days. Capabilities phases 1-5 (b67710c, 2026-08-01) shipped Gmail OAuth flow, social media token storage, connector registry — all require encrypted OAuth token persistence. Without INTEGRATIONS_ENC_KEY, these tokens are stored unencrypted in the database. connector_registry.py handles tenant-provided OAuth tokens for Gmail, social media. This is a live security gap, not a feature gap.
**Action:** Post comment on GH #536 via mcp__github__add_issue_comment reframing from "feature blocker" to "security gap" — specifically: capability phases 1-5 now store Gmail OAuth tokens and social media API credentials in the database; without INTEGRATIONS_ENC_KEY these are stored in plaintext; rotation urgency has changed since this issue was filed.
**Impact:** Surfaces the security dimension to trigger faster human action. Capabilities phases 1-5 are the largest feature expansion in project history — token exposure is meaningful risk.
**Category:** operational / security

---

### Idea 3: Security Audit Request for Capabilities Phases 1-5
**Evidence:** b67710c (2026-08-01) — 62 files, 13,916 insertions. 5 new high-risk routers: gmail_integration.py (OAuth flow), escalations.py (push notifications to external services), prospecting.py (external contact scraping/emailing), social_media.py (social publishing with AI image gen), connectors.py (tenant-configurable external URL connectors). Nightly-2026-08-02 confirmed no invariant violations but explicitly did NOT evaluate: SSRF via connector_registry (tenant-supplied URLs), Gmail OAuth scope creep, prospecting PII handling (TCPA compliance), social token lifetime management. The nightly's 7-rule invariant check doesn't cover these attack vectors.
**Action:** File GH issue with labels security, human-action-required, audit. Title: "Security audit required: capabilities phases 1-5 (gmail OAuth, connector SSRF, prospecting PII, social token storage)". Body: specific attack vectors to evaluate — SSRF in connector_registry via tenant-controlled URLs, Gmail OAuth scope vs least-privilege, TCPA compliance in prospecting router, social media token lifetime and rotation, INTEGRATIONS_ENC_KEY gap for stored credentials.
**Impact:** Prevents a future security incident on the largest surface area expansion in project history. Prospecting + Gmail access = significant PII exposure risk.
**Category:** code_health / security

---

### Idea 4: GH #399 Renewed Economic Escalation
**Evidence:** GH #399 (AUTOPILOT_GH_TOKEN expired) is now Day 26+ with no human action. nightly-2026-07-31 lists it as CRITICAL. 30 ai-ready issues stalled. The capabilities expansion just added new features that will likely generate additional ai-ready issues. Previous subconscious escalation comments have not moved the needle. Last comment on #399 was 2026-07-16 per run_96_governance_corrections.
**Action:** Post a fresh comment on GH #399 with updated economic framing: 26 days stalled × 30 issues × estimated 2h/issue = ~60 engineering-hours of queued automated work sitting idle. The token rotation is estimated 5 minutes in Railway dashboard. New context: capabilities phases 1-5 will generate additional ai-ready issues, compounding the backlog.
**Impact:** May trigger human action that unblocks the entire 30-issue queue + future issues. Even 10% probability of triggering action justifies the 2-minute autonomous action.
**Category:** operational

---

### Idea 5: Capabilities Phases 1-5 Test Coverage Report
**Evidence:** b67710c adds 5 new routers (gmail_integration.py, escalations.py, prospecting.py, social_media.py, connectors.py) plus 6+ new services. Commit message notes 156 tests passing, but this is aggregate — coverage distribution is unknown. High-risk paths with likely gaps: Gmail OAuth callback with invalid state token, connector_registry with tenant-supplied malformed URL, prospecting with duplicate-send guard, social media post with image gen failure path. The nightly review found no bugs but did not audit coverage.
**Action:** Run `python3 -m pytest backend/tests/ --co -q 2>/dev/null | grep -E "gmail|escalat|prospect|social|connector" | wc -l` to count test files targeting new routes. If coverage appears thin (<10 tests per new router), file GH issue with ai-ready label requesting specific test additions.
**Impact:** Catches gaps before they become production bugs. 13.9k-line expansion with thin test coverage = future regression risk.
**Category:** code_health
