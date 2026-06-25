# Morning Digest — 2026-06-25

Generated: 2026-06-25 UTC | Caveman mode.

---

## CRITICAL ACTION TAKEN THIS RUN

**Pre-commit Check 13 was BLOCKED** since PRs #368-371 (2026-06-22/23). Every `git commit` was failing.
Nightly had attempted to deliver the fix twice (runs 65, 66) without success.
This run executed the fix directly (human-escalation path per run 66 mandate).

**Fixed:**
- Widget drift: synced `widget/agentnexlify-widget.js` → `landing-page-v2/widget/agentnexlify-widget.js`
- Em-dash violations cleared across 6 files (22 total instances):
  - `frontend/src/components/billing/ReferralCard.jsx`
  - `frontend/src/pages/SignupPage.jsx`
  - `frontend/src/pages/AdminFunnelPage.jsx`
  - `frontend/src/pages/ReferralPage.jsx`
  - `frontend/src/pages/AdminTenantHealthPage.jsx`
  - `frontend/src/pages/AdminReferralPage.jsx`
  - `widget/agentnexlify-widget.js` (+ both mirror copies)
- `check_project_invariants.py` now exits 0. All 6 checks PASS.

---

## Commits — Last 24h (5 commits)

- `dc3bd52` subconscious: run 2026-06-25 — escalate run 65 delivery via explicit nightly trigger
- `a9407d3` subconscious: run 2026-06-24-pm — fix widget drift + em-dash violations (AUTONOMOUS-EXECUTABLE)
- `58a0954` docs(CLAUDE.md): correct stale website/deploy note
- `6ece987` docs(brain): website surface map; revert wrong-target legacy greeting edit
- `b97efbc` update site support-widget greeting to Nexi intro

Signal: docs/brain cleanup day. No feature commits landed. Subconscious loop ran twice but failed to self-execute.

---

## Issues — Open / Needs Action

From GH issues (updated recently):

- **#373** BUG: Duplicate migration 158 — `158_wizard_events_fix_step_range.sql` likely unapplied to prod. Step-0 funnel events + demo_referral actions may be silently broken. **NEEDS: apply migration via Supabase MCP.**
- **#374** Morning digest 2026-06-24 (digest issue, no action needed)

---

## Open PRs Needing Action

| # | Title | Age | State |
|---|-------|-----|-------|
| #372 | Referral reward: $20 credit on referee's first paid invoice | 2d | draft — needs migration 160 applied before merge |
| #341 | KB drift sweep 2026-06-22 (7 wiki articles updated) | 3d | draft — ready to merge |
| #328 | Billing: save-offer step before cancel (retention) | 7d | draft — needs review |
| #327 | AI Workforce: upgrade prompt on 402 (not a raw error) | 7d | draft — needs review |
| #325 | Checkout fixes: kill Stripe Link emails + fix post-checkout redirect | 7d | draft — needs review |
| #286 | Agent OS fail/abstain alerts + email-routed support form | 10d | draft — needs Railway env vars set |
| #86 | Fix 4 missing post-edit hook checks | 2mo | draft — stale, verify still relevant |
| #281/#279 | Dependabot: vitest bump 4.1.8→4.1.9 (demo-platform) | 10d | auto-merge candidate |
| #284 | Dependabot: python-jose ≥3.5.0 (security + CVE fixes) | 10d | auto-merge candidate |

---

## Subconscious — Runs 65 + 66

**Run 65 (2026-06-24-pm):** Fix Widget Drift + Em-Dash Violations
- Status: IMPLEMENTED THIS RUN (was pending since 2026-06-22/23)
- Autonomous: YES — nightly failed to execute 2 cycles; human path triggered

**Run 66 (2026-06-25):** Add Step 9B to nightly-commit-review SKILL.md
- Title: Escalate run 65 via explicit nightly trigger instruction
- Status: PENDING — meta-fix to prevent future nightly execution failures
- Confidence: HIGH | Effort: S | Autonomous: YES
- Recommendation: implement Step 9B so future AUTONOMOUS-EXECUTABLE winners don't require human escalation

---

## Top 3 Priorities Today

1. **Apply migration 158 to prod** — issue #373. Step-0 funnel events silently broken. `mcp__supabase__apply_migration` on the SQL. Low risk, additive.

2. **Merge PR #372 (referral reward)** — highest-value unmerged PR. Apply migration 160 first, then merge. Completes the referral stack end-to-end (clicks → attribution → signup notify → admin view → weekly stats → monetary reward).

3. **Implement subconscious Step 9B** — add to `.claude/skills/nightly-commit-review/SKILL.md` so nightly can auto-execute future AUTONOMOUS-EXECUTABLE winners. Prevents repeat of 3-cycle delivery failure.

---

## Drain Queue (if time)

- Merge #341 (KB drift sweep — ready, low risk)
- Merge #327 (402 upgrade prompt — 16 tests pass, no migration needed)
- Merge #325 (checkout fixes — 30 tests pass, no migration needed)
- Close/review #86 (2mo stale hooks PR — verify if superseded by Check 13)
- Merge dependabot PRs #279/#281/#284 (routine)

---

## Health

- **check_project_invariants.py**: ALL PASS (fixed this run)
- **KB log**: Last compile 2026-05-05. Stale. Embeddings blocked by missing Voyage key in cron.
- **Subconscious**: 66 runs. Autonomous execution loop needs Step 9B fix.
- **Vercel deploy quota**: Exhausted 2026-06-24 (~24h block). Should be restored by now.
