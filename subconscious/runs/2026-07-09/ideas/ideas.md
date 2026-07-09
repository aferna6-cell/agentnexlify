# Ideas — Run 84 (2026-07-09)

## Context
Run 84 mandate: verify Step 9D executed correctly; confirm whether issue-to-pr-loop opened PR for #385 or stalled; check kb-autopopulate.yml first run; revisit lead source analytics if pipeline healthy.

**Mandate findings:**
- Step 9D: VERIFIED — added by nightly e8b2ddc. Executed first time this run. Found 30 consecutive autopilot-issue-loop failures since 2026-07-04 (AUTOPILOT_GH_TOKEN expired). GH #399 filed. Comment added to #385.
- Issue-to-PR loop: CONFIRMED STALLED — 30 consecutive failures, AUTOPILOT_GH_TOKEN expired 2026-07-04.
- KB autopopulate.yml: VERIFIED SUCCESS — first run 2026-07-08T19:02:13Z. 63-day gap closed.
- Lead source analytics: DEFERRED — mandate condition not met (pipeline not healthy; loop stalled).

---

## Idea 1: Step 9E — Proactive Credential Rotation Tracking

**Category:** operational  
**Effort:** XS  
**Evidence:** 2026-07-04 credential event = AUTOPILOT_GH_TOKEN + brain connector GitHub PAT both expired same day. autopilot-issue-loop: 30 consecutive failures, 5 days down, all ai-ready issues stalled. Brain connector: 8+ consecutive days down. Both tokens likely created same date, expired together. Steps 9B/9C/9D are reactive. No proactive warning mechanism exists. 14-day advance warning = human has time to rotate before failure.

**Action:**
1. Create `ops/credential-rotation-schedule.md` — table of all CI secrets (AUTOPILOT_GH_TOKEN, brain connector GitHub PAT, SUPABASE_ACCESS_TOKEN) with last-rotation date and 90-day interval
2. Add Step 9E to `.claude/skills/nightly-commit-review/SKILL.md` — read schedule, compare last-rotation + 90 days vs today, file GH issue with `credential-rotation` label if any credential within 14 days of expiry

**Autonomous-executable:** YES — SKILL.md edit + ops file creation, same class as 9B/9C/9D  
**Impact:** Prevents next silent credential expiry event that kills two systems simultaneously

---

## Idea 2: Lead Source Analytics Dashboard

**Category:** customer_value  
**Effort:** S  
**Evidence:** customer-gaps.md: cross-industry, Low Effort, HIGH impact. `source` column exists on leads table (migration 122). Recharts installed. Run 82/83 parking lot. Mandate condition: "revisit if pipeline confirmed healthy." Pipeline NOT healthy (loop stalled, brain connector down, #399 and #394 unresolved). Mandate condition unmet.

**Action:** Add `/api/leads/source-analytics` endpoint + LeadSourceAnalytics.jsx dashboard page.

**Autonomous-executable:** NO — requires backend + frontend + human review  
**Impact:** Customer-facing analytics, clear need, blocked by mandate condition this run

---

## Idea 3: SMS Compliance Dashboard Direct Delivery

**Category:** customer_value  
**Effort:** S  
**Evidence:** GH #385 open since 2026-07-01, ai-ready label applied 2026-07-08, ai-ready for 25+ days total. Loop stalled 30 cycles. Paste-ready code exists in runs/2026-06-30-pm/winning-concept.md. But: root cause of stall is expired AUTOPILOT_GH_TOKEN (GH #399). Rotating the token unblocks the loop which then picks up #385 AND all other 29 stalled ai-ready issues automatically. Direct delivery is less efficient than fixing root cause.

**Action:** Rotate AUTOPILOT_GH_TOKEN (GH #399) to unblock loop → loop picks up #385 automatically.

**Autonomous-executable:** NO — credential rotation is human-required  
**Impact:** Unblocks 30 stalled ai-ready issues, not just #385

---

## Idea 4: INGESTION-LOG.md in Subconscious Phase 2

**Category:** operational  
**Effort:** S  
**Evidence:** brain/INGESTION-LOG.md exists, 5 consecutive failures, not read by Phase 2. Step 9C catches this after 3+ failures now. Overlap with existing monitoring is high. Diminishing returns vs Step 9E.

**Action:** Modify subconscious SKILL.md Phase 2 to read INGESTION-LOG.md directly.

**Autonomous-executable:** YES but lower priority  
**Impact:** Redundant with Step 9C. Low marginal value unless Step 9C fails.

---

## Idea 5: Dependabot + PR #387 Batch Merge

**Category:** operational (housekeeping)  
**Effort:** XS  
**Evidence:** Backlog from run 83: PRs #279 #281 #380 #381 #382 #383 #396 (7 Dependabot) + PR #387 (draft 7 days). Human merge action required. Not an improvement to the system itself.

**Action:** Human merges PR #387 + 7 Dependabot PRs.

**Autonomous-executable:** NO — merge decisions are human-required  
**Impact:** Security patches, dependency freshness. Low system improvement value.
