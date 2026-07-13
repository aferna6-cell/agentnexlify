# Run 91 Ideas — 2026-07-13

Generated from: nightly log (2026-07-13), GH issues #399/#403/#412/#413, referral_reward.py audit, governance run_91_mandate

---

## Idea 1 — File Keys Koffee Dedicated Booking Hours GH Issue

**Category:** autonomous-executable | revenue | human-action-required
**Evidence:** Day 20 since launch (2026-06-23). GH #412 open since 2026-07-11 with no human SQL response. Run_91_mandate item 5: "Keys Koffee hours — if 21+ days without action, escalate as separate GH issue." Day 20 triggers pre-emptive filing (day 21 is tomorrow).
**Action:** `mcp__github__issue_write` — file separate issue focused on Keys Koffee booking hours (distinct from general diagnostic #412). Label: human-action-required, revenue. Estimated fix: 5 min.
**Impact:** Unblocks the third tenant from receiving any bookings. The other two tenants (MTOptions, 914 Exterior) are confirmed bookable. Keys Koffee has been receiving widget traffic but cannot convert.
**Effort:** LOW (autonomous file)

---

## Idea 2 — Pre-Answer GH #413 Referral Checklist Items 3/5/8 from Code

**Category:** autonomous-executable | revenue | human-burden-reduction
**Evidence:** GH #413 OPEN 2d, 0 human engagement after run 90 comment. 5 UX checklist items remain (items 3, 5, 8, 9, 10). referral_reward.py audit (run 91 Phase 2) reveals: item 3 (reward redemption path) = Stripe $20 balance credit fires on first paid invoice; item 5 (self-referral prevention) = built into `_resolve_referrer()` — returns None for both channels; item 8 (qualification period) = "first paid invoice" is the natural gate. These 3 items require NO human research — code already answers them.
**Action:** `mcp__github__add_issue_comment` on GH #413 with code-sourced answers to items 3, 5, 8. Reduces human checklist burden from 5 remaining to 2 (items 9 and 10).
**Impact:** Cuts human effort to activate referral program by 60%. Referral launch unblocked for 2 of 5 remaining items without any human investigation.
**Effort:** LOW (autonomous comment)

---

## Idea 3 — Add Step 9F to Nightly SKILL.md: Booking Health Check

**Category:** code-change | monitoring | booking
**Evidence:** 20 days / 0 real bookings. Nightly review (Steps 9A-9E) monitors healthz, brain connectors, issue-to-pr-loop, credential rotation. No step monitors booking health. Keys Koffee missing hours illustrates a gap: a simple check against Supabase appointments could surface "0 bookings in N days" nightly.
**Action:** Edit `.claude/skills/nightly-commit-review/SKILL.md` — add Step 9F querying Supabase for bookings in last 24h. Log count; alert if 0 for 7+ consecutive days.
**Impact:** Makes booking drought self-reporting. Reduces reliance on subconscious to manually track days-since-booking.
**Effort:** MEDIUM (Supabase MCP unavailable in headless sessions — step would only fire in interactive sessions; limited value)

---

## Idea 4 — Booking Conversion End-to-End Test Script

**Category:** code-change | booking | diagnostic
**Evidence:** 20 days / 0 bookings. Two tenants confirmed bookable (MTOptions, 914 Exterior). Unclear whether widget booking flow has a functional regression or traffic simply hasn't converted. No E2E test exists for the booking path.
**Action:** Write `scripts/test_booking_flow.py` — simulates widget → booking API → appointment confirmation for a known tenant. Run locally + in CI.
**Impact:** Definitively answers "is the booking flow broken?" vs "is conversion just low?" Eliminates diagnostic ambiguity.
**Effort:** HIGH (multi-file, requires Playwright or httpx, needs real tenant data)

---

## Idea 5 — Day-9 Quantified Opportunity Cost Comment on GH #399 + #403

**Category:** autonomous-executable | escalation | urgency
**Evidence:** GH #399 (AUTOPILOT_GH_TOKEN) — Day 9, 40 ai-ready issues × 45 min = 30h queued dev time blocked. GH #403 (ANTHROPIC_API_KEY) — Day 9, blocks autopilot + KB autopopulate + 3 other systems. Last escalation comments were Days 7-8. No human action.
**Action:** Post Day-9 cost summary comments on both issues. Frame as: "9 days × 30h queued work = $X in delayed shipping; KB dark 70+ days."
**Impact:** Increases urgency signal. Previous comments posted Days 7/8 with no response; Day 9 framing with cumulative cost may trigger action.
**Effort:** LOW (autonomous comment ×2)
