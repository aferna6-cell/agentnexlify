# Credential Rotation Schedule

| Secret | Used by | Last rotated | Interval | Next due |
|--------|---------|-------------|----------|---------|
| AUTOPILOT_GH_TOKEN | autopilot-issue-loop.yml (GitHub Actions → GitHub Secrets: aferna6-cell/agentnexlify) | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| Brain connector GitHub PAT | brain/_tools/refresh_connectors.py (local cron + Railway) | 2026-07-04 (estimated — expired this date) | 90 days | 2026-10-02 |
| SUPABASE_ACCESS_TOKEN | brain/_tools/refresh_connectors.py (Railway cron env) | unknown — not yet set in environment | 90 days | set first, then track |

## How to update this file
After rotating any credential:
1. Set new token in environment (Railway Variables / GitHub Secrets)
2. Update "Last rotated" date in this table
3. Update "Next due" = last_rotated + 90 days
4. Commit: `git commit -m "ops: rotate [credential name] (90-day cycle)"`

## Notes
- AUTOPILOT_GH_TOKEN: set in GitHub Secrets under repo aferna6-cell/agentnexlify. GH #399 tracks rotation.
- Brain connector PAT: set in Railway Variables (or local cron env). GH #394 tracks rotation.
- SUPABASE_ACCESS_TOKEN: set in Railway Variables for brain connector. Voyage API key also required.
- Step 9E in .claude/skills/nightly-commit-review/SKILL.md reads this file nightly.
  Files a GH issue if any credential is >=76 days since last rotation (14-day warning before 90-day expiry).
