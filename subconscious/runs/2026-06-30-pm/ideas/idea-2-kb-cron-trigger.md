# Idea 2 — KB Autopopulate Cron Diagnostic + Manual Trigger

**Category:** Operational
**Effort:** XS (15 min — one bash command + one commit)
**Moratorium impact:** AUTONOMOUS-EXECUTABLE (no human approval needed)
**Evidence:**

- `knowledge-base/log.md` last entry: 2026-05-05 (56 days stale)
- Commit 65284cc landed the fix to `scripts/daily/kb-autopopulate.sh`
- Cloud container environment: cron not firing (confirmed via log staleness)
- Morning digest shows knowledge-base listed in health checks but no output since May

## Root Cause Hypothesis

Cloud container likely does not have a system cron daemon running. The `scripts/daily/kb-autopopulate.sh` is designed to be run by cron at 6 AM + 6 PM, but:
1. Container may use a process supervisor (supervisord, s6, etc.) without crond
2. Or crontab was never installed in the container's session

## Proposed Action

1. **Verify**: `crontab -l` — check if the cron job is registered
2. **If missing**: `crontab -e` to add `0 6,18 * * * bash /home/user/agentnexlify/scripts/daily/kb-autopopulate.sh`
3. **Immediate**: run `bash scripts/daily/kb-autopopulate.sh` manually to restore 56-day gap
4. **Document**: add note to `ops/CONTEXT.md` that cloud containers need cron registration at session start

## Why This Is AUTONOMOUS-EXECUTABLE

- Additive only (adds cron entry + runs a script)
- No schema changes, no code changes
- Script already exists and was already approved (65284cc)
- Risk: none (worst case the script fails silently, already the current state)

## Confidence: MEDIUM (cron hypothesis; diagnose first)
