# Winning Concept — 2026-07-19 (Run 99)

## Recommendation

Add **Step 9F: KB Autopopulate Staleness Check** to `.claude/skills/nightly-commit-review/SKILL.md` via **human-session direct edit** (not autonomous nightly channel).

This is a carry-forward of runs 97 and 98 with a critical channel correction: the autonomous nightly-commit-review channel cannot add Step 9F because it only fires on live problems, and KB is currently healthy. Human must paste the block directly.

## Why This, Why Now

- Run 97 selected Step 9F as winner. Run 98 confirmed ABSENT (1st miss). Run 99 confirms ABSENT (2nd consecutive miss after 98, 3rd cycle total).
- **Root cause identified this run:** Steps 9B-9E each triggered when nightly found an *active* problem (brain connector DOWN, loop stalled, credential overdue). KB last ran 2026-07-13 (6 days, within 7-day threshold) — no live staleness trigger fires. The autonomous nightly channel CANNOT add Step 9F while KB is healthy.
- **Channel pivot:** Prior winning-concepts assumed "nightly will add it via SKILL.md-edit channel." This run proves that assumption wrong. Human must paste the block. This IS the new insight distinguishing run 99 from runs 97-98.
- Three governance cycles of failure warrant changing the execution channel, not waiting for a 4th miss.
- Value unchanged: every nightly log gets "Step 9F: KB autopopulate last run: YYYY-MM-DD (N days ago)" — permanent observability. GH #403 gets automated comment when KB goes >7 days without a run.

## Implementation

**Target file:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insertion point:** After Step 9E block (confirmed at lines 265-288 of SKILL.md). Insert immediately after the closing `fi` of Step 9E.

**Block to insert:**

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
# Confirm insertion point (Step 9E ends, Step 9F and Step 10 absent)
grep -n "Step 9E\|Step 9F\|Step 10" .claude/skills/nightly-commit-review/SKILL.md

# Verify knowledge-base/log.md exists and has readable date format
tail -3 knowledge-base/log.md

# Confirm Step 9F absent
grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md
# Expected: 0
```

## Mandate Check Results (Run 99)

| Mandate Item | Status |
|---|---|
| Step 9F block in SKILL.md? | ❌ ABSENT — 3rd consecutive cycle. Carry-forward fires. Channel pivot required. |
| First nightly after implementation has "Step 9F:" line? | N/A — not yet implemented |
| GH #403 Step 9F comment if KB stale? | N/A — KB healthy (6 days, within 7-day threshold) |
| GH #399 resolved? | ❌ OPEN Day 18+ — AUTOPILOT_GH_TOKEN expired, 30 ai-ready issues blocked |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — Day 29+, 7 comments, 0 human responses |
| conversation_enrichment_job scheduling? | ❌ NOT SCHEDULED — batch_runtime.py shipped but job runs nowhere. File GH issue after verifying WHERE clause + rate controls. Tracked as supporting recommendation. |
| kb_hybrid enable? | ❌ PENDING — mechanism now available via platform_flags. Needs human session with Supabase MCP. |

## Governance Corrections (Run 99)

Three active_directions items confirmed IMPLEMENTED by PR #475 (2026-07-19) and should be moved to completed:
1. **appointment_completion.py** — NOW `appointment_jobs.py` in `backend/services/automation/scheduled/`. `auto_complete_past_appointments()` wired into `scheduled_jobs.py` (lines 34, 62). GH #454 CLOSED.
2. **BotHealthPage.jsx** — Implemented in `frontend/src/pages/BotHealthPage.jsx`. GH #465 CLOSED.
3. **AttributionPage.jsx / Lead Source Analytics** — Implemented in `frontend/src/pages/AttributionPage.jsx`. GH #453 CLOSED.

## Supporting Recommendations (Backlog)

1. **conversation_enrichment_job scheduling** — Read implementation first (WHERE clause, rate controls, idempotency), then add to scheduled_jobs.py. File GH issue with implementation review notes. Mandate item 6.
2. **GH #413 final escalation** — Post comment on GH #413 with new framing: appointment auto-complete is now live (PR #475). First completed appointments are imminent. Setting REFERRAL_REWARD_ENABLED=1 before first completion bundles referral reward with first review request — highest leverage moment. Day 29+, 7 comments, 0 human responses.
3. **kb_hybrid enable for Keys Koffee** — Insert row `(tenant_id, 'kb_hybrid_enabled', '1')` into `platform_settings` via Supabase MCP in human-interactive session. PR #476 provides the mechanism. No code deployment needed.

## Parking Lot (Run 99)

| Item | Status | Notes |
|---|---|---|
| platform_flags ALLOWED_TOGGLE_KEYS guard | PARKING LOT | 0 present-risk rows; nightly said "no action required"; guard has maintenance cost. Revisit after first misconfigured row incident. |
| conversation_enrichment_job scheduling | Supporting recommendation | See above; needs read-before-schedule gate. Not the top winner. |
| BotHealthPage.jsx | ✅ IMPLEMENTED | PR #475. Remove from active_directions. |
| appointment_completion.py | ✅ IMPLEMENTED | PR #475 as appointment_jobs.py. Remove from active_directions. |
| AttributionPage.jsx | ✅ IMPLEMENTED | PR #475. Remove from active_directions. |

## Confidence: HIGH

- 3 consecutive mandate failures force carry-forward unconditionally.
- Root cause of channel failure identified for first time this run (KB healthy = no nightly trigger).
- Channel pivot (human session) resolves the stall.
- Implementation: exact block exists in winning-concept.md (run 97). Zero design work. Paste operation.
- Risk: zero (guards wrap all failure paths).
- Value: daily KB health signal in every nightly log, permanent.

## Run 100 Mandate

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`? (grep — MUST PASS)
2. First nightly log after implementation — does it contain "Step 9F:" line?
3. KB still within 7-day threshold? If stale: GH #403 has new Step 9F comment?
4. GH #399 resolved? (Day 18+ at time of this run) — unlocks issue-to-pr-loop for 30 queued ai-ready issues
5. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 29+) — final escalation comment sent?
6. conversation_enrichment_job.py: GH issue filed after reviewing WHERE clause + rate controls?
7. kb_hybrid enable for Keys Koffee: platform_settings row inserted?
