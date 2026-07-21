# Debate Log — Run 101 (2026-07-21)

Top 3 ideas ranked by impact. Each gets challenge-and-defend cycle.

---

## Idea 1: Fix Step 9F execution gap

### Challenge
- **Is the evidence strong enough?** The nightly log has 105 lines and no "Step 9F:" text. But could Step 9F have fired and written to a DIFFERENT log? Or fired but been silently suppressed?
- **Is this the highest-leverage thing?** KB has been stale 8 days and no customer-facing degradation has been reported. The KB feeds the widget's knowledge base — if tenants aren't using the KB-backed widget, the staleness hurts nobody right now.
- **What could go wrong?** Adding Step 9F to the bash script creates a dependency on `knowledge-base/log.md` format parsing. If the date format ever changes, the bash check false-positives.
- **Has something similar been tried?** Yes — Step 9F was added to SKILL.md in runs 97-99. The mechanism exists but doesn't fire. Are we solving the right layer?
- **Too similar to current active direction?** No — run 100 winner was mcp_client.py wiring. This is a new gap.

### Defend
- `scripts/daily/nightly-commit-review.sh` runs the automated nightly, not SKILL.md. SKILL.md is a guide for when Claude Code runs it interactively. The automated bash script was never updated with Step 9F logic. This explains the gap exactly: subconscious added the SKILL.md step, but the CRON runs the bash script, not the SKILL.md.
- Evidence strength: nightly log 2026-07-21 has 45 commits reviewed, full section headers for triage/action-required/invariants/auto-fixes/stats. If Step 9F had fired, it would appear here. Absence is evidence of absence.
- Leverage: the KB is the backbone of vertical knowledge-base moat (CLAUDE.md §Competitive positioning). An 8-day gap means tenants on KB-backed widgets get stale answers. If KB staleness hits 30 days, customer churn risk rises.
- Bash format risk: log.md last-line date format has been stable for 100+ runs. Read the last line, grep for YYYY-MM-DD pattern — robust enough for a monitoring script.

### Verdict: **SURVIVES**
Evidence confirmed (nightly log is exhaustive, Step 9F absent). Leverage is real (KB is the competitive moat). Fix is a single bash block addition to `scripts/daily/nightly-commit-review.sh`. Low implementation risk.

---

## Idea 2: Add referral analytics to LeadAttributionPage

### Challenge
- **Is the evidence strong enough?** GH #413 closed yesterday — feature just went live. Referral data may be near-zero (no leads yet referred). Building a dashboard for empty data is premature.
- **Is this highest-leverage?** The referral system is live but we don't know if referrals are happening. Building analytics before any data exists means the dashboard shows zeros until organic referrals arrive.
- **What could go wrong?** If `referral_code` column doesn't exist in current migration state, the endpoint 422s on every request.
- **Has something similar been tried?** `customer-gaps.md` has had "lead source analytics" as open since cycle 122. Multiple runs have noted it. It keeps getting deprioritized.
- **Too similar to current active direction?** No conflict with run 100 winner.

### Defend
- Referral feature activating with zero analytics is exactly backward — you need the dashboard BEFORE data arrives to catch day-1 performance. Retrofitting analytics after 2 weeks means the first 2 weeks of referral data is opaque.
- `referral_code` is on the leads table (it's a capture field from the widget flow, populated at lead submission). The column exists — it was part of the referral implementation. Verify with a quick grep.
- "Lead source analytics" has been open for 30+ cycles, which means it's either low-effort-high-value (should have been done) or blocked by something. customer-gaps.md says "source column exists, no dashboard visualization" = pure frontend gap. Low effort.
- The GH #413 activation by the human is a signal that the product owner is investing in referrals. Analytics support is the obvious next step.

### Verdict: **SURVIVES (WEAKENED)**
Referral analytics is real and timely, but the "referral data is empty" objection has merit. Weakened from HIGH to MEDIUM-HIGH confidence. The idea survives but should be scoped to a minimal implementation: one chart showing referral_code distribution with a "no data yet" empty state, rather than full conversion funnel analytics.

---

## Idea 4: Post GH #399 resolution runbook as comment

### Challenge
- **Is the evidence strong enough?** Day 17, 30 issues blocked. But subconscious has flagged this 5+ times. If the human hasn't fixed it in 17 days, posting a runbook comment might not change anything either.
- **Is this highest-leverage?** The constraint is not knowledge (the human probably knows it's a token rotation). The constraint might be willingness or prioritization. A comment doesn't change prioritization.
- **What could go wrong?** The runbook comment is permanent and visible on GH #399. If token rotation requires org-level GitHub admin access (not just personal), the steps in the comment would be wrong and misleading.
- **Has something similar been tried?** Subconscious has been MENTIONING this 5+ runs. The distinction is actually WRITING the comment with exact steps vs. just flagging it in governance.

### Defend
- The evidence for posting the runbook is additive: it takes 30 seconds (one MCP call), has zero downside (comment can be ignored), and may reduce human friction enough to tip the decision. The human sees GH #399 in their issue list — a concrete "here are the 3 exact steps" comment changes the action cost from "I need to look this up" to "I just need to click."
- Token rotation typically does NOT require org admin — a PAT with `repo` scope is sufficient for the autopilot-loop (it reads issues and creates PRs). Caveat: if the GitHub account is an org with SSO enforcement, the PAT needs SSO authorization too. Include that caveat in the comment.
- 30 ai-ready issues blocked for 17 days represents ~17 person-days of autonomous development capacity lost. Even a 10% chance this comment tips the human to act justifies writing it.

### Verdict: **SURVIVES**
The action is cheap (zero code changes, one MCP call), the downside is minimal, and the upside is unblocking the entire autonomous development pipeline. Evidence strong (17 days, 30 issues, confirmed root cause). The objection about "human won't act" is real but the cost of trying is near zero.

---

## Ranking for Synthesis

| Idea | Verdict | Confidence | Implementation Cost |
|------|---------|------------|---------------------|
| 1 — Fix Step 9F execution gap | SURVIVES | HIGH | XS — add bash block to nightly-commit-review.sh |
| 4 — Post GH #399 runbook comment | SURVIVES | HIGH | XS — one mcp__github__add_issue_comment call |
| 2 — Referral analytics dashboard | SURVIVES (WEAKENED) | MEDIUM | M — new frontend page + backend endpoint |

Ideas 3 (migration monitoring) and 5 (vault-status endpoint) not in top 3 — excluded from debate. Both survive as parking lot candidates.
