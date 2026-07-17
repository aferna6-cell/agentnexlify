# Winning Concept — 2026-07-17 (Run 97)

## Recommendation

Add **Step 9F: KB Autopopulate Staleness Check** to `.claude/skills/nightly-commit-review/SKILL.md`.

## Why This, Why Now

KB autopopulate has been dark 72+ days (last run: 2026-05-05). GH #403 is open tracking the issue but receives zero daily pressure — no automated signal fires on KB staleness between subconscious runs. Steps 9B, 9C, 9D, and 9E were all implemented autonomously in 1 nightly cycle each via the same SKILL.md-edit channel. Step 9F uses the same proven mechanism. The nightly-commit-review-2026-07-17.md confirmed 0 service files were created (0 bugs fixed) — SKILL.md edits remain the viable autonomous execution path.

KB feeds the AI chat system directly. Dark KB means AI answers degrade over time. 72 days dark without a daily signal = silent degradation. This SKILL.md block adds a daily health check that: (a) shows in every nightly log, (b) optionally comments on GH #403 when stale count crosses threshold, (c) creates machine-readable staleness data for future dashboards.

## Implementation Sketch

**Target file:** `.claude/skills/nightly-commit-review/SKILL.md`

**Insert after Step 9E (credential rotation schedule):**

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
- Threshold: >7 days stale triggers comment — matches KB autopopulate design (twice-daily cadence means >7 days = likely broken, not just slow)
- $GH_REPO, $NIGHTLY_LOG: already set by nightly preamble (same as Steps 9D/9E)
```

## Pre-implementation Verification

```bash
# Verify knowledge-base/log.md exists and has readable date format
tail -3 knowledge-base/log.md

# Check Steps 9D/9E for exact bash variable names ($NIGHTLY_LOG, $GH_REPO)
grep -A 20 "Step 9E" .claude/skills/nightly-commit-review/SKILL.md | head -25

# Verify Step 9E block ends cleanly (insertion point)
grep -n "Step 9E\|Step 9F\|Step 10" .claude/skills/nightly-commit-review/SKILL.md
```

## What This Replaces

Previous winner: appointment_completion.py (runs 95 + 96, carry-forward). Reason for switch: 2 consecutive nightly cycles confirmed appointment_completion.py ABSENT — root cause is nightly-commit-review is a bug-fix system, not a feature-implement system. Cannot create new service files autonomously. Correct path for appointment_completion.py: issue-to-pr-loop via GH #454 (ai-ready) when GH #399 resolved.

## Mandate Check (Run 97)

| Mandate Item | Status |
|---|---|
| appointment_completion.py committed by nightly? | ❌ ABSENT — nightly-2026-07-17: 0 fixes applied (confirmed). Root cause: mechanism mismatch — nightly is a bug-fix channel, not feature-implement. |
| Regression tests pass? | ❌ test_appointment_completion.py ABSENT |
| First real booking in AdminFunnelPage? | UNKNOWN — nightly log silent on bookings |
| GH #399 resolved? | ❌ OPEN Day 15+ — 30 ai-ready issues blocked |
| GH #413 REFERRAL_REWARD_ENABLED=1 set? | ❌ NOT SET — Day 26+, 0 human responses |
| BotHealthPage.jsx GH issue filed? | ✅ CONFIRMED — filed as Bonus B in run 96 |

## Bonus Actions (Autonomous)

**Bonus A:** Post Day-15+ escalation on GH #399 if not already posted today. Framing: "Day 15+: 30 ai-ready issues stalled. appointment_completion.py is the highest-value queued item (would unlock review requests + aftercare automations for all future bookings). Single action: Railway → Variables → rotate AUTOPILOT_GH_TOKEN."

**Bonus B:** Note in GH #413 comment: Day 26+ with 0 human responses. The referral program is 10/10 complete — REFERRAL_REWARD_ENABLED=1 is the sole remaining step. Suppress if subconscious has posted in last 7 days (escalation decay rule).

## Confidence: HIGH

Evidence direct: Steps 9B-9E implemented in 1 cycle each via same channel. KB dark 72 days confirmed in governance. nightly-2026-07-17 confirmed SKILL.md edits are viable autonomous path. Mechanism is proven, risk is zero (guard wraps all failure paths).

## Run 98 Mandate

1. Step 9F block present in `.claude/skills/nightly-commit-review/SKILL.md`?
2. First nightly run after implementation — does log contain "Step 9F:" line?
3. If KB still stale: does GH #403 have a new Step 9F comment?
4. appointment_completion.py: GH #454 verified with ai-ready label + full implementation sketch? (issue-to-pr-loop will pick up when GH #399 resolved)
5. GH #399 resolved? (Day 16+)
6. GH #413 REFERRAL_REWARD_ENABLED=1 set? (Day 27+)
7. Parking lot: notify_common.py failure-mode tests (verify 12 new tests don't already cover SPOF paths before recommending)
