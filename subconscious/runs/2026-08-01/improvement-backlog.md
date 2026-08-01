# Improvement Backlog — Run 103 (2026-08-01)

## Active Queue (ordered by priority)

### P1 — Step 9I: GH #500 Daily Spending Limit Escalation
- **Status**: Recommended (carry-forward 1 from run 102). Direct-implement authorized for run 104 if still absent.
- **File**: `.claude/skills/nightly-commit-review/SKILL.md` — add `## Step 9I` bash block after Step 9G
- **Effort**: XS (~20 bash lines)
- **Blocker**: None — autonomous channel proven. Human approval accelerates; run 104 implements directly.
- **Impact**: Daily automated pressure on GH #500 until spending limit resolved. Resolving GH #500 unblocks CI + Step 9G + autopilot + Dependabot batch simultaneously.

### P2 — Tenant Silence Detection (GH #610)
- **Status**: Parking lot. 3 days old, architecture unclear (Supabase REST vs MCP), security design needed for anon key handling.
- **Target**: Run 105+. Requires design session before implementation.

### P3 — PR Dedup Guard Hardening
- **Status**: Parking lot. Dedup guard in SKILL.md Phase 8 works when cron reads it. Monitor one more cycle. If duplicate PR created again, promote to P1.
- **Target**: Run 105+ if another duplicate appears.

### P4 — Nightly ai-ready Issue Count
- **Status**: Parking lot. Low urgency. Promote when Step 9I and #610 are shipped.
- **Target**: Run 107+.

## Blocked (human action required)
| Issue | Age | Action needed |
|-------|-----|---------------|
| GH #399 | 23d | Rotate AUTOPILOT_GH_TOKEN in GH Actions Secrets |
| GH #536 | 11d | Provision INTEGRATIONS_ENC_KEY in Railway |
| GH #394 | 27d | Provision SUPABASE_ACCESS_TOKEN for brain-refresh[bot] |
| GH #500 | 12d+ | Increase GH Actions spending limit in org billing settings |

## Recently Implemented
- **Step 9G** (run 101, 2026-07-31): KB autopopulate self-healing trigger. In SKILL.md on `subconscious/run-2026-07-31` branch (pending merge). First fire pending PR merge.
- **Step 9F** (run 99, 2026-07-20): KB staleness alert. In SKILL.md on main. Firing correctly.
- **Autonomy sweeper** (8e78f5b, 2026-07-28): Crash recovery for stranded autonomy runs. 422 tests green.
