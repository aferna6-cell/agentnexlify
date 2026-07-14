# Improvement Backlog — Run 87 (2026-07-10-pm)

Items considered this run but not selected as winner. Ranked by potential next-run priority.

---

## Parking Lot (active candidates)

### P1 — Referral Reward Pre-Gate Diagnostic
**Category:** operational
**Effort:** XS
**Blocked by:** credential crisis (GH #399/#403) makes automation pipeline unreliable for additional checks
**Resume condition:** AUTOPILOT_GH_TOKEN rotated (GH #399 resolved) + ANTHROPIC_API_KEY set in GitHub Actions (GH #403 resolved)
**Action:** Add nightly diagnostic: read `migrations/` to confirm migration 162 exists; log REFERRAL_REWARD_ENABLED env var value; surface "ready to flip" signal when both conditions confirmed.
**Source:** Run 87 Idea 3 (weakened → parking lot)
**Run 88 candidate:** YES — if GH #399/#403 resolved by then

---

### P2 — ANTHROPIC_API_KEY Blockage Escalation  
**Category:** operational
**Effort:** XS
**Context:** GH #403 CRITICAL — ANTHROPIC_API_KEY not set in GitHub Actions blocks KB autopopulate + autopilot. Present in morning digest priority list 5+ days. All autonomous AI-powered workflows dead without it.
**Action:** Add Step 9F to nightly: detect whether GH Actions workflows depending on ANTHROPIC_API_KEY had any successful run in last 7 days. If not, comment on GH #403 with escalating urgency (Day 1: note, Day 3: HIGH, Day 7: CRITICAL with full manual procedure embedded).
**Source:** Run 87 Idea 5
**Run 88 candidate:** YES — escalating urgency supports this

---

### P3 — landing-page-v2 Widget Retirement Decision
**Category:** code_health
**Effort:** XS
**Context:** GH #408 MEDIUM — `8b1e44b` fixed widget drift in `landing-page-v2/widget/`. CLAUDE.md confirms `landing-page-v2/` is legacy do-not-touch. Two options exist: delete the file or document as intentional exception. Nightly has flagged this for multiple runs.
**Action:** File a decision request on GH #408 with exact options: A) delete `landing-page-v2/widget/agentnexlify-widget.js` or B) add `<!-- drift-ok -->` comment in `check_project_invariants.py` to exclude it.
**Source:** Run 87 Idea 4
**Run 88 candidate:** MAYBE — low urgency; no revenue impact

---

## Killed Ideas (do not revisit)

### KILLED — Draft PR Triage
**Reason:** Root cause is automation outage (GH #399/#403), not PR management process. Once autopilot is fixed, most draft PRs will be handled by issue-to-pr-loop. Triage would create noise without resolving the underlying block. Human attention better spent on credential rotation.
**Exception:** PR #325 (checkout conversion fix, 18+ days old) predates the automation outage and should be merged by human directly.
**Source:** Run 87 Idea 2

---

## Carry-Forward from Prior Runs

### Brain Connector Credentials (run 79 winner)
**Status:** pending_human
**Action:** Rotate GitHub token with repo/issues read scope + set SUPABASE_ACCESS_TOKEN in cron environment. ~7 min.
**Note:** Still unresolved. Step 9C provides detection; fix is human-only.

### SMS Compliance Dashboard (run 73/74 winner)
**Status:** pending_autonomous (GH #385 has ai-ready label)
**Note:** Issue-to-pr-loop should pick up #385 once AUTOPILOT_GH_TOKEN is rotated (GH #399). Blocked by credential crisis.
