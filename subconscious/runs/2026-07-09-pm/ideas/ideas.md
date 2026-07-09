# Run 85 — Candidate Ideas (2026-07-09-pm)

## Evidence Sources
- git log --since="3 days ago": 5 substantive commits (dfa8201, 3596009, 0e0ee00, 3b30505, e8b2ddc)
- Audit: `audits/audit-post-deploy-measurement-2026-07-09.md`
- Customer gaps: `docs/dev-knowledge/customer-gaps.md`
- Governance mandate: `subconscious/state/governance.json` run_85_mandate
- Brain connector: `brain/INGESTION-LOG.md` (9+ consecutive failures)
- Memory: runs 80–84 (Steps 9C, 9D, 9E pipeline + GH #399 fix)

---

## Idea 1 — Lead Source Analytics Dashboard

**Category:** customer_value  
**Effort:** L  
**Confidence:** HIGH

**Evidence:**
- `customer-gaps.md` explicitly notes "source column exists in leads table, no dashboard visualization" — open since run 2 (83-run parking lot)
- 7 real leads captured post-deploy with unknown acquisition sources; MTOptions is 4/7 but UTM/source origin unknown
- GH #399 (autopilot-issue-loop disabled 30 days) fixed by dfa8201 — issue-to-pr-loop can now pick up new ai-ready issues
- Recharts already installed in `frontend/` — zero new dep
- `run_85_mandate`: "revisit lead source analytics dashboard as run 85 winner" if pipeline confirmed healthy

**Action:** Create GH issue (ai-ready label) to:
1. Add `GET /api/leads/source-breakdown` endpoint — `GROUP BY source` on `leads` WHERE `client_id = X`
2. Add BarChart in `frontend/src/pages/AnalyticsPage.jsx` showing source attribution
3. Link from leads table (click-through filter)

**Invariants enforced:** `client_id` not `tenant_id`; no `__future__` annotations; RLS-aware; auth required

---

## Idea 2 — Warm Lead Recovery Email Sequence

**Category:** customer_value  
**Effort:** M  
**Confidence:** MEDIUM

**Evidence:**
- Audit finding: 2 warm recovery targets identified — Sunset Mobile Detailing, Niko's Consulting (abandoned free plan signups)
- `0e0ee00` shipped `last-call recovery email` logic for widget leads, but NOT for abandoned signups
- `/email-sequence` skill exists; no recovery campaign currently running
- Zero new signups in 16 days — recovery of 2 abandoned signups = 67% increase in non-demo external tenants

**Action:** Use `/email-sequence` skill to author 3-email recovery sequence targeting free-plan tenants with >0 leads captured but no upgrade in 30 days. GH issue with copy + trigger logic.

**Blocker:** Email deliverability setup (Resend domain auth) must be verified before sending; risk of poor deliverability on cold sequence.

---

## Idea 3 — Booking Flow Diagnosis on Real Tenants

**Category:** operational  
**Effort:** S  
**Confidence:** MEDIUM

**Evidence:**
- Audit: "7 real leads with 0 booking offers accepted is either a prompt problem, a booking-enabled config problem, or a UX problem"
- All 9 prod appointments are demo-seeded — real booking conversion = 0%
- `booking_enabled` may be off on MTOptions/914 Exterior; no service types configured
- `3596009` shipped bookable-by-default hours seeding — but only for NEW tenants; existing tenants not backfilled

**Action:** Query `SELECT client_id, booking_enabled, service_types FROM tenants WHERE client_id IN (mtOptions_id, 914_exterior_id)` via Supabase MCP. If `booking_enabled = false` → create GH issue to backfill existing tenants with bookable-by-default migration.

**Risk:** Enabling booking on existing tenants without their knowledge = UX surprise. Needs tenant notification.

---

## Idea 4 — Stale "Item A" Cleanup in Nightly SKILL.md

**Category:** code_health  
**Effort:** XS  
**Confidence:** HIGH

**Evidence:**
- SKILL.md lines 67–79 contain stale Item A: "Wire check_project_invariants.py as pre-commit Check 10. Status: pending_autonomous. Blocked 2026-06-01: script fails on em-dash violations"
- check_project_invariants.py was wired as Check 13 on 2026-06-17 — the Item A text is now dead
- Stale text could confuse the nightly runner into re-wiring it (duplicate hook check)
- This is a LOW-risk doc edit — no code behavior change

**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` lines 67–79 to remove the stale Item A block and replace with "Current pending item: Step 9E (run 84 winner) — see Step 9E below once nightly-2026-07-10 adds it." Commit as `docs(nightly): remove stale Item A reference [auto-nightly-YYYY-MM-DD]`.

**Note:** AUTONOMOUS-EXECUTABLE candidate (LOW-risk doc edit within SKILL.md).

---

## Idea 5 — Wire Weekly Funnel Report to GitHub Actions Scheduler

**Category:** operational  
**Effort:** S  
**Confidence:** MEDIUM

**Evidence:**
- `3596009` shipped `scripts/daily/weekly_funnel_report.py` (107 tests) but no GH Actions schedule
- Weekly funnel report exists as code but never runs
- run_85_mandate (implicit): "Wire weekly funnel report" was noted as parking lot item
- Pattern precedent: `kb-autopopulate.yml` (run 82) = same XS effort, same autonomous pipeline

**Action:** Create `.github/workflows/weekly-funnel-report.yml` running `python scripts/daily/weekly_funnel_report.py` on `cron: '0 8 * * 1'` (Monday 8 AM). AUTONOMOUS-EXECUTABLE if winning-concept has inline file content.

**Risk:** Script must be tested clean before wiring (same pattern as check_project_invariants.py — if script exits non-zero, blocked).
