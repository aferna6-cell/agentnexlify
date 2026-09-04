# Nightly Review — 2026-09-04

**Run time:** 2026-09-04 (automated, CCR session)
**Branch:** main (HEAD after rebase)
**Commits reviewed:** 16 (last 24h, no merges)

---

## Commits reviewed

| SHA | Summary | Risk |
|-----|---------|------|
| `105a3c0` | fix(m9): durable bakeoff harness + planner completeness rules | MEDIUM |
| `9589c26` | Website/Chatbot Connect v1 — verify live widget before "connected" (#772) | MEDIUM |
| `ae81e5f` | test(billing): Agent OS invoicing E2E proof (PR3) (#771) | LOW |
| `10fcd33` | feat(billing): wire Invoicing & Collections to invoice actions (#766) | MEDIUM |
| `fdcbb97` | fix(m9): M9.4 bakeoff miss classification (#773) | MEDIUM |
| `bc29de4` | fix(security): guard residual demo-write routes (#776) | MEDIUM (positive fix) |
| `ffcc70e` | fix(m9): harden department scoring and Action registry manifest parity (#777) | MEDIUM |
| `f22ef04` | Billing Automation v1 — typed invoice action bridge (#765) | MEDIUM |
| `27071b5` | fix(m9): harden M9.4 bakeoff evaluation integrity (#764) | MEDIUM |
| `33eafe6` | fix(m9): terminalize exhausted-failure workflow dependency deadlocks (#763) | MEDIUM |
| `50da659` | feat(m9): M9.4 offline LLM planner bakeoff harness (#762) | MEDIUM |
| `f669390` | fix(m9): harden M9.3 planner eval before LLM bakeoff (#758) | MEDIUM |
| `f8ccd20` | chore(m9): strip trailing whitespace for diff hygiene | LOW |
| `e2b500c` | feat(m9): M9.3 frozen planner eval + deterministic validator | MEDIUM |
| `32f4ec2` | ops: morning-digest 2026-09-03 | LOW |
| `ead83ba` | ops: nightly-commit-review 2026-09-03 | LOW |

---

## Findings

### Fixed autonomously (0)
No LOW-risk bugs found for autonomous fix. No typos, dead code, or unused imports in the changed lines.

### Issues opened (1)
- **[MEDIUM] #787** — [security] website_connect.py: POST endpoints missing Depends(block_demo_role)
  - Commit: `9589c26` — two new POST routes (`/api/v1/website-connect`, `/api/v1/website-connect/verify`) use `Depends(_get_current_tenant)` not `Depends(block_demo_role)`. Demo tenants can persist website connections and trigger live HTTP fetches from the server.
  - File: `backend/routers/website_connect.py` lines 68–101

### Skipped / not acted on
- 14 MEDIUM commits: M9 planner/bakeoff eval work (staging-only), billing automation (flag-gated off), bc29de4 security fix (correct).
- `from __future__ import annotations` in `backend/services/website_connect.py` — noted but service file uses no Pydantic BaseModels; rule targets FastAPI + Pydantic 422 risk, which is not present here. Pre-existing pattern across 30+ service files.
- `widget_config.py` double-auth dependency (`_get_jwt_claims` + `block_demo_role`): belt-and-suspenders design, not a bug.
- FORBIDDEN paths not touched: migrations, auth, stripe, widget files — no autonomous action taken.

---

## Routine health checks

### Step 9A — Moratorium Status
moratorium_active: False — no escalation needed.
Pending approval: 1 item (god-class-splitter on email_sequences.py, 2026-05-30).

### Step 9C — Brain Connector Health
- Last successful run: 2026-07-23 (43 days ago). Age gate: >14 days → STALE.
- GitHub connector: OK on 2026-07-23. Supabase: skipped (SUPABASE_ACCESS_TOKEN not set).
- Action: Added comment to GH #684 with updated staleness count and fix steps.

### Step 9D — Issue-to-PR Loop Health
- 6 open ai-ready issues. #787 (just created), #760 (~1d, PR #761 exists). Stalled >24h with no PR: #643 (28d), #660 (20d), #669 (15d), #728 (3d).
- GitHub Actions dark since 2026-07-20 (GH #500) — this is by design. Loop health via GH Actions cannot be assessed. No new dormancy issue filed (known state).
- Step 9D: 6 ai-ready issues open, 4 stalled (>24h no PR), loop dark by design — PASS (expected state).

### Step 9E — Credential Rotation
- AUTOPILOT_GH_TOKEN: last rotated 2026-07-04, 62 days ago. Threshold: 76 days. NOT yet in warning window.
- Brain connector GitHub PAT: last rotated 2026-07-04, 62 days ago. NOT yet in warning window.
- SUPABASE_ACCESS_TOKEN: unknown rotation date. Flagged in ops/credential-rotation-schedule.md.
- Result: 3 credentials checked, 0 approaching expiry (>=76 days), 1 unknown state. No new issue filed.

### Step 9F — KB Autopopulate Staleness
- Last successful run: 2026-08-26 19:28 (9 days ago). Threshold: 7 days → STALE.
- Added comment to GH #403 with staleness alert and manual trigger instructions.

### Step 9G — KB Autopopulate Self-Heal
- `gh` CLI not available in CCR session. Cannot trigger workflow remotely.
- Result: Step 9G skipped — manual trigger required: `bash scripts/daily/kb-autopopulate.sh`

### Step 9I — Demo-Role Security Sweep
- Found: `backend/routers/website_connect.py` — two POST endpoints missing `block_demo_role` (commit 9589c26).
- Dedup check: no existing open issue found for this file.
- Filed GH #787 with fix pattern and affected lines.
- Result: 1 file scanned (new), 1 violation found, 1 new issue filed.

### Step 9J — Dependabot Auto-Merge
- 19 open Dependabot PRs. Checking `mergeable_state` requires per-PR API calls (rate concern).
- Most recent: #722 (eslint bump), #721 (typescript-eslint bump) — both dev deps.
- Step 9J: 19 Dependabot PRs open. Merge eligibility check deferred — requires mergeable_state per-PR read; no merges executed this run.

### Step 9K — Stale Subconscious PRs
- 1 open subconscious PR: #782 (1 day old, draft). Under threshold (30 days).
- Result: 1 subconscious PR open, 0 stale (>30d), 0 critical (>60d) — PASS.

---

## Next action

**1 issue needs human attention:** GH #787 (website_connect.py demo-role guard — small focused fix, ai-ready). Brain connector (GH #684) needs credential rotation to resume (62 days since rotation, 28 days from expiry). KB autopopulate (GH #403) needs manual trigger or GitHub Actions secret rotation.
