# Idea 4 — Fix Vercel daily deploy quota exhaustion (thin evidence, likely self-resolving)

**Score:** 3.8 / 10
**Effort:** Unknown (investigation first)
**Category:** operational
**Autonomous:** NO
**Status:** KILLED in debate (insufficient evidence for systemic fix)

## Evidence

- git log entry `5b62a9b`: brain note "Vercel daily deploy quota exhausted — frontend deploys blocked ~24h"
- Single note, no repeat occurrences in recent git log
- Referral sprint PRs #368-371 shipped 4 PRs in rapid succession on 2026-06-22/23 — likely triggered quota

## Why it doesn't win

- Vercel free tier deploy quota resets daily — if this was a spike from the referral sprint burst, it self-resolved within 24h
- No evidence of recurring pattern (not in bug-patterns.md, not in ops logs)
- No atomic fix for "deploy quota" — it's either upgrade Vercel tier (product decision, not engineering task) or reduce deploy frequency (process change)
- Insufficient evidence to justify a systemic recommendation: one note vs. run 65's confirmed-failing invariants script
- Subconscious rule: evidence first. Single note ≠ pattern. If it recurs 2+ more times, promote to parking lot.

## If it recurs

Evidence threshold: 3 quota events in 7 days → promote to parking lot with:
- Assess Vercel tier vs Railway hosting decision
- Consider preview-deploy throttle via branch protections
- Check if Railway can serve frontend (already used for backend)
