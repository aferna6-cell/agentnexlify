# Candidate Ideas — Run 21 (2026-05-17)

## Context

Moratorium ACTIVE. pending=6 (runs 4, 7, 8, 14, 19, 20). Run 20 NOT implemented
(governance.json max_pending_approvals still=3, GH milestone not created, SKILL.md not updated).
Run 20 governing condition fires per its own winning-concept.md §"After Run 20 Implemented":
"Governance action: open a P0 GH issue 'Subconscious backlog unactioned 30+ days — sprint required'."
Zero production commits day 12 (since 72f8204 May 5). Run 4 now day 31.
Five consecutive governance/meta-fix recommendations (runs 18-20 + the two expected for run 21 if
following moratorium protocol) without a single implementation.

Evidence gathered:
- git log: only subconscious, nightly review, and ops commits since May 5
- check-widget-sync.sh: MISSING (day 23)
- lead-qualifier-eval.yml: MISSING (day 12)
- check_project_invariants.py: not in pre-commit (day 22)
- SKILL.md Moratorium Escalation Protocol: MISSING
- check_project_invariants.py when run: PASS all 6 checks
- widget copies: IN SYNC per nightly
- issue-to-pr-loop: no production commits from loop in last 14 days (loop not running)
- customer-gaps.md: AI-to-Human Handoff = CRITICAL, all 7 industries
- run 20 backlog: explicitly authorizes run 4 as "parallel track independent of moratorium"

---

### Idea 1: P0 GH Issue — "Moratorium deadlock: sprint required"
**Evidence:** Run 20 winning-concept.md explicitly mandates this if run 20 not implemented by run 21.
12 days no production commits. Run 4 at 31 days (oldest). pending=6. GH #169 open (informational)
but P0 label + "product blocker" framing is qualitatively different.
**Action:** Create single P0 GH issue titled "Subconscious backlog unactioned 30+ days — sprint
required" with P0 label, list of 4 S-effort items (~50 min), and run 4 as parallel-track item.
**Impact:** Highest-urgency signal in GitHub. Puts moratorium status where human looks daily.
Converts abstract governance constraint to actionable sprint board entry.
**Category:** workflow

---

### Idea 2: AI-to-Human Handoff v1 — Implementation Sprint GH Issue
**Evidence:** customer-gaps.md: CRITICAL, all 7 industries. Run 4: 31 days pending (oldest item).
Infrastructure confirmed: conversations table exists, Twilio wired (SMS/voice), Resend wired (email).
Run 20 backlog explicitly states: "Sprint allocation required... parallel track independent of
moratorium." 5 consecutive meta-fix recommendations without implementation — pivoting to customer value.
**Action:** Create GH issue with full implementation sketch: explicit-trigger flow, POST endpoint,
conversation handoff state machine, Twilio/Resend notification handlers, 6 acceptance criteria,
~1.5-2 day estimate. Labels: customer-value, medium-effort, run-4.
**Impact:** Unlocks critical feature blocking trial-to-paid conversion across all 7 industry verticals.
Breaks meta loop by providing sprint entry point the human can start working on directly.
**Category:** customer_value

---

### Idea 3: Tag S-effort moratorium items as ai-ready for autopilot-issue-loop.yml
**Evidence:** autopilot-issue-loop.yml confirmed in .github/workflows/. 4 S-effort moratorium items
have pre-written implementation sketches. If loop picks them up, drops pending 6→2 without human
manual work. WEAKENED in run 20 debate (loop-running status uncertain). Run 21 evidence: zero
issue-to-pr-loop commits in last 14 days (git log confirms).
**Action:** Create GH issues for runs 7, 8, 14, 19 with `ai-ready` label so autopilot loop can
auto-implement the S-effort items.
**Impact:** Would drop pending from 6 to 2 without manual work — but only if loop is running.
**Category:** workflow

---

### Idea 4: Zapier API key plan_status enforcement
**Evidence:** GH #107 open 17+ days. backend/services/zapier_auth.py::_get_api_key_client resolves
API keys without checking plan_status — cancelled tenants with un-revoked keys bypass tier gate.
Parking lot ROI 2.5 (highest). First post-moratorium code fix candidate.
**Action:** Add plan_status IN ('active','trialing') filter to _get_api_key_client + regression test.
**Impact:** Prevents revenue leak via unpaid tier bypass. HIGH security.
**Category:** code_health/security
**⚠️ Moratorium protocol:** Requires pending ≤ 3. Currently pending = 6. Protocol forbids this.

---

### Idea 5: Custom automation templates (new customer value)
**Evidence:** customer-gaps.md: "Custom automation templates" = Medium priority Open gap. Birthday
messages, post-service follow-ups listed as missing across Salon + Dental + Lawyer verticals.
No GH issue exists. Not previously debated by subconscious.
**Action:** Create spec + GH issues for custom template builder (birthday automations, post-service
follow-ups, review request sequences per vertical).
**Impact:** Medium — expands automation suite, improves retention for existing tenants.
**Category:** customer_value
