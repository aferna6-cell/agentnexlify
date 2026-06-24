# Improvement Backlog — Run 65 (2026-06-24)

Ranked by priority. Not the winner this cycle; carry forward.

## 1. AI-to-Human Handoff PRD [NEXT INTERACTIVE SESSION]
**Source:** Idea 2, debate runner-up
**Why high priority:** "buildable backlog exhausted" signal (0dc4839); only Critical gap in customer-gaps.md; affects all 13 verticals; GoHighLevel already has this
**Action:** `/write-prd` + `/grill-me` in next interactive session → `specs/ai-human-handoff_spec.md`
**Trigger for run 66:** if no urgent regression, declare this the run 66 winner

## 2. In-Widget Referral Prompt Post-Conversion [WIDGET SPRINT]
**Source:** Idea 3
**Why:** Referral pipeline complete through #371; activation layer missing; post-conversion is highest-intent moment
**Blocked by:** None. Pipeline infrastructure ready.
**Action:** ~40 lines widget JS + 1 endpoint `/api/referrals/my-link` + byte-identical copy

## 3. Vercel Deploy Quota Optimization [OPS BACKLOG]
**Source:** Idea 4
**Why:** Quota exhausted after #369 blocked frontend deploys ~24h; recurring ops risk
**Action:** GitHub Actions path filter for `frontend/**` + `[skip vercel]` commit token

## 4. Vertical KB Seeding — Roofing, Home Cleaning, Veterinary [CONTENT SPRINT]
**Source:** Idea 5
**Why:** 3 new verticals (#367) with generic KB templates; vertical differentiation is the moat
**Action:** 3 KB files in `widget/knowledge-bases/`, ~150 lines each; no code changes

## Governance corrections applied this run
- GH #308: marked IMPLEMENTED (was pending_approval)
- GH #292/#293: marked IMPLEMENTED (was pending_approval)
- Moratorium: exited (both overrides resolved)
- Active direction for run 66: AI-to-human handoff PRD
