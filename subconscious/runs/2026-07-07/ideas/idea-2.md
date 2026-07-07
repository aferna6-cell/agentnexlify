# Idea 2: Diagnose KB Autopopulate Cloud Cron Root Cause (63 Days Degraded)

**Category:** Operational  
**Effort:** S (diagnosis + recommended fix; actual fix may be XS or human-required)  
**Autonomous:** Partially (diagnosis phase fully autonomous; fix depends on root cause)  
**Source:** New idea — not in parking lot; evidence: `knowledge-base/log.md` last entry 2026-05-05  

---

## Evidence

- `knowledge-base/log.md` last entry: **2026-05-05** (63+ days ago as of 2026-07-07)
- Fix committed 2026-06-30: `65284cc` — "fix: kb-autopopulate add WebFetch to allowedTools + correct DISCOVER_PROMPT"
- Morning digest 2026-07-01 confirmed: "KB cron status: Fix shipped but knowledge-base/log.md last entry still 2026-05-05"
- Nightly 2026-07-07: "KB autopopulate: DEGRADED — last entry 2026-05-05"

The code fix was shipped but the cron has never run successfully since. Two possibilities:
1. Cloud scheduler (Railway or GitHub Actions) never triggers the script
2. Script works locally but fails silently in cloud (missing env var, path issue)

## Impact of Continued Degradation

Every AI session — subconscious, issue-to-pr-loop, nightly-commit-review — operates on knowledge compiled from 2026-05-05. Any KB articles, competitor intel, or regulatory updates from the past 63 days are invisible to agents. SMS compliance, TCPA changes, GoHighLevel moves — all stale.

## Diagnosis Steps

1. Read `scripts/daily/kb-autopopulate.sh` — identify any hardcoded paths or env var requirements
2. Check for Railway cron config (`.railway/cron.yaml` or similar)
3. Check GitHub Actions for `.github/workflows/kb*.yml`
4. Read `knowledge-base/log.md` — confirm last entry date, inspect last error if logged
5. Identify root cause category: scheduler gap / env var / script path / code bug

## Likely Root Causes (ranked by probability)

1. **Railway scheduled task not configured** — 65284cc fixed code but never set up the scheduler trigger
2. **Missing env var in cloud** — ANTHROPIC_API_KEY or SUPABASE credentials absent in Railway cron environment
3. **Script path wrong in scheduler** — relative path works locally, breaks in cloud working directory

## Autonomous Fix (if root cause is code/config)

If root cause = missing GitHub Actions workflow → create `.github/workflows/kb-autopopulate.yml` (same class as other CI YAMLs, AUTONOMOUS-EXECUTABLE per nightly governance)

If root cause = Railway env var → escalate to human (document exact variable name + steps)

## Effort Breakdown

- Diagnosis: XS (reading scripts + config files)
- Fix (code/config path): XS-S
- Fix (human action needed): document + GH issue

## Risk

Low — diagnostic only until root cause known. Any code fix is additive (new cron trigger, not touching existing code).
