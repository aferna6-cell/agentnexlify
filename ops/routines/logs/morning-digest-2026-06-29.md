# Morning Digest — 2026-06-29

Generated: 2026-06-29 UTC | Caveman mode

---

## Commits (last 24h)

- `f7195cd` — subconscious: run 2026-06-29 — Fix KB autopopulate discover step
- `291819f` — ops: nightly-commit-review 2026-06-29
- `86890cb` — subconscious: run 2026-06-28-pm — SMS Compliance Dashboard (run 70 mandate: widget drift retired)

3 commits. All docs/ops/planning. Zero code shipped in last 24h.

---

## Issues Opened / Updated (24h)

- **#378** — Widget drift: landing-page-v2 out of sync (OPEN, filed by nightly 2026-06-29)
  - 6th consecutive invariant failure (since 2026-06-23)
  - Fix = 30-second `cp` command. FORBIDDEN path = human only.
  - Fix command: `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js && git add landing-page-v2/widget/ && git commit -m "fix: sync widget to landing-page-v2"`

---

## Open PRs Needing Action

| # | Title | State | Age |
|---|-------|-------|-----|
| #372 | Referral reward: $20 credit to referrer on referee's first paid invoice | Draft | 6d |
| #341 | kb: drift sweep 2026-06-22 | Draft | 7d |
| #328 | Billing: save-offer step before cancel (retention) | Draft | 11d |
| #327 | AI Workforce: upgrade prompt on 402 (not a raw error) | Draft | 11d |
| #325 | Checkout fixes: kill Stripe Link emails + dashboard redirect post-pay | Draft | 12d |
| #286 | Agent OS fail/abstain alerts + email-routed support form | Draft | 14d |
| #284 | Dependabot: python-jose >=3.5.0 | Open | 14d |
| #281 | Dependabot: @vitest/coverage-v8 4.1.9 | Open | 14d |
| #279 | Dependabot: vitest 4.1.9 | Open | 14d |
| #86 | hooks: add 4 missing post-edit checks | Draft | 65d |

**Action needed:** #372 requires migration 160 applied before merge. #286 requires Railway env vars (`AGENT_OS_ALERT_EMAIL`, `SUPPORT_FORM_EMAIL`). Dependabot PRs (#279, #281, #284) are routine — safe to merge/approve. #86 is 65 days stale — review or close.

---

## Subconscious Recommendation

**Run 71 winner (2026-06-29):** Fix KB autopopulate discover step — already committed `f7195cd`. Bug was broken for 53+ days. Two-line fix: adds `WebFetch` to allowed tools + corrects false CLAUDE.md rule in prompt. AUTONOMOUS-EXECUTED. KB should now auto-populate on next 6am/6pm cron (if cron runs in container).

**Run 70 winner (2026-06-28-pm, still pending):** SMS Compliance Dashboard — backend complete (migration 160 `sms_compliance_log` + `sms_compliance.py`). No operator UI exists. TCPA liability gap: tenants have no visibility into opt-in/opt-out rates. Human approval needed. Effort: S (~3-4 hours, backend endpoint + frontend page + tests).

---

## Knowledge Base

Last KB log entry: 2026-05-05 (55 days stale). KB autopopulate script was broken until today's fix (run 71). Next run should ingest new articles. Monitor `knowledge-base/log.md` at next 6am/6pm window.

---

## Top 3 Priorities Today

1. **Fix widget drift (#378) — 30-second human task**
   ```bash
   cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js
   python3 scripts/check_project_invariants.py
   git add landing-page-v2/widget/agentnexlify-widget.js
   git commit -m "fix: sync widget to landing-page-v2 (resolves invariant FAIL)"
   git push -u origin main
   ```
   Unblocks `check_project_invariants.py` after 6 consecutive failures.

2. **SMS Compliance Dashboard (run 70 winner)**
   - Backend: `GET /api/sms/compliance-summary` using `sms_compliance_log` (migration 160 already on main)
   - Frontend: `SMSCompliancePage.jsx` — opt-in/opt-out counts, 30d trend, recent opt-out table
   - Use `client_id` not `tenant_id` (CLAUDE.md invariant #1)
   - Invoke `/new-feature` or compound-engineering pipeline

3. **Clear draft PR backlog**
   - Merge #341 (KB drift — clean docs-only)
   - Apply migration 160 + merge #372 (referral reward — verified 18 tests pass)
   - Merge #327 (402 upgrade prompt — 16 tests pass, `npm run build` clean)
   - Merge #325 (checkout fixes — 30 tests pass)
   - Set Railway env vars + merge #286 (Agent OS alerts + support form)
   - Close or merge #86 (65-day-old hooks PR — review if still relevant)

---

## Standing Backlog (not today, awareness only)

- AI-to-Human Handoff v1 — 75+ days pending, M effort, needs human scoping
- Email sequences split — `email_sequences.py` at 1143 lines, post-moratorium
- Record Audit Dashboard — run 72 candidate (after SMS Dashboard ships)
- Dependabot PRs #279/#281/#284 — routine dep bumps, safe to merge

---

*3 commits | 10 open PRs | 1 open issue (active) | subconscious run 71 complete*
