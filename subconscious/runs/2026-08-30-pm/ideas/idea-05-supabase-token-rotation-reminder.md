# Idea 05 — SUPABASE_ACCESS_TOKEN Railway Setup Reminder

## Category
operational

## Summary
SUPABASE_ACCESS_TOKEN has been missing from Railway for 38+ days (threshold: 14 days), blocking the brain connector and Step 9E credential rotation tracking. Post setup instructions to GH #684 if not already posted.

## Evidence
- nightly-commit-review-2026-08-30.md: brain connector 38 days stale, commented #684
- Run 113 memory: GH #684 comment posted (ID: 5465159836) on 2026-08-24
- Run 113 mandate: "GH #684 SUPABASE_ACCESS_TOKEN: set in Railway after bonus comment?" — FAIL
- Comment was posted in run 112 — token still not set by run 113 nightly check
- Step 9E cannot track 90-day rotation without this token

## Status
Comment already posted by run 112 (ID: 5465159836). No new action needed from subconscious loop — issue is human action required (set token in Railway dashboard).

## Recommendation
None (already actioned). Track in run summary as blocked-on-human.

## Risk
LOW (existing comment, human action required, not a subconscious task)

## Confidence
HIGH (run 112 memory confirms comment posted)
