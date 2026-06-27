# Improvement Backlog — Run 69 (2026-06-27)

## Active (In Progress)

### WIDGET-DRIFT — Pre-Commit Blocked (CRITICAL, runs 65-69)
- **Status:** Winning concept: Step 9B widget-sync exception + hard run 70 deadline
- **Blocker:** Human must approve SKILL.md amendment before nightly runs (before 2:37 AM 2026-06-28)
- **Fallback:** Manual `cp widget/agentnexlify-widget.js landing-page-v2/widget/agentnexlify-widget.js` + commit
- **Mandate:** If check still exits 1 at run 70 → URGENT human task, subconscious retires topic

---

## Ready (Sequencing-Blocked on Widget Drift Fix)

### PLAN-NAME-GUARD — Invariant Check Expansion (Code Health, Low Effort)
- Add `foundation` and `operations` to `check_project_invariants.py` Invariant #3 (retired plan names)
- Currently checks: `lead_stage`, `service_interest` (schema fields)
- Add: `foundation`, `operations` (billing tier names, retired per CLAUDE.md)
- 1 file change, 2 string additions, no migration needed
- **Blocked by:** Check 13 (pre-commit). Unblocks when widget drift resolves.

### PRE-COMMIT-AUTOSYNC — check_project_invariants.py --fix flag (Code Health, Medium)
- Add `--fix` flag to widget byte-sync invariant
- Eliminates the cp delivery problem permanently for future drifts
- `shutil.copy2(src, dst)` on detected drift when `--fix` passed
- **Blocked by:** Check 13. Also requires code review on auto-fix pre-commit pattern.
- **Risk:** auto-fix in pre-commit can be surprising; needs explicit opt-in flag

---

## Backlog (Approved for Next Implementation Sprint)

### SMS-COMPLIANCE-DASHBOARD — Tenant TCPA Visibility (Customer Value, Medium)
- Backend: `/api/sms-compliance` endpoint querying `leads.sms_opted_out` + consent timestamps
- Frontend: `SMSComplianceDashboard.jsx` page with Recharts trend lines
- Metrics: opt-out rate, opt-in count, blocked contacts, compliance score (0-100)
- Export: one-click CSV of opted-out contacts for audit
- **Dependency:** Council fix #1 (landed 2026-06-24) added TCPA backend enforcement — no new migration needed
- **Priority:** High — TCPA violations $500-$1,500/day per violation; GoHighLevel has this feature

### AI-HUMAN-HANDOFF — Critical Cross-Industry Gap (Customer Value, High Effort)
- Widget: "Talk to a person" intent detection → handoff signal
- Backend: `conversations.escalated_to_human_at` field + staff notification (SMS/email)
- Frontend: Inbox view showing escalated conversations for staff reply
- **Source:** `docs/dev-knowledge/customer-gaps.md` — marked Critical, all industries
- **Priority:** High — differentiated from competitor AI receptionists

### LEAD-SOURCE-ANALYTICS — Traffic Attribution (Customer Value, Low Effort)
- Track `utm_source`, `utm_medium`, `utm_campaign` on widget load
- Store on `leads.source_metadata` (JSONB)
- Surface in dashboard as "Where are leads coming from?" chart
- **Source:** `docs/dev-knowledge/customer-gaps.md`
- **Priority:** Medium

---

## Frozen (Mandate/Governance)

### STEP-9B-PREVIOUS-ADDITIONS — runs 66 instruction
- Step 9B (added run 66) already in SKILL.md and proven working (ffefe61)
- Run 69 winner adds widget-sync exception to Step 9B scope

---

## Rejected (Do Not Revisit)

- `tenant_id` → `client_id` rename: **production invariant, never rename** (CLAUDE.md Critical Rule #1)
- `lead_stage` field: **never existed** (CLAUDE.md Critical Rule #2)  
- `service_interest` field: **never existed** (CLAUDE.md Critical Rule #3)
- `foundation` plan tier: **retired, never use** (CLAUDE.md plan names)
- `operations` plan tier: **retired, never use** (CLAUDE.md plan names)
- `from __future__ import annotations` in FastAPI: **pre-commit hard block, invariant #1**
