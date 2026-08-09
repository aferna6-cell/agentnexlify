# Improvement Backlog — 2026-08-09 (Run 102)

## Active
- **Step 9H: KB Autopopulate Outcome Monitor** — Add bash block to nightly SKILL.md after Step 9G: check whether kb-autopopulate.yml actually succeeded on the run after Step 9G triggered; comment on GH #403 with secrets diagnostic if failed.

## Parking Lot (survived debate but not chosen)
- **response_score.py plan gate** — `backend/services/response_score.py` calls Claude 2x per request with no ai_usage_guard check. Add gate matching the pattern in `daily_focus.py`. Human-reviewed PR required; different channel from autonomous SKILL.md path. Evidence strong; defer to human PR review.
- **Typed KB notes discovery banner** — Add freshness banner to `KnowledgeSourcesPage.jsx` showing article count + last-compiled date with color-coded staleness indicator. Customer-visible KB health. Carry forward from run 101 parking lot.
- **Nexlify Score token-burn guard + nightly Step 5 scan** — Add response_score.py to nightly Step 5 pattern list. Preventive: makes future AI-call additions auto-flagged rather than one-off discoveries. Pairs with response_score plan gate above.
- **Grandfathered plan gate audit** — Audit `backend/services/ai_usage_guard.py` for grandfathered plan handling (`growth`, `autopilot`, `professional`, `enterprise`). Verify they fall through to correct token baselines. Carry forward from run 101 parking lot.

## Rejected This Run
- **Close superseded subconscious PRs** — Valid ops hygiene but human action required; already flagged in morning-digest-2026-08-07. Not autonomous-executable. Demoted to parking lot note: PRs #606, #611, #613 likely carry superseded Step 9G iterations; #625/#626 are canonical.

## Questions for Next Run
1. Did Step 9H fire? Check `ops/routines/logs/nightly-commit-review-2026-08-10.md` for "Step 9H:" entries.
2. Did kb-autopopulate.yml conclude as success/failure/in_progress? Which secrets are missing?
3. Is `knowledge-base/INDEX.md` still showing "Last compiled: 2026-07-23" or has a fresh compile landed?
4. Has GH #403 received a Step 9H comment with a secrets diagnostic?
5. Has response_score.py accrued chatbot-plan usage? Check tenant-level AI token usage for chatbot plan tenants.
6. Are any of the open subconscious PRs (#606, #611, #613, #625, #626) now merged or closed?
