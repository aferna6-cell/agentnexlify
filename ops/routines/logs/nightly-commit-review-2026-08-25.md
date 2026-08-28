# Nightly Commit Review — 2026-08-25

**Run time:** 2026-08-25 UTC (scheduled 2:37 AM)
**Commits in last 24h:** 10

---

## Commits Reviewed

| SHA | Title | Risk |
|-----|-------|------|
| `3875310` | subconscious: run #109 — Step 9J Dependabot auto-merge (#674) | LOW |
| `ed1553f` | ops: morning-digest 2026-08-20 (#671) | LOW |
| `ecb6653` | ops: morning-digest 2026-08-21 (#673) | LOW |
| `1c49ac5` | ops: morning-digest 2026-08-24 (#676) | LOW |
| `6fe6efc` | kb: drift sweep 2026-08-24 (#681) | LOW |
| `4c45e67` | fix(ci): unschedule the remaining 11 workflows (#682) | LOW |
| `334d32c` | fix(ci): unschedule replaced workflows, close the local-gate gaps (#680) | LOW |
| `decc1e9` | fix(agents): stop confirming appointments that do not exist (#678) | MEDIUM |
| `08e9178` | Managed-agents audit + fixes for all 7 findings (#677) | MEDIUM |
| `9709afe` | chore: weekly skill discovery report 2026-08-24 | LOW |

---

## Findings

### Fixed Autonomously (0)
No low-risk bugs found requiring autonomous fix. All commits were clean fixes or operational/docs additions.

### Issues Opened (1)
- **[OPERATIONAL] #684** — Brain connector 33 days stale (last run 2026-07-23, threshold 14 days). Needs SUPABASE_ACCESS_TOKEN + GitHub PAT rotation.

### Existing Issues Updated (1)
- **#403** — KB autopopulate staleness comment added (33 days since last run, threshold 7 days).

### Already-Tracked Issues (skip)
- **Step 9I (block_demo_role sweep):** 10 routers flagged as missing `block_demo_role`. All covered under existing class-wide tracker GH #669 ("[security] Class-wide: 95 routers missing Depends(block_demo_role)"). No new issues filed.

---

## Health Checks

### Step 9A — Moratorium Status
`moratorium_active: false` → no escalation needed.
1 pending_approval item (god-class-splitter on email_sequences.py, since 2026-05-30) — below N>3 threshold, moratorium inactive.

### Step 9B — Healthz Monitor
`ops/monitoring/healthz-alert.sh` EXISTS — monitoring active.

### Step 9C — Brain Connector Health
Last successful run: **2026-07-23** (33 days ago). Threshold: 14 days.
→ **WARNING:** Age gate triggered. New GH issue filed: #684.

### Step 9D — Issue-to-PR Loop Health
GH Actions dark since 2026-07-20 (GH #500) — autopilot-issue-loop.yml disabled per `fix(ci)` commits. Loop runs via Routines instead. No stalled ai-ready issues checked (Actions API unavailable).

### Step 9E — Credential Rotation
`ops/credential-rotation-schedule.md` found. No credentials approaching expiry (all < 76 days).

### Step 9F — KB Autopopulate Staleness
Last run: **2026-07-23** (33 days ago). Threshold: 7 days.
→ **STALE.** Comment added to GH #403.

### Step 9G — KB Autopopulate Self-Healing
Skipped — GH Actions dark (GH #500). Manual trigger: `bash scripts/daily/kb-autopopulate.sh`.

### Step 9I — Demo-Role Security Sweep
10 routers with mutating endpoints scanned for `block_demo_role`:
- All 10 missing: sms.py, intake_ai.py, managed_agent_runs.py, pricing_experiment.py, escalations.py, zapier.py, menu.py, embed_instructions.py, os_instructions.py, scoring_config.py
- Already tracked under GH #669 (class-wide). No new issues filed.

### Step 9J — Dependabot Auto-Merge
19 open Dependabot PRs found via `mcp__github__list_pull_requests`.

**Major-version bumps skipped (safety gate):**
- #598 — stripe 11.x → 15.x (4 major versions)
- #591 — react 18.x → 19.x
- #593 — react-dom 18.x → 19.x
- #586 — react 18.x → 19.x (demo-platform)
- #588 — @testing-library/jest-dom 6.x → 7.x
- #587 — jsdom 29.x → 30.x

**Minor/patch candidates checked:**
- #679 — eslint 10.7.0 → 10.9.0: `mergeable_state: "unknown"` → skip
- #666 — @typescript-eslint/parser 8.64.0 → 8.67.0: `mergeable_state: "unknown"` → skip

**Result:** 0 PRs merged. All minor/patch candidates have `mergeable_state: "unknown"` (CI not clean or not yet evaluated). No action taken.

---

## Commit Triage Detail

### `decc1e9` — fix(agents): stop confirming appointments that do not exist
- **Risk:** MEDIUM (business logic, customer-facing)
- **Status:** Already fixed and merged in this PR.
- **Review:** Well-executed fix. `_extract_appointment_id` correctly uses regex for UUID extraction. `_appointment_row_exists` correctly queries `appointments.tenant_id` (which maps from `AppointmentBookerInput.client_id` — correct per schema-discipline.md). Fail-closed pattern consistent with CLAUDE.md critical rules. Test rewrite is justified with documented evidence. No issues.

### `08e9178` — Managed-agents audit + fixes for all 7 findings
- **Risk:** MEDIUM (new backend services, session budgets)
- **Status:** Already fixed and merged.
- **Review:** Session budget implementation looks correct. Command injection fix in field-monitor-weekly.yml (input interpolation removed) is valid. Model ID updates to current canonical IDs per model-routing.md. Symlink fix for dead skills is infrastructure-only. No issues.

---

## Moratorium Status
Moratorium inactive — no escalation needed.

---

## Next Action
2 items need human attention:
1. **#684** — Brain connector stale 33 days. Rotate SUPABASE_ACCESS_TOKEN + GitHub PAT, re-run `brain/_tools/refresh_connectors.py`.
2. **#403** — KB autopopulate stale 33 days. Rotate ANTHROPIC_API_KEY + SUPABASE_ACCESS_TOKEN in GH Actions, or run `bash scripts/daily/kb-autopopulate.sh` manually.
