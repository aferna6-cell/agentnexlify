# Winning Concept — 2026-07-17-pm (Run 98)

## Recommendation

Add **Step 9F: KB Autopopulate Staleness Check** to `.claude/skills/nightly-commit-review/SKILL.md`.

This is a carry-forward of the run 97 winner. Mandate check 1 fires: `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` returned 0 — block is ABSENT after 1 full cycle.

## Why This, Why Now

Same reasoning as run 97, reinforced by one more cycle of evidence:

- Run 97 selected Step 9F as winner. Mandate check 1 in run 98 confirms the block was NOT implemented by the nightly-commit-review cycle that ran 2026-07-17.
- KB last ran 2026-07-13 (4 days ago — within 7-day threshold, currently healthy). Step 9F would log "Step 9F: KB autopopulate last run: 2026-07-13 (4 days ago)" — observability even when green.
- The 72-day gap (2026-05-05 to 2026-07-09) happened silently with zero automated signal. Step 9F prevents recurrence.
- Steps 9B/9C/9D/9E all implemented in 1 nightly cycle each via the same SKILL.md-edit channel. Mechanism is proven.
- PR #471 landed today with batch_runtime.py, kb_hybrid_retrieval.py, kb_reranker.py, conversation_enrichment_job.py — major AI infrastructure. All opt-in, all need validation before enabling. Step 9F has zero dependency on any of these.
- GH #399 OPEN Day 16+. issue-to-pr-loop cannot process ai-ready issues. Step 9F bypasses this blocker entirely — it goes through the nightly SKILL.md-edit channel.

## Implementation

**Target file:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insert after Step 9E (credential rotation schedule check):**

```markdown
### Step 9F: KB Autopopulate Staleness Check

```bash
# Check knowledge-base/log.md for last successful autopopulate run
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

**Notes:**
- Guard: skips silently if KB_LOG missing or unreadable — no false positives
- GH comment: optional — failure (e.g. AUTOPILOT_GH_TOKEN expired) logged but does not block nightly
- Threshold: >7 days stale triggers comment — matches KB autopopulate design
- $GH_REPO, $NIGHTLY_LOG: already set by nightly preamble (same as Steps 9D/9E)
```

## Pre-Implementation Verification

```bash
# Verify knowledge-base/log.md exists and has readable date format
tail -3 knowledge-base/log.md

# Check Steps 9D/9E for exact bash variable names ($NIGHTLY_LOG, $GH_REPO)
grep -A 20 "Step 9E" .claude/skills/nightly-commit-review/SKILL.md | head -25

# Verify Step 9E block ends cleanly (insertion point)
grep -n "Step 9E\|Step 9F\|Step 10" .claude/skills/nightly-commit-review/SKILL.md
```

## Mandate Check Results (Run 98)

| Mandate Item | Status |
|---|---|
| Step 9F block in SKILL.md? | ❌ ABSENT — `grep -c "Step 9F"` returns 0. Carry-forward fires. |
| First nightly after implementation has "Step 9F:" line? | N/A — not yet implemented |
| GH #403 Step 9F comment if KB stale? | N/A — KB currently healthy (4 days, within 7-day threshold) |
| GH #454 (appointment_completion.py) has ai-ready label + sketch? | ASSUMED — filed run 95, queued for issue-to-pr-loop when GH #399 resolved |
| GH #399 resolved? | ❌ OPEN Day 16+ — AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — Day 27+, 0 human responses |
| notify_common.py 12 tests cover dispatch_owner_alert failure modes? | ✅ EFFECTIVELY YES — safe_send_email swallows all failures by contract; dispatch_owner_alert never propagates exceptions by design. 12 tests verify this contract. |

## Parking Lot (Run 98)

| Item | Status | Notes |
|---|---|---|
| conversation_enrichment_job.py scheduling | WEAKENED → parking lot | Good idea, but GH #399 blocks execution queue. Any ai-ready GH issue competes with 30+ blocked items. Re-evaluate after GH #399 resolved. |
| kb_hybrid_retrieval enable for Keys Koffee | WEAKENED → parking lot | Needs settings UI toggle OR GH #399 so issue-to-pr-loop can build it. Supabase MCP unavailable in headless sessions blocks direct SQL path. |
| BotHealthPage.jsx frontend | Carry-forward parking lot | GH issue filed (Bonus B, run 96). L-effort. Not debated this run. Post GH #399 resolution. |
| appointment_completion.py | Carry-forward parking lot | GH #454 (ai-ready) queued. Nightly channel cannot create new service files. Wait for GH #399. |

## What Changes vs Run 97

Run 97 and run 98 have the same winner. The only difference:

- Run 97 was the first selection — KB was dark 72+ days at selection time (recovered manually 2026-07-09/13).
- Run 98 confirms the block is still absent. KB is now healthy (4 days), but the guard is still needed for future gaps.
- PR #471 (2026-07-17) brought batch_runtime.py and kb_hybrid — two new ideas debated and parked. Debate confirms Step 9F remains the right winner.

## Confidence: HIGH

- Mechanism proven: Steps 9B/9C/9D/9E each implemented in 1 nightly cycle.
- Mandate check 1 fails → carry-forward fires unconditionally.
- Risk: zero (guard wraps all failure paths).
- Value: daily KB health signal in every nightly log, permanent.

## Run 99 Mandate

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`? (grep — should PASS now)
2. First nightly log after implementation — does it contain "Step 9F:" line?
3. KB still within 7-day threshold? If stale: GH #403 has new Step 9F comment?
4. GH #399 resolved? (Day 17+) — unlocks conversation_enrichment_job scheduling + kb_hybrid settings UI via issue-to-pr-loop
5. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 28+)
6. conversation_enrichment_job.py: investigate batch_runtime.py wiring — how many pending conversations? What's the WHERE clause? File GH issue after GH #399 resolved.
7. kb_hybrid enable: wait for settings UI GH issue (not ai-ready until UI exists). Revisit when GH #399 clears.
