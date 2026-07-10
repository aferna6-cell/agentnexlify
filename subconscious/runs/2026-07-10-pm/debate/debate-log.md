# Debate Log — Run 87 (2026-07-10-pm)

## Top 3 Ideas Debated (ranked by impact × autonomy)

1. **Booking Enabled Audit** — customer_value, XS, AUTONOMOUS-EXECUTABLE
2. **Draft PR Triage** — workflow/code_health, XS, AUTONOMOUS-EXECUTABLE
3. **Referral Reward Pre-Gate Diagnostic** — operational, XS, AUTONOMOUS-EXECUTABLE

---

## Idea 1: Booking Enabled Audit

### Challenge
- Is the evidence strong? We don't actually KNOW booking_enabled=false for any real tenant. This is a hypothesis.
- 0e0ee00 description says "Booking on by default" — maybe it retroactively updated existing tenants?
- Even if booking_enabled is false, is that why 0 bookings? MTOptions has 4 leads but we don't know if they even tried to book.
- The automation pipeline is broken (GH #399). Nightly can still run Supabase MCP queries but filing GH issues requires GitHub API (also needs auth). Both credentials are expired. Can this actually execute?
- "Booking Enabled Audit" is diagnostic, not a fix. The actual fix still requires human action.

### Defense
- `0e0ee00` commit title is "Booking on by default + real SEO surface + last-call recovery email" and it lands in `onboarding.py`. The code explicitly sets `booking_enabled=True` in onboarding data seed — this runs during onboarding flow, not retroactively for existing tenants. The 3 real tenants predate this commit by weeks.
- Evidence is strong enough for a diagnostic: 7 leads, 0 bookings, feature shipped 2026-06-23 (17 days), known boolean flag. If booking is on and 0 bookings after 17 days, that's a different problem (but we'd know). If booking is off, that's a 1-line fix.
- On pipeline: Supabase MCP connects to the DB directly — it does NOT go through GitHub Actions. Nightly commit review uses MCP tools, not GitHub Actions. The expired tokens are GitHub Secrets for Actions workflows. Nightly can still query Supabase and create GH issues via `mcp__github__issue_write` (GitHub MCP, not Actions).
- AUTOPILOT_GH_TOKEN is for the autopilot-issue-loop workflow. The nightly-commit-review uses the GitHub MCP server directly. They are different auth paths.

### Verdict: **SURVIVES**
Evidence is strong. Implementation path is clear and does not depend on broken GitHub Actions. Query is XS effort. Even if booking_enabled is already true, the diagnostic confirms it and closes the question. Highest potential revenue impact of any idea this run.

---

## Idea 2: Draft PR Triage

### Challenge
- 10 stale PRs is a symptom of the broken autopilot loop, not an independent problem. Once GH #399 is fixed, the loop resumes.
- Adding nightly comments to stale PRs creates noise without resolving anything. Human doesn't need more GH notifications — they need credentials rotated.
- PR #325 (checkout conversion fix) should just be merged, not triaged. Adding a comment doesn't help.
- The governance.json already tracks pending items — adding PR triage on top creates duplication.
- Automation scope creep: nightly already does Steps 9A-9E + commit review. Adding PR triage inflates scope further.

### Defense
- Valid point: root cause is credential expiry, not PR age. Once autopilot is fixed, most PRs will be handled.
- However, PR #325 (Stripe Link kill + conversion funnel fix) is revenue-relevant and has been sitting 18+ days. It predates the automation outage.
- Nightly commenting is low-value noise vs. just recommending human merges 3 specific PRs.

### Verdict: **KILLED**
Root cause is automation outage, not PR management process. Triage creates noise without resolving the underlying block. Human attention is better spent on credential rotation (GH #399/#403). Demoted to parking lot as a post-fix housekeeping task.

---

## Idea 3: Referral Reward Pre-Gate Diagnostic

### Challenge
- Migration 162 check: nightly can read the migrations/ folder and grep for "162" — trivial. But this doesn't confirm it's APPLIED in prod. Applied ≠ file exists.
- Stripe staging smoke: requires a live Stripe API call. Nightly doesn't have Stripe credentials.
- The feature is already gated off (REFERRAL_REWARD_ENABLED=0). There's no urgency — this can wait until after the credential crisis is resolved.
- GH #407 already exists and captures the prerequisites. A second diagnostic would duplicate what the nightly comment system already handles via GH #407.
- Idea 3 is a "nice to have" check on a feature that's already safely gated. Not the highest leverage.

### Defense
- Migration file existence is a meaningful signal: if migrations/162_*.sql doesn't exist in the repo, Supabase never had the chance to apply it. File presence is a necessary (not sufficient) condition.
- REFERRAL_REWARD_ENABLED=0 means no customer is affected. The risk of this being wrong is zero. The reward of enabling it is non-trivial (growth channel).
- The diagnostic closes the human-verification loop: once both conditions auto-confirm, the flip is a 5-second env var change.

### Verdict: **WEAKENED → Parking Lot**
Good idea but wrong timing. The credential crisis is the higher priority and the automation pipeline can't reliably run additional checks until that's fixed. Defer to run 88 as a candidate when GH #399/#403 are resolved.

---

## Winner Selection

Idea 1 (Booking Enabled Audit) SURVIVES with strong evidence and a clear autonomous execution path.
Idea 2 (Draft PR Triage) KILLED — root cause is automation outage, not process.
Idea 3 (Referral Reward Diagnostic) WEAKENED — valid but wrong timing, parking lot.

**Winner: Booking Enabled Audit**
