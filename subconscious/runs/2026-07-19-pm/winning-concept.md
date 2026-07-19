# Winning Concept — 2026-07-19-pm (Run 99)

## Recommendation

Add **Step 9F: KB Autopopulate Staleness Check** to `.claude/skills/nightly-commit-review/SKILL.md`.

This is a carry-forward of runs 97 and 98. **Mechanism change this run:** the delivery channel changes from "nightly autonomous" to "next interactive session, human approval." Three consecutive nightly cycles have proven the nightly mechanism cannot proactively add this block.

## Why This, Why Now

- Run 99 mandate check 1 fires: `grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md` returns 0. Block ABSENT after 3 full cycles.
- **Root cause (confirmed run 99):** Nightly adds SKILL.md blocks reactively — when it detects health issues in recent commits. Step 9F is a proactive guard. No commit-based trigger exists for it. The nightly mechanism is architecturally wrong for this task type.
- Steps 9B/9C/9D/9E were all reactive: each had a commit-detectable trigger. Step 9F does not.
- **KB last ran 2026-07-13 (6 days ago). Crosses 7-day threshold TOMORROW (2026-07-20).** Without Step 9F, this staleness event will be silent — the same class of silent gap that motivated Step 9F in the first place (72-day gap 2026-05-05 → 2026-07-09).
- PR #475 (23b1da5) confirmed: appointment_jobs.py, BotHealthPage.jsx, AttributionPage.jsx all shipped. Major parking lot items cleared. Step 9F remains the one unimplemented monitoring block.
- GH #399 OPEN Day 17+. Step 9F bypasses this blocker entirely — goes through interactive session, not issue-to-pr-loop.
- GH #413 Day 28+. Referral chain now complete (booking auto-complete live per PR #475). Separate human-action notification.

## Delivery Channel Change

| Run | Channel | Result |
|-----|---------|--------|
| 97 | Nightly autonomous (pending_autonomous) | ABSENT — proactive, no trigger |
| 98 | Nightly autonomous (carry-forward) | ABSENT — same structural reason |
| 99 | **Interactive session, human approval** | PENDING — mechanism changed |

**The nightly cannot add Step 9F.** It must be added in an interactive session where the human approves the SKILL.md edit directly.

## Implementation

**Target file:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insertion point:** After Step 9E block (line 288), before Step 10 (line 289).

**Add this block:**

```markdown
9F. (KB Autopopulate Staleness Check) Check knowledge-base/log.md for last successful run:
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
```

**Notes:**
- Guard: skips silently if KB_LOG missing or unreadable — no false positives
- GH comment: optional — failure (e.g. AUTOPILOT_GH_TOKEN expired) logged but does not block nightly
- Threshold: >7 days stale triggers comment — matches KB autopopulate design
- `$GH_REPO`, `$NIGHTLY_LOG`: already set by nightly preamble (same as Steps 9D/9E)

## Pre-Implementation Verification

Run these before editing:

```bash
# Confirm Step 9F still absent
grep -c "Step 9F" .claude/skills/nightly-commit-review/SKILL.md

# Confirm Step 9E ends at line 288, Step 10 at 289
grep -n "Step 9E\|Step 9F\|Step 10" .claude/skills/nightly-commit-review/SKILL.md

# Confirm KB log format (need first field to be YYYY-MM-DD)
tail -3 knowledge-base/log.md

# Confirm $NIGHTLY_LOG and $GH_REPO variable names
grep -A 5 "NIGHTLY_LOG\|GH_REPO" .claude/skills/nightly-commit-review/SKILL.md | head -15
```

## Mandate Check Results (Run 99)

| Mandate Item | Status |
|---|---|
| Step 9F block in SKILL.md? | ❌ ABSENT — `grep -c "Step 9F"` returns 0. Carry-forward fires (3rd time). |
| Root cause of nightly mechanism failure identified? | ✅ YES — nightly is reactive; Step 9F is proactive; no commit trigger exists |
| Delivery channel changed from nightly to interactive? | ✅ YES — this run's key change |
| First nightly after implementation has "Step 9F:" line? | N/A — not yet implemented |
| GH #403 Step 9F comment if KB stale? | N/A — KB currently at 6 days (crosses threshold 2026-07-20) |
| KB 7-day threshold crossed? | ⚠️ TOMORROW (2026-07-20) — urgency is highest it has ever been |
| appointment_completion.py shipped? | ✅ YES — PR #475, appointment_jobs.py |
| BotHealthPage.jsx shipped? | ✅ YES — PR #475 |
| AttributionPage.jsx shipped? | ✅ YES — PR #475 |
| GH #399 resolved? | ❌ OPEN Day 17+ — AUTOPILOT_GH_TOKEN expired |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — Day 28+ (notify via PushNotification) |

## Parking Lot (Run 99)

| Item | Status | Notes |
|---|---|---|
| conversation_enrichment_job.py scheduling | Parking lot | Needs Supabase MCP to check queue depth; GH #399 blocks issue-to-pr. Re-evaluate after GH #399 resolves. |
| kb_hybrid_retrieval enable for Keys Koffee | Parking lot | Needs settings UI or GH #399. |
| Step 9G (GH #399 queue depth alert) | Parking lot | Step 9F must ship first. Also has same proactive-trigger problem. |
| platform_flags.py safety registry | Parking lot | No current production risk. Re-evaluate when 3+ keys in platform_settings. |
| appointment_completion.py | ✅ SHIPPED — remove from parking lot (PR #475) |
| BotHealthPage.jsx | ✅ SHIPPED — remove from parking lot (PR #475) |
| AttributionPage | ✅ SHIPPED — remove from parking lot (PR #475) |

## What Changes vs Runs 97/98

| Aspect | Runs 97/98 | Run 99 |
|---|---|---|
| Winner idea | Step 9F | Step 9F |
| Delivery channel | Nightly autonomous | Interactive session (human approval) |
| Root cause stated? | Suspected | Confirmed (3-cycle evidence) |
| KB urgency | 4 days stale (run 97), healthy (run 98) | 6 days stale — crosses threshold TOMORROW |
| Parking lot clears | 0 | 3 (appointment_completion, BotHealth, Attribution) |

## Confidence: HIGH

- Mandate check failure is unconditional carry-forward trigger. 3rd firing.
- KB threshold crossing tomorrow is date-bound and measurable.
- Root cause confirmed by 3 data points.
- Implementation block is copy-paste ready (written in run 97).
- Delivery channel change is substantive — not the same recommendation repeated.
- Risk: zero (guard wraps all failure paths).

## Run 100 Mandate

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`? (grep — should PASS)
2. First nightly log after implementation contains "Step 9F:" line?
3. KB staleness: if >7 days, GH #403 has Step 9F comment?
4. GH #399 resolved? (Day 18+) — AUTOPILOT_GH_TOKEN rotation
5. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 29+)
6. conversation_enrichment_job.py: investigate after GH #399 resolves
7. platform_flags.py: re-evaluate when 3+ keys in platform_settings
8. kb_hybrid enable: re-evaluate when settings UI exists or GH #399 clears
