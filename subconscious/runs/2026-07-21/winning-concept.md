# Winning Concept — 2026-07-21 (Run 100)

## Recommendation

File a human-action-required GH issue for **Migration 176 / INTEGRATIONS_ENC_KEY provisioning blocker** before the first GCal OAuth connect arrives.

## Why This, Why Now

Migration `migrations/176_sunset_plaintext_integration_tokens.sql` is an irreversible schema change that drops `access_token` and `refresh_token` from the `integrations` table. Its own comment says "DO NOT APPLY until INTEGRATIONS_ENC_KEY is set in Railway prod." The GCal integration just shipped (commit `34fa9bd`, 2026-07-21 nightly window) — OAuth connects are incoming. Currently 0 rows in the `integrations` table: safe window to provision the key and then apply. Once real rows accumulate, applying the migration drops live token data permanently. The nightly log flagged this as HIGH / ACTION REQUIRED; a GH issue makes this durable, assignable, and closes only when the key is provisioned and migration applied successfully.

## Implementation Sketch

1. Create GH issue in `aferna6-cell/agentnexlify` via `mcp__github__issue_write` with:
   - **Title:** "ACTION REQUIRED: Provision INTEGRATIONS_ENC_KEY in Railway before applying Migration 176"
   - **Labels:** `migration`, `infrastructure`, `action-required`, `security`
   - **Body:**
     - What migration 176 does (drops access_token + refresh_token from integrations)
     - Why INTEGRATIONS_ENC_KEY must be provisioned first (vault's encrypt_oauth_tokens() no-ops without it)
     - Current safe state: 0 rows in integrations table, GCal just shipped
     - How to provision: Railway → Variables → INTEGRATIONS_ENC_KEY → set value (generate with `openssl rand -base64 32`)
     - How to apply after provisioning: `mcp__supabase__apply_migration` with migration 176 SQL, or Supabase SQL editor
     - How to verify: new OAuth connect → check integrations row has encrypted token (access_token column gone, vault_token populated)
     - Acceptance criteria: CLOSE ONLY when (1) key in Railway prod, (2) migration 176 applied, (3) at least one GCal OAuth round-trip verified

## What This Replaces

Run 99 winner was Step 9F (KB staleness check) — implemented directly by the subconscious. This run's winner is a new direction: infrastructure action tracking for an imminent irreversible migration risk.

## Mandate Check Results (Run 100)

| Mandate Item | Status |
|---|---|
| Step 9F in SKILL.md? | ✅ CONFIRMED — `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` returns 6 |
| Nightly-2026-07-21 "Step 9F:" line? | ❌ NOT FOUND in log — possible log format suppresses silent steps; investigate in run 101 |
| KB stale >7 days? | ✅ YES — last run 2026-07-13, 8 days ago. GH #403 comment: UNKNOWN (not verified this run) |
| GH #399 resolved? | ⚪ UNKNOWN — Day 18+, not checked this run |
| GH #413 REFERRAL_REWARD_ENABLED=1? | ⚪ UNKNOWN — Day 10+, not checked this run |
| appointment_completion.py working? | ⚪ UNKNOWN — no backend log check this run |
| platform_settings non-boolean rows? | ⚪ NOT CHECKED — 0 prod rows, low priority |

## Parking Lot (Run 100)

| Item | Status | Notes |
|---|---|---|
| Photo-quote billing audit | WEAKENED → parking lot | `photo_quote_usage.py` verified solid: idempotency key correct, client_id correct, fail-open correct, daily+monthly layers both present |
| Migrations 181/182 peer apply | WEAKENED → parking lot | Correct mechanism: peer agent (Codex or Kimi3) must apply — not Fable5 (author). File team-channel request or GH tag instead |
| Step 9F nightly execution gap | SURVIVED → parking lot | Mandate item. Log format may suppress silent steps. Verify in run 101 by checking GH #403 for Step 9F comment |
| platform_settings integer audit | KILLED | 0 prod rows, no evidence of imminent risk |
| GH #399 (expired AUTOPILOT_GH_TOKEN) | OPEN Day 18+ | Blocks 30 ai-ready issues + issue-to-pr-loop |
| GH #413 (REFERRAL_REWARD_ENABLED=1) | OPEN Day 10+ | 0 human responses |

## Confidence: HIGH

- Nightly explicitly labeled Migration 176 as HIGH / ACTION REQUIRED
- Mechanism is proven: subconscious recommends → human files GH issue (or this subconscious files it via mcp__github__issue_write)
- Time-sensitive: safe window closes when first GCal OAuth connect arrives
- Zero implementation risk: issue creation only, no code changes
- Novel this run: not a carry-forward, not a frozen idea

## Run 101 Mandate

1. Migration 176 GH issue filed? (check `aferna6-cell/agentnexlify` issues for "INTEGRATIONS_ENC_KEY")
2. INTEGRATIONS_ENC_KEY provisioned and Migration 176 applied? (if GH issue was created)
3. Step 9F nightly execution confirmed? (check nightly-2026-07-22.md for "Step 9F:" line OR check GH #403 for Step 9F comment from 2026-07-21/22)
4. KB stale alert: if still >7 days since 2026-07-13, Step 9F should have commented on GH #403
5. GH #399 resolved? (Day 19+) — unlocks: issue-to-pr-loop, conversation_enrichment_job.py
6. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 11+)
7. Migrations 181+182 applied by peer agent? (unblocks conversation memory + KB provenance)
