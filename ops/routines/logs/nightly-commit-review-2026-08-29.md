# Nightly Review — 2026-08-29

## Commits reviewed (24h)

| SHA | Message | Files | Risk |
|-----|---------|-------|------|
| b092227 | ops: morning-digest 2026-08-28 | ops/routines/logs/morning-digest-2026-08-28.md (+105) | LOW |
| d36fc91 | subconscious: run 2026-08-28 — Fix Step 9J rebase trigger | subconscious state files (+372) | LOW |
| 08c3eb4 | ops: nightly-commit-review 2026-08-28 | ops/routines/logs/nightly-commit-review-2026-08-28.md (+92) | LOW |

All 3 commits are ops/internal-state only. Zero production code changed.

## Findings

### Fixed autonomously (0)
None. No bugs in production code paths.

### Issues opened (0)
No new issues. All known problems already tracked in open GH issues.

### Skipped
- 3 commits touching ops/internal paths only — no bug candidates

---

## Extended Checks

### Step 9B — Healthz Monitor
`ops/monitoring/healthz-alert.sh` EXISTS — monitoring active. SKIP.

### Step 9C — Brain Connector Health
- Last successful run: **2026-07-23T14:38Z** (via CCR session MCP workaround)
- Days since last run: **37 days** (threshold: 14 days)
- Consecutive failures from log tail: **0** (last entry was success — connector hasn't run, not erroring)
- Age gate: **WARNING — 37 days stale (>14 day threshold)**
- Existing open issue: **#684** "Brain connector 33 days stale — last run 2026-07-23" (opened 2026-08-25)
- Action taken: Comment added to #684 with updated staleness count (37 days)
- Fix: Set SUPABASE_ACCESS_TOKEN in Railway Variables, rotate GitHub PAT if expired

### Step 9D — Issue-to-PR Loop Health
- Open ai-ready issues: **3**
  - #643 (22 days old) — `appointment_briefs.py` missing block_demo_role + plan gate: **STALLED** (no linked PR)
  - #660 (14 days old) — `scoring_config.py` missing block_demo_role: **STALLED** (no linked PR)
  - #669 (9 days old) — class-wide 95 routers missing block_demo_role: related PR #653 open (subconscious proposal PR, not a fix PR)
- Loop health: GH Actions workflow status unavailable in this headless env. Previous runs confirmed AUTOPILOT_GH_TOKEN expired (GH #399). Loop likely stalled.
- Step 9D: 3 ai-ready issues, 2-3 stalled (>24h, no dedicated fix PRs), loop status: UNKNOWN/STALLED

### Step 9E — Credential Rotation Tracking
- AUTOPILOT_GH_TOKEN: last rotated 2026-07-04 → 56 days since. Under 76-day threshold. OK.
- Brain connector GitHub PAT: last rotated 2026-07-04 → 56 days since. Under 76-day threshold. OK.
- SUPABASE_ACCESS_TOKEN: **unknown state** — "not yet set" in tracking file. Cannot compute days since rotation.
- Open credential-rotation issues: 0
- No issues approaching 76-day threshold. Logging SUPABASE_ACCESS_TOKEN as unknown_state only.
- Step 9E: 3 credentials checked, 0 approaching expiry (>=76 days), 1 unknown state (SUPABASE_ACCESS_TOKEN)

### Step 9F — KB Autopopulate Staleness
- Last successful run: **2026-08-26T19:28Z** (3 days ago)
- Under 7-day threshold → **PASS**
- Step 9F: KB autopopulate last run: 2026-08-26 (3 days ago) — PASS

### Step 9G — KB Self-Healing
Skipped — Step 9F PASS (staleness <= 7 days).

### Step 9I — Demo-Role Security Sweep
- Files with mutating routes (POST/PUT/DELETE/PATCH), excluding known exceptions: 30+
- Files WITH block_demo_role: `phone.py`, `billing_addons.py`, `billing_usage.py`, `billing.py`, `auth_billing.py`, `auth_demo.py`, `account_deletion.py` (7 files)
- Class-wide issue **#669** (opened 2026-08-20) already tracks "95 routers missing block_demo_role." Open, 9 days old, ai-ready label.
- No new untracked violations found. #669 is the canonical tracking issue.
- Step 9I: 30+ files scanned, violations tracked by #669, 0 new issues filed (all already tracked)

### Step 9J — Dependabot Auto-Merge
- Open Dependabot PRs: 10+ (#679, #666, #631, #630, #629, #598, #597, #596, #595, #594, ...)
- Previous nightly (2026-08-28): 3 PRs checked, all `mergeable_state: unknown`, 0 merged
- Per current SKILL.md: `unknown` state → skip (no rebase trigger logic yet)
- Run 110 winning concept recommends adding `@dependabot rebase` trigger for unknown state PRs
- Carry-forward mandate (run 111 = today): implementation sketch in `subconscious/runs/2026-08-28/winning-concept.md`
- Status: **RECOMMENDATION — not yet autonomous-executed** (SKILL.md LOW conditions don't cover EXISTING SKILL.md edits)
- Step 9J: 0 Dependabot PRs merged this run (all in unknown/stale state, no rebase trigger in current SKILL.md)

### Moratorium Status
`moratorium_active: false` — moratorium inactive. No escalation needed.

---

## Run 110 Carry-Forward Mandate (run 111 = today)

Run 110 winning concept: **Fix Step 9J — add `@dependabot rebase` trigger for `mergeable_state: unknown` PRs**
- Status in governance.json: `recommendation`, `autonomous_executable: true`
- Escalation: "Autonomous-executable if not approved by run 111 (1st carry-forward mandate)"
- Implementation sketch: `.claude/skills/nightly-commit-review/SKILL.md` Step 9J edit (10-15 lines)
- Nightly determination: SKILL.md LOW conditions authorize NEW SKILL.md creation, not editing existing ones. Conservative path taken — not auto-executed.
- **Human action recommended**: Review `subconscious/runs/2026-08-28/winning-concept.md` and approve/execute via `/moratorium-sprint` or direct edit.

---

## Next action
3 open items for human:
1. **#684 (brain connector 37d stale)** — set SUPABASE_ACCESS_TOKEN in Railway
2. **#643, #660 stalled ai-ready issues** — AUTOPILOT_GH_TOKEN rotation (#399) unblocks loop
3. **Run 110 carry-forward** — review winning concept and execute Step 9J rebase trigger edit
