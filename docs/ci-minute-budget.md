# CI Minute Budget — keeping PR Validation runnable without topping up

**Problem (2026-06-22):** `PR Validation` (`.github/workflows/pr-check.yml`) was
failing on every PR in ~2 seconds with HTTP 404 logs. That signature means the
GitHub Actions **monthly minute quota is exhausted** — jobs die at runner
allocation, before any step runs. It is not a code failure.

## Root cause: scheduled pollers, not PR runs

The free tier for private repos is ~2,000 min/mo. Three scheduled workflows
alone were burning ~3× that:

| Workflow | Old schedule | ~min/mo | New schedule | ~min/mo |
|---|---|---|---|---|
| `public-uptime-watch` | `*/30` (48/day) | ~2,880 | `0 */2` (12/day) | ~720 |
| `autopilot-issue-loop` | hourly (24/day) | ~1,440 | `0 */4` (6/day) | ~360 |
| `railway-error-watch` | hourly (24/day) | ~1,440 | `0 */4` (6/day) | ~360 |

Net: **~5,760 → ~1,440 min/mo** on these three (≈4,320 saved), leaving headroom
under the free tier for PR validation + the daily/weekly jobs.

## Changes made (no minute top-up required)

1. **Throttled the three pollers** (above). All keep `workflow_dispatch` for an
   on-demand run, and all already had `concurrency` guards.
2. **`pr-check.yml` concurrency** — `cancel-in-progress: true` per PR, so a
   re-push cancels the prior in-flight run instead of stacking a second full run.
3. **Dependency caching** — `cache: pip` on `setup-python`, `cache: npm` on
   `setup-node` (covers root + frontend + demo-platform lockfiles). Cuts install
   time on every PR run.

## Interim validation while the current cycle's minutes are spent

This cycle's already-consumed minutes do not come back until the monthly reset.
Until then (and as a permanent fast path), validate locally with **zero Actions
minutes**:

```bash
bash scripts/ci-local.sh            # invariants + agent guard + tests + build
bash scripts/ci-local.sh --no-tests # docs/copy-only changes
bash scripts/ci-local.sh --fast     # skip the frontend build
```

`ci-local.sh` mirrors the high-signal gates from `pr-check.yml` (it pulls the
pytest allowlist live from the workflow so it can't drift). It skips only the
network-bound advisory steps (Semgrep, npm/pip audit, Vercel preview).

## Recommended next (move work off Actions entirely)

- **Uptime** → an external monitor (cron-job.org, UptimeRobot, Better Uptime).
  Polling uptime from Actions is the single most wasteful use of the quota.
- **Railway errors** → Sentry (already installed) instead of log polling.

Doing both would drop the recurring Actions footprint to roughly just
`autopilot-issue-loop` + the daily/weekly jobs.
