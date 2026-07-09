# Morning Digest — 2026-07-06

Generated: 2026-07-06 (automated routine)

---

## Commits (last 24h)

- `19682fc` subconscious: run 80 (2026-07-06) — add Step 9C to nightly SKILL.md for brain connector health check

**1 commit. Low velocity day.**

---

## Issues (opened/updated since 2026-07-05)

- **#394** OPEN `human-action-required` — Fix brain-refresh[bot] credentials — GitHub 403 + SUPABASE_ACCESS_TOKEN missing _(opened 2026-07-05, subconscious run 79)_
- **#393** OPEN `human-action-required` `P0` — CRITICAL: ops/monitoring/healthz-alert.sh missing — 3rd consecutive miss, mandate chain closed _(opened 2026-07-05)_
- **#392** OPEN `nightly-review` `medium-risk` `ops` — Brain refresh connectors failing 4+ consecutive days _(opened 2026-07-05, nightly bot)_

**3 issues. All require human action. Nothing automated can close these.**

---

## Open PRs Needing Action

| # | Title | Age | Status |
|---|-------|-----|--------|
| #387 | brain: sync Maps to 2026-07-01 reality + fix landing-page-v2 widget drift | ~5 days | Awaiting review/merge |

- **#387** resolves widget byte-identical invariant violation (`landing-page-v2` drift, Check 13 was FAIL+BLOCK). Autonomous loop couldn't touch it — `landing-page-v2/` on forbidden paths list. Fix is in — needs merge.

---

## Subconscious (last 2 runs)

**Run 80 (today, 2026-07-06):**
- Winner: Add Step 9C to `nightly-commit-review` SKILL.md — automated brain connector failure detection
- Status: AUTONOMOUS-EXECUTED (`19682fc`)
- Effect: Future nightly runs detect 3+ consecutive connector failures → auto-create GH issue (deduplicated by `brain-connector-failure` label)

**Run 79 (yesterday, 2026-07-05):**
- Winner: Fix brain connector credentials (GitHub 403 + SUPABASE_ACCESS_TOKEN missing)
- Status: PENDING HUMAN — GH #394 open, credential rotation required
- Also executed: Step 9B added to nightly SKILL.md; P0 GH #393 filed (mandate chain closed for healthz-alert.sh)

---

## Top 3 Priorities Today

### 1. FIX BRAIN CONNECTOR CREDENTIALS (7 min) — GH #394
**Blocker.** Brain has been stale 6 days (Jul 1–6). All autonomous agents running on degraded context.
- Rotate GitHub PAT: Settings → Developer settings → PATs → new token (`repo` + `issues` read) → update Railway Variable
- Set `SUPABASE_ACCESS_TOKEN`: Supabase → Project Settings → API → service_role key → Railway Variable
- Verify: `python brain/_tools/refresh_connectors.py` → `tail -5 brain/INGESTION-LOG.md`

### 2. SET SLACK_ALERT_WEBHOOK_URL IN RAILWAY — GH #393
**2 min.** `ops/monitoring/healthz-alert.sh` will be auto-written by nightly Step 9B but webhook URL is human-only config. Without it, health alerts fire silently.
- Railway → Project → Variables → add `SLACK_ALERT_WEBHOOK_URL = <your webhook>`
- Script content reference: `subconscious/runs/2026-07-03/winning-concept.md §Script Content`

### 3. MERGE PR #387
**~5 days old.** Brain Maps synced to 2026-07-01 + widget drift fix. Widget byte-identical invariant restored. `scripts/check_project_invariants.py` green (Check 13 was blocking). No reason to hold.

---

## Status Snapshot

| System | Status |
|--------|--------|
| Brain connectors | FAILING — 6 consecutive days |
| ops/monitoring/healthz-alert.sh | MISSING (nightly Step 9B will write it) |
| SLACK_ALERT_WEBHOOK_URL | NOT SET |
| Widget byte-identical invariant | FIXED (PR #387 ready to merge) |
| Subconscious | HEALTHY — run 80 executed today |
| Nightly commit review | HEALTHY — runs nightly |
| KB autopopulate | DEGRADED — last log entry 2026-05-05 |

---

_Next digest: 2026-07-07. Brain connector fix closes 3 issues + unblocks autonomous agent context quality._
