# Ideas — Run 58 (2026-06-14-pm)

## Evidence Digest

3 days, 6 production commits, ~12,000 lines changed. Launch-readiness sprint
completed. Key findings: (1) `3234597` cleared ALL `check_project_invariants.py`
failures — widget sync, em-dash, `from __future__` — runs 55+57 both IMPLEMENTED.
(2) `billing.py` now has `15000→autopilot` and `25000→professional` — GH #181
FIXED, runs 31/32/34/51 all IMPLEMENTED. (3) Pre-commit still has Checks 1–9,
NO Check 10 (`check_project_invariants.py` wire) — 55-day pending item now
COMPLETELY UNBLOCKED for first time. (4) `integration_key_vault.py` (9f9203d)
added encryption-at-rest for OAuth tokens, `backfill_integration_encryption.py`
created but requires manual execution — existing tenant secrets may still be
plaintext. (5) 13 E2E journey tests created but "run red until demo seed created"
per commit. (6) Run 56 winner (Check 13 `from __future__` guard) SUPERSEDED —
Check 2 already guards this path.

---

### Idea 1: Wire check_project_invariants.py into pre-commit as Check 10
**Evidence:** Pre-commit has Checks 1–9, no Check 10. Run 8 winner (55+ days
pending). `3234597` cleared all 3 blockers: invariants now ALL PASS for first time
in project history. Autonomous channel delivered Check 11 (061582c, 22 lines bash)
and Check 12 (ca3ce68, 20 lines bash) — same class. check_project_invariants.py
guards 4 things NOT covered by any other check: widget sync across 3 copies, banned
column names (`client_id` discipline), retired plan names, LLM runtime wrapper usage.
Widget sync drift just caused run 57 and was fixed manually — without Check 10 the
exact same drift will recur on the next multilateral widget PR.
**Action:** Add 6-line bash Check 10 block to `scripts/hooks/pre-commit` after Check
9 that calls `python3 scripts/check_project_invariants.py`. Mark AUTONOMOUS-EXECUTABLE
in governance.json.
**Impact:** Seals the full invariant system at commit time. Prevents recurrence of
the bug classes that dominated runs 44–57 (widget sync, em-dash, `from __future__`,
column naming). Self-healing loop: any future violation is blocked before it enters
the codebase.
**Category:** code_health

---

### Idea 2: Verify integration encryption backfill execution for existing tenants
**Evidence:** `9f9203d` (2026-06-13) shipped `integration_key_vault.py` (242L),
migration 148, and `backfill_integration_encryption.py` (108L). Commit message:
"encrypt integrations secrets at rest — fixes GH #129, #131, #264." Script header:
"Reads every `integrations` row that has a plaintext `access_token` but no
`access_token_enc` yet, encrypts the plaintext." The plaintext column is left intact
pending backfill verification (Rule 8 compliance). No CI check confirms backfill ran.
`managed_agents/preflight.py` was updated in same commit — indicates live integrations
exist. If backfill not run, existing Google/Meta/Twilio/Zapier OAuth tokens are still
in plaintext despite the encrypt-at-rest PR shipping.
**Action:** Add a CI check (or cron validation) that queries `integrations` table:
if `access_token IS NOT NULL AND access_token_enc IS NULL` → warn in CI/Slack that
backfill hasn't run yet. Alternatively, add backfill execution to the deployment
runbook (`docs/dev-knowledge/schema-log.md` migration 148 entry).
**Impact:** Ensures encryption backfill doesn't get silently forgotten. Closes the
security gap for existing tenants who connected OAuth integrations before 9f9203d.
**Category:** operational / security

---

### Idea 3: Create check-widget-sync.sh + wire into pre-push hook
**Evidence:** `scripts/check-widget-sync.sh` still MISSING (run 7 winner, 55+ days).
PR #254 (Spanish translation + web push) updated `widget/` and
`frontend/public/widget/` but missed `landing-page-v2/widget/` — exactly the
scenario check-widget-sync.sh was designed to prevent. `3234597` fixed the drift
manually via `cp`. Without the guard, the next multilateral widget PR (web push
config changes, future translations) will silently drift again.
**Action:** Create `scripts/check-widget-sync.sh` (diff all 3 widget copies, FAIL
on diverge) + wire into `scripts/hooks/pre-push`.
**Impact:** Prevents widget sync drift from recurring. Provides a second gate
(pre-push) in addition to the pre-commit check that check_project_invariants.py
would provide as Check 10. Closes the oldest outstanding script gap (run 7, April 24).
**Category:** code_health

---

### Idea 4: Stabilize E2E journey demo seed — verify advisory CI and fixture path
**Evidence:** `cfdd6e3` commit message: "Runs red until tonight's demo seed creates
the fixture tenants (verified live: demo-login returns 'Demo is not set up yet')."
13 E2E tests in `e2e/journeys/` (demo-funnel, demo-vertical, approval-inbox).
`e2e.yml` workflow created (3f79d7f) as advisory/`continue-on-error: true`. E2E
journey tests depend on the demo seed fixture which may not exist in CI. Demo is
central to the launch-readiness sprint that just completed — if the demo funnel
tests are permanently red, they lose all signal value.
**Action:** Verify `e2e.yml` CI configuration correctly handles missing demo fixtures
(skip vs fail), ensure demo seed script runs before E2E in CI or the tests are
properly gated on the demo-login health check endpoint. Document fixture dependency
in `e2e/journeys/README.md`.
**Impact:** Converts 13 currently-red advisory tests into reliable signal for demo
funnel regressions. Prevents demo breakage from going undetected before customer
demos.
**Category:** operational

---

### Idea 5: AI-to-Human Handoff v1 — wire trigger into widget_chat.py
**Evidence:** Customer gaps: "AI-to-human handoff" = Critical, all industries,
Medium effort. Run 4 winner (58+ days pending, oldest active_direction). Agent OS
`os_outbound_mirror.py` (PR #188) provides SMS/email delivery layer. Recent
PRs #252/#254 shipped "SMS approval alerts" and "approve-by-text" — adjacent
infrastructure that overlaps with handoff delivery. These features confirm the
delivery pathway is production-tested. Moratorium may be exiting after governance
corrections applied this run.
**Action:** Add explicit trigger detection in `widget_chat.py`: when message
contains "speak to someone", "talk to a human", "call me", etc. → set
`lead.status='needs_follow_up'` + call `os_outbound_mirror.send_sms()` to
owner + emit `handoff_requested` to Widget.
**Impact:** Closes the Critical gap across all 7 industries. Converts lost leads
(AI can't answer complex queries) into owner-notified warm leads. Scope is ~1 day
with Agent OS delivery layer already in place.
**Category:** customer_value
