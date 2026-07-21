# Ideas — Run 100 (2026-07-21)

## Idea 1: File Human-Action-Required GH Issue for Migration 176 (INTEGRATIONS_ENC_KEY)

**Evidence:** nightly-commit-review-2026-07-21 explicitly flagged commit `ec0de08` (migration 176) as HIGH / ACTION REQUIRED. Migration drops `access_token` + `refresh_token` from `integrations` table — irreversible. Migration comment: "DO NOT APPLY until INTEGRATIONS_ENC_KEY is set in Railway prod (and CI). Without the key the vault's encrypt_oauth_tokens() no-ops, so new OAuth connects would have nowhere to store tokens after this drop." Prod has 0 rows currently (safe window). GCal integration just shipped (commit `34fa9bd`) — OAuth connects are incoming. No GH issue tracks this requirement.

**Action:** Create a GH issue in `aferna6-cell/agentnexlify` titled "ACTION REQUIRED: Provision INTEGRATIONS_ENC_KEY in Railway before applying Migration 176" with full context: what the migration does, why the key must be provisioned first, how to do it (Railway → Variables → INTEGRATIONS_ENC_KEY), how to then apply via `mcp__supabase__apply_migration`, and why the window is closing (GCal OAuth connects imminent).

**Impact:** Prevents an irreversible data loss event (OAuth tokens for new integrations silently failing to store). Creates a durable human-action tracking item. Converts nightly's transient log warning into a persistent, assignable task.

**Category:** operational

---

## Idea 2: Apply Migrations 181+182 via Team Peer Protocol

**Evidence:** nightly-commit-review-2026-07-21 lists migrations 181 (`kb_article_provenance`) and 182 (`conversation_message_memory`) as DRAFT — pending peer apply via cross-provider team protocol. Commit `ba10d80` established the team protocol. Migration 182 enables conversation memory tier (commit `44f9042`) — chat messages need `chat_messages` table (`tenant_id`-scoped). KB provenance (migration 181) ties into article lifecycle. Both authored by Fable5; peer (Codex or Kimi3) must apply.

**Action:** Follow `docs/TEAM_OPERATING_CONTRACT.md` Tier A flow: invoke `mcp__supabase__apply_migration` for migration 181 and 182 in sequence, as peer agent fulfilling the team contract.

**Impact:** Unblocks conversation memory tier and KB article provenance features. Features are shipped but silently no-op without schema. Estimated unblock: 2 features, immediate.

**Category:** operational

---

## Idea 3: Photo-Quote Overage Billing Stripe Integration Audit

**Evidence:** Photo-quote feature shipped in this nightly window (commits `37ba729`, `18ad432`, `e0aa720`, `9573d48`). Metered Stripe billing (`$0.15/overage` above 500/mo) is complex — separate daily quota (50/day) + monthly cap (500/mo), Stripe metered reporting via `stripe_photo_quote_metered_price_id`. Risk: metered billing is the most failure-prone Stripe integration pattern.

**Action:** Read `backend/services/photo_quote_usage.py` and verify: (a) idempotency key pattern prevents double-billing, (b) daily vs monthly quota logic doesn't conflict, (c) `client_id` (not `tenant_id`) used throughout, (d) fail-open behavior doesn't allow infinite free usage.

**Impact:** Prevents revenue leakage or customer double-billing in the first metered billing feature. Risk mitigation before OAuth connects start.

**Category:** code_health

**Note: WEAKENED during debate** — `photo_quote_usage.py` was read and billing is solid. See debate log.

---

## Idea 4: Step 9F Nightly Execution Gap Investigation

**Evidence:** Run 100 mandate item 2 requires `nightly-commit-review-2026-07-21.md` to contain "Step 9F:" line. The log does NOT contain this line. Step 9F was implemented by run 99 (2026-07-20) directly into SKILL.md. `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` returns 6 — step IS present. However, the nightly log format may only surface steps that generate notable output (GH comments, errors). If KB stale was detected and GH #403 comment was added, Step 9F DID fire — just silently. If GH #403 has no new Step 9F comment as of today, the step may have been skipped.

**Action:** Check GH issue #403 for a Step 9F comment dated 2026-07-21. KB is 8 days stale (>7 threshold) — Step 9F SHOULD have fired. If no comment: investigate whether Step 9F block's guard condition (file-missing, parse-error) triggered, or whether nightly didn't execute Step 9F at all.

**Impact:** Confirms nightly pipeline health monitoring is working end-to-end. If Step 9F is silently skipping, it defeats the purpose of the implementation.

**Category:** operational

**Note: WEAKENED during debate** — ambiguous; cannot verify GH #403 state in this run without making a live GH API call. Parking for nightly's own mandate checks.

---

## Idea 5: Platform_settings Integer Kill-Switch Safety Audit

**Evidence:** `platform_settings` table uses boolean flags for feature kill-switches. Pre-existing concern: if a non-boolean (integer) row is added accidentally, type-mismatch bugs emerge silently. Currently 0 prod rows at risk (per governance.json parking lot entry from run 99).

**Action:** Read `backend/services/platform_settings_service.py` and check: (a) all reads cast to bool, (b) write path validates bool type, (c) any integer-typed rows would be caught before deployment.

**Impact:** Low priority. 0 prod rows at risk. More of a code health hygiene item than urgent fix.

**Category:** code_health

**Note: KILLED during debate** — lowest leverage given 0 prod rows, no evidence of imminent risk, pre-existing parking lot item with no change in status.
