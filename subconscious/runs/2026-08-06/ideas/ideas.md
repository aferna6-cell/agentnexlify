# Ideas — 2026-08-06 (Run 101)

**Generated:** 2026-08-06 | **Evidence window:** 14-day git log + bug-patterns.md + nightly logs + governance.json

---

## Idea 1 — Step 9G: KB Autopopulate Self-Healing Trigger (4th-cycle escalation)

**Category:** operational  
**Effort:** XS  
**Confidence:** HIGH  
**Autonomous-executable:** true  
**Channel:** nightly-commit-review SKILL.md-edit + direct implementation escalation

**Problem:** KB last run 2026-07-23 (14 days stale). Step 9F fires alert correctly; Step 9G adds self-repair. Two PRs (#625, #626) implement it but neither merged — same 4-cycle pattern as Step 9F (runs 97-99 recommended, run 99 implemented directly on 3rd carry-forward).

**Action:** Add Step 9G bash block to `.claude/skills/nightly-commit-review/SKILL.md` after Step 9F block. Condition: `DAYS_STALE -gt 7`. Trigger `gh workflow run kb-autopopulate.yml -R aferna6-cell/agentnexlify`, sleep 30, parse conclusion, comment on GH #403 if failed.

**Evidence:** Morning digest 2026-08-05: "KB stale 13+ days — Step 9G PRs not yet merged." Nightly 2026-08-06: same finding. grep Step 9G in SKILL.md = 0. 14 days of degraded AI chat quality for all 3 live tenants. Run 99 precedent: direct implementation on 3rd carry-forward is governance-sanctioned.

---

## Idea 2 — Fix PR Dedup Guard in Subconscious SKILL.md

**Category:** workflow  
**Effort:** S  
**Confidence:** MEDIUM  
**Autonomous-executable:** true (SKILL.md edit)  
**Channel:** nightly-commit-review SKILL.md-edit

**Problem:** Subconscious SKILL.md Phase 8 has a dedup guard (added run 99), but 7 subconscious draft PRs exist: #625, #626, #613, #611, #606, #604, plus more. Guard is clearly not working. Root cause undiagnosed but likely: guard checks for open `subconscious/*` branches but new branches are named differently each run, so check returns 0 results and guard falls through.

**Action:** Read current guard logic in SKILL.md Phase 8. If guard only checks branch names, strengthen to also check PR titles containing "subconscious:". Cap: if >3 open subconscious PRs, halt branch creation and file a dedup-required GH issue instead.

**Evidence:** Morning digest: "10 open PRs, 7 drafts from subconscious." Nightly: "Step 9G duplicated across #625 and #626 — one needs to win." PR debt actively blocking visibility.

---

## Idea 3 — Tenant Conversation Heartbeat (Silent-Green Automation Prevention)

**Category:** observability  
**Effort:** M  
**Confidence:** MEDIUM  
**Autonomous-executable:** false (requires Supabase access in headless)  
**Channel:** new Step 9H in nightly SKILL.md + GH issue

**Problem:** bug-patterns.md documents "silent-green automation" pattern: widget went missing 5 weeks with no automated detection. Nightly commit review does not check if live tenants are actively generating conversations. A tenant could go dark (widget broken, domain changed, billing lapsed) with no alert.

**Action:** Add Step 9H: query nightly log or backend logs for conversation count per tenant in last 24h. If any paying tenant has 0 conversations for 48h, comment on a designated monitoring GH issue with tenant + last-seen timestamp. File GH issue with `human-action-required` label if 72h dark.

**Blocking concern:** Supabase MCP unavailable in headless sessions (confirmed runs 88, 89). Would need a different mechanism (backend API call or GitHub Actions context).

---

## Idea 4 — Document `client_id` Requirement on `tenant_api_keys` Table

**Category:** bug prevention  
**Effort:** XS  
**Confidence:** HIGH  
**Autonomous-executable:** true  
**Channel:** bug-patterns.md edit

**Problem:** 2026-08-01 bug: `connector_awareness.connection_status()` used `.eq("tenant_id", client_id)` on `tenant_api_keys` table — should be `.eq("client_id", client_id)`. Fixed in connector_registry.py. But bug-patterns.md entry says "Files Changed: none yet" — the pattern is documented but the canonical fix location is not recorded.

**Action:** Update bug-patterns.md `client_id` entry to: (1) add `tenant_api_keys` as a table covered by the invariant, (2) record the connector_awareness.py fix location (connector_registry.py), (3) update the fix status to reflect the 2026-08-01 fix.

**Evidence:** docs/dev-knowledge/bug-patterns.md top entry (2026-08-01): `connector_awareness.connection_status()` `.eq("tenant_id", client_id)` on `tenant_api_keys` — should be `.eq("client_id", client_id)`. Fixed in `connector_registry.py`. Bug-patterns entry says "Files Changed: none yet."

---

## Idea 5 — Governance State Sync (active_directions archive)

**Category:** meta  
**Effort:** M  
**Confidence:** HIGH  
**Autonomous-executable:** false (governance.json edit + manual effort)  
**Channel:** direct edit

**Problem:** governance.json `total_runs` is 100, but multiple runs (101-103) have happened on unmerged branches. `active_directions` contains many `pending_human_action` items from runs 89-93 that are stale (referral program, Keys Koffee booking) — these may already be resolved or abandoned. The list has grown to 15+ entries, many superseded.

**Action:** Archive `active_directions` items older than 30 days with `status: superseded` into a `archived_directions` array. Separate concern: this run correctly updates total_runs to 101 and sets last_run to 2026-08-06 as governance maintenance.

---

## Summary Table

| # | Idea | Effort | Confidence | Executable? |
|---|------|--------|------------|-------------|
| 1 | Step 9G direct implementation | XS | HIGH | ✅ yes |
| 2 | PR dedup guard fix | S | MEDIUM | ✅ yes |
| 3 | Tenant conversation heartbeat | M | MEDIUM | ❌ Supabase headless gap |
| 4 | `tenant_api_keys` bug-patterns.md update | XS | HIGH | ✅ yes |
| 5 | Governance state sync | M | HIGH | ❌ human judgment needed |
