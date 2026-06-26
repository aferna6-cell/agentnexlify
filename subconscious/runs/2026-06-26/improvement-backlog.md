# Improvement Backlog — Run 68 (2026-06-26)

## Active (pending human approval/action)

### Run 67 (still pending — ESCALATED to run 68 mandate)
- **Direction:** Execute Run 65 Steps + Step 9B in interactive human session
- **Status:** pending
- **Autonomous:** NO (HUMAN-REQUIRED)
- **Blocker:** human must run 30-second terminal commands from winning-concept.md
- **Escalation:** Run 68 mandate fires — verbatim copy-paste commands provided

### Run 66 (still pending — superseded by run 68 mandate)
- **Direction:** Escalate run 65 delivery — add Step 9B to nightly-commit-review SKILL.md
- **Status:** pending
- **Autonomous:** YES (but blocked because check exits 1 — can't commit)
- **Note:** Step 9B now in run 68 winning-concept.md for human to apply with the fix

### Run 65 (still pending — superseded by run 68 mandate)
- **Direction:** Fix widget drift + em-dash violations
- **Status:** pending
- **Autonomous:** YES (but blocked because check exits 1 — can't commit)
- **Note:** verbatim commands in run 68 winning-concept.md

---

## Parking Lot (sequencing-blocked or lower priority)

### Run 69 Candidate — Plan-Name Guard Check 7
- **Direction:** Add Check 7 to check_project_invariants.py — assert chatbot + agent_os appear in all plan gates
- **Status:** parking_lot
- **Autonomous:** YES (after check exits 0)
- **Evidence:** GH #292/#293 — 6 plan gate dicts missing chatbot/agent_os for 7 days
- **Effort:** S (~20 lines Python)
- **Sequencing:** BLOCKED until runs 65/66/67 are implemented (check must exit 0)

### Run 70+ Candidate — KB Autopopulate Fix
- **Direction:** Replace agent-browser CLI with curl in scripts/daily/kb-autopopulate.sh
- **Status:** parking_lot
- **Autonomous:** YES
- **Evidence:** KB stale ~50 days. Last compile ~2026-05-05. New council articles not indexed.
- **Effort:** XS (~15 min)
- **Priority:** Lower than commit blocker; raise after check exits 0

### Run 70+ Candidate — OPS #2 GH Issue
- **Direction:** Create GH issue for 10DLC/A2P registration (code ready, business action needed)
- **Status:** parking_lot
- **Autonomous:** YES
- **Evidence:** council-fixes-register.md OPS #2 — missed-call text-back code ready, no tracking
- **Effort:** XS (~5 min)

### Deferred — email_sequences.py Split
- **Direction:** Factor backend/routers/email_sequences.py (1143 lines) into 3 modules
- **Status:** deferred
- **Autonomous:** NO (multi-hour refactor, plan approval required)
- **Evidence:** Rule 9 violation (>600 lines); god class compounds bug blast radius
- **Effort:** M (~2 hours)
- **Priority:** Low; raise when active direction count drops below 2

### Deferred — Home.jsx Split
- **Direction:** Factor frontend/src/pages/Home.jsx (1006 lines)
- **Status:** deferred
- **Autonomous:** NO
- **Evidence:** Rule 9 violation; noted in council audit
- **Effort:** M (~2 hours)
- **Priority:** Low; raise together with email_sequences.py split

---

## Implemented This Cycle (last 3 days)

Council sprint (2026-06-25): 9 fixes shipped.
- TCPA SMS compliance (sms_compliance.py, migration 160, quiet hours, opt-out)
- Lead temperature badge (AI scoring + visual indicator)
- Integration health banner (Stripe/Twilio/Resend status)
- Record audit trail (immutable action log)
- No-website onboarding (onboarding wizard tolerates missing website)
- Outcome-focused copy (widget greeting + landing page)
- council-onboarding-integration-2026-06-25 article (brain/)
- Pre-commit Check 13 added (wired check_project_invariants.py as FAIL+BLOCK)

---

## Moratorium Status

- **Active:** YES
- **Current true_pending:** ~6 (runs 65, 66, 67 pending + run 69+ parking lot)
- **Exit condition:** pending_approvals ≤ 2
- **Path to exit:** Human runs 30-second fix → 65/66/67 clear → true_pending drops to ~3 → run 69 (Check 7) executes autonomously → true_pending drops to ~2 → moratorium exits

---

## ROI Tracking

| Run | Idea | Status | ROI |
|-----|------|--------|-----|
| 65 | Widget drift + em-dash fix | pending | blocked commits = infinite ROI if unblocked |
| 66 | Step 9B for nightly scope | pending | prevents recurrence |
| 67 | 30-sec mandate execution | pending | escalation attempt |
| 68 | Verbatim terminal commands | pending | lowest-friction delivery attempt yet |
| 69 | Plan-name guard Check 7 | parking_lot | prevents $10k+ repricing incident |

Parking lot ROI: 1.8 (runs 53-67 average). Main drag: runs 65-68 unimplemented.
