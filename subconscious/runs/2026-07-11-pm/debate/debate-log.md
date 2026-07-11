# Debate Log — Run 89 (2026-07-11-pm)

## Top 3 Selected for Debate

1. Idea 2 — Referral Reward Activation Pre-Gate Diagnostic
2. Idea 1 — Post Day-2 Escalation Comment on GH #403
3. Idea 3 — Update GH #412 with PR #404 Booking Findings

---

## Round 1: Initial Verdicts

### Idea 2 — Referral Reward Pre-Gate Diagnostic
**FOR:** Migration 162 in prod. REFERRAL_REWARD_ENABLED=1 = single Railway env var. Zero engineering. Zero schema changes. Never previously recommended (parking lot since run 87, always beaten by booking chain). Referral programs deliver 3-5x CAC reduction in SaaS. 7 real leads = 7 potential referrers. If even one tenant shares their widget with a 10-person list, that's 10 new leads at $0 CAC. Asymmetric upside.

**AGAINST:** Unknown if referral reward UX is complete (reward redemption, fraud detection, email notifications for rewards). If activation causes a broken UX, it damages tenant trust. Human must verify UX completeness before flipping the var.

**VERDICT:** SURVIVES. The safety checklist in the GH issue body is the mitigation. Subconscious does not flip the var — it files a diagnostic issue for human review, same as GH #412. No risk of broken UX from a GH issue. Recommendation appropriately gates on human verification.

---

### Idea 1 — Day-2 Comment on GH #403
**FOR:** GH #403 has 0 comments. It blocks autopilot-issue-loop AND kb-autopopulate. Day-2 comment with quantified impact (40 queued issues, 67-day KB gap) raises urgency.

**AGAINST:** Step 9D already comments on GH #399 daily. Filing a second subconscious comment on a related issue creates noise. GH #403 body already documents the impact. Human reads issues — it's already visible. The unique value of this idea is additive, not categorical.

**VERDICT:** WEAKENED → Bonus Action. Not winner. Better executed as bonus action alongside winner, not as the primary recommendation.

---

### Idea 3 — Update GH #412 with PR #404 Findings
**FOR:** Narrows investigation for human. MTOptions + 914 Exterior confirmed bookable (Hypothesis B answered for 2/3). Human only needs to investigate Keys Koffee. Reduces cognitive load. Fast.

**AGAINST:** GH #412 had 0 comments = human hasn't looked at it yet. An update comment may be premature if the human hasn't even run the original queries. PR #404 commit message explains the fix but does not explicitly state booking_enabled=true for all tenants — it says "2 of 3 fully bookable" implying the booking flow works end-to-end, not necessarily that booking_enabled column = true (could be seeded hours + assumed enabled).

**VERDICT:** WEAKENED → Bonus Action. Valuable additive action after winner is executed. Not the primary recommendation given uncertainty about booking_enabled vs hours-only fix.

---

## Round 2: Winner Confirmation

**Idea 2 (Referral Reward)** vs. **Idea 1 (Day-2 Comment)** vs. **Idea 3 (GH #412 Update)**:

- Idea 2 is the only idea addressing a NEW revenue channel not previously activated. Booking funnel is largely resolved (2/3 tenants). GH #399/#403 pipeline escalation is handled by Step 9D. Referral rewards represent viral growth potential with zero additional development.
- Idea 1 is auxiliary. Best as bonus action.
- Idea 3 is useful clarification. Best as bonus action.

**Winner: Idea 2 — Referral Reward Activation Pre-Gate Diagnostic**

---

## Round 3: Stress Test (Fight-Me on Winner)

**Argument against Idea 2:**

"Migration 162 is in prod but has it been tested end-to-end? What does REFERRAL_REWARD_ENABLED=1 actually activate? Is there a reward redemption UI? What prevents abuse? Does Stripe integrate with referral payouts? Filing a GH issue that says 'flip this env var' without verifying the full UX path is irresponsible."

**Response:**

The GH issue is NOT a flip command. It is a diagnostic + activation checklist, same as GH #412. The issue body explicitly lists safety checklist items the human must verify before activation:
1. Confirm referral reward UI renders correctly (widget + dashboard)
2. Confirm reward redemption path (Stripe or credit mechanism)
3. Confirm referral tracking links working
4. Confirm notification emails sent on referral event
5. Test fraud prevention (same user cannot self-refer)

The recommendation is: "Review and activate if checklist passes." The human decides. This is exactly the same gate used for GH #412 ("run the SQL, review the result, then apply UPDATE if needed"). No autonomous activation.

**Verdict: Objection overruled.** GH issue with safety checklist is the correct mechanism.

---

## Bonus Actions (execute this run alongside winner)

1. **Comment on GH #412** (Idea 3 demoted): Post PR #404 findings — MTOptions 20 slots live, 914 Exterior 22 slots post-prod-bug-fix, Keys Koffee still needs tenant-provided hours. Narrows human's investigation scope.

2. **Comment on GH #403** (Idea 1 demoted): Day-2 escalation with quantified impact — 40 ai-ready issues stalled, kb-autopopulate 67 days degraded, Lead Source Analytics GH #409 queued.

---

## Ideas Killed

- Idea 4 (Booking Conversion Rate GH issue): loop stalled, issue would queue not execute.
- Idea 5 (G3 Voice Scope): not revenue-immediate vs referral reward.
