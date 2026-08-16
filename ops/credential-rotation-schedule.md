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

### SUPABASE_ACCESS_TOKEN — Action Required
- Last rotated: unknown — confirm in Supabase dashboard (Settings → API → Personal Access Tokens or Service Role Key)
- Likely a personal access token or service role key tied to the Supabase project
- Required for: brain connector (GH #394), KB autopopulate GH Action (GH #403), nightly Supabase MCP sessions
- If brain connector ran until 2026-07-23 with this token, it was valid then — assume still valid but untracked
- Human action: log the rotation date in the table above after confirming in Supabase dashboard
- Alert threshold: 76 days (14-day warning before 90-day expiry) — Step 9E cannot alert until last_rotated date is filled in
