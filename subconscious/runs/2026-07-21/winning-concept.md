# Winning Concept — 2026-07-21

## Recommendation

Add the Step 9F KB-staleness bash block directly to `scripts/daily/nightly-commit-review.sh` — the automated cron script — because SKILL.md is a guide for interactive Claude Code sessions only and the automated nightly never executes it.

## Why This, Why Now

Step 9F was implemented in run 99 by editing `.claude/skills/nightly-commit-review/SKILL.md`. The implementation was correct in concept but targeted the wrong layer: the automated nightly-commit-review cron runs `scripts/daily/nightly-commit-review.sh`, not the SKILL.md. Today's nightly log (2026-07-21, 105 lines, 45 commits reviewed) has zero "Step 9F:" text despite `knowledge-base/log.md` showing a last-run date of 2026-07-13 — 8 days stale. The KB is the competitive moat for vertical widget intelligence. At 8+ days stale, tenants on KB-backed widgets receive outdated answers. The fix is a single bash block addition to the shell script — no SKILL.md edits needed, no new infrastructure.

## Implementation Sketch

1. **Read** `scripts/daily/nightly-commit-review.sh` to confirm Step 9F bash block is absent.
2. **Add** to the script (after the existing commit-review section, before the final summary):
   ```bash
   # Step 9F: KB autopopulate staleness check
   KB_LOG="knowledge-base/log.md"
   if [ -f "$KB_LOG" ]; then
     LAST_RUN=$(grep -Eo '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$KB_LOG" | tail -1)
     TODAY=$(date +%Y-%m-%d)
     DAYS_STALE=$(( ( $(date -d "$TODAY" +%s) - $(date -d "$LAST_RUN" +%s) ) / 86400 ))
     if [ "$DAYS_STALE" -gt 7 ]; then
       echo "Step 9F: KB autopopulate stale ${DAYS_STALE} days (last: ${LAST_RUN}). Threshold: 7 days. GH #403 tracking." | tee -a "$LOG_FILE"
       # Comment on GH #403 if GITHUB_TOKEN available
       if [ -n "$GITHUB_TOKEN" ]; then
         gh issue comment 403 --body "Step 9F alert: KB autopopulate last ran ${LAST_RUN} (${DAYS_STALE} days ago). Threshold exceeded. Manual trigger: \`bash scripts/daily/kb-autopopulate.sh\`." 2>/dev/null || true
       fi
     else
       echo "Step 9F: KB autopopulate OK — last ran ${LAST_RUN} (${DAYS_STALE} days ago)." | tee -a "$LOG_FILE"
     fi
   else
     echo "Step 9F: ${KB_LOG} not found — cannot check KB staleness." | tee -a "$LOG_FILE"
   fi
   ```
3. **Verify** by running `bash scripts/daily/nightly-commit-review.sh --dry-run` (or equivalent) and confirming "Step 9F:" appears in output.
4. **No SKILL.md edits needed** — Step 9F already documented there. The shell script is the gap.
5. **Commit** as `fix(nightly): add Step 9F KB staleness check to automated daily script [skip ci]`.

## What This Replaces

Previous active direction was run 100 winner (Wire mcp_client.py into agent execution path). That recommendation is on PR #537 pending human approval. This run's winner is independent — a monitoring gap that exists regardless of the mcp_client.py status.

## Confidence

**HIGH** — Evidence is confirmatory (nightly log exhaustive, Step 9F absent, KB last run 8 days ago). Fix is a single well-scoped shell script addition with no schema changes, no dependency changes, and an existing GH issue (#403) to comment on. Implementation risk: near zero. The SKILL.md/bash-script layer confusion is the exact root cause, and this fix closes it.
