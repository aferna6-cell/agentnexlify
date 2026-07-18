# Winning Concept — 2026-07-18-pm (Run 99)

## Recommendation

**Step 9F: KB Autopopulate Staleness Check — DIRECT IMPLEMENTATION THIS RUN**

This run edits `.claude/skills/nightly-commit-review/SKILL.md` directly and includes it in the commit.
Three consecutive nightly misses confirm the recommended channel (nightly SKILL.md edits) only fires
on nights with bugs to fix. CLEAN nights exit before the SKILL.md step block runs.

## Why Direct Implementation

| Run | Nightly result | Step 9F status |
|-----|---------------|----------------|
| 97 | CLEAN (0 fixes, 2026-07-17) | ABSENT |
| 98 | CLEAN (0 fixes, 2026-07-18 06:40 UTC — before PRs landed) | ABSENT |
| 99 | N/A — subconscious implements directly | PRESENT (this commit) |

Root cause: `auto_fix_commit()` in the nightly script only fires when bugs are found and committed.
Steps 9B/9C/9D/9E were all added on nights WITH commits. The nightly's self-modification path
is gated behind fix-mode entry. When the system is healthy, it skips self-modification.

This is not a bug in the nightly — it's a mechanism mismatch. The fix is to change the channel.

## Mandate Check (Run 99)

| Item | Status |
|------|--------|
| Step 9F in SKILL.md? | ❌ ABSENT (3rd miss) → IMPLEMENTING THIS RUN |
| Nightly log with "Step 9F:" line? | PENDING — first firing will be next nightly after this commit |
| KB health (<7 days)? | ✅ HEALTHY — last run 2026-07-13 (5 days). No GH #403 comment needed. |
| GH #399 resolved? (Day 17+) | ❌ OPEN — AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked |
| GH #413 REFERRAL_REWARD_ENABLED=1? | ✅ EFFECTIVELY YES — PR #476 seeded referral_reward_enabled=1 in platform_settings. Program LIVE without Railway env-var. |
| conversation_enrichment_job.py schedule? | ❌ GH #399 still blocking queue |
| kb_hybrid enable: wait for settings UI? | ✅ NOW LIVE — widget_kb_hybrid_enabled=1 + widget_kb_rerank_enabled=1 seeded via PR #476 |

## Implementation

**File:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insert after Step 9E (after line 288, before step 10):**

```
9F. (KB Autopopulate Staleness Check) Check knowledge-base/log.md for last successful autopopulate run:
    1. **Check if log exists and parse last date:**
       ```bash
       KB_LOG="knowledge-base/log.md"
       if [[ ! -f "$KB_LOG" ]]; then
         echo "Step 9F: KB log not found — cannot assess staleness. Skipping." | tee -a "$NIGHTLY_LOG"
       else
         LAST_RUN=$(tail -1 "$KB_LOG" | grep -oP '^\d{4}-\d{2}-\d{2}' || echo "unknown")
         if [[ "$LAST_RUN" == "unknown" ]]; then
           echo "Step 9F: KB log format unreadable. Last line: $(tail -1 "$KB_LOG")" | tee -a "$NIGHTLY_LOG"
         else
           TODAY=$(date +%Y-%m-%d)
           DAYS_STALE=$(( ( $(date -d "$TODAY" +%s) - $(date -d "$LAST_RUN" +%s) ) / 86400 ))
           echo "Step 9F: KB autopopulate last run: $LAST_RUN ($DAYS_STALE days ago)" | tee -a "$NIGHTLY_LOG"
           if [[ $DAYS_STALE -gt 7 ]]; then
             echo "Step 9F: KB STALE ($DAYS_STALE days). Commenting on GH #403." | tee -a "$NIGHTLY_LOG"
             gh issue comment 403 --repo "$GH_REPO" \
               --body "**KB autopopulate staleness alert (Step 9F):** ${DAYS_STALE} days since last successful run (last: ${LAST_RUN}). Check: (1) ANTHROPIC_API_KEY in GitHub Actions secrets — may need rotation. (2) SUPABASE_ACCESS_TOKEN — may be expired. Manual trigger: \`bash scripts/daily/kb-autopopulate.sh\`." \
               2>/dev/null || echo "Step 9F: GH comment failed (token may be expired — GH #399)." | tee -a "$NIGHTLY_LOG"
           fi
         fi
       fi
       ```
    2. **Guard:** silent skip if KB log missing or unreadable — no false positives. GH comment
       failure (e.g., expired AUTOPILOT_GH_TOKEN) logged but does not block nightly.
```

## Guardrails Verified

- `$NIGHTLY_LOG` set in preamble (confirmed Step 9D/9E use same var)
- `$GH_REPO` set in preamble (confirmed Step 9D/9E use same var)
- `knowledge-base/log.md` exists and has date-prefixed entries (confirmed run 98)
- `date -d` is GNU date — confirmed same pattern as Step 9E credential rotation logic
- `grep -oP` uses Perl regex — confirmed available in nightly environment
- Threshold >7 days: KB currently 5 days — will log healthy entry, no GH comment

## Bonus Action A

Post comment on GH #413 explaining referral program now live via `platform_settings` table
(PR #476 seeded `referral_reward_enabled=1`). No Railway env-var change needed.
`referral_reward.reward_enabled()` reads from `flag_enabled("referral_reward_enabled", ...)` → DB row.
Suggest closing GH #413 as resolved via alternative implementation path.

## What Changed vs Runs 97/98

- Same bash block, same rationale.
- New: mechanism failure confirmed (CLEAN-night pattern, 3 data points).
- New: direct implementation path activated (3-miss escalation).
- New: PR #475 (#454/#465/#453 all CLOSED) + PR #476 (referral live, hybrid+rerank live).
- New: governance corrections for PRs #475/#476/#477.

## Confidence: HIGH

- Mechanism failure confirmed with 3 data points.
- Bash block stable for 3 runs.
- All failure paths guarded.
- KB currently healthy — Step 9F fires in "green" mode first, confirming the check before next gap.
- Direct implementation path: proven (moratorium-sprint precedent, subconscious has git access).

## Run 100 Mandate

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`? (grep — MUST PASS, added this run)
2. First nightly after this commit — does log contain "Step 9F: KB autopopulate last run:" line?
3. KB still within 7-day threshold? (last run 2026-07-13 → 6 days at next nightly ~2026-07-19)
4. If KB stale by run 100: GH #403 has new Step 9F comment?
5. GH #399 resolved? (Day 18+) — unlocks 30 ai-ready issues
6. GH #413 closed as resolved? (platform_settings path explained in Bonus A comment)
7. appointment_jobs.py first auto-complete: any confirmed appointments past window?
8. Platform Settings Admin UI: file ai-ready GH issue if GH #399 resolves
9. Step 9G (kb_hybrid smoke test): candidate if hybrid shows no FTS results after 7+ days live
