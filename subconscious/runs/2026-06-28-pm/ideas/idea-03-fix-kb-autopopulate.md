# Idea 03 — Fix KB Autopopulate

**Category:** Operational  
**Effort:** S-M (debug + fix broken script, ~1-3 hours depending on failure)  
**Confidence:** MEDIUM  
**KB last compiled:** 2026-05-05 (53 days stale)

---

## The Gap

`scripts/daily/kb-autopopulate.sh` runs twice daily (6 AM + 6 PM via cron) and is broken since approximately run 53 (2026-06-09-pm).

`knowledge-base/INDEX.md` has 114 articles. None have been updated in 53 days. The wiki is stale for:
- New council sprint findings (TCPA, integration health)
- 2-plan repricing decisions
- Council fixes documentation
- Competitor landscape (GoHighLevel AI Employee shipped, Drillbit YC)
- New compliance rules (SMS TCPA, California SB 243)

---

## Root Cause (Unknown)

No error log investigated. Candidates:
1. Broken Python dependency (kb-autopopulate.sh calls Python compile script)
2. API key rotation (Anthropic API key may have changed)
3. Path error after directory restructuring during council sprint
4. Quota/rate limit on kb compile

Diagnosis: `bash scripts/daily/kb-autopopulate.sh --dry-run 2>&1` or check `knowledge-base/log.md`

---

## What to Build

1. Read `knowledge-base/log.md` → find last error
2. Run `npm run kb:health` → assess scope of failure
3. Fix root cause (likely 1-2 lines)
4. Add error logging to kb-autopopulate.sh (currently fails silently)
5. Run manual compile: `npm run kb:lint` → then compile
6. Add health check to nightly review: if `knowledge-base/log.md` shows failure, create GH issue

---

## Why This Is In the Running

53-day stale KB degrades AI response quality. The widget AI falls back to stale information when new knowledge exists. Council sprint fixes are not yet in the KB — tenants asking about TCPA compliance get outdated answers.

---

## Debate Considerations

SURVIVES. Valid, operational, fixable. Lower priority than SMS Compliance Dashboard because:
- No immediate legal liability (just quality degradation)
- Requires diagnosis before fix (unknown failure mode)
- S-M effort range is uncertain

Correct for parking lot as Bonus Action. Not winner when SMS Dashboard has higher evidence and defined scope.
