# Run 85 — Improvement Backlog (2026-07-09-pm)

## Active (approved for implementation)

| Item | Status | Owner |
|------|--------|-------|
| Lead Source Analytics Dashboard | **pending_approval** (this run's winner) | issue-to-pr-loop |
| Step 9E: Proactive credential rotation tracking | pending_autonomous (run 84 winner) | nightly-2026-07-10 |

---

## Parking Lot (next runs)

### Booking Flow Diagnosis on Real Tenants
**Priority:** HIGH (0 real bookings despite 7 leads — booking conversion = 0%)  
**Evidence:** Audit 2026-07-09 explicitly calls this out as a follow-up  
**Action when picked up:**
1. Query `booking_enabled` on MTOptions and 914 Exterior via Supabase MCP
2. Check if service types are configured
3. If `booking_enabled = false` on existing tenants: migration to backfill bookable-by-default (pattern from `3596009` commit — already done for new tenants, needs backfill for existing)
4. Tenant notification required before enabling booking on their behalf  
**Risk:** Medium (tenant notification required; can't silently enable features)

### Warm Lead Recovery Email Sequence
**Priority:** MEDIUM  
**Evidence:** 2 warm targets: Sunset Mobile Detailing, Niko's Consulting (abandoned free plan signups)  
**Action when picked up:**  
Use `/email-sequence` skill to author 3-email sequence for free-plan tenants with >0 leads and no upgrade in 30 days. Verify Resend domain auth before sending.  
**Blocker:** Email deliverability verification needed; risk of poor inbox placement on first send

### Wire Weekly Funnel Report to GitHub Actions
**Priority:** LOW  
**Evidence:** `scripts/daily/weekly_funnel_report.py` shipped in `3596009` (107 tests) but no GH Actions cron  
**Action when picked up:**  
1. Smoke test: `python scripts/daily/weekly_funnel_report.py` — must exit 0 clean  
2. If passes: create `.github/workflows/weekly-funnel-report.yml` (`cron: '0 8 * * 1'`)  
3. AUTONOMOUS-EXECUTABLE pattern: same as `kb-autopopulate.yml` (run 82)  
**Blocker:** Script must pass smoke test first (same pattern as check_project_invariants.py Item A)

### Stale "Item A" Cleanup in Nightly SKILL.md
**Priority:** XS (housekeeping)  
**Evidence:** Lines 67–79 reference check_project_invariants.py as "pending Check 10" — it was wired as Check 13 on 2026-06-17  
**Action:** Remove stale block; replace with status note. LOW-risk SKILL.md edit.  
**Owner:** Nightly runner (AUTONOMOUS-EXECUTABLE doc edit)

---

## Frozen / Rejected Ideas

| Idea | Status | Reason |
|------|--------|--------|
| AI-to-human handoff | FROZEN | governance.json frozen_ideas; not revisited without explicit unfreeze |
| Step 9E re-recommendation | ELIMINATED this run | Already pending_autonomous from run 84; governance loop violation |

---

## Open Questions for Next Run

1. Did nightly-2026-07-10 add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md`?
2. Was `ops/credential-rotation-schedule.md` created (Step 9E companion artifact)?
3. Did issue-to-pr-loop pick up the Lead Source Analytics GH issue within 24h?
4. Is `booking_enabled` false on MTOptions and 914 Exterior? (diagnostic needed)
5. Is the brain connector local cron (`refresh_connectors.py`) still failing? (SUPABASE_ACCESS_TOKEN and GitHub PAT rotation needed)
6. Zero signups in 16 days — is distribution the only constraint, or is there a UX funnel issue in the onboarding wizard?
